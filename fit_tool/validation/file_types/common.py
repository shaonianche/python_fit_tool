"""Shared FILE_TYPE helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from fit_tool.data_message import DataMessage
from fit_tool.validation.report import ConformanceLevel, add_error


def require_fields_findings(
        findings: list,
        message: DataMessage,
        field_names: tuple,
        record_index: int | None,
) -> None:
    """Report one finding listing every required field the message left unset.

    A field present on the wire but carrying only FIT invalid sentinels counts
    as unset (:meth:`~fit_tool.field.Field.has_value`), so a required field
    written as the protocol sentinel is reported instead of accepted.
    """
    missing = []
    for name in field_names:
        field = message.get_field_by_name(name)
        if field is not None and not field.has_value():
            missing.append(name)
        elif getattr(message, name, None) is None:
            missing.append(name)

    if missing:
        add_error(
            findings,
            ConformanceLevel.FILE_TYPE,
            f'{message.name} is missing required field(s): {", ".join(missing)}.',
            record_index,
        )


def require_fields_for_messages(
        data_messages: Sequence[DataMessage],
        findings: list,
        data_message_indices: Mapping[int, int],
        required_fields: Mapping[int, tuple],
) -> None:
    """Apply ``required_fields`` (global id -> field names) to matching messages."""
    for message_pos, message in enumerate(data_messages):
        field_names = required_fields.get(message.global_id)
        if field_names is not None:
            require_fields_findings(
                findings,
                message,
                field_names,
                data_message_indices.get(message_pos),
            )
