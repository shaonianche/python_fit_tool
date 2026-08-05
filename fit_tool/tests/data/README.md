# Test fixture corpus

Committed FIT/CSV/JSON samples and constructive test helpers used by the
protocol and regression suite. Prefer **constructing bytes in tests** (see
`fit_tool/tests/protocol_fixture_helpers.py`) unless a real-device or SDK
binary is needed for interoperability.

## Layout

| Path | Role |
| --- | --- |
| `sdk/` | Official Garmin FIT SDK sample files (small golden activities, workouts, weight scale, settings, monitoring) |
| `sdk/*.csv` | Companion CSV exports for some SDK samples |
| `interop/activity.json` | Shared Activity semantics for Python ↔ `fit-javascript-sdk` interop |
| `activity_*.fit`, `stagesLink_*.fit`, `palisade.fit`, `trainerroad_*.fit`, `old_stage_*.fit` | Third-party / device samples for decoder smoke |
| `old_stage_left_hand_lee.gpx` | GPX companion for course/activity examples |

## How to obtain Garmin SDK samples

Garmin publishes sample FIT files and tools under their FIT SDK license.

1. **SDK package (preferred for new samples)**  
   - Site: <https://developer.garmin.com/fit/download/>  
   - Also: <https://github.com/garmin/fit-sdk-tools> and language SDKs such as
     <https://github.com/garmin/fit-javascript-sdk> (tag must match
     `fit_tool.SDK_VERSION`, currently Profile **21.212.0**).
2. **What you may commit**  
   - Only small, redistributable SDK examples that Garmin ships as samples.  
   - Do **not** commit proprietary device dumps, Connect exports with PII, or
     multi‑megabyte activities. Prefer synthetic constructors in tests.
3. **Licensing**  
   - Follow Garmin’s FIT SDK / sample license in the package you download.  
   - This repository already vendors a minimal subset under `sdk/` for CI; do
     not bulk-replace it with a full SDK tree.
4. **Profile spreadsheet**  
   - Bundled at `fit_tool/gen/Profile_21.212.0.xlsx` for codegen only; not a
     runtime fixture.

## Live interop (optional)

The default `pytest` run does **not** need Node or an external SDK checkout.
Committed goldens under `sdk/` and `interop/` are enough.

To run the live bidirectional Activity check against Garmin’s JavaScript SDK:

```bash
fit_profile_version=$(uv run python -c 'from fit_tool import SDK_VERSION; print(SDK_VERSION)')
git clone --depth 1 --branch "$fit_profile_version" \
  https://github.com/garmin/fit-javascript-sdk.git ../fit-javascript-sdk
FIT_JS_SDK_PATH=../fit-javascript-sdk \
  uv run pytest fit_tool/tests/test_garmin_sdk_interop.py -q
```

See also the README section **Run Garmin SDK interoperability tests**.

## Gap inventory (protocol / SHA-12 topics)

Maps protocol topics to fixtures or constructive tests after Stages 1–4
(C–J). Prefer promoting known-gap `xfail` cases over inventing silent skips.
User-facing Supported/Partial claims live in the repository `README.md`
capability matrix; residual §11 blockers are in
[`docs/FIT_CONFORMANCE_DESIGN.md`](../../../docs/FIT_CONFORMANCE_DESIGN.md) §11.

| Gap / topic | Status today | Fixture or generator | Primary tests | Stage |
| --- | --- | --- | --- | --- |
| Compressed timestamp offset + rollover | Supported (decode → field 253) | Constructive + unit helpers | `test_protocol_high_severity.py` | done |
| Chained multi-segment FIT | Supported | Constructive (`segment + segment`) | `test_protocol_high_severity.TestChainedAndTrailing` | done |
| Trailing bytes after last segment | Supported (`allow_trailing_bytes`) | Constructive | same | done |
| Component: `compressed_speed_distance` | Supported (Profile registry) | Constructive wire + in-memory | `test_protocol_high_severity.TestComponents`, `test_components.py`, `test_protocol_gap_fixtures` | C done |
| Component: `compressed_accumulated_power` + accumulate | Supported | In-memory expansion | same | C done |
| Component: 16-bit / 8-bit / 12-bit accumulator **rollover** | Supported | Constructive expansion helper | `test_components.py`, `test_protocol_gap_fixtures` | C done |
| Nested components (e.g. speed → enhanced_speed) | Supported | Constructive | `test_components.py` | C done |
| Full Profile **main-field** component set | Supported (37/37 sources, generated registry) | `fit_tool/profile/component_registry.py` | `test_components.TestRegistryCoverage` | C done |
| Subfield-gated components (event sport_point, etc.) | **Supported** (active subfield via D) | Constructive / unit | `test_components`, `test_subfields` | D done |
| Unknown **global** messages | Partial (`GenericMessage`) | Device/SDK files with odd IDs; wire decode | `test_wire.py`, SDK smokes | E |
| Unknown **field ids** on known messages | **Supported** (`UnknownField` + `raw_bytes`; unedited + post-edit preserve when not mutated) | Constructive definition + data | `test_protocol_gap_fixtures`, `test_post_edit_preservation` | E/F done |
| Subfields (e.g. `workout_step.duration_value`) | **Supported** (ref match + scale/units; multi-ref AND; PROFILE ERROR on ambiguity) | Constructive workout step | `test_subfields`, `test_protocol_gap_fixtures` | D done |
| Developer fields (common patterns) | Supported | `sdk/DeveloperData.fit`, `activity_developerdata.fit` | `test_sdk_files.py`, `test_developer_fields.py` | — |
| Header CRC (14-byte / extended) | Supported | Constructive | `test_protocol_high_severity.TestHeaderCRC` | done |
| File CRC | Supported | All CRC-checked loads | suite-wide | done |
| Post-edit PRESERVATION | **Supported** (dirty records + mixed encode; opt-in PRESERVATION level) | Constructive | `test_post_edit_preservation`, encode policy tests | F done |
| Encode modes PRESERVE / CANONICAL | **Supported** | Constructive | `test_encode_policies` | G done |
| FILE_TYPE Activity / Workout / Course | **Supported** for those three; other types fail closed | SDK Activity/Workout + Course builders | `test_validation`, `test_workout_files`, `test_course_files` | I/J done |
| PROFILE scopes CORE / DOMAIN / FULL | **Partial** (CORE default; DOMAIN/FULL = base-type + closed-enum; no native required/units yet) | Gen `field_catalog` + constructive | `test_profile_scope`, `test_validation` | H done (scoped) |

Legend: rows marked **Partial** or residual §11 items are incomplete relative to
full design-doc DoD, not relative to the closed Multica stage letter.

## Adding fixtures

1. Prefer `protocol_fixture_helpers.build_fit_bytes(...)` or in-memory
   `FitFileBuilder` over new `.fit` blobs.
2. If a binary is required, keep it small and document origin in this README.
3. Resolve paths with `Path(__file__).resolve().parent / 'data' / ...`.
4. Never write into this directory from tests; use `fit_tool/tests/out/` or
   pytest tmp paths.

## Related design docs

- [`docs/FIT_CONFORMANCE_DESIGN.md`](../../../docs/FIT_CONFORMANCE_DESIGN.md) — target architecture and Phase 0 golden corpus list (§9.1)
- Repository `README.md` capability matrix — what ships today
