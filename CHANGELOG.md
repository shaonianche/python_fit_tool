## Release v0.9.16 (2026-08-05)

### Features & Improvements

- Expose a stable package-level public API (`FitFile`, `FitFileBuilder`, exceptions, version constants)
  via `from fit_tool import ...`, documented in the README. Existing deep imports remain supported. ([#SHA-5](https://github.com/shaonianche/python_fit_tool/issues/SHA-5))
- Introduce a wire-layer MVP (`fit_tool/wire`) with raw header/record models and a
  stateful decoder that keeps immutable definition snapshots. `FitFile.from_bytes`
  decodes via the wire layer and projects to existing typed messages while keeping
  public API behavior compatible. ([#SHA-7](https://github.com/shaonianche/python_fit_tool/issues/SHA-7))
- Unify stream and in-memory FIT decoding on one state machine (`FitDecoder`
  over the wire layer) so definition snapshots, developer-field registration,
  and CRC handling stay aligned between `FitFile.from_bytes` and `iter_*`. ([#SHA-8](https://github.com/shaonianche/python_fit_tool/issues/SHA-8))
- Add a composable validation API (`validate_fit_file`, `FitFile.validate`) with
  WIRE / PROFILE / FILE_TYPE levels and report or raise modes. Builder
  `strict=True` now delegates to the same checks. ([#SHA-9](https://github.com/shaonianche/python_fit_tool/issues/SHA-9))
- Split generated message construction into explicit create (`MessageClass()`)
  and decode (`MessageClass.from_definition(...)`) paths; MessageFactory uses the
  definition factory. ([#SHA-10](https://github.com/shaonianche/python_fit_tool/issues/SHA-10))
- Expand decode-time component / accumulator coverage to all Profile main-field
  sources via a generated registry (`fit_tool/profile/component_registry.py`),
  with nested expansion (e.g. compressed speed → enhanced speed) and modular
  accumulator rollover. Subfield-gated components remain deferred to subfield work. ([#SHA-15](https://github.com/shaonianche/python_fit_tool/issues/SHA-15))
- Fix Profile **subfield resolution**: match reference field *values* (AND across multi-ref maps), apply the active subfield's type/scale/offset/units, expand components declared on that subfield, and report **ambiguous** multi-matches as PROFILE validation errors (decode still uses the first match). ([#SHA-16](https://github.com/shaonianche/python_fit_tool/issues/SHA-16))
- Retain unknown native field ids on known messages during decode as
  `UnknownField` (with `raw_bytes` for later PRESERVATION rewrite). Unedited
  `to_bytes(preserve=True)` remains bit-identical via `wire_document`. ([#SHA-17](https://github.com/shaonianche/python_fit_tool/issues/SHA-17))
- Post-edit **PRESERVATION**: per-record dirty tracking (field mutations mark
  `Record.dirty`) so `to_bytes(preserve=True)` re-encodes only edited records and
  copies `source_bytes` for the rest (unknown fields and other records survive).
  Opt-in `ConformanceLevel.PRESERVATION` reports loss when unknown-field
  `raw_bytes` were cleared. Structural `mark_dirty()` / add / remove still force
  a full projected re-encode. ([#SHA-18](https://github.com/shaonianche/python_fit_tool/issues/SHA-18))
- Encode policies: explicit `EncodeMode.PRESERVE` / `EncodeMode.CANONICAL` on
  `FitFile.to_bytes` (legacy `preserve=` still works). Canonical rebuilds all
  records with normalized sizes/CRCs; `strict=True` validates first and never
  clamps invalid values. Policy matrix documented in README and design doc §6. ([#SHA-19](https://github.com/shaonianche/python_fit_tool/issues/SHA-19))
- PROFILE validation supports selectable scopes (`ProfileScope.CORE` / `DOMAIN` /
  `FULL`). Default `strict` / `DEFAULT_LEVELS` remain **CORE** (developer fields +
  ambiguous subfields). DOMAIN and FULL add data-driven native base-type and
  closed-enum checks from a gen-exported field catalog
  (`fit_tool.profile.field_catalog`) derived from the bundled Profile. FULL is
  opt-in only via `validate_fit_file(..., profile_scope=ProfileScope.FULL)`. ([#SHA-20](https://github.com/shaonianche/python_fit_tool/issues/SHA-20))
- FILE_TYPE validation for **Workout** files: required `workout` / `workout_step`
  messages and fields (`num_valid_steps`, step `message_index` /
  `duration_type` / `target_type`). Activity behavior unchanged; other
  `file_id.type` values (e.g. Course) still fail closed. SDK Workout fixtures
  validate clean under FILE_TYPE. ([#SHA-21](https://github.com/shaonianche/python_fit_tool/issues/SHA-21))
- FILE_TYPE validation for Course files: required course / lap / record / timer
  events and fields (aligned with Garmin Course rules and real device exports).
  Workout and other non-Activity/Course types still fail closed. ([#SHA-22](https://github.com/shaonianche/python_fit_tool/issues/SHA-22))
- Protocol high-severity fixes: chained multi-segment FIT decode, trailing-byte rejection, compressed-timestamp reconstruction, known component expansion, and wire preservation encode for unedited buffer-decoded files. ([#sha3](https://github.com/shaonianche/python_fit_tool/issues/sha3))
- Validate FIT header CRC when the header is larger than 12 bytes (CRC of the preceding header bytes in the final two bytes; gated by ``check_crc``). ([#sha3-medium](https://github.com/shaonianche/python_fit_tool/issues/sha3-medium))
- Add bidirectional FIT interoperability coverage against the Garmin JavaScript
  SDK at the bundled Profile version, plus corrected generated Profile scales. ([#33](https://github.com/shaonianche/python_fit_tool/issues/33))

### Bug Fixes

- Copy record-header `local_id` onto parsed definition and data messages, and fix FLOAT field encoding so fractional values are preserved and FIT invalid all-ones bit patterns round-trip as `None`. ([#sha3](https://github.com/shaonianche/python_fit_tool/issues/sha3))

### Documentation

- Move the detailed capability matrix and validation/encode notes from the
  README into ``docs/CAPABILITY_BOUNDARY.md``. The README now keeps a short
  install, public API, and minimal examples section, with a link to that doc. ([#readme-capability-docs](https://github.com/shaonianche/python_fit_tool/issues/readme-capability-docs))
- Document the protocol fixture corpus and gap inventory under
  `fit_tool/tests/data/README.md`, with constructive golden tests for component
  edges, unknown fields on known messages, and subfield-bearing workout steps. ([#SHA-14](https://github.com/shaonianche/python_fit_tool/issues/SHA-14))
- Document the current capability boundary for readers: README Supported /
  Partial / Not-supported matrix and a short “what this library still does not
  claim” section now match the shipped code (PROFILE scopes CORE/DOMAIN/FULL,
  Activity/Workout/Course FILE_TYPE validation, post-edit PRESERVE/CANONICAL
  encode). The conformance design doc and residual checklist are re-synced so
  public claims stay honest — full Garmin FIT / Profile conformance is still
  not advertised until every Definition of Done item is met. ([#SHA-23](https://github.com/shaonianche/python_fit_tool/issues/SHA-23))
- Document the maintainer release checklist and harden the tag-based PyPI/GitHub
  Release workflow (version gate, `v`-prefix tags, changelog extraction, split
  build/publish/github-release jobs). ([#SHA-36](https://github.com/shaonianche/python_fit_tool/issues/SHA-36))

### Dependencies

- Move profile-generation packages (`openpyxl`, `inflection`, plus `jinja2`) to an optional `[gen]` extra and drop unused `bitstruct` from the runtime install. ([#sha6](https://github.com/shaonianche/python_fit_tool/issues/sha6))
- Upgrade the bundled Garmin FIT SDK Profile to 21.212.0. ([#60](https://github.com/shaonianche/python_fit_tool/issues/60))

### Removals and Deprecations

- Deprecate ``Record.from_bytes`` for full-file decode. Prefer ``FitFile.from_bytes`` / ``WireDecoder`` + compatibility; the method remains for isolated record pack/unpack tests. ([#sha3-medium](https://github.com/shaonianche/python_fit_tool/issues/sha3-medium))

### Miscellany

- Raise typed `Fit*` errors on core parse/encode paths and improve CLI error exits;
  align package metadata with Python 3.9+ and Ruff as a CI gate. ([#sha3-hygiene](https://github.com/shaonianche/python_fit_tool/issues/sha3-hygiene))


## Release v0.9.15 (2026-02-02)

### Features & Improvements

- Optimize `Field.to_bytes` with `b''.join` for better performance. ([#4](https://github.com/shaonianche/python_fit_tool/issues/4))
- Remove redundant record re-encoding verification from `FitFile.from_bytes` for improved performance. ([#10](https://github.com/shaonianche/python_fit_tool/issues/10))
- Add proper logging for unknown base types in profile generation. ([#17](https://github.com/shaonianche/python_fit_tool/issues/17))
- Add uv support and modernize CLI. ([#18](https://github.com/shaonianche/python_fit_tool/issues/18))

### Bug Fixes

- Fix test errors. ([#2](https://github.com/shaonianche/python_fit_tool/issues/2))
- Optimize `get_developer_field` lookup and fix `StopIteration` bug. ([#7](https://github.com/shaonianche/python_fit_tool/issues/7))

### Dependencies

- Switch the build toolchain to UV ([#19](https://github.com/shaonianche/python_fit_tool/issues/19))

### Miscellany

- Add Codecov integration for code coverage reporting. ([#11](https://github.com/shaonianche/python_fit_tool/issues/11))
- Improve test coverage. ([#13](https://github.com/shaonianche/python_fit_tool/issues/13))
