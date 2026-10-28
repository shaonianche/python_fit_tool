"""Validation report types, severity levels, and profile scopes."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

from fit_tool.exceptions import FitValidationError


class ConformanceLevel(Enum):
    """Independently selectable validation dimensions."""

    WIRE = 'wire'
    PROFILE = 'profile'
    FILE_TYPE = 'file_type'
    PRESERVATION = 'preservation'


class ProfileScope(Enum):
    """Depth of :attr:`ConformanceLevel.PROFILE` rules (design doc §3.1 O1).

    * **CORE** — developer-field declarations + ambiguous subfield ERROR.
      Default for :data:`DEFAULT_LEVELS` / Builder ``strict=True``.
    * **DOMAIN** — CORE plus native base-type and closed-enum checks on
      high-frequency Activity/Workout messages (:data:`DOMAIN_MESSAGE_IDS`).
    * **FULL** — CORE plus the same native rules for **all** messages in the
      bundled Profile field catalog. Explicit opt-in only.
    """

    CORE = 'core'
    DOMAIN = 'domain'
    FULL = 'full'


class Severity(Enum):
    """Finding severity at a conformance level."""

    ERROR = 'error'
    WARNING = 'warning'
    INFO = 'info'


# Default / Builder-strict levels. PRESERVATION is opt-in (post-edit loss checks).
DEFAULT_LEVELS = frozenset({
    ConformanceLevel.WIRE,
    ConformanceLevel.PROFILE,
    ConformanceLevel.FILE_TYPE,
})

# Builder(strict=True) and FitFileValidator().validate() use all default levels.
STRICT_LEVELS = DEFAULT_LEVELS

# PROFILE scope for DEFAULT_LEVELS / strict. FULL must never be the default.
DEFAULT_PROFILE_SCOPE = ProfileScope.CORE

# All levels recognized by validate_fit_file (includes opt-in PRESERVATION).
KNOWN_LEVELS = frozenset(ConformanceLevel)


@dataclass(frozen=True)
class ValidationFinding:
    """One validation finding at a conformance level."""

    level: ConformanceLevel
    severity: Severity
    message: str
    record_index: int | None = None

    def __str__(self) -> str:
        location = f' @ record {self.record_index}' if self.record_index is not None else ''
        return f'[{self.level.value}/{self.severity.value}]{location} {self.message}'


class ValidationReport:
    """Collected findings from :func:`validate_fit_file`."""

    def __init__(self, findings: Sequence[ValidationFinding] | None = None):
        self.findings: list[ValidationFinding] = list(findings or ())

    @property
    def errors(self) -> list[ValidationFinding]:
        return [finding for finding in self.findings if finding.severity is Severity.ERROR]

    @property
    def warnings(self) -> list[ValidationFinding]:
        return [finding for finding in self.findings if finding.severity is Severity.WARNING]

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    def raise_for_errors(self) -> None:
        """Raise :class:`FitValidationError` with the first error message, if any."""
        errors = self.errors
        if not errors:
            return
        raise FitValidationError(errors[0].message)

    def __bool__(self) -> bool:
        return not self.has_errors

    def __repr__(self) -> str:
        return f'ValidationReport(findings={self.findings!r})'


def enum_value(value: Any) -> Any:
    """Return the raw value of an enum-like value, else the value itself."""
    return value.value if hasattr(value, 'value') else value


def normalize_levels(levels: Iterable[ConformanceLevel] | None) -> frozenset:
    if levels is None:
        return DEFAULT_LEVELS
    normalized = frozenset(levels)
    if not normalized:
        raise FitValidationError('levels must contain at least one ConformanceLevel')
    unknown = normalized - KNOWN_LEVELS
    if unknown:
        names = ', '.join(sorted(level.value for level in unknown))
        raise FitValidationError(f'Unsupported conformance level(s): {names}')
    return normalized


def normalize_profile_scope(scope: ProfileScope | None) -> ProfileScope:
    if scope is None:
        return DEFAULT_PROFILE_SCOPE
    if not isinstance(scope, ProfileScope):
        raise FitValidationError(
            f'profile_scope must be a ProfileScope, got {type(scope).__name__}'
        )
    return scope


def add_error(
        findings: list[ValidationFinding],
        level: ConformanceLevel,
        message: str,
        record_index: int | None = None,
) -> None:
    findings.append(
        ValidationFinding(
            level=level,
            severity=Severity.ERROR,
            message=message,
            record_index=record_index,
        )
    )
