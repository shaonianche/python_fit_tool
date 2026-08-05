# Capability boundary

What **fit-tool** implements today versus the long-term conformance roadmap.

This document is the **source of truth for current capability claims**. The
strict-conformance **target** architecture remains
[`FIT_CONFORMANCE_DESIGN.md`](FIT_CONFORMANCE_DESIGN.md) (not a guarantee of
what the installed package already does).

Bundled Profile version: **`21.212.0`** (`fit_tool.SDK_VERSION` / `fit_tool/gen/`).
Protocol version string: **`2.4`** (`fit_tool.PROTOCOL_VERSION`).

---

## Status matrix

The library is suitable for everyday Activity / Workout / Course read-write,
CSV export, and typed message editing. It does **not** claim full Garmin FIT
protocol or Profile conformance.

| Status | Capabilities |
| --- | --- |
| **Supported** | Common Activity / Workout / Course read-write via typed profile messages; `FitFileBuilder` encode path; **header CRC** (14-byte headers) and **file-level CRC** on load / stream exhaustion (`check_crc=True` default); developer fields for common declaration patterns; streaming iterators (`FitFile.iter_file` / `iter_stream`); CSV export (`to_csv` / `to_rows`); **chained multi-segment** FIT decode via `from_bytes` / `from_file` (all segments projected into `records`); **compressed timestamp** reconstruction into field 253; **subfield resolution** (ref-field match → type / scale / offset / units; multi-ref AND; first match wins); **component expansion** for all Profile main-field sources (generated registry, 37 sources) **and** components on the active subfield; nested expansion + accumulator rollover; **unknown field ids** on known messages as `UnknownField` (decoded values + `raw_bytes`); **encode modes** `EncodeMode.PRESERVE` (default; unedited bit-identical + post-edit dirty re-project) and `EncodeMode.CANONICAL` (full re-project, normalized sizes/CRCs; optional `strict=True` precheck) |
| **Partial** | Unknown global messages via `GenericMessage` (readable; unedited preserve keeps wire bytes; post-edit re-encodes dirty records only); composable validation (`validate_fit_file` / `FitFile.validate`) with **WIRE** + **PROFILE** + **FILE_TYPE** (Activity / Workout / Course) and opt-in **PRESERVATION**; **PROFILE scopes** under O1 (`ProfileScope.CORE` default for `strict` / `DEFAULT_LEVELS`: developer-field rules + ambiguous-subfield ERROR; **DOMAIN** / **FULL** opt-in: native base-type + closed-enum checks from gen-exported `field_catalog` for high-frequency vs entire Profile.xlsx catalog) — design doc §3.1; Builder `strict=True` wraps WIRE+PROFILE+FILE_TYPE at **CORE** only |
| **Not supported / incomplete** | Remaining PROFILE rule families (native **required** fields, units/scale consistency beyond subfield scale/units, open/ranged enums as ERROR); FILE_TYPE for types other than Activity/Workout/Course (fails closed); intentional `repair()` API (strict path never silent-repairs); bit-identical rewrite of compressed-timestamp dirty records when field 253 is not on the definition (strict raises; non-strict keeps compressed header); public `FitDocument` / multi-segment encode API; full Garmin SDK cross-validation as a release gate |

### What this library still does not claim

Until design-doc [§11 Definition of Done](FIT_CONFORMANCE_DESIGN.md#11-definition-of-done)
is met with evidence, do **not** describe the package as “full Garmin FIT /
Profile conformant.” Prefer:

- “Supports common Activity / Workout / Course workflows”
- “PROFILE validation defaults to CORE; DOMAIN/FULL are opt-in”
- “FILE_TYPE validates Activity, Workout, and Course only”

**Non-goals** (by design, not just unfinished work):

- Reproducing undocumented Garmin Connect acceptance heuristics
- Silent repair of corrupt files on the strict path
- Treating every Garmin best-practice note as a wire ERROR
- Replacing generated typed message classes as the ergonomic public API

**Residuals** that still block §11 marketing claims: other standard file types,
remaining PROFILE rule families, broader interop/golden corpus,
compressed-timestamp encode parity, and performance/API migration items in
design-doc Phases 1–5. See the design doc **Remaining gaps** / §11 residual
checklist.

If you need a construct listed as incomplete, prefer an official Garmin SDK or
track follow-up work against the design doc. Architecture reviews should judge
this package against the matrix above, not against full protocol conformance.

---

## Validation levels (code-aligned)

| Level | What it checks | Status in code |
| --- | --- | --- |
| `ConformanceLevel.WIRE` | Local IDs, definition field layout/sizes, data records vs active definition | Implemented |
| `ConformanceLevel.PROFILE` | Scoped Profile semantics via `profile_scope=` / `ProfileScope` | **CORE (default):** developer-field declarations + **ambiguous native subfields** as ERROR. **DOMAIN (opt-in):** CORE + native base-type and closed-enum checks on high-frequency Activity/Workout messages. **FULL (opt-in):** same native rules for the gen-exported catalog from Profile.xlsx `21.212.0`. FULL is never default `strict` (§3.1 O1). Open/ranged enums (e.g. `activity_class`) are excluded from closed-enum checks |
| `ConformanceLevel.FILE_TYPE` | `file_id` first/unique + required fields; Activity, Workout, and Course rules | **`IMPLEMENTED_FILE_TYPES`** = Activity, Workout, Course; other `file_id.type` values **fail closed** |
| `ConformanceLevel.PRESERVATION` | Post-edit rewrite loss (e.g. `UnknownField.raw_bytes` cleared) | **Opt-in** — not in `DEFAULT_LEVELS` / Builder `strict=True` |

```python
from fit_tool import ConformanceLevel, FitFile, ProfileScope, validate_fit_file

fit_file = FitFile.from_file("activity.fit")
report = fit_file.validate()
fit_file.validate(raise_on_error=True)
validate_fit_file(fit_file, levels={ConformanceLevel.WIRE})
validate_fit_file(fit_file, profile_scope=ProfileScope.FULL)
validate_fit_file(fit_file, levels={ConformanceLevel.PRESERVATION})
```

`FitFileBuilder(strict=True)` runs default levels (WIRE + PROFILE + FILE_TYPE)
with `raise_on_error=True`. Prefer `validate_fit_file` for reports and level
selection on the read path.

---

## Encode policies

`FitFile.to_bytes` supports two modes (`EncodeMode`); legacy `preserve=` remains
an alias. Defaults: **PRESERVE**, non-strict.

```python
from fit_tool import EncodeMode, FitFile

fit = FitFile.from_bytes(raw_bytes)
fit.to_bytes()                                   # PRESERVE
fit.to_bytes(mode=EncodeMode.CANONICAL)
fit.to_bytes(mode=EncodeMode.CANONICAL, strict=True)
fit.to_bytes(preserve=False)                     # → CANONICAL
```

| Concern | PRESERVE (default) | CANONICAL | + `strict=True` |
| --- | --- | --- | --- |
| Untouched records | copy `source_bytes` | re-project all | re-project all |
| Dirty records | re-project | re-project | re-project |
| Out-of-range values | reject at set (no clamp) | same | same + pre-encode validation |
| Cleared field still on definition | protocol-invalid fill | same | same |
| Scale / offset | `round((v+offset)*scale)` | same | same |
| Expanded components | only definition fields on wire | same | same |
| Compressed timestamp headers | keep if untouched; dirty may expand when field 253 is on the definition | expand when 253 on def; else keep compressed | expand when 253 on def; else **raise** |
| CRC / sizes | recompute dirty segments only | recompute all | recompute; bad override raises |

`strict=True` forces CANONICAL and runs WIRE + PROFILE + FILE_TYPE before encode.
Design notes: [`FIT_CONFORMANCE_DESIGN.md`](FIT_CONFORMANCE_DESIGN.md) §6.

### Post-edit preservation

After `FitFile.from_bytes` / `from_file`, field mutations mark the owning
`Record` dirty. PRESERVE re-encodes dirty records and copies wire bytes for the
rest. Structural edits (`add_record` / `remove_record` / `mark_dirty()`) drop the
wire snapshot and fully re-project.

---

## Tests and fixtures

- Gap inventory: [`fit_tool/tests/data/README.md`](../fit_tool/tests/data/README.md)
- Constructive helpers: `fit_tool/tests/protocol_fixture_helpers.py`
- Epic release narrative: [`EPIC_SHA12_RELEASE_NOTES.md`](EPIC_SHA12_RELEASE_NOTES.md)

### Garmin JS SDK interop (optional live job)

```bash
fit_profile_version=$(uv run python -c 'from fit_tool import SDK_VERSION; print(SDK_VERSION)')
git clone --depth 1 --branch "$fit_profile_version" \
  https://github.com/garmin/fit-javascript-sdk.git ../fit-javascript-sdk
FIT_JS_SDK_PATH=../fit-javascript-sdk \
  uv run pytest fit_tool/tests/test_garmin_sdk_interop.py -q
```

Legal encodings need not be byte-identical.

---

## Keeping this document honest

When capability status flips:

1. Update **this** matrix and the relevant design-doc “Current status” /
   remaining-gaps rows.
2. Add a Towncrier fragment for user-visible changes.
3. Prefer small PRs; PROFILE FULL remains opt-in (never default `strict`).
