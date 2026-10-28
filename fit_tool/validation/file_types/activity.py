"""Activity FILE_TYPE rules."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence

from fit_tool.data_message import DataMessage
from fit_tool.profile.profile_type import MesgNum
from fit_tool.validation.file_types.common import (
    require_fields_findings,
    require_fields_for_messages,
)
from fit_tool.validation.report import ConformanceLevel, add_error

_REQUIRED_FILE_ID_FIELDS = ('type', 'manufacturer', 'product', 'serial_number', 'time_created')

_REQUIRED_FIELDS = {
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


def collect_activity_file_findings(
        data_messages: Sequence[DataMessage],
        findings: list,
        data_message_indices: Mapping[int, int],
        message_counts: Counter,
) -> None:
    """Required messages and fields for Activity files."""
    require_fields_findings(
        findings,
        data_messages[0],
        _REQUIRED_FILE_ID_FIELDS,
        data_message_indices.get(0),
    )
    if message_counts[MesgNum.RECORD.value] < 1:
        add_error(
            findings,
            ConformanceLevel.FILE_TYPE,
            'An activity FIT file requires at least one record message.',
        )
    if message_counts[MesgNum.LAP.value] < 1:
        add_error(
            findings,
            ConformanceLevel.FILE_TYPE,
            'An activity FIT file requires at least one lap message.',
        )
    if message_counts[MesgNum.SESSION.value] < 1:
        add_error(
            findings,
            ConformanceLevel.FILE_TYPE,
            'An activity FIT file requires at least one session message.',
        )
    activity_count = message_counts[MesgNum.ACTIVITY.value]
    if activity_count != 1:
        add_error(
            findings,
            ConformanceLevel.FILE_TYPE,
            f'An activity FIT file requires exactly one activity message; found {activity_count}.',
        )
    require_fields_for_messages(data_messages, findings, data_message_indices, _REQUIRED_FIELDS)
