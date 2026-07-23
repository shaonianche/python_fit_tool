"""Validation for FIT wire constraints and profile-level file rules."""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from fit_tool.base_type import BaseType
from fit_tool.data_message import DataMessage
from fit_tool.definition_message import DefinitionMessage
from fit_tool.exceptions import FitValidationError
from fit_tool.message import Message
from fit_tool.profile.profile_type import FileType, MesgNum
from fit_tool.record import Record

MAX_LOCAL_MESSAGE_NUMBER = 15
MAX_GLOBAL_MESSAGE_NUMBER = 65535
MAX_FIELD_NUMBER = 255
MAX_FIELD_SIZE = 255
MAX_FIELD_COUNT = 255


def _enum_value(value: Any) -> Any:
    return value.value if hasattr(value, 'value') else value


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


class FitFileValidator:
    """Validate ordered FIT records using protocol and selected file-type rules."""

    def __init__(self, records: list[Record]):
        self.records = records
        self.data_messages = [
            record.message for record in records
            if not record.is_definition and isinstance(record.message, DataMessage)
        ]

    def validate(self) -> None:
        self._validate_definitions_and_data()
        self._validate_developer_fields()
        self._validate_file_type()

    def _validate_definitions_and_data(self) -> None:
        active_definitions = {}
        for record in self.records:
            message = record.message
            if isinstance(message, DefinitionMessage):
                validate_definition(message)
                if not message.field_definitions:
                    raise FitValidationError(
                        f'Strict validation does not allow an empty definition for global_id {message.global_id}.'
                    )
                active_definitions[message.local_id] = message
            elif isinstance(message, DataMessage):
                definition = active_definitions.get(message.local_id)
                if definition is None:
                    raise FitValidationError(
                        f'{message.name} uses undefined local_id {message.local_id}.'
                    )
                validate_data_message(message, definition)

    def _validate_developer_fields(self) -> None:
        developer_data_indices = set()
        descriptions = {}

        for message in self.data_messages:
            if message.global_id == MesgNum.DEVELOPER_DATA_ID.value:
                developer_data_index = _enum_value(getattr(message, 'developer_data_index', None))
                if developer_data_index is None:
                    raise FitValidationError('developer_data_id is missing developer_data_index.')
                application_id = getattr(message, 'application_id', None)
                if application_id is None or len(application_id) != 16:
                    raise FitValidationError('developer_data_id.application_id must contain exactly 16 bytes.')
                if developer_data_index in developer_data_indices:
                    raise FitValidationError(
                        f'Duplicate developer_data_id for developer_data_index {developer_data_index}.'
                    )
                developer_data_indices.add(developer_data_index)

            elif message.global_id == MesgNum.FIELD_DESCRIPTION.value:
                developer_data_index = _enum_value(getattr(message, 'developer_data_index', None))
                field_number = _enum_value(getattr(message, 'field_definition_number', None))
                fit_base_type_id = _enum_value(getattr(message, 'fit_base_type_id', None))
                if developer_data_index not in developer_data_indices:
                    raise FitValidationError(
                        f'field_description references developer_data_index {developer_data_index} '
                        f'before its developer_data_id message.'
                    )
                if field_number is None or fit_base_type_id is None:
                    raise FitValidationError(
                        'field_description requires field_definition_number and fit_base_type_id.'
                    )
                try:
                    base_type = BaseType(fit_base_type_id)
                except ValueError as exc:
                    raise FitValidationError(
                        f'field_description contains unknown fit_base_type_id {fit_base_type_id}.'
                    ) from exc
                if (developer_data_index, field_number) in descriptions:
                    raise FitValidationError(
                        f'Duplicate field_description for developer field '
                        f'{(developer_data_index, field_number)}.'
                    )
                descriptions[(developer_data_index, field_number)] = base_type

            for developer_field in message.developer_fields:
                if not developer_field.is_valid():
                    continue
                key = (developer_field.developer_data_index, developer_field.field_id)
                described_base_type = descriptions.get(key)
                if described_base_type is None:
                    raise FitValidationError(
                        f'Developer field {key} is used before a matching field_description message.'
                    )
                if described_base_type != developer_field.base_type:
                    raise FitValidationError(
                        f'Developer field {key} uses {developer_field.base_type.name}, but its '
                        f'field_description declares {described_base_type.name}.'
                    )

    def _validate_file_type(self) -> None:
        if not self.data_messages:
            raise FitValidationError('A FIT file must contain data messages.')

        file_id_messages = [
            message for message in self.data_messages
            if message.global_id == MesgNum.FILE_ID.value
        ]
        if len(file_id_messages) != 1:
            raise FitValidationError(f'A FIT file must contain exactly one file_id message; found {len(file_id_messages)}.')
        if self.data_messages[0] is not file_id_messages[0]:
            raise FitValidationError('file_id must be the first data message in a FIT file.')

        file_type = _enum_value(getattr(file_id_messages[0], 'type', None))
        if file_type is None:
            raise FitValidationError('file_id.type is required.')
        self._require_fields(
            file_id_messages[0],
            ('type', 'manufacturer', 'product', 'serial_number', 'time_created'),
        )

        message_counts = Counter(message.global_id for message in self.data_messages)
        if file_type == FileType.ACTIVITY.value:
            self._require_at_least_one(message_counts, MesgNum.RECORD, 'record')
            self._require_at_least_one(message_counts, MesgNum.LAP, 'lap')
            self._require_at_least_one(message_counts, MesgNum.SESSION, 'session')
            self._require_exactly_one(message_counts, MesgNum.ACTIVITY, 'activity')
            self._validate_activity_fields()
        else:
            raise FitValidationError(
                f'Strict file-type validation is not implemented for file_id.type {file_type!r}.'
            )

    def _validate_activity_fields(self) -> None:
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
        for message in self.data_messages:
            field_names = required_fields.get(message.global_id)
            if field_names is not None:
                self._require_fields(message, field_names)

    @staticmethod
    def _require_fields(message: DataMessage, field_names: tuple[str, ...]) -> None:
        missing = [name for name in field_names if getattr(message, name, None) is None]
        if missing:
            raise FitValidationError(
                f'{message.name} is missing required field(s): {", ".join(missing)}.'
            )

    @staticmethod
    def _require_at_least_one(
        message_counts: Mapping[int, int],
        message_number: MesgNum,
        name: str,
    ) -> None:
        if message_counts[message_number.value] < 1:
            raise FitValidationError(f'An activity FIT file requires at least one {name} message.')

    @staticmethod
    def _require_exactly_one(
        message_counts: Mapping[int, int],
        message_number: MesgNum,
        name: str,
    ) -> None:
        count = message_counts[message_number.value]
        if count != 1:
            raise FitValidationError(f'An activity FIT file requires exactly one {name} message; found {count}.')
