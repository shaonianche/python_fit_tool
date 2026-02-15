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
