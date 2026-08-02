# Protocol epic (SHA-12) — release-note rollup

Draft narrative for the next version bump. Towncrier fragments under `news/`
(`SHA-13`…`SHA-22`, related SHA-3/9 wire work) are the machine-readable source;
this document is the human rollup for product claims.

**Do not** market “full Garmin FIT / Profile conformance.” See
[`FIT_CONFORMANCE_DESIGN.md`](FIT_CONFORMANCE_DESIGN.md) §11 residual checklist
and the [capability boundary](CAPABILITY_BOUNDARY.md) document.

## Epic outcome

Stages 1–4 closed Multica children **A–J** (docs/fixtures, components,
subfields, unknown fields, post-edit PRESERVATION, encode policies, PROFILE
scopes CORE/DOMAIN/FULL, Workout + Course FILE_TYPE). Stage 5 (**L**) publishes
honest Supported/Partial/Not-supported claims.

Profile / SDK version: **`21.205.0`** (`SDK_VERSION`, `fit_tool/gen/`).

## User-visible capabilities (rollup)

### Wire and decode

- Header CRC (14-byte) and file CRC on load / stream exhaustion (`check_crc`)
- Chained multi-segment FIT decode; optional trailing-byte allowance
- Compressed timestamp reconstruction into field 253 (decode path)
- Unified wire / facade decode path (earlier SHA-7/8 hygiene)

### Profile runtime

- Full main-field component registry (generated) with nested expansion and
  accumulator rollover
- Subfield resolution (ref-field match, multi-ref AND, scale/offset/units) and
  active-subfield components
- Unknown field ids on known messages as `UnknownField` with `raw_bytes`
- Unknown global messages via `GenericMessage` (partial preserve semantics)

### Encode

- `EncodeMode.PRESERVE` (default): unedited bit-identical; post-edit re-encodes
  dirty records only
- `EncodeMode.CANONICAL`: full re-project; `strict=True` validates first, never
  silent-repairs

### Validation

- Levels: WIRE, PROFILE, FILE_TYPE, opt-in PRESERVATION
- PROFILE scopes: **CORE** (default strict), **DOMAIN**, **FULL** (opt-in;
  native base-type + closed-enum from gen field catalog)
- FILE_TYPE: **Activity**, **Workout**, **Course**; other types fail closed

## Explicit non-goals / residuals

| Item | Notes |
| --- | --- |
| Full PROFILE required-field / units rules | Not in CORE/DOMAIN/FULL today |
| FILE_TYPE beyond A/W/C | Fail closed |
| `repair()` API | Future; strict path never auto-repairs |
| Public `FitDocument` API | Design target; facade + wire only today |
| Compressed timestamp encode parity | Decode supported; encode edges remain |
| Garmin Connect heuristics | Non-goal |
| “Full conformance” marketing | Blocked by §11 residual checklist |

## Towncrier / CHANGELOG

Unreleased fragments for this epic include (non-exhaustive):

- `news/SHA-13.doc` … `news/SHA-22.feature` (stages 1–4)
- `news/SHA-23.doc` (this matrix / claims pass)
- Earlier wire/validation fragments (`SHA-7`…`SHA-9`, `sha3-*`, etc.)

At release time, run Towncrier to fold `news/*` into `CHANGELOG.md` under the
chosen version. No version bump is implied by Stage 5 alone.

## Verification

```bash
uv run pytest fit_tool/tests/test_validation.py fit_tool/tests/test_profile_scope.py \
  fit_tool/tests/test_encode_policies.py fit_tool/tests/test_post_edit_preservation.py \
  fit_tool/tests/test_workout_files.py fit_tool/tests/test_course_files.py -q
```

Capability claims must match `README.md` and design-doc **Current status**.
