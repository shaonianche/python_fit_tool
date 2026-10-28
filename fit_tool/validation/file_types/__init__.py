"""FILE_TYPE-level validation: file_id rules per FIT file type."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping, Sequence

from fit_tool.data_message import DataMessage
from fit_tool.profile.profile_type import FileType, MesgNum
from fit_tool.validation.context import ValidationContext
from fit_tool.validation.file_types.activity import collect_activity_file_findings
from fit_tool.validation.file_types.course import collect_course_file_findings
from fit_tool.validation.file_types.workout import collect_workout_file_findings
from fit_tool.validation.report import ConformanceLevel, add_error, enum_value

_FileTypeValidator = Callable[
    [Sequence[DataMessage], list, Mapping[int, int], Counter],
    None,
]

_FILE_TYPE_VALIDATORS: dict[int, _FileTypeValidator] = {
    FileType.ACTIVITY.value: collect_activity_file_findings,
    FileType.WORKOUT.value: collect_workout_file_findings,
    FileType.COURSE.value: collect_course_file_findings,
}

# file_id.type values with a FILE_TYPE rule set implemented today.
IMPLEMENTED_FILE_TYPES = frozenset(_FILE_TYPE_VALIDATORS)


def collect_file_type_findings(context: ValidationContext) -> None:
    """Run the FILE_TYPE rule set registered for ``file_id.type``."""
    data_messages = context.data_messages
    findings = context.findings
    data_message_indices = context.data_message_indices

    if not data_messages:
        add_error(findings, ConformanceLevel.FILE_TYPE, 'A FIT file must contain data messages.')
        return

    file_id_messages = [
        message for message in data_messages
        if message.global_id == MesgNum.FILE_ID.value
    ]
    if len(file_id_messages) != 1:
        add_error(
            findings,
            ConformanceLevel.FILE_TYPE,
            f'A FIT file must contain exactly one file_id message; found {len(file_id_messages)}.',
        )
        return
    if data_messages[0] is not file_id_messages[0]:
        add_error(
            findings,
            ConformanceLevel.FILE_TYPE,
            'file_id must be the first data message in a FIT file.',
            data_message_indices.get(0),
        )
        return

    file_id = file_id_messages[0]
    file_id_index = data_message_indices.get(0)
    file_type = enum_value(getattr(file_id, 'type', None))
    if file_type is None:
        add_error(findings, ConformanceLevel.FILE_TYPE, 'file_id.type is required.', file_id_index)
        return

    validator = _FILE_TYPE_VALIDATORS.get(file_type)
    if validator is None:
        add_error(
            findings,
            ConformanceLevel.FILE_TYPE,
            f'Strict file-type validation is not implemented for file_id.type {file_type!r}.',
            file_id_index,
        )
        return
    validator(data_messages, findings, data_message_indices, context.message_counts)


__all__ = [
    'IMPLEMENTED_FILE_TYPES',
    'collect_file_type_findings',
]
