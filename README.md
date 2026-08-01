> **Note**: This is a community-maintained fork. The original package was removed from PyPI by its author and cannot be restored. This repository continues development and publishing under the same package name.

A library for reading and writing Garmin FIT files — strong for common Activity
and Workout workflows, not a full Garmin FIT protocol implementation.

## Background

> The Flexible and Interoperable Data Transfer (FIT) protocol is designed specifically for the storing and sharing of data that originates from sport, fitness and health devices. The FIT protocol defines a set of data storage templates (FIT messages) that can be used to store information such as user profiles, activity data, courses, and workouts. It is specifically designed to be compact, interoperable and extensible.

[More info...](https://developer.garmin.com/fit/overview/)

## Capability boundary

This library is suitable for everyday Activity / Workout / Course read-write,
CSV export, and typed message editing. It does **not** claim full Garmin FIT
protocol or Profile conformance.

The long-term architecture and strict-conformance roadmap live in
[`docs/FIT_CONFORMANCE_DESIGN.md`](docs/FIT_CONFORMANCE_DESIGN.md). That document
describes the **target** design; it is not a guarantee of what the current
package already implements. Profile version in use: `21.205.0` (see
`fit_tool/gen/`).

| Status | Capabilities |
| --- | --- |
| **Supported** | Common Activity and Workout read/write via typed profile messages; `FitFileBuilder` encode path; **header CRC** (14-byte headers) and **file-level CRC** on load / stream exhaustion (`check_crc=True` default); developer fields for common declaration patterns; streaming iterators (`FitFile.iter_file` / `iter_stream`); CSV export (`to_csv` / `to_rows`); Course and similar message types when you construct them yourself; **chained multi-segment** FIT decode via `from_bytes` / `from_file` (all segments projected into `records`); **compressed timestamp** reconstruction into field 253; **component expansion** for known packed fields (e.g. `compressed_speed_distance`); **preservation encode** (`to_bytes(preserve=True)`, default) when the file was buffer-decoded and not edited |
| **Partial** | Unknown global messages via `GenericMessage` (readable; preservation rewrite keeps original bytes only while `wire_document` is intact); composable validation API (`validate_fit_file` / `FitFile.validate`) with WIRE + PROFILE + Activity FILE_TYPE levels — **PROFILE is a developer-field subset**, not full Garmin Profile field/enum checks; Builder `strict=True` is a thin wrapper over the same checks; component registry covers common record packed fields (not every Profile component until codegen re-enables full metadata) |
| **Not supported / incomplete** | Full PROFILE semantics (native field requirements, enums, units, subfields); file-type rules for non-Activity types (FILE_TYPE level fails closed); full PRESERVATION conformance level after in-memory edits (edited files re-encode from projected messages); every Profile component/accumulator not yet listed in the runtime registry |

If you need a construct listed as incomplete, prefer an official Garmin SDK or
wait for the phased work in the design doc. Architecture reviews should judge
this package against the matrix above, not against full protocol conformance.

Installation
==================

The runtime library and `fit-tool` CLI have no third-party dependencies.
Optional packages are only needed for profile generation (maintainers regenerating
code from the Garmin Profile spreadsheet).

### Using uv (recommended)

```bash
uv add fit-tool
```

### Using pip

```bash
python3 -m pip install --upgrade pip
python3 -m pip install --upgrade fit-tool
```

### Profile generation tooling (optional)

Regenerating `fit_tool/profile/` from the Garmin Profile spreadsheet requires the
`gen` extra (`openpyxl`, `inflection`, `jinja2`):

```bash
# pip
python3 -m pip install 'fit-tool[gen]'

# uv (published package)
uv add 'fit-tool[gen]'

# local checkout (dev group already includes gen deps for the full test suite)
uv sync --group dev
# or, without the full dev toolchain:
uv sync --extra gen
```

Then run:

```bash
uv run gen-profile
```

Without the gen extra, `gen-profile` exits with an install hint. End users who
only read/write FIT files do not need these packages.

Command line interface
=======================

```console
usage: fit-tool [-h] [-v] [-o OUTPUT] [-l LOG] [-t {csv,fit}] FILE

Tool for managing FIT files.

positional arguments:
  FILE                  FIT file to process

options:
  -h, --help            show this help message and exit
  -v, --verbose         specify verbose output
  -o, --output OUTPUT   Output filename.
  -l, --log LOG         Log filename.
  -t, --type {csv,fit}  Output format type. Options: csv, fit.
```

### Convert file to CSV

```bash
# Using uvx
uvx fit-tool oldstage.fit

# Or after installation
fit-tool oldstage.fit
```

Library Usage
=======================

See [Capability boundary](#capability-boundary) for what works today. The
strict-conformance roadmap (target architecture, not current guarantees) is in
[`docs/FIT_CONFORMANCE_DESIGN.md`](docs/FIT_CONFORMANCE_DESIGN.md).

### Public API

Application code should import the stable surface from the package root:

```python
from fit_tool import (
    FitFile,
    FitFileBuilder,
    FitError,
    FitParseError,
    FitCRCError,
    FitValidationError,
    ConformanceLevel,
    validate_fit_file,
    PROTOCOL_VERSION,
    SDK_VERSION,
)
```

| Symbol | Role |
| --- | --- |
| `FitFile` | Load, inspect, stream, serialize, and validate FIT files |
| `FitFileBuilder` | Build FIT files from messages |
| `validate_fit_file`, `ConformanceLevel`, `ValidationReport` | Composable validation (independent of Builder) |
| `FitError` and subclasses | Typed errors for parse, CRC, encode, and validation failures |
| `PROTOCOL_VERSION`, `SDK_VERSION`, `FIT_DATA_TYPE` | Bundled protocol/profile version metadata |

The same symbols are defined in `fit_tool.api` and re-exported by `fit_tool`.

**Profile messages** (generated types such as `RecordMessage`, `FileIdMessage`) are
not re-exported at the package root. Import them by module path:

```python
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.messages.record_message import RecordMessage
from fit_tool.profile.profile_type import FileType, Sport
```

Naming convention: message module is the snake_case form of the class
(`record_message` → `RecordMessage`), under `fit_tool.profile.messages`.

**Construction paths** (do not pass a definition into `__init__`):

| Mode | API | Use when |
| --- | --- | --- |
| Create / author | `RecordMessage()` | Writing new messages in a builder |
| Project / decode | `RecordMessage.from_definition(definition, developer_fields=...)` | Applying a local definition (decode path) |

`MessageFactory.from_definition` and the FitFile/wire projection path use the
definition factory. Example authoring:

```python
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.profile_type import FileType, Manufacturer

msg = FileIdMessage()
msg.type = FileType.ACTIVITY
msg.manufacturer = Manufacturer.DEVELOPMENT
```

**Compatibility:** deep imports such as `from fit_tool.fit_file import FitFile`
remain supported. Prefer the package-root form for new code. No deep-import paths
are removed in this release; future deprecations will be announced in the changelog.

### Minimal read/convert example

```python
from pathlib import Path

from fit_tool import FitFile

root = Path.cwd()
in_file = root / "fit_tool" / "tests" / "data" / "sdk" / "Activity.fit"
out_file = root / "fit_tool" / "tests" / "out" / "Activity.csv"
out_file.parent.mkdir(parents=True, exist_ok=True)

fit_file = FitFile.from_file(str(in_file))
fit_file.to_csv(str(out_file))
```

### Stream records from large FIT files

`FitFile.from_file()` loads a complete file and is convenient when records must be edited. For read-only,
record-by-record processing, use the streaming iterator to keep memory usage bounded:

```python
from fit_tool import FitFile

for record in FitFile.iter_file("activity.fit"):
    process(record)
```

CRC validation is performed when the iterator is fully exhausted. `FitFile.iter_stream()` accepts an already-open
binary stream. Builders can serialize directly with `FitFileBuilder.build_bytes()` when a `FitFile` object is not needed.

### Validate FIT files

Validation is a first-class API. Levels match the design doc
([`docs/FIT_CONFORMANCE_DESIGN.md`](docs/FIT_CONFORMANCE_DESIGN.md) §3):

| Level | What it checks | Status |
| --- | --- | --- |
| `ConformanceLevel.WIRE` | Local IDs, definition field layout/sizes, data records vs active definition | Implemented |
| `ConformanceLevel.PROFILE` | Developer field declarations (`developer_data_id` / `field_description`) and base-type consistency | Implemented as a **developer-field subset only** — not full Garmin Profile validation (enums, units, required native fields, subfields deferred) |
| `ConformanceLevel.FILE_TYPE` | `file_id` first/unique + required fields; Activity required messages and fields | **Activity only**; other `file_id.type` values **fail closed** (intentional until more validators exist) |

Call validation on any `FitFile` or record list — after decode or before encode:

```python
from fit_tool import ConformanceLevel, FitFile, validate_fit_file

fit_file = FitFile.from_file("activity.fit")

# Report mode (default: all implemented levels)
report = fit_file.validate()
if report.has_errors:
    for finding in report.errors:
        print(finding.level, finding.message)

# Raise on first error
fit_file.validate(raise_on_error=True)

# Wire-only (e.g. after decode, without file-type rules)
validate_fit_file(fit_file, levels={ConformanceLevel.WIRE})
```

`FitFileBuilder` always checks wire limits on `add` (local message numbers, definition
sizes). `strict=True` is a thin wrapper over the same API with all levels and
`raise_on_error=True`:

```python
from fit_tool import FitFileBuilder

builder = FitFileBuilder(strict=True)
builder.add_all(messages)
fit_bytes = builder.build_bytes()
```

Non-strict builders remain unchanged. Prefer `validate_fit_file` / `FitFile.validate`
when you need a report, level selection, or validation on the read path.

### Protocol fixture corpus and gap inventory

Committed samples live under [`fit_tool/tests/data/`](fit_tool/tests/data/). See
[`fit_tool/tests/data/README.md`](fit_tool/tests/data/README.md) for:

- layout of `sdk/`, `interop/`, and device smokes;
- a **gap inventory** mapping Stage-2 topics (components, subfields, unknown fields,
  multi-segment) to constructive helpers or fixtures;
- how to obtain additional Garmin SDK samples when licensing allows.

Prefer constructive builders in `fit_tool/tests/protocol_fixture_helpers.py` over
new large binary dumps. Known incomplete semantics are pinned with explicit
`xfail` in `fit_tool/tests/test_protocol_gap_fixtures.py` (no silent skips).

### Run Garmin SDK interoperability tests

The normal test suite includes committed Garmin SDK golden bytes. A live bidirectional test additionally generates the
same Activity with this library and the `fit-javascript-sdk` release matching `fit_tool.SDK_VERSION`, cross-decodes both
files, runs Garmin's integrity check, and compares normalized semantics:

```bash
fit_profile_version=$(uv run python -c 'from fit_tool import SDK_VERSION; print(SDK_VERSION)')
git clone --depth 1 --branch "$fit_profile_version" \
  https://github.com/garmin/fit-javascript-sdk.git ../fit-javascript-sdk
FIT_JS_SDK_PATH=../fit-javascript-sdk \
  uv run pytest fit_tool/tests/test_garmin_sdk_interop.py -q
```

CI resolves and checks out the matching official SDK tag in a dedicated interoperability job. The test intentionally
does not require the two legal FIT encodings to be byte-for-byte identical.

### Runnable examples in this repository

These examples are synchronized with the current codebase and are runnable from the repository root:

```bash
uv run python fit_tool/examples/read_activity_example.py
uv run python fit_tool/examples/modify_activity_example.py
uv run python fit_tool/examples/write_workout_example.py
```

Output files are written to `fit_tool/tests/out/`.

### Optional examples that require extra packages

`write_activity_example.py` and `write_course_example.py` depend on `gpxpy` and `geopy`.
The plotting workflow depends on `numpy` and `matplotlib`.

Install extras first, then run:

```bash
uv add gpxpy geopy numpy matplotlib
uv run python fit_tool/examples/write_activity_example.py
uv run python fit_tool/examples/write_course_example.py
```
