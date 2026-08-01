# Garmin FIT Strict Conformance Design

## Current status (implementation vs this document)

**This document is the target architecture and roadmap.** It is not a claim that
the installed package already meets full Garmin FIT conformance.

For the library as shipped today, use the capability matrix in
[`README.md`](../README.md#capability-boundary). That matrix is the source of
truth for user-facing claims; this section must stay aligned with it.

Baseline after Multica epic **SHA-12** stages 1–4 on `main` (wire #44/#45,
hygiene, then C–J). **User-facing claims must match**
[`README.md`](../README.md#capability-boundary); update both together.

| Area | Today | This design |
| --- | --- | --- |
| Common Activity / Workout / Course read-write, `FitFileBuilder`, file-level CRC, streaming iterators, developer fields (common declaration patterns), CSV export | Supported | Baseline to preserve |
| **Header CRC** (14-byte headers, gated by `check_crc`) | Supported | Keep strict; no silent repair |
| **Chained multi-segment** FIT decode via `FitFile.from_bytes` / `from_file` (all segments projected into `records`) | Supported | Full `FitDocument` / segment API remains the long-term surface (§4–5) |
| **Compressed timestamp** reconstruction into field 253 (wire decoder + projection) | Supported | Encode compressed headers still optional / canonical path |
| **Component expansion** for all Profile **main-field** sources (generated registry, nested expansion, accumulators); also expands components declared on the **active subfield** | Supported (main fields + active-subfield components) | Remaining edge cases only |
| **Subfield resolution** (ref-field match → type / scale / offset / units; first match wins; multi-ref AND) | Supported | Generated property accessors call `get_valid_sub_field` |
| **Ambiguous subfields** (more than one match) | PROFILE ERROR (decode still uses first match) | Same policy |
| **Preservation encode** (`to_bytes(mode=EncodeMode.PRESERVE)` / `preserve=True`, default) for buffer-decoded files: unedited path bit-identical; **post-edit** path re-encodes dirty records and copies `source_bytes` for the rest | Supported | Aligns with design §6.1 |
| **Canonical encode** (`to_bytes(mode=EncodeMode.CANONICAL)` / `preserve=False`); optional `strict=True` precheck | Supported | Compressed-header expansion only when field 253 is on the definition; otherwise keep compressed (non-strict) or raise (strict) |
| Unknown global messages (`GenericMessage`); composable validation with WIRE + PROFILE scopes (CORE default; DOMAIN/FULL opt-in native base-type + closed-enum) + Activity/Workout/Course FILE_TYPE; opt-in **PRESERVATION**; Builder `strict=True` wraps default levels at **CORE** only | Partial | Remaining PROFILE rule families (required fields, units); other FILE_TYPE values |
| Remaining PROFILE rule families (native required fields, units/scale beyond subfield scale/units); FILE_TYPE for types other than Activity/Workout/Course; `repair()` API; public `FitDocument` | Not supported / incomplete | Follow-ups outside closed SHA-12 stages C–J; see residual checklist under §11 |
| Unknown field ids on known messages (`UnknownField` + `raw_bytes` on decode; survive post-edit when not mutated) | Supported | Mutating an unknown field clears `raw_bytes` (PRESERVATION ERROR if that level is selected) |

Until §11 Definition of Done is met, do not describe the library as fully
protocol-conformant. Prefer “supports common Activity/Workout/Course workflows”
and point readers at the README matrix (including **What this library still
does not claim**).

### Remaining gaps (roadmap ↔ Multica)

Tracked under Multica epic **SHA-12** (protocol / capability extension). Stages
1–4 children **C–J** are **done** on `main`; Stage 5 (**L** / SHA-23) is the
public-claims pass that keeps this table and the README matrix honest.

| Gap | Design doc | Multica | Notes |
| --- | --- | --- | --- |
| Docs / status truth vs main | Phase 0 | **A** SHA-13 | **Done** (re-synced at Stage 5 / L) |
| Fixture / golden corpus for protocol edges | Phase 0 | **B** SHA-14 | **Done** inventory + constructive goldens; expand as follow-up only |
| Full component / accumulator coverage beyond `_KNOWN_COMPONENTS` | Phase 3 | **C** SHA-15 | **Done** main-field registry + nested + rollover; active-subfield components via D |
| Subfield resolution (type / scale / units / components) | Phase 3 | **D** SHA-16 | **Done** runtime match + PROFILE ambiguity ERROR |
| Unknown field ids on known messages (decode retain + raw bytes) | Phase 3 | **E** SHA-17 | **Done** `UnknownField` + `raw_bytes` on main path |
| Post-edit PRESERVATION (edited files, dirty records) | Phase 4 / PRESERVATION level | **F** SHA-18 | **Done** per-record dirty + mixed encode; opt-in PRESERVATION findings |
| Encode policies (canonical vs preserve, strict vs repair) | Phase 4 §6 | **G** SHA-19 | **Done** `EncodeMode` + policy matrix; no silent invalid clamp; `repair()` still future |
| PROFILE scopes from bundled Profile.xlsx `21.205.0` | Phase 3 PROFILE / §3.1 | **H** SHA-20 | **Done** CORE/DOMAIN/FULL + gen `field_catalog`; default remains CORE; native required fields / units still residual |
| Workout FILE_TYPE rules | Phase 4 §7 | **I** SHA-21 | **Done** required messages/fields; SDK Workout*.fit pass FILE_TYPE |
| Course FILE_TYPE rules | Phase 4 §7 | **J** SHA-22 | **Done** Course required messages/fields; Activity + Workout unchanged |
| Public capability matrix / release-note pass | Phase 5 | **L** SHA-23 | **This pass** — README + this section + §11 residual checklist + Towncrier epic notes |

Letter **A** (SHA-13) was the first status-truth pass. After Stage 5, gaps
C–J are closed for the epic’s staged scope; residuals below §11 are **follow-up
work**, not silent “Supported” claims.

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
   `Profile.xlsx` (see §3.1: full xlsx as metadata ceiling; validation **scopes**
   CORE / DOMAIN / FULL — FULL is not the default strict set).
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

### 3.1 PROFILE depth decision (O1 — confirmed)

**Decision (SHA-3 architecture review, accepted):** treat the bundled
`Profile.xlsx` as the **single source of truth** and design for full-table
capability, but **do not** make full-table ERROR validation the default product
behavior.

Three layers must not be conflated:

| Layer | Role | Full xlsx? |
| --- | --- | --- |
| **A. Typed API / codegen** | Generated messages and enums from Profile | Already near-complete message coverage |
| **B. Runtime semantics** | Subfields, components, accumulators, native overrides | Design for full metadata; implement incrementally |
| **C. `ConformanceLevel.PROFILE` validation** | Required fields, base types, enums, units consistency | Full catalog is an **opt-in scope**, not the default strict set |

#### Scopes (shipped API)

When `ConformanceLevel.PROFILE` is selected, validation applies
`profile_scope=` / `ProfileScope`:

| Scope | Intent | Default for `strict=True` / DEFAULT_LEVELS | Status |
| --- | --- | --- | --- |
| **CORE** | Developer-field rules + ambiguous native subfield ERROR | **Yes** | Shipped |
| **DOMAIN** | CORE + native base-type and closed-enum checks on high-frequency Activity/Workout messages | No | Shipped (required-field / units families still residual) |
| **FULL** | CORE + same native base-type / closed-enum rules for the entire gen-exported catalog from Profile.xlsx | **No** — explicit opt-in | Shipped for those rule families only; not “full Profile semantics” |

Principles:

1. **Metadata is one-way:** `Profile.xlsx` → gen artifacts → runtime tables and
   validation catalogs. Do not hand-maintain a second full rule book.
2. **Semantics before strict validation:** subfields/components (B) must be
   correct enough that FULL validation does not flood false positives.
3. **Severity:** MUST-level wire/profile requirements → ERROR; best-practice or
   rare messages → WARNING/INFO.
4. **Orthogonal dimensions:** FULL PROFILE field rules do **not** replace
   FILE_TYPE (Workout/Course) or PRESERVATION.
5. **Public claims:** the library may claim “Profile.xlsx is the source of
   truth” and “FULL scope available” only when the corresponding milestone is
   implemented; it must not imply default strict equals FULL.

#### Implementation milestones (for Multica H / related stages)

| Milestone | Meaning | Status |
| --- | --- | --- |
| M1 | Gen exports field / enum catalog (and related) from xlsx | **Done** (`field_catalog`, component registry; required-field table still residual) |
| M2 | Runtime applies those tables (semantics) | **Partial** (components, subfields, accumulators; not all rule families) |
| M3 | PROFILE CORE validation (developer subset + ambiguous subfields) | **Done** |
| M4 | PROFILE DOMAIN (Activity/Workout high-frequency messages) | **Done** for base-type + closed-enum |
| M5 | PROFILE FULL catalog; default remains CORE | **Done** for base-type + closed-enum on full catalog; default still CORE |
| M6 | Marketing / §11 DoD only with WIRE + scoped PROFILE + FILE_TYPE + PRESERVATION | **Blocked** by residual checklist under §11 (honest Partial claims only) |

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

Subfield selection is centralized and deterministic via
`Field.resolve_sub_field` / `get_valid_sub_field` and `SubField.is_valid`:

```python
all(
    reference_field.value in permitted_values
    for reference_field, permitted_values in references
)
```

Implementation notes (runtime today):

- **AND** across every entry in `reference_map` (multi-ref). A missing or
  invalid reference field means the subfield is not active.
- Permitted values are compared to the decoded ref-field value (enums via
  `.value`).
- **First match in Profile order** is selected for decode/encode
  (type, scale, offset, units, and any components on that subfield).
- **Ambiguity** (two or more matches) is a **PROFILE-level ERROR** in
  `validate_fit_file`; decode still uses the first match so values remain
  defined. This is intentional and covered by golden tests.

Generated property accessors must call this shared resolver rather than
duplicating reference checks (named subfield properties may still gate on
the ref field for `None` vs value, but scale/units come from
`get_valid_sub_field`).

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

The encoder has two explicit modes, exported as
`fit_tool.EncodeMode` / `EncodeOptions` and accepted by
`FitFile.to_bytes(mode=..., strict=...)`. The boolean `preserve=` kwarg remains
as a compatibility alias (`True` → PRESERVE, `False` → CANONICAL).

### 6.1 Preservation mode

```python
from fit_tool import EncodeMode, FitFile

fit.to_bytes(mode=EncodeMode.PRESERVE)  # default
fit.to_bytes(preserve=True)             # alias
```

- Untouched raw records are copied byte-for-byte.
- Dirty records are rebuilt from their definition snapshot (encode policies apply).
- Unknown messages, fields, header extensions, and compressed headers survive
  when untouched.
- Segment boundaries are retained.
- CRCs and sizes are recalculated only for dirty segments.

### 6.2 Canonical mode

```python
fit.to_bytes(mode=EncodeMode.CANONICAL)
fit.to_bytes(mode=EncodeMode.CANONICAL, strict=True)
fit.to_bytes(preserve=False)  # alias for non-strict canonical
```

- Rebuild all definitions and data records from the projected model.
- Prefer normal record headers; expand compressed-timestamp headers when field
  253 is present on the definition (otherwise keep compressed, or raise if
  `strict=True`).
- Generate consistent header and file CRCs (sizes always rewritten).
- Reject out-of-range encoded values at set time (no clamp). Cleared fields
  emit protocol-invalid fill so the definition stays aligned.
- `strict=True` runs default conformance levels (WIRE + PROFILE + FILE_TYPE)
  before returning bytes and forces CANONICAL.

`strict=True` never silently repairs caller-supplied invariants (no range
clamping; mismatched overridden CRC raises when `check_crc=True`). A separate
`repair()` API may intentionally fix sizes or CRCs and must return a report of
every repair — **not implemented yet**.

### 6.3 Encode policy matrix (implemented)

| Concern | PRESERVE (default) | CANONICAL | CANONICAL + `strict=True` |
| --- | --- | --- | --- |
| Untouched records | `source_bytes` copy | full re-project | full re-project |
| Dirty records | re-project | re-project | re-project |
| Out-of-range field values | rejected at set (no clamp) | same | same + pre-encode validation |
| Cleared field (`None`) still on definition | protocol-invalid fill | same | same |
| Scale / offset | `round((v+offset)*scale)` | same | same |
| Expanded component destinations | off-wire unless listed on definition | same | same |
| Compressed timestamp (untouched) | keep wire bytes | expand to normal if def has 253; else keep compressed | expand if 253; else **raise** |
| Compressed timestamp (dirty re-encode) | expand if def has 253; else keep compressed | same | expand if 253; else **raise** |
| Header / file CRC | recompute dirty segments only | recompute all | recompute; wrong override raises |
| Pre-encode validation | no | no | DEFAULT levels, raise on ERROR |

### 6.4 Compatibility-layer implementation status

Composable validation is available independently of the Builder:

```python
from fit_tool import ConformanceLevel, validate_fit_file

report = validate_fit_file(fit_file)  # WIRE + PROFILE + FILE_TYPE
report = fit_file.validate(levels={ConformanceLevel.WIRE})
report.raise_for_errors()
```

`FitFileBuilder(strict=True)` is a thin wrapper over the same API (all default
levels, raise on error). Wire-range and Definition Message checks still run on
every `add`. FILE_TYPE rules cover Activity and Workout; other `file_id.type`
values (e.g. Course) fail closed.

**Already on the wire / compatibility path** (see Current status): layered
decode (`fit_tool/wire`), chained multi-segment load, header + file CRC,
compressed-timestamp reconstruction into field 253, component/subfield runtime
semantics (main-field registry + active subfield), unknown fields on known
messages, and preservation encode via `to_bytes(preserve=True)` for unedited
**and post-edit** files (per-record dirty tracking; mixed `source_bytes` /
re-project).

This still does **not** complete the conformance claim. Remaining work includes
full Profile validation scopes (DOMAIN/FULL) and Course FILE_TYPE validators —
see **Remaining gaps** and Phases 3–5. Encode modes (G) are on the compatibility
path; the long-term `FitDocument` encode surface remains future.

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

- Python 3.9-3.14 full tests (package requires Python >=3.9).
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
- Keep README capability matrix and this **Current status** table in sync
  (Multica A / SHA-13); expand golden fixtures for remaining gaps (B / SHA-14).

Exit: every known conformance gap has a fixture and issue.

**Progress:** status table and README matrix aligned after #44/#45 (SHA-13) and
re-synced at Stage 5 (SHA-23). Fixture inventory and constructive goldens
landed under SHA-14; further corpus growth is optional follow-up.

### Phase 1: lossless wire layer

- Implement `FitDocument`, segments, raw records, immutable definition
  snapshots, header extensions, CRC validation, and chained files.
- Implement the base-type codec registry and exact invalid bit patterns.

Exit: all structural fixtures preserve exact bytes.

**Progress (partial):** `fit_tool/wire` decoder/encoder models, immutable
definition snapshots, header + file CRC, chained multi-segment decode, and
unedited / post-edit preservation rewrite of source segment bytes are on
`main`. Public `FitDocument` API and a full structural golden corpus remain
incomplete relative to the exit criteria above.

### Phase 2: compressed timestamps

- Implement decoder timestamp state, rollover, omitted timestamp fields, and
  compressed encoding.

Exit: Garmin compressed-timestamp examples cross-decode in both directions.

**Progress (partial):** decode-time reconstruction into field 253 is on `main`.
Compressed encode and full Garmin bidirectional golden coverage remain.

### Phase 3: Profile semantics

- Fix subfields.
- Implement components, nested components, and accumulation.
- Implement complete developer fields and native overrides.
- Preserve unknown fields in known messages.

Exit: Profile-level golden corpus and Garmin cross-validation pass.

**Progress (partial):** main-field component registry (37/37 sources) with
nested expansion and accumulator rollover; active-subfield components via
subfield resolution (C/D); unknown field ids retained as `UnknownField` +
`raw_bytes` (E); PROFILE scopes CORE/DOMAIN/FULL with gen `field_catalog` for
native base-type + closed-enum (H / O1). Remaining: native required-field and
units rule families, broader Profile golden / Garmin cross-validation.

### Phase 4: strict encoder and file validators

- Add preservation/canonical modes.
- Add strict versus repair policies.
- Add File Type validators.

Exit: all produced standard files pass the selected Garmin and repository
validators without repair.

**Progress (partial):** unedited and **post-edit** PRESERVE paths; explicit
`EncodeMode` / `strict` / policy matrix (G / SHA-19). FILE_TYPE for
**Activity**, **Workout**, and **Course** (I / SHA-21, J / SHA-22); other
`file_id.type` values still fail closed. `repair()` API is still future.

### Phase 5: API migration and performance

- Route legacy APIs through the conformance core.
- Add compatibility shims and deprecation warnings.
- Re-establish parse, encode, and streaming-memory budgets.
- Publish accurate public capability claims (README matrix + this status table).

Exit: no undocumented breaking changes and performance is no worse than the
current optimized branch by more than the agreed budget; public claims match
code.

**Progress (partial):** Stage 5 / **L** (SHA-23) lands the public capability
matrix and release-note rollup for SHA-12. Full API migration and performance
budgets remain follow-up work outside the protocol epic’s staged children.

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

### §11 residual checklist (after SHA-12 stages 1–4)

Honest status vs the bullets above. **None** of these residuals re-open C–J as
“undone”; they bound marketing claims until a future epic closes them.

| §11 requirement | Status after SHA-12 C–J | Evidence / residual |
| --- | --- | --- |
| All published FIT wire constructs | **Partial** | Header/file CRC, chained decode, compressed-ts **decode**, definitions/data path on `main`; public `FitDocument`, full structural goldens, compressed-ts **encode** parity incomplete |
| Bundled Profile semantics | **Partial** | Subfields, main-field + active-subfield components, accumulators, developer fields (common patterns), PROFILE CORE/DOMAIN/FULL (base-type + closed-enum). Missing: native required fields, units/scale consistency rules, full developer native-override matrix |
| Every legal unknown field preserved | **Mostly met** | `UnknownField` + `raw_bytes`; unedited + post-edit PRESERVE when not mutated; PRESERVATION level reports loss. Structural edit / full re-project still drops wire snapshot (documented) |
| Standard file-type rules (caller-selected) | **Partial** | Activity + Workout + Course implemented; other types fail closed intentionally |
| Garmin cross-validation | **Incomplete** | SDK samples used as smokes/fixtures; not a release gate for full interop |
| Non-`xfail` tests for listed constructs | **Partial** | Strong constructive coverage for C–J; expand goldens / remove any remaining known-gap xfails as follow-up |
| Strict mode no silent repair | **Met** | `strict=True` / DEFAULT_LEVELS never clamp or auto-repair; no `repair()` on strict path |
| Published SDK/Profile version | **Met** | Profile / SDK `21.205.0` (`fit_tool/gen/`, `SDK_VERSION`) |

**Bottom line:** SHA-12 may move to `done` / `in_review` with the residuals
above explicit. Do **not** flip public marketing to “full Garmin FIT
conformance” until this checklist is actually green.
