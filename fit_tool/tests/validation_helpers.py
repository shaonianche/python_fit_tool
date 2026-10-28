"""Shared builders for validation tests."""

from fit_tool.profile.messages.activity_message import ActivityMessage
from fit_tool.profile.messages.course_message import CourseMessage
from fit_tool.profile.messages.event_message import EventMessage
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.messages.lap_message import LapMessage
from fit_tool.profile.messages.record_message import RecordMessage
from fit_tool.profile.messages.session_message import SessionMessage
from fit_tool.profile.profile_type import Event, EventType, FileType, Manufacturer, Sport


def add_minimal_activity_messages(builder, record_message=None):
    file_id = FileIdMessage()
    file_id.type = FileType.ACTIVITY
    file_id.manufacturer = Manufacturer.DEVELOPMENT.value
    file_id.product = 0
    file_id.serial_number = 1234
    file_id.time_created = 1_700_000_000_000
    builder.add(file_id)

    record = record_message if record_message is not None else RecordMessage()
    record.timestamp = 1_700_000_000_000
    builder.add(record)

    lap = LapMessage()
    lap.message_index = 0
    lap.timestamp = 1_700_000_001_000
    lap.start_time = 1_700_000_000_000
    lap.total_elapsed_time = 1
    lap.total_timer_time = 1
    builder.add(lap)

    session = SessionMessage()
    session.message_index = 0
    session.timestamp = 1_700_000_001_000
    session.start_time = 1_700_000_000_000
    session.total_elapsed_time = 1
    session.total_timer_time = 1
    session.sport = Sport.CYCLING
    session.first_lap_index = 0
    session.num_laps = 1
    builder.add(session)

    activity = ActivityMessage()
    activity.timestamp = 1_700_000_001_000
    activity.num_sessions = 1
    activity.total_timer_time = 1
    builder.add(activity)


def add_minimal_course_messages(builder, *, include_course=True, include_lap=True,
                                 include_record=True, include_timer_start=True,
                                 include_timer_stop=True, course_name='test course'):
    """Build a minimal legal Course file (file_id + course + lap + records + timers)."""
    file_id = FileIdMessage()
    file_id.type = FileType.COURSE
    file_id.manufacturer = Manufacturer.DEVELOPMENT.value
    file_id.product = 0
    file_id.serial_number = 1234
    file_id.time_created = 1_700_000_000_000
    builder.add(file_id)

    if include_course:
        course = CourseMessage()
        course.course_name = course_name
        course.sport = Sport.CYCLING
        builder.add(course)

    if include_lap:
        lap = LapMessage()
        lap.timestamp = 1_700_000_001_000
        lap.start_time = 1_700_000_000_000
        lap.total_elapsed_time = 1.0
        builder.add(lap)

    if include_timer_start:
        start = EventMessage()
        start.event = Event.TIMER
        start.event_type = EventType.START
        start.timestamp = 1_700_000_000_000
        builder.add(start)

    if include_record:
        record = RecordMessage()
        record.timestamp = 1_700_000_000_000
        record.position_lat = 40.0
        record.position_long = -105.0
        builder.add(record)

    if include_timer_stop:
        stop = EventMessage()
        stop.event = Event.TIMER
        stop.event_type = EventType.STOP_ALL
        stop.timestamp = 1_700_000_001_000
        builder.add(stop)
