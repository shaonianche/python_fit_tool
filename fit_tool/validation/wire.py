"""WIRE-level validation: local ids, definition layout, record sizes."""

from __future__ import annotations

from fit_tool.data_message import DataMessage
from fit_tool.definition_message import DefinitionMessage
from fit_tool.exceptions import FitValidationError
from fit_tool.message import Message
from fit_tool.validation.context import ValidationContext
from fit_tool.validation.report import ConformanceLevel

MAX_LOCAL_MESSAGE_NUMBER = 15
MAX_GLOBAL_MESSAGE_NUMBER = 65535
MAX_FIELD_NUMBER = 255
MAX_FIELD_SIZE = 255
MAX_FIELD_COUNT = 255


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


def collect_wire_findings(context: ValidationContext) -> None:
    """Run WIRE checks over the ordered records."""
    active_definitions = {}
    for record_index, record in enumerate(context.records):
        message = record.message
        if isinstance(message, DefinitionMessage):
            try:
                validate_definition(message)
            except FitValidationError as exc:
                context.error(ConformanceLevel.WIRE, str(exc), record_index)
                continue
            if not message.field_definitions:
                context.error(
                    ConformanceLevel.WIRE,
                    f'Strict validation does not allow an empty definition for global_id {message.global_id}.',
                    record_index,
                )
            active_definitions[message.local_id] = message
        elif isinstance(message, DataMessage):
            definition = active_definitions.get(message.local_id)
            if definition is None:
                context.error(
                    ConformanceLevel.WIRE,
                    f'{message.name} uses undefined local_id {message.local_id}.',
                    record_index,
                )
                continue
            try:
                validate_data_message(message, definition)
            except FitValidationError as exc:
                context.error(ConformanceLevel.WIRE, str(exc), record_index)


__all__ = [
    'MAX_FIELD_COUNT',
    'MAX_FIELD_NUMBER',
    'MAX_FIELD_SIZE',
    'MAX_GLOBAL_MESSAGE_NUMBER',
    'MAX_LOCAL_MESSAGE_NUMBER',
    'collect_wire_findings',
    'validate_data_message',
    'validate_definition',
    'validate_message_header',
]
