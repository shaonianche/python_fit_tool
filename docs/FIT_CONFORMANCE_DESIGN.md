# Garmin FIT Strict Conformance Design

## 1. Objective

The target is full conformance with the published Garmin FIT protocol and the
bundled Global FIT Profile, not merely successful decoding of common Activity
files.

For this project, "strict conformance" has four independently verifiable
dimensions:

1. **Wire conformance**: every legal FIT file structure can be decoded and every
   encoded byte sequence follows the FIT binary protocol.
2. **Profile conformance**: fields, subfields, components, accumulated values,
   invalid values, developer fields, and native overrides follow the bundled
   `Profile.xlsx`.
3. **File-type conformance**: Activity, Workout, Course, and other standard file
   types follow Garmin's required-message and ordering rules.
4. **Forward-compatible preservation**: unknown messages and fields can be
   retained byte-for-byte even when the local Profile does not understand them.

Passing one dimension must not be reported as passing all four.

The conformance target is the Garmin FIT Protocol documentation and the exact
`Profile.xlsx` version committed under `fit_tool/gen/`. The current repository
uses Profile `21.205.0`.

Official references:

- <https://developer.garmin.com/fit/protocol/>
- <https://developer.garmin.com/fit/file-types/>
- <https://developer.garmin.com/fit/fitcsvtool/>
- <https://github.com/garmin/fit-sdk-tools>

## 2. Non-goals

- Reproducing undocumented Garmin Connect acceptance heuristics.
- Repairing corrupt FIT files in the strict decoder. Repair belongs in a
  separate, explicitly permissive API.
- Treating every best-practice recommendation as a wire-format error.
- Replacing the generated, typed message classes as the ergonomic public API.

## 3. Conformance levels

Validation must report a level and must not collapse all findings into a single
boolean.

| Level | Scope | Example failure |
| --- | --- | --- |
| `WIRE` | Header, records, definitions, base types, sizes, CRC, chaining | Data record without a definition |
| `PROFILE` | Global message and field semantics | Wrong base type for a known native field |
| `FILE_TYPE` | Required messages and ordering | Activity file without a `file_id` message |
| `PRESERVATION` | Lossless unknown-data round-trip | Unknown field discarded during rewrite |

Each finding has a severity:

- `ERROR`: violates a MUST requirement at the selected level.
- `WARNING`: violates a Garmin best practice or loses semantic information.
- `INFO`: legal but non-canonical representation.

Proposed API:

```python
report = document.validate(
    levels={
        ConformanceLevel.WIRE,
        ConformanceLevel.PROFILE,
        ConformanceLevel.FILE_TYPE,
        ConformanceLevel.PRESERVATION,
    }
)
report.raise_for_errors()
```

## 4. Architectural principle: separate wire data from semantic projection

The current model constructs generated `DataMessage` objects while bytes are
being consumed. That makes unknown-field preservation, compressed timestamps,
components, and chained files difficult.

The new architecture has two layers:

```text
bytes / stream
    |
    v
WireDecoder  --->  FitDocument / FitSegment / RawRecord
                           |
                           v
                    ProfileDecoder
                           |
                           v
              DataMessage / generated classes
```

The wire layer is authoritative for byte layout. The profile layer is a
projection that can be regenerated without destroying unknown wire data.

### 4.1 Proposed package boundaries

```text
fit_tool/
├── wire/
│   ├── model.py          # Raw headers, records, segments, and documents
│   ├── decoder.py        # Stateful binary decoder
│   ├── encoder.py        # Preservation and canonical encoders
│   ├── base_type.py      # Exact FIT base-type codecs and invalid bits
│   ├── timestamp.py      # Compressed timestamp state and rollover
│   └── crc.py
├── profile_runtime/
│   ├── projector.py      # Raw record -> generated/semantic message
│   ├── subfields.py
│   ├── components.py
│   └── developer.py
├── validation/
│   ├── report.py
│   ├── wire.py
│   ├── profile.py
│   └── file_types/
├── profile/              # Generated classes remain generated
└── compatibility.py      # Existing FitFile/Record facade
```

Dependency direction is one-way:

```text
wire <- profile_runtime <- public compatibility API
  ^             ^
  └── validation┘
```

The wire package must not import generated message classes. This keeps binary
correctness independent of the bundled Profile version.

### 4.2 Wire model

```text
FitDocument
└── segments: list[FitSegment]
    ├── header: RawFileHeader
    ├── records: list[RawRecord]
    │   ├── RawDefinitionRecord
    │   └── RawDataRecord
    ├── stored_crc: int
    └── calculated_crc: int
```

Every raw object retains:

- its exact source byte range;
- the parsed structural values;
- any unknown or extension bytes;
- a dirty flag;
- diagnostics associated with that byte range.

An untouched document encoded in preservation mode must produce the exact input
bytes, including unknown fields, header extensions, compressed headers, and
chained segments.

### 4.3 Semantic model

The existing generated message classes remain the high-level API. A semantic
message references its source `RawDataRecord` and contains `FieldValue` objects:

```text
FieldValue
├── raw_bytes
├── raw_values
├── decoded_values
├── validity
├── source          # native, developer, component, or synthetic timestamp
└── dirty
```

Unknown fields in a known message are represented as `UnknownFieldValue`, not
discarded. Unknown global messages continue to use `GenericMessage`.

### 4.4 Key architecture decisions

1. **Raw bytes are the preservation authority.** Decoded Python values are not
   sufficient to reproduce NaN payloads, unknown fields, compressed headers, or
   header extensions.
2. **Definitions are immutable snapshots.** Reusing a mutable definition object
   would reinterpret earlier records after a local message ID is redefined.
3. **Strict validation and repair are separate operations.** A strict encoder
   must not silently replace CRCs, sizes, definitions, or invalid values.
4. **Streaming and in-memory decoding share one state machine.** The in-memory
   API collects events from the streaming decoder rather than implementing a
   second parser.
5. **Generated classes are a projection, not the parser.** Updating
   `Profile.xlsx` must not change whether structurally legal unknown data can be
   read and preserved.

## 5. Decoder design

### 5.1 Segment scanner

The top-level scanner repeatedly reads:

1. a 12-byte minimum file header;
2. any declared header extension and optional header CRC;
3. exactly `data_size` record bytes;
4. the two-byte file CRC;
5. the next segment, if bytes remain.

This provides proper chained FIT support. `FitFile.from_bytes()` remains a
compatibility facade for a one-segment document; the new canonical API is
`FitDocument.from_bytes()` or `FitDocument.from_stream()`.

Header validation includes:

- minimum and declared size;
- `.FIT` signature;
- supported protocol major version;
- header CRC when present;
- data section bounds;
- file CRC;
- trailing data interpreted only as another complete segment.

### 5.2 Per-segment decoding state

Each segment has isolated state:

```text
definitions[0..15]
developer_registry[developer_data_index][field_number]
last_timestamp
component_accumulators[(global_message, field, component)]
```

The state resets at a segment boundary.

### 5.3 Record headers

Normal and compressed timestamp headers are distinct types:

```text
NormalRecordHeader
CompressedTimestampHeader
```

A compressed timestamp header is always a data-message header. It is invalid
for local message IDs outside 0-3.

For a compressed record:

1. resolve its local definition;
2. read the record content with the timestamp field omitted;
3. reconstruct field 253 using the previous timestamp and the official
   5-bit rollover algorithm;
4. update the timestamp reference;
5. preserve the compressed header and omitted wire field in the raw model.

The decoder must fail if no prior full timestamp is available.

### 5.4 Definition messages

Definition validation includes:

- reserved byte value;
- architecture value 0 or 1;
- field count and record bounds;
- valid base type identifier and endian flag;
- field size being a valid multiple of the base type size, except strings and
  byte arrays as permitted by the protocol;
- developer field definitions only when the record-header flag is set;
- redefinition of local message IDs taking effect only for subsequent records.

Definition snapshots are immutable. A data record keeps the exact definition
revision that decoded it.

### 5.5 Base-type codecs and invalid values

Replace conditional encoding with an explicit codec registry:

```text
BaseTypeCodec
├── width
├── struct_format
├── invalid_bit_pattern
├── decode_raw()
├── encode_raw()
└── is_invalid_bits()
```

Invalid values are recognized from raw bits before conversion. This is required
for floating-point invalid values, where the FIT invalid value is a specific NaN
bit pattern rather than an ordinary Python number.

The public representation is:

- `None` for an invalid scalar;
- `None` entries for invalid array elements;
- raw bytes retained in `FieldValue` for lossless re-encoding.

Setting a field to `None` writes the exact invalid bit pattern for its base type.

### 5.6 Subfields

Subfield selection is centralized and deterministic:

```python
all(
    reference_field.value in permitted_values
    for reference_field, permitted_values in references
)
```

The selected subfield controls type, scale, offset, units, and components.
Ambiguous matching subfields produce a profile-conformance error.

Generated property accessors must call this shared resolver rather than
duplicating reference checks.

### 5.7 Components and accumulation

Component decoding runs after the containing field is decoded:

1. select the active main field or subfield;
2. extract components least-significant bits first using their declared widths;
3. apply signedness where defined;
4. apply accumulation rollover state;
5. apply component scale and offset;
6. recursively expand nested components;
7. expose destination fields as synthetic `FieldValue` instances.

The raw containing field remains authoritative for preservation mode.

When a synthetic destination field is modified, canonical encoding rebuilds the
containing field and checks that the value fits its bit width.

### 5.8 Developer fields and native overrides

The developer registry is populated from `developer_data_id` and
`field_description` messages.

Strict behavior includes:

- field descriptions must refer to a defined developer data index;
- base type, scale, offset, units, array size, and string handling;
- delayed resolution when definitions precede descriptions, while preserving
  raw values;
- `native_mesg_num` and `native_field_num` override semantics;
- the Garmin requirement that native overrides preserve native units;
- multiple developer indices defining the same field number independently.

Unresolved developer fields are retained as raw values and reported, not
discarded.

## 6. Encoder design

The encoder has two explicit modes.

### 6.1 Preservation mode

```python
document.to_bytes(mode=EncodeMode.PRESERVE)
```

- Untouched raw records are copied byte-for-byte.
- Dirty records are rebuilt from their definition snapshot.
- Unknown messages, fields, header extensions, and compressed headers survive.
- Segment boundaries are retained.
- CRCs and sizes are recalculated only for dirty segments.

### 6.2 Canonical mode

```python
document.to_bytes(mode=EncodeMode.CANONICAL, strict=True)
```

- Rebuild all definitions and data records.
- Use normal headers by default; compressed timestamps are an explicit option.
- Generate consistent header and file CRCs.
- Emit the bundled Profile version.
- Reject invalid values, sizes, local IDs, missing definitions, and unresolved
  developer fields.
- Run the selected conformance levels before returning bytes.

`strict=True` never silently repairs caller-supplied invariants. A separate
`repair()` API may intentionally fix sizes or CRCs and must return a report of
every repair.

### 6.1 Compatibility-layer implementation status

`FitFileBuilder(strict=True)` now provides the first additive strict-encoding
slice: wire-range and Definition Message checks, ordered Developer Field
declaration checks, common `file_id` rules, and Activity required-message and
required-field checks. It fails closed for file types whose rule set has not
yet been implemented.

This compatibility validator does not complete the conformance claim. The
lossless wire model, compressed timestamps, generated Profile constraints,
components and accumulation, native overrides, chained files, and the remaining
file-type validators still follow the phases below.

## 7. File-type validators

Wire validity and Activity/Workout/Course validity are separate.

Validators are registered by `file_id.type`:

```text
FileTypeValidator
├── validate_required_messages()
├── validate_message_order()
├── validate_timestamp_order()
├── validate_references()
└── validate_file_specific_rules()
```

Common rules include:

- exactly one `file_id` message;
- `file_id` is the first data message;
- required `file_id` fields are valid;
- every data message has a preceding definition;
- timestamped messages are chronologically ordered where required.

Activity, Workout, Course, and other file types add their documented required
messages and reference constraints.

## 8. Public API and compatibility migration

Strict conformance should not require an immediate breaking rewrite.

### Phase A: additive APIs

- Add `FitDocument`, `DecodeOptions`, `EncodeOptions`, and
  `ConformanceReport`.
- Keep `FitFile`, `Record`, and generated message classes.
- Make `FitFile.from_*()` delegate to a one-segment `FitDocument`.
- Preserve existing exception inheritance from `ValueError`.

### Phase B: deprecations

- Deprecate implicit CRC repair in `to_bytes(check_crc=True)`.
- Deprecate treating `FitFile` as capable of representing chained files.
- Deprecate direct message-class re-exports from `message_factory`, but retain a
  lazy compatibility shim for at least one release cycle.
- Introduce an overridable row iterator shared by `to_rows()` and `to_csv()`.

### Phase C: strict defaults in the next major release

- Strict decoding and encoding become the default.
- Repair and permissive decoding require explicit options.
- Legacy behavior remains available through `CompatibilityMode.LEGACY` for a
  documented transition period.

## 9. Verification strategy

### 9.1 Golden corpus

Maintain committed, minimal fixtures for:

- 12-byte and 14-byte headers;
- little- and big-endian definitions;
- all FIT base types and every invalid bit pattern;
- arrays and strings;
- local-message redefinition;
- compressed timestamps, including 5-bit rollover;
- components, nested components, and accumulated rollover;
- subfields with single and multiple references;
- developer fields and native overrides;
- unknown native messages and fields;
- chained files;
- each supported standard file type.

Every fixture includes expected semantic values and expected exact bytes.

### 9.2 Garmin cross-validation

CI or a reproducible conformance job must:

1. decode repository-produced FIT files with Garmin FitCSVTool;
2. compare the decoded CSV with expected semantics;
3. create FIT files using FitCSVTool or an official encoding SDK;
4. decode them with this library;
5. compare canonical semantics;
6. verify untouched preservation round-trips byte-for-byte.

The Garmin tool version and `Profile.xlsx` checksum must be pinned.

The first live cross-validation job resolves the `fit-javascript-sdk` tag from
the library's `SDK_VERSION`. It generates the same Activity through both
libraries, checks both files with Garmin's integrity checker, cross-decodes
them, and compares normalized semantics. FitCSVTool, Developer Field,
compressed timestamp, unknown-field, and chained-file cases remain to be added
to the conformance matrix.

### 9.3 Property and fuzz testing

Property tests generate legal definition/data combinations and verify:

```text
semantic == decode(encode(semantic))
bytes == preserve(decode(bytes))
```

Fuzz tests cover truncated input, malicious counts and sizes, invalid local IDs,
bad CRCs, invalid UTF-8, definition churn, and deep component nesting. The
decoder must produce a bounded exception, never an infinite loop or unbounded
allocation based solely on untrusted lengths.

### 9.4 Required CI gates

- Python 3.8 compatibility test, or remove the advertised Python 3.8 support.
- Python 3.9-3.14 full tests.
- Ruff and progressively expanded mypy.
- Garmin conformance corpus.
- Generated-profile determinism.
- Package build.
- Parse/encode performance budgets.
- Streaming-memory budget.

## 10. Implementation phases and exit criteria

### Phase 0: freeze and characterize

- Add current behavior tests and known-failure fixtures.
- Mark unsupported legal FIT cases with explicit `xfail`.
- Add Garmin tool acquisition/checksum documentation.

Exit: every known conformance gap has a fixture and issue.

### Phase 1: lossless wire layer

- Implement `FitDocument`, segments, raw records, immutable definition
  snapshots, header extensions, CRC validation, and chained files.
- Implement the base-type codec registry and exact invalid bit patterns.

Exit: all structural fixtures preserve exact bytes.

### Phase 2: compressed timestamps

- Implement decoder timestamp state, rollover, omitted timestamp fields, and
  compressed encoding.

Exit: Garmin compressed-timestamp examples cross-decode in both directions.

### Phase 3: Profile semantics

- Fix subfields.
- Implement components, nested components, and accumulation.
- Implement complete developer fields and native overrides.
- Preserve unknown fields in known messages.

Exit: Profile-level golden corpus and Garmin cross-validation pass.

### Phase 4: strict encoder and file validators

- Add preservation/canonical modes.
- Add strict versus repair policies.
- Add File Type validators.

Exit: all produced standard files pass the selected Garmin and repository
validators without repair.

### Phase 5: API migration and performance

- Route legacy APIs through the conformance core.
- Add compatibility shims and deprecation warnings.
- Re-establish parse, encode, and streaming-memory budgets.

Exit: no undocumented breaking changes and performance is no worse than the
current optimized branch by more than the agreed budget.

## 11. Definition of done

The project may claim strict Garmin FIT conformance only when:

- all published FIT wire constructs are implemented;
- the bundled Profile semantics are implemented;
- every legal unknown field can be preserved;
- all standard file-type rules selected by the caller are validated;
- Garmin cross-validation passes;
- compressed timestamps, components, accumulation, developer native overrides,
  invalid values, and chained files have non-`xfail` tests;
- strict mode performs no silent repair;
- the exact supported Garmin SDK/Profile version is published.
