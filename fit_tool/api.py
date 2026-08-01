"""Stable public API for application users.

Prefer importing symbols from the package root::

    from fit_tool import FitFile, FitFileBuilder, FitCRCError

Deep imports such as ``from fit_tool.fit_file import FitFile`` remain supported
for backward compatibility; the package root is the documented entry point.

Profile message classes are generated and live under
``fit_tool.profile.messages``. They are intentionally not re-exported here so
that package import stays light and each message stays discoverable by name.
Import them by module path, for example::

    from fit_tool.profile.messages.record_message import RecordMessage
    from fit_tool.profile.profile_type import Sport, FileType
"""

from fit_tool.encode import EncodeMode, EncodeOptions
from fit_tool.exceptions import (
    FitCRCError,
    FitEncodingError,
    FitError,
    FitHeaderError,
    FitParseError,
    FitRecordError,
    FitValidationError,
)
from fit_tool.fit_file import FitFile
from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.validation import (
    ConformanceLevel,
    ProfileScope,
    Severity,
    ValidationFinding,
    ValidationReport,
    profile_rule_coverage,
    validate_fit_file,
)

__all__ = [
    'FitFile',
    'FitFileBuilder',
    'FitError',
    'FitParseError',
    'FitHeaderError',
    'FitRecordError',
    'FitCRCError',
    'FitEncodingError',
    'FitValidationError',
    'EncodeMode',
    'EncodeOptions',
    'ConformanceLevel',
    'ProfileScope',
    'Severity',
    'ValidationFinding',
    'ValidationReport',
    'profile_rule_coverage',
    'validate_fit_file',
]
