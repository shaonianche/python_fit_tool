"""fit-tool: a library for reading and writing Garmin FIT files.

The stable application-facing surface is defined in :mod:`fit_tool.api` and
re-exported from this package. Prefer::

    from fit_tool import FitFile, FitFileBuilder, FitCRCError, SDK_VERSION

Existing deep imports (for example ``from fit_tool.fit_file import FitFile``)
continue to work; no modules are moved or removed in this change.
"""

# Version and format constants must be defined before re-exports so modules that
# import ``from fit_tool import SDK_VERSION`` during package initialization
# (e.g. fit_file_header) see a fully assigned name.
PROTOCOL_VERSION = '2.4'
SDK_VERSION = '21.205.0'
FIT_DATA_TYPE = b'.FIT'

from fit_tool.api import (  # noqa: E402
    ConformanceLevel,
    FitCRCError,
    FitEncodingError,
    FitError,
    FitFile,
    FitFileBuilder,
    FitHeaderError,
    FitParseError,
    FitRecordError,
    FitValidationError,
    Severity,
    ValidationFinding,
    ValidationReport,
    validate_fit_file,
)

__all__ = [
    'PROTOCOL_VERSION',
    'SDK_VERSION',
    'FIT_DATA_TYPE',
    'FitFile',
    'FitFileBuilder',
    'FitError',
    'FitParseError',
    'FitHeaderError',
    'FitRecordError',
    'FitCRCError',
    'FitEncodingError',
    'FitValidationError',
    'ConformanceLevel',
    'Severity',
    'ValidationFinding',
    'ValidationReport',
    'validate_fit_file',
]
