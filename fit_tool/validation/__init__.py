"""Composable FIT validation: wire, profile, file-type, and preservation levels.

Validation is a first-class API independent of :class:`~fit_tool.fit_file_builder.FitFileBuilder`.
Builder ``strict=True`` is a thin wrapper that runs the same checks and raises on errors.

Levels (aligned with ``docs/FIT_CONFORMANCE_DESIGN.md``):

* **WIRE** — local IDs, definition layout, data-record size vs definition
* **PROFILE** — Profile semantics under a selectable :class:`ProfileScope`
  (CORE / DOMAIN / FULL). Default scope is **CORE** (developer-field rules +
  ambiguous native subfields). DOMAIN and FULL add data-driven native base-type
  and closed-enum checks from the gen-exported field catalog (design doc §3.1 O1).
  FULL is **opt-in**, never the default for ``strict=True`` / :data:`DEFAULT_LEVELS`.
* **FILE_TYPE** — ``file_id`` rules plus required messages/fields for
  **Activity**, **Workout**, and **Course**
* **PRESERVATION** — opt-in checks for post-edit rewrite loss (e.g. unknown
  field ``raw_bytes`` cleared). Not part of default / strict levels.

File-type rules are implemented for Activity, Workout, and Course
(:data:`IMPLEMENTED_FILE_TYPES`). Other ``file_id.type`` values fail closed at
the FILE_TYPE level (intentional until more validators exist).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING

from fit_tool.data_message import DataMessage
from fit_tool.record import Record
from fit_tool.validation.context import ValidationContext, build_context
from fit_tool.validation.file_types import (
    IMPLEMENTED_FILE_TYPES,
    collect_file_type_findings,
)
from fit_tool.validation.preservation import collect_preservation_findings
from fit_tool.validation.profile import (
    DOMAIN_MESSAGE_IDS,
    collect_profile_findings,
    profile_rule_coverage,
)
from fit_tool.validation.report import (
    DEFAULT_LEVELS,
    DEFAULT_PROFILE_SCOPE,
    KNOWN_LEVELS,
    STRICT_LEVELS,
    ConformanceLevel,
    ProfileScope,
    Severity,
    ValidationFinding,
    ValidationReport,
    normalize_levels,
    normalize_profile_scope,
)
from fit_tool.validation.wire import (
    MAX_FIELD_COUNT,
    MAX_FIELD_NUMBER,
    MAX_FIELD_SIZE,
    MAX_GLOBAL_MESSAGE_NUMBER,
    MAX_LOCAL_MESSAGE_NUMBER,
    collect_wire_findings,
    validate_data_message,
    validate_definition,
    validate_message_header,
)

if TYPE_CHECKING:
    from fit_tool.fit_file import FitFile


def _records_from_source(source: FitFile | Sequence[Record]) -> list[Record]:
    if hasattr(source, 'records'):
        return list(source.records)
    return list(source)


def validate_fit_file(
    source: FitFile | Sequence[Record],
    levels: Iterable[ConformanceLevel] | None = None,
    *,
    profile_scope: ProfileScope | None = None,
    raise_on_error: bool = False,
) -> ValidationReport:
    """Validate a :class:`~fit_tool.fit_file.FitFile` or ordered record list.

    Parameters
    ----------
    source:
        A :class:`FitFile` or a sequence of :class:`~fit_tool.record.Record`.
    levels:
        Conformance levels to run. Defaults to WIRE + PROFILE + FILE_TYPE.
        Pass ``{ConformanceLevel.PRESERVATION}`` (or include it) for opt-in
        post-edit loss checks. PRESERVATION is **not** in the default set.
    profile_scope:
        Depth of PROFILE rules when :attr:`ConformanceLevel.PROFILE` is selected.
        Defaults to :data:`DEFAULT_PROFILE_SCOPE` (**CORE**). Pass
        :attr:`ProfileScope.DOMAIN` or :attr:`ProfileScope.FULL` for native
        field/enum checks from the gen-exported Profile catalog. FULL is never
        the default for Builder ``strict=True``.
    raise_on_error:
        If true, raise :class:`FitValidationError` when any ERROR findings exist
        (first error message is used, matching historical Builder strict behavior).

    Returns
    -------
    ValidationReport
        Collected findings. Truthy when there are no errors.
    """
    selected = normalize_levels(levels)
    selected_scope = normalize_profile_scope(profile_scope)
    records = _records_from_source(source)
    findings: list[ValidationFinding] = []
    context = build_context(records, findings, selected_scope)

    if ConformanceLevel.WIRE in selected:
        collect_wire_findings(context)
    if ConformanceLevel.PROFILE in selected:
        collect_profile_findings(context)
    if ConformanceLevel.FILE_TYPE in selected:
        collect_file_type_findings(context)
    if ConformanceLevel.PRESERVATION in selected:
        collect_preservation_findings(context)

    report = ValidationReport(findings)
    if raise_on_error:
        report.raise_for_errors()
    return report


class FitFileValidator:
    """Validate ordered FIT records (legacy raise-only facade).

    Prefer :func:`validate_fit_file` for report mode and level selection.
    This class preserves the historical ``FitFileValidator(records).validate()``
    raise-on-error behavior used by Builder ``strict=True``.
    """

    def __init__(self, records: list):
        self.records = records
        self.data_messages = [
            record.message for record in records
            if not record.is_definition and isinstance(record.message, DataMessage)
        ]

    def validate(self) -> None:
        """Run WIRE + PROFILE + FILE_TYPE and raise on the first error."""
        validate_fit_file(self.records, levels=STRICT_LEVELS, raise_on_error=True)

    def _validate_definitions_and_data(self) -> None:
        report = validate_fit_file(self.records, levels={ConformanceLevel.WIRE})
        report.raise_for_errors()

    def _validate_developer_fields(self) -> None:
        report = validate_fit_file(self.records, levels={ConformanceLevel.PROFILE})
        report.raise_for_errors()

    def _validate_file_type(self) -> None:
        report = validate_fit_file(self.records, levels={ConformanceLevel.FILE_TYPE})
        report.raise_for_errors()


__all__ = [
    'ConformanceLevel',
    'DEFAULT_LEVELS',
    'DEFAULT_PROFILE_SCOPE',
    'DOMAIN_MESSAGE_IDS',
    'FitFileValidator',
    'IMPLEMENTED_FILE_TYPES',
    'KNOWN_LEVELS',
    'MAX_FIELD_COUNT',
    'MAX_FIELD_NUMBER',
    'MAX_FIELD_SIZE',
    'MAX_GLOBAL_MESSAGE_NUMBER',
    'MAX_LOCAL_MESSAGE_NUMBER',
    'ProfileScope',
    'STRICT_LEVELS',
    'Severity',
    'ValidationContext',
    'ValidationFinding',
    'ValidationReport',
    'profile_rule_coverage',
    'validate_data_message',
    'validate_definition',
    'validate_fit_file',
    'validate_message_header',
]
