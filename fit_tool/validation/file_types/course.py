"""Course FILE_TYPE rules."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence

from fit_tool.data_message import DataMessage
from fit_tool.profile.profile_type import Event, EventType, MesgNum
from fit_tool.validation.file_types.common import (
    require_fields_findings,
    require_fields_for_messages,
)
from fit_tool.validation.report import ConformanceLevel, add_error, enum_value

# Product is optional on real Course exports (e.g. Stages Link).
_REQUIRED_FILE_ID_FIELDS = ('type', 'manufacturer', 'serial_number', 'time_created')

# Course timer stop event types accepted by FILE_TYPE (Garmin devices vary).
_COURSE_TIMER_STOP_TYPES = frozenset({
    EventType.STOP.value,
    EventType.STOP_ALL.value,
    EventType.STOP_DISABLE.value,
    EventType.STOP_DISABLE_ALL.value,
})

_REQUIRED_FIELDS = {
    MesgNum.COURSE.value: ('course_name', 'sport'),
    MesgNum.RECORD.value: ('position_lat', 'position_long'),
    MesgNum.LAP.value: (
        'timestamp',
        'start_time',
        'total_elapsed_time',
    ),
    MesgNum.EVENT.value: ('timestamp', 'event', 'event_type'),
}


def collect_course_file_findings(
        data_messages: Sequence[DataMessage],
        findings: list,
        data_message_indices: Mapping[int, int],
        message_counts: Counter,
) -> None:
    """Required messages for Course files (Garmin FIT Course file type).

    Must include: exactly one ``course``, ≥1 ``lap``, ≥1 ``record``, a timer
    start event, and a timer stop event. ``course_point`` is optional.
    """
    require_fields_findings(
        findings,
        data_messages[0],
        _REQUIRED_FILE_ID_FIELDS,
        data_message_indices.get(0),
    )
    _collect_course_structure_findings(data_messages, findings, message_counts)
    require_fields_for_messages(data_messages, findings, data_message_indices, _REQUIRED_FIELDS)


def _is_course_timer_event(message: DataMessage, event_types: frozenset) -> bool:
    """True when message is Event.TIMER with an event_type in ``event_types``."""
    if message.global_id != MesgNum.EVENT.value:
        return False
    if enum_value(getattr(message, 'event', None)) != Event.TIMER.value:
        return False
    return enum_value(getattr(message, 'event_type', None)) in event_types


def _collect_course_structure_findings(
        data_messages: Sequence[DataMessage],
        findings: list,
        message_counts: Counter,
) -> None:
    """Required message counts and timer-event ordering for Course files."""
    course_count = message_counts[MesgNum.COURSE.value]
    if course_count != 1:
        add_error(
            findings,
            ConformanceLevel.FILE_TYPE,
            f'A course FIT file requires exactly one course message; found {course_count}.',
        )
    if message_counts[MesgNum.LAP.value] < 1:
        add_error(
            findings,
            ConformanceLevel.FILE_TYPE,
            'A course FIT file requires at least one lap message.',
        )
    if message_counts[MesgNum.RECORD.value] < 1:
        add_error(
            findings,
            ConformanceLevel.FILE_TYPE,
            'A course FIT file requires at least one record message.',
        )

    start_positions = [
        pos for pos, message in enumerate(data_messages)
        if _is_course_timer_event(message, frozenset({EventType.START.value}))
    ]
    stop_positions = [
        pos for pos, message in enumerate(data_messages)
        if _is_course_timer_event(message, _COURSE_TIMER_STOP_TYPES)
    ]
    record_positions = [
        pos for pos, message in enumerate(data_messages)
        if message.global_id == MesgNum.RECORD.value
    ]

    if not start_positions:
        add_error(
            findings,
            ConformanceLevel.FILE_TYPE,
            'A course FIT file requires a timer start event message.',
        )
    if not stop_positions:
        add_error(
            findings,
            ConformanceLevel.FILE_TYPE,
            'A course FIT file requires a timer stop event message.',
        )

    # Ordering: timer start before track records and before terminal timer stop
    # (message order; timestamps may be equal in real Garmin exports).
    if start_positions and stop_positions:
        first_start = min(start_positions)
        last_stop = max(stop_positions)
        if first_start >= last_stop:
            add_error(
                findings,
                ConformanceLevel.FILE_TYPE,
                'A course FIT file requires the timer start event to precede '
                'the timer stop event.',
            )
    if start_positions and record_positions:
        if min(start_positions) > min(record_positions):
            add_error(
                findings,
                ConformanceLevel.FILE_TYPE,
                'A course FIT file requires the timer start event to precede '
                'track record messages.',
            )
    if stop_positions and record_positions:
        if max(stop_positions) < max(record_positions):
            add_error(
                findings,
                ConformanceLevel.FILE_TYPE,
                'A course FIT file requires the timer stop event to follow '
                'track record messages.',
            )
