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
     `fit_tool.SDK_VERSION`, currently Profile **21.205.0**).
2. **What you may commit**  
   - Only small, redistributable SDK examples that Garmin ships as samples.  
   - Do **not** commit proprietary device dumps, Connect exports with PII, or
     multi‑megabyte activities. Prefer synthetic constructors in tests.
3. **Licensing**  
   - Follow Garmin’s FIT SDK / sample license in the package you download.  
   - This repository already vendors a minimal subset under `sdk/` for CI; do
     not bulk-replace it with a full SDK tree.
4. **Profile spreadsheet**  
   - Bundled at `fit_tool/gen/Profile_21.205.0.xlsx` for codegen only; not a
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

## Gap inventory (protocol / Stage 2 topics)

Maps known conformance gaps to fixtures or constructive tests. Stage-2 work
(C/D/E) should promote `xfail` cases rather than invent new silent skips.

| Gap / topic | Status today | Fixture or generator | Primary tests | Stage |
| --- | --- | --- | --- | --- |
| Compressed timestamp offset + rollover | Supported | Constructive + unit helpers | `test_protocol_high_severity.py` | done |
| Chained multi-segment FIT | Supported | Constructive (`segment + segment`) | `test_protocol_high_severity.TestChainedAndTrailing` | done |
| Trailing bytes after last segment | Supported (`allow_trailing_bytes`) | Constructive | same | done |
| Component: `compressed_speed_distance` | Supported (Profile registry) | Constructive wire + in-memory | `test_protocol_high_severity.TestComponents`, `test_components.py`, `test_protocol_gap_fixtures` | C done |
| Component: `compressed_accumulated_power` + accumulate | Supported | In-memory expansion | same | C done |
| Component: 16-bit / 8-bit / 12-bit accumulator **rollover** | Supported | Constructive expansion helper | `test_components.py`, `test_protocol_gap_fixtures` | C done |
| Nested components (e.g. speed → enhanced_speed) | Supported | Constructive | `test_components.py` | C done |
| Full Profile **main-field** component set | Supported (37/37 sources, generated registry) | `fit_tool/profile/component_registry.py` | `test_components.TestRegistryCoverage` | C done |
| Subfield-gated components (event sport_point, etc.) | **Gap** (needs D) | deferred | Stage 2 D | D |
| Unknown **global** messages | Partial (`GenericMessage`) | Device/SDK files with odd IDs; wire decode | `test_wire.py`, SDK smokes | E |
| Unknown **field ids** on known messages | **Supported** (`UnknownField` + `raw_bytes` on decode; unedited preserve ok) | Constructive definition + data | `test_protocol_gap_fixtures` | E |
| Subfields (e.g. `workout_step.duration_value`) | **Supported** (ref match + scale/units; multi-ref AND; PROFILE ERROR on ambiguity) | Constructive workout step | `test_subfields`, `test_protocol_gap_fixtures` | D |
| Developer fields (common patterns) | Supported | `sdk/DeveloperData.fit`, `activity_developerdata.fit` | `test_sdk_files.py`, `test_developer_fields.py` | — |
| Header CRC (14-byte / extended) | Supported | Constructive | `test_protocol_high_severity.TestHeaderCRC` | done |
| File CRC | Supported | All CRC-checked loads | suite-wide | done |
| Post-edit PRESERVATION | **Gap** | Untouched preserve tests only | `test_protocol_high_severity.TestPreservationEncode` | F |
| FILE_TYPE Workout / Course rules | **Gap** (not Stage 1) | Builder examples / later | deferred | I/J |
| Full PROFILE validation | **Gap** | deferred | deferred | H |

Legend: **Gap** = behavior incomplete or incorrect relative to design doc;
constructive tests may assert current behavior and mark the desired semantics
with `@pytest.mark.xfail(strict=True, reason='… Stage N …')`.

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
