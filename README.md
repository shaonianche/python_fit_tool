> **Note**: This is a community-maintained fork. The original package was removed from PyPI by its author and cannot be restored. This repository continues development and publishing under the same package name.

A library for reading and writing Garmin FIT files.

## Background

> The Flexible and Interoperable Data Transfer (FIT) protocol is designed specifically for the storing and sharing of data that originates from sport, fitness and health devices. The FIT protocol defines a set of data storage templates (FIT messages) that can be used to store information such as user profiles, activity data, courses, and workouts. It is specifically designed to be compact, interoperable and extensible.

[More info...](https://developer.garmin.com/fit/overview/)

Installation
==================

### Using uv (recommended)

```bash
uv add fit-tool
```

### Using pip

```bash
python3 -m pip install --upgrade pip
python3 -m pip install --upgrade fit-tool
```

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

The protocol-conformance architecture and implementation roadmap are documented
in [`docs/FIT_CONFORMANCE_DESIGN.md`](docs/FIT_CONFORMANCE_DESIGN.md).

### Minimal read/convert example

```python
from pathlib import Path

from fit_tool.fit_file import FitFile

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
from fit_tool.fit_file import FitFile

for record in FitFile.iter_file("activity.fit"):
    process(record)
```

CRC validation is performed when the iterator is fully exhausted. `FitFile.iter_stream()` accepts an already-open
binary stream. Builders can serialize directly with `FitFileBuilder.build_bytes()` when a `FitFile` object is not needed.

### Validate generated FIT files

`FitFileBuilder` always validates wire-level limits such as local message numbers and Definition Message field sizes.
Use strict mode to additionally validate Developer Field declarations, `file_id` ordering, and Activity file message
cardinality before bytes are produced:

```python
from fit_tool.fit_file_builder import FitFileBuilder

builder = FitFileBuilder(strict=True)
builder.add_all(messages)
fit_bytes = builder.build_bytes()
```

Strict file-type rules currently cover Activity files and fail closed for other file types. Existing builder calls remain
compatible because profile-level strict validation is opt-in.

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
