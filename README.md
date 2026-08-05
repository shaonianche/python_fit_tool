> **Note**: This is a community-maintained fork. The original package was removed from PyPI by its author and cannot be restored. This repository continues development and publishing under the same package name.

A Python library for reading and writing Garmin FIT files — practical for
common Activity, Workout, and Course workflows.

**What works / what we do not claim** (capability matrix, validation levels,
encode policies): [`docs/CAPABILITY_BOUNDARY.md`](docs/CAPABILITY_BOUNDARY.md).

Long-term strict-conformance **roadmap** (target architecture, not current
guarantees): [`docs/FIT_CONFORMANCE_DESIGN.md`](docs/FIT_CONFORMANCE_DESIGN.md).

Profile in use: `21.212.0` (`fit_tool.SDK_VERSION`).

## Installation

Runtime has **no** third-party dependencies.

```bash
uv add fit-tool
# or
python3 -m pip install --upgrade fit-tool
```

Optional profile regeneration (maintainers only):

```bash
uv add 'fit-tool[gen]'   # openpyxl, inflection, jinja2
uv run gen-profile
```

## CLI

```bash
fit-tool activity.fit                 # → CSV
fit-tool -t fit -o out.fit in.fit
fit-tool -h
```

## Public API

Import the stable surface from the package root:

```python
from fit_tool import (
    FitFile,
    FitFileBuilder,
    EncodeMode,
    EncodeOptions,
    ConformanceLevel,
    ProfileScope,
    validate_fit_file,
    FitError,
    FitParseError,
    FitCRCError,
    FitValidationError,
    PROTOCOL_VERSION,
    SDK_VERSION,
)
```

| Symbol | Role |
| --- | --- |
| `FitFile` | Load, inspect, stream, serialize, validate |
| `FitFileBuilder` | Build FIT files from messages |
| `EncodeMode` / `EncodeOptions` | PRESERVE vs CANONICAL encode policies |
| `validate_fit_file` / `ConformanceLevel` / `ProfileScope` | Composable validation |
| `FitError` and subclasses | Typed parse / CRC / encode / validation errors |
| `PROTOCOL_VERSION` / `SDK_VERSION` | Bundled protocol and Profile version strings |

Profile messages are **not** re-exported at the root:

```python
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.messages.record_message import RecordMessage
from fit_tool.profile.profile_type import FileType, Sport
```

| Mode | API |
| --- | --- |
| Create | `RecordMessage()` |
| Decode projection | `RecordMessage.from_definition(definition, ...)` |

Deep imports (`from fit_tool.fit_file import FitFile`) still work; prefer the
package root for new code.

## Examples

### Read and convert to CSV

```python
from fit_tool import FitFile

fit = FitFile.from_file("activity.fit")
fit.to_csv("activity.csv")
```

### Stream large files (bounded memory)

```python
from fit_tool import FitFile

for record in FitFile.iter_file("activity.fit"):
    process(record)  # CRC checked when the iterator is exhausted
```

### Build a small Activity

```python
from fit_tool import FitFileBuilder
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.messages.record_message import RecordMessage
from fit_tool.profile.profile_type import FileType, Manufacturer

builder = FitFileBuilder(auto_define=True)
file_id = FileIdMessage()
file_id.type = FileType.ACTIVITY
file_id.manufacturer = Manufacturer.DEVELOPMENT
file_id.product = 0
file_id.serial_number = 1
file_id.time_created = 1_700_000_000_000
builder.add(file_id)

record = RecordMessage()
record.timestamp = 1_700_000_000_000
record.heart_rate = 120
builder.add(record)

data = builder.build_bytes()
# FitFileBuilder(strict=True) also runs WIRE + PROFILE(CORE) + FILE_TYPE
# (Activity needs lap/session/activity messages — see examples/).
```

### Validate

```python
from fit_tool import FitFile, ProfileScope, validate_fit_file, ConformanceLevel

fit = FitFile.from_file("activity.fit")
report = fit.validate()
if report.has_errors:
    print(report.errors)

# Opt-in deeper PROFILE rules (never the default for strict)
validate_fit_file(fit, profile_scope=ProfileScope.FULL)
```

### Encode modes

```python
from fit_tool import EncodeMode, FitFile

fit = FitFile.from_bytes(raw)
fit.to_bytes()                              # PRESERVE (default)
fit.to_bytes(mode=EncodeMode.CANONICAL)
fit.to_bytes(mode=EncodeMode.CANONICAL, strict=True)
```

Details: [capability boundary — encode policies](docs/CAPABILITY_BOUNDARY.md#encode-policies).

### Repository examples

```bash
uv run python fit_tool/examples/read_activity_example.py
uv run python fit_tool/examples/modify_activity_example.py
uv run python fit_tool/examples/write_workout_example.py
```

`write_activity_example.py` / `write_course_example.py` need extra packages
(`gpxpy`, `geopy`, …).

## Further documentation

| Doc | Contents |
| --- | --- |
| [`docs/CAPABILITY_BOUNDARY.md`](docs/CAPABILITY_BOUNDARY.md) | Supported / partial / incomplete matrix; validation & encode details |
| [`docs/FIT_CONFORMANCE_DESIGN.md`](docs/FIT_CONFORMANCE_DESIGN.md) | Target architecture and roadmap |
| [`docs/EPIC_SHA12_RELEASE_NOTES.md`](docs/EPIC_SHA12_RELEASE_NOTES.md) | Protocol-capability epic rollup notes |
| [`docs/RELEASING.md`](docs/RELEASING.md) | Maintainer checklist for PyPI / GitHub releases |
| [`fit_tool/tests/data/README.md`](fit_tool/tests/data/README.md) | Fixture inventory and gap map |
