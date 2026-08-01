"""Composable FIT validation: wire, profile, file-type, and preservation levels.

Validation is a first-class API independent of :class:`~fit_tool.fit_file_builder.FitFileBuilder`.
Builder ``strict=True`` is a thin wrapper that runs the same checks and raises on errors.

Levels (aligned with ``docs/FIT_CONFORMANCE_DESIGN.md``):

* **WIRE** — local IDs, definition layout, data-record size vs definition
* **PROFILE** — developer-field declarations (``developer_data_id`` /
  ``field_description``) plus **ambiguous native subfield** matches.
  This is **not** full Garmin Profile validation (enums, units, required
  native fields per message, and broader subfield rule families remain deferred).
* **FILE_TYPE** — ``file_id`` rules plus Activity and Workout required
  messages/fields
* **PRESERVATION** — opt-in checks for post-edit rewrite loss (e.g. unknown
  field ``raw_bytes`` cleared). Not part of default / strict levels.

File-type rules are implemented for **Activity** and **Workout**. Other
``file_id.type`` values fail closed at the FILE_TYPE level (intentional until
more validators exist, e.g. Course).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

from fit_tool.base_type import BaseType
from fit_tool.data_message import DataMessage
from fit_tool.definition_message import DefinitionMessage
from fit_tool.exceptions import FitValidationError
from fit_tool.field import UnknownField
from fit_tool.message import Message
from fit_tool.profile.profile_type import FileType, MesgNum
from fit_tool.record import Record

if TYPE_CHECKING:
    from fit_tool.fit_file import FitFile

MAX_LOCAL_MESSAGE_NUMBER = 15
MAX_GLOBAL_MESSAGE_NUMBER = 65535
MAX_FIELD_NUMBER = 255
MAX_FIELD_SIZE = 255
MAX_FIELD_COUNT = 255

# file_id.type values with a FILE_TYPE rule set implemented today.
IMPLEMENTED_FILE_TYPES = frozenset({
    FileType.ACTIVITY.value,
    FileType.WORKOUT.value,
})


class ConformanceLevel(Enum):
    """Independently selectable validation dimensions."""

    WIRE = 'wire'
    PROFILE = 'profile'
    FILE_TYPE = 'file_type'
    PRESERVATION = 'preservation'


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


def _enum_value(value: Any) -> Any:
    return value.value if hasattr(value, 'value') else value


# All levels recognized by :func:`validate_fit_file` (includes opt-in PRESERVATION).
KNOWN_LEVELS = frozenset(ConformanceLevel)


def _normalize_levels(levels: Iterable[ConformanceLevel] | None) -> frozenset:
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


def _records_from_source(source: FitFile | Sequence[Record]) -> list[Record]:
    if hasattr(source, 'records'):
        return list(source.records)
    return list(source)


def validate_message_header(message: Message) -> None:
    """Validate values represented directly by FIT record/definition headers."""
    if not isinstance(message.local_id, int) or not 0 <= message.local_id <= MAX_LOCAL_MESSAGE_NUMBER:
        raise FitValidationError(
            f'local_id must be between 0 and {MAX_LOCAL_MESSAGE_NUMBER}, got {message.local_id!r}.'
        )

    if not isinstance(message.global_id, int) or not 0 <= message.global_id <= MAX_GLOBAL_MESSAGE_NUMBER:
        raise FitValidationError(
            f'global_id must be between 0 and {MAX_GLOBAL_MESSAGE_NUMBER}, got {message.global_id!r}.'
        )


def _validate_field_number_and_size(field_id: int, size: int, label: str) -> None:
    if not isinstance(field_id, int) or not 0 <= field_id <= MAX_FIELD_NUMBER:
        raise FitValidationError(f'{label} number must be between 0 and {MAX_FIELD_NUMBER}, got {field_id!r}.')
    if not isinstance(size, int) or not 1 <= size <= MAX_FIELD_SIZE:
        raise FitValidationError(f'{label} size must be between 1 and {MAX_FIELD_SIZE}, got {size!r}.')


def validate_definition(definition: DefinitionMessage) -> None:
    """Validate constraints imposed by the FIT Definition Message wire layout."""
    validate_message_header(definition)

    if len(definition.field_definitions) > MAX_FIELD_COUNT:
        raise FitValidationError(f'A definition can contain at most {MAX_FIELD_COUNT} native fields.')
    if len(definition.developer_field_definitions) > MAX_FIELD_COUNT:
        raise FitValidationError(f'A definition can contain at most {MAX_FIELD_COUNT} developer fields.')

    native_field_ids = set()
    for native_definition in definition.field_definitions:
        _validate_field_number_and_size(native_definition.field_id, native_definition.size, 'Field')
        if native_definition.field_id in native_field_ids:
            raise FitValidationError(f'Duplicate native field number {native_definition.field_id} in definition.')
        native_field_ids.add(native_definition.field_id)

        base_type_size = native_definition.base_type.size
        if native_definition.size % base_type_size:
            raise FitValidationError(
                f'Field {native_definition.field_id} size {native_definition.size} is not a multiple '
                f'of {native_definition.base_type.name} size {base_type_size}.'
            )

    developer_field_ids = set()
    for developer_definition in definition.developer_field_definitions:
        _validate_field_number_and_size(developer_definition.field_id, developer_definition.size, 'Developer field')
        if not 0 <= developer_definition.developer_data_index <= MAX_FIELD_NUMBER:
            raise FitValidationError(
                f'developer_data_index must be between 0 and {MAX_FIELD_NUMBER}, '
                f'got {developer_definition.developer_data_index!r}.'
            )
        key = (developer_definition.developer_data_index, developer_definition.field_id)
        if key in developer_field_ids:
            raise FitValidationError(
                f'Duplicate developer field {developer_definition.field_id} for developer_data_index '
                f'{developer_definition.developer_data_index}.'
            )
        developer_field_ids.add(key)


def validate_data_message(message: DataMessage, definition: DefinitionMessage) -> None:
    """Validate a data message against the active local definition."""
    validate_message_header(message)
    candidate = DefinitionMessage.from_data_message(message)
    if not definition.supports(candidate):
        raise FitValidationError(
            f'Active definition does not support {message.name} on local_id {message.local_id}.'
        )
    if message.size != definition.defined_data_size:
        raise FitValidationError(
            f'{message.name} encodes {message.size} bytes but its definition requires '
            f'{definition.defined_data_size}.'
        )


def _error(
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


def _collect_wire_findings(records: Sequence[Record], findings: list[ValidationFinding]) -> None:
    active_definitions = {}
    for record_index, record in enumerate(records):
        message = record.message
        if isinstance(message, DefinitionMessage):
            try:
                validate_definition(message)
            except FitValidationError as exc:
                _error(findings, ConformanceLevel.WIRE, str(exc), record_index)
                continue
            if not message.field_definitions:
                _error(
                    findings,
                    ConformanceLevel.WIRE,
                    f'Strict validation does not allow an empty definition for global_id {message.global_id}.',
                    record_index,
                )
            active_definitions[message.local_id] = message
        elif isinstance(message, DataMessage):
            definition = active_definitions.get(message.local_id)
            if definition is None:
                _error(
                    findings,
                    ConformanceLevel.WIRE,
                    f'{message.name} uses undefined local_id {message.local_id}.',
                    record_index,
                )
                continue
            try:
                validate_data_message(message, definition)
            except FitValidationError as exc:
                _error(findings, ConformanceLevel.WIRE, str(exc), record_index)


def _collect_profile_findings(
    data_messages: Sequence[DataMessage],
    findings: list[ValidationFinding],
    data_message_indices: Mapping[int, int],
) -> None:
    developer_data_indices = set()
    descriptions = {}

    for message_pos, message in enumerate(data_messages):
        record_index = data_message_indices.get(message_pos)
        if message.global_id == MesgNum.DEVELOPER_DATA_ID.value:
            developer_data_index = _enum_value(getattr(message, 'developer_data_index', None))
            if developer_data_index is None:
                _error(findings, ConformanceLevel.PROFILE, 'developer_data_id is missing developer_data_index.', record_index)
            else:
                application_id = getattr(message, 'application_id', None)
                if application_id is None or len(application_id) != 16:
                    _error(
                        findings,
                        ConformanceLevel.PROFILE,
                        'developer_data_id.application_id must contain exactly 16 bytes.',
                        record_index,
                    )
                if developer_data_index in developer_data_indices:
                    _error(
                        findings,
                        ConformanceLevel.PROFILE,
                        f'Duplicate developer_data_id for developer_data_index {developer_data_index}.',
                        record_index,
                    )
                else:
                    developer_data_indices.add(developer_data_index)

        elif message.global_id == MesgNum.FIELD_DESCRIPTION.value:
            developer_data_index = _enum_value(getattr(message, 'developer_data_index', None))
            field_number = _enum_value(getattr(message, 'field_definition_number', None))
            fit_base_type_id = _enum_value(getattr(message, 'fit_base_type_id', None))
            if developer_data_index not in developer_data_indices:
                _error(
                    findings,
                    ConformanceLevel.PROFILE,
                    f'field_description references developer_data_index {developer_data_index} '
                    f'before its developer_data_id message.',
                    record_index,
                )
            if field_number is None or fit_base_type_id is None:
                _error(
                    findings,
                    ConformanceLevel.PROFILE,
                    'field_description requires field_definition_number and fit_base_type_id.',
                    record_index,
                )
            else:
                try:
                    base_type = BaseType(fit_base_type_id)
                except ValueError:
                    _error(
                        findings,
                        ConformanceLevel.PROFILE,
                        f'field_description contains unknown fit_base_type_id {fit_base_type_id}.',
                        record_index,
                    )
                    base_type = None
                if base_type is not None:
                    key = (developer_data_index, field_number)
                    if key in descriptions:
                        _error(
                            findings,
                            ConformanceLevel.PROFILE,
                            f'Duplicate field_description for developer field {key}.',
                            record_index,
                        )
                    else:
                        descriptions[key] = base_type

        for developer_field in message.developer_fields:
            if not developer_field.is_valid():
                continue
            key = (developer_field.developer_data_index, developer_field.field_id)
            described_base_type = descriptions.get(key)
            if described_base_type is None:
                _error(
                    findings,
                    ConformanceLevel.PROFILE,
                    f'Developer field {key} is used before a matching field_description message.',
                    record_index,
                )
            elif described_base_type != developer_field.base_type:
                _error(
                    findings,
                    ConformanceLevel.PROFILE,
                    f'Developer field {key} uses {developer_field.base_type.name}, but its '
                    f'field_description declares {described_base_type.name}.',
                    record_index,
                )

        _collect_subfield_ambiguity_findings(message, findings, record_index)


def _collect_subfield_ambiguity_findings(
    message: DataMessage,
    findings: list[ValidationFinding],
    record_index: int | None,
) -> None:
    """PROFILE ERROR when more than one subfield matches the same ref values.

    Decode still picks the first match (see :meth:`Field.resolve_sub_field`);
    ambiguity is reported only at the PROFILE level.
    """
    fields = getattr(message, 'fields', None) or []
    if not fields:
        return
    for field in fields:
        if not getattr(field, 'sub_fields', None):
            continue
        if not field.is_valid():
            continue
        resolution = field.resolve_sub_field(fields)
        if not resolution.is_ambiguous:
            continue
        names = ', '.join(sub.name for sub in resolution.matches)
        _error(
            findings,
            ConformanceLevel.PROFILE,
            f'Ambiguous subfields for {message.name}.{field.name}: {names}.',
            record_index,
        )


def _require_fields_findings(
    findings: list[ValidationFinding],
    message: DataMessage,
    field_names: tuple,
    record_index: int | None,
) -> None:
    missing = [name for name in field_names if getattr(message, name, None) is None]
    if missing:
        _error(
            findings,
            ConformanceLevel.FILE_TYPE,
            f'{message.name} is missing required field(s): {", ".join(missing)}.',
            record_index,
        )


def _collect_file_type_findings(
    data_messages: Sequence[DataMessage],
    findings: list[ValidationFinding],
    data_message_indices: Mapping[int, int],
) -> None:
    if not data_messages:
        _error(findings, ConformanceLevel.FILE_TYPE, 'A FIT file must contain data messages.')
        return

    file_id_messages = [
        message for message in data_messages
        if message.global_id == MesgNum.FILE_ID.value
    ]
    if len(file_id_messages) != 1:
        _error(
            findings,
            ConformanceLevel.FILE_TYPE,
            f'A FIT file must contain exactly one file_id message; found {len(file_id_messages)}.',
        )
        return
    if data_messages[0] is not file_id_messages[0]:
        _error(
            findings,
            ConformanceLevel.FILE_TYPE,
            'file_id must be the first data message in a FIT file.',
            data_message_indices.get(0),
        )
        return

    file_id = file_id_messages[0]
    file_id_index = data_message_indices.get(0)
    file_type = _enum_value(getattr(file_id, 'type', None))
    if file_type is None:
        _error(findings, ConformanceLevel.FILE_TYPE, 'file_id.type is required.', file_id_index)
        return

    _require_fields_findings(
        findings,
        file_id,
        ('type', 'manufacturer', 'product', 'serial_number', 'time_created'),
        file_id_index,
    )

    message_counts = Counter(message.global_id for message in data_messages)
    if file_type == FileType.ACTIVITY.value:
        if message_counts[MesgNum.RECORD.value] < 1:
            _error(
                findings,
                ConformanceLevel.FILE_TYPE,
                'An activity FIT file requires at least one record message.',
            )
        if message_counts[MesgNum.LAP.value] < 1:
            _error(
                findings,
                ConformanceLevel.FILE_TYPE,
                'An activity FIT file requires at least one lap message.',
            )
        if message_counts[MesgNum.SESSION.value] < 1:
            _error(
                findings,
                ConformanceLevel.FILE_TYPE,
                'An activity FIT file requires at least one session message.',
            )
        activity_count = message_counts[MesgNum.ACTIVITY.value]
        if activity_count != 1:
            _error(
                findings,
                ConformanceLevel.FILE_TYPE,
                f'An activity FIT file requires exactly one activity message; found {activity_count}.',
            )
        _collect_activity_field_findings(data_messages, findings, data_message_indices)
    elif file_type == FileType.WORKOUT.value:
        workout_count = message_counts[MesgNum.WORKOUT.value]
        if workout_count != 1:
            _error(
                findings,
                ConformanceLevel.FILE_TYPE,
                f'A workout FIT file requires exactly one workout message; found {workout_count}.',
            )
        if message_counts[MesgNum.WORKOUT_STEP.value] < 1:
            _error(
                findings,
                ConformanceLevel.FILE_TYPE,
                'A workout FIT file requires at least one workout_step message.',
            )
        _collect_workout_field_findings(data_messages, findings, data_message_indices)
    else:
        _error(
            findings,
            ConformanceLevel.FILE_TYPE,
            f'Strict file-type validation is not implemented for file_id.type {file_type!r}.',
            file_id_index,
        )


def _collect_activity_field_findings(
    data_messages: Sequence[DataMessage],
    findings: list[ValidationFinding],
    data_message_indices: Mapping[int, int],
) -> None:
    required_fields = {
        MesgNum.RECORD.value: ('timestamp',),
        MesgNum.LAP.value: (
            'message_index',
            'timestamp',
            'start_time',
            'total_elapsed_time',
            'total_timer_time',
        ),
        MesgNum.SESSION.value: (
            'message_index',
            'timestamp',
            'start_time',
            'total_elapsed_time',
            'total_timer_time',
            'sport',
            'first_lap_index',
            'num_laps',
        ),
        MesgNum.ACTIVITY.value: ('timestamp', 'num_sessions', 'total_timer_time'),
    }
    for message_pos, message in enumerate(data_messages):
        field_names = required_fields.get(message.global_id)
        if field_names is not None:
            _require_fields_findings(
                findings,
                message,
                field_names,
                data_message_indices.get(message_pos),
            )


def _collect_workout_field_findings(
    data_messages: Sequence[DataMessage],
    findings: list[ValidationFinding],
    data_message_indices: Mapping[int, int],
) -> None:
    """Required fields for Workout FILE_TYPE (Garmin file-type + SDK samples).

    ``num_valid_steps`` is required on the workout message. Step count is not
    cross-checked against that value: official SDK Workout fixtures sometimes
    disagree (repeat meta-steps), and acceptance requires those fixtures to
    validate clean. ``workout_session`` is optional (multi-sport only).
    """
    required_fields = {
        MesgNum.WORKOUT.value: ('num_valid_steps',),
        MesgNum.WORKOUT_STEP.value: (
            'message_index',
            'duration_type',
            'target_type',
        ),
    }
    for message_pos, message in enumerate(data_messages):
        field_names = required_fields.get(message.global_id)
        if field_names is not None:
            _require_fields_findings(
                findings,
                message,
                field_names,
                data_message_indices.get(message_pos),
            )


def _collect_preservation_findings(
    records: Sequence[Record],
    findings: list[ValidationFinding],
) -> None:
    """Report post-edit rewrite risks (opt-in PRESERVATION level).

    Findings fire when an unknown native field lost its captured wire slice
    (``raw_bytes is None``) so a projected re-encode cannot guarantee the same
    bytes. Untouched records that still have ``source_bytes`` are fine.
    """
    for record_index, record in enumerate(records):
        if record.is_definition or not isinstance(record.message, DataMessage):
            continue
        message = record.message
        for field in message.fields:
            if not isinstance(field, UnknownField):
                continue
            if not field.is_valid():
                continue
            if field.raw_bytes is None:
                findings.append(
                    ValidationFinding(
                        level=ConformanceLevel.PRESERVATION,
                        severity=Severity.ERROR,
                        message=(
                            f'Unknown field id {field.field_id} on message '
                            f'{message.name!r} (global {message.global_id}) lost '
                            f'raw_bytes; post-edit rewrite cannot preserve the '
                            f'original wire slice.'
                        ),
                        record_index=record_index,
                    )
                )
            elif len(field.raw_bytes) != field.size:
                findings.append(
                    ValidationFinding(
                        level=ConformanceLevel.PRESERVATION,
                        severity=Severity.ERROR,
                        message=(
                            f'Unknown field id {field.field_id} on message '
                            f'{message.name!r} has raw_bytes length '
                            f'{len(field.raw_bytes)} != field size {field.size}.'
                        ),
                        record_index=record_index,
                    )
                )


def validate_fit_file(
    source: FitFile | Sequence[Record],
    levels: Iterable[ConformanceLevel] | None = None,
    *,
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
    raise_on_error:
        If true, raise :class:`FitValidationError` when any ERROR findings exist
        (first error message is used, matching historical Builder strict behavior).

    Returns
    -------
    ValidationReport
        Collected findings. Truthy when there are no errors.
    """
    selected = _normalize_levels(levels)
    records = _records_from_source(source)
    findings: list[ValidationFinding] = []

    data_messages: list[DataMessage] = []
    data_message_indices: dict = {}
    for record_index, record in enumerate(records):
        if not record.is_definition and isinstance(record.message, DataMessage):
            data_message_indices[len(data_messages)] = record_index
            data_messages.append(record.message)

    if ConformanceLevel.WIRE in selected:
        _collect_wire_findings(records, findings)
    if ConformanceLevel.PROFILE in selected:
        _collect_profile_findings(data_messages, findings, data_message_indices)
    if ConformanceLevel.FILE_TYPE in selected:
        _collect_file_type_findings(data_messages, findings, data_message_indices)
    if ConformanceLevel.PRESERVATION in selected:
        _collect_preservation_findings(records, findings)

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
