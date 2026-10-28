"""FILE_TYPE-level validation: Activity, Workout, and Course rules."""

import os
import unittest

from fit_tool.exceptions import FitValidationError
from fit_tool.fit_file import FitFile
from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.profile.messages.activity_message import ActivityMessage
from fit_tool.profile.messages.course_message import CourseMessage
from fit_tool.profile.messages.event_message import EventMessage
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.messages.lap_message import LapMessage
from fit_tool.profile.messages.record_message import RecordMessage
from fit_tool.profile.messages.session_message import SessionMessage
from fit_tool.profile.profile_type import Event, EventType, FileType, Manufacturer, Sport
from fit_tool.tests.validation_helpers import (
    add_minimal_activity_messages,
    add_minimal_course_messages,
)
from fit_tool.validation import (
    ConformanceLevel,
    validate_fit_file,
)


class TestValidationFileTypes(unittest.TestCase):

    def test_strict_activity_requires_profile_messages(self):
        builder = FitFileBuilder(strict=True)
        file_id = FileIdMessage()
        file_id.type = FileType.ACTIVITY
        file_id.manufacturer = Manufacturer.DEVELOPMENT.value
        file_id.product = 0
        file_id.serial_number = 1234
        file_id.time_created = 1_700_000_000_000
        builder.add(file_id)

        with self.assertRaisesRegex(FitValidationError, 'record'):
            builder.build_bytes()

    def test_strict_activity_accepts_required_message_structure(self):
        builder = FitFileBuilder(strict=True)
        add_minimal_activity_messages(builder)

        encoded = builder.build_bytes()

        self.assertGreater(len(encoded), 0)

    def test_strict_validation_fails_closed_for_unsupported_file_type(self):
        builder = FitFileBuilder(strict=True)
        file_id = FileIdMessage()
        # Settings (and other non-Activity/Workout/Course types) still fail closed.
        file_id.type = FileType.SETTINGS
        file_id.manufacturer = Manufacturer.DEVELOPMENT.value
        file_id.product = 0
        file_id.serial_number = 1234
        file_id.time_created = 1_700_000_000_000
        builder.add(file_id)

        with self.assertRaisesRegex(FitValidationError, 'not implemented'):
            builder.build_bytes()

    def test_strict_course_accepts_required_message_structure(self):
        builder = FitFileBuilder(strict=True)
        add_minimal_course_messages(builder)

        encoded = builder.build_bytes()

        self.assertGreater(len(encoded), 0)

    def test_strict_course_requires_course_message(self):
        builder = FitFileBuilder(strict=True)
        add_minimal_course_messages(builder, include_course=False)

        with self.assertRaisesRegex(FitValidationError, 'course message'):
            builder.build_bytes()

    def test_strict_course_requires_lap_and_record(self):
        builder = FitFileBuilder(strict=True)
        add_minimal_course_messages(builder, include_lap=False)

        with self.assertRaisesRegex(FitValidationError, 'lap message'):
            builder.build_bytes()

        builder = FitFileBuilder(strict=True)
        add_minimal_course_messages(builder, include_record=False)

        with self.assertRaisesRegex(FitValidationError, 'record message'):
            builder.build_bytes()

    def test_strict_course_requires_timer_events(self):
        builder = FitFileBuilder(strict=True)
        add_minimal_course_messages(builder, include_timer_start=False)

        with self.assertRaisesRegex(FitValidationError, 'timer start'):
            builder.build_bytes()

        builder = FitFileBuilder(strict=True)
        add_minimal_course_messages(builder, include_timer_stop=False)

        with self.assertRaisesRegex(FitValidationError, 'timer stop'):
            builder.build_bytes()

    def test_course_missing_sport_reports_file_type_error(self):
        """Codex P1: course.sport is required Course metadata."""
        builder = FitFileBuilder(auto_define=True, min_string_size=20)
        add_minimal_course_messages(builder, include_course=False)
        course = CourseMessage()
        course.course_name = 'no sport'
        # sport intentionally unset
        builder.add(course)
        # Re-add remaining structure without a course was already partial — rebuild fully.
        builder = FitFileBuilder(auto_define=True, min_string_size=20)
        file_id = FileIdMessage()
        file_id.type = FileType.COURSE
        file_id.manufacturer = Manufacturer.DEVELOPMENT.value
        file_id.product = 0
        file_id.serial_number = 1234
        file_id.time_created = 1_700_000_000_000
        builder.add(file_id)
        course = CourseMessage()
        course.course_name = 'no sport'
        builder.add(course)
        lap = LapMessage()
        lap.timestamp = 1_700_000_001_000
        lap.start_time = 1_700_000_000_000
        lap.total_elapsed_time = 1.0
        builder.add(lap)
        start = EventMessage()
        start.event = Event.TIMER
        start.event_type = EventType.START
        start.timestamp = 1_700_000_000_000
        builder.add(start)
        record = RecordMessage()
        record.timestamp = 1_700_000_000_000
        record.position_lat = 40.0
        record.position_long = -105.0
        builder.add(record)
        stop = EventMessage()
        stop.event = Event.TIMER
        stop.event_type = EventType.STOP_ALL
        stop.timestamp = 1_700_000_001_000
        builder.add(stop)
        report = validate_fit_file(builder.build(), levels={ConformanceLevel.FILE_TYPE})
        self.assertTrue(report.has_errors)
        self.assertTrue(any('sport' in f.message for f in report.errors), [f.message for f in report.errors])

    def test_course_timer_stop_before_start_errors(self):
        """Codex P2: timer start must precede timer stop."""
        builder = FitFileBuilder(auto_define=True, min_string_size=20)
        file_id = FileIdMessage()
        file_id.type = FileType.COURSE
        file_id.manufacturer = Manufacturer.DEVELOPMENT.value
        file_id.product = 0
        file_id.serial_number = 1
        file_id.time_created = 1_700_000_000_000
        builder.add(file_id)
        course = CourseMessage()
        course.course_name = 'order'
        course.sport = Sport.CYCLING
        builder.add(course)
        lap = LapMessage()
        lap.timestamp = 1_700_000_001_000
        lap.start_time = 1_700_000_000_000
        lap.total_elapsed_time = 1.0
        builder.add(lap)
        # stop before start
        stop = EventMessage()
        stop.event = Event.TIMER
        stop.event_type = EventType.STOP_ALL
        stop.timestamp = 1_700_000_001_000
        builder.add(stop)
        start = EventMessage()
        start.event = Event.TIMER
        start.event_type = EventType.START
        start.timestamp = 1_700_000_000_000
        builder.add(start)
        record = RecordMessage()
        record.position_lat = 40.0
        record.position_long = -105.0
        builder.add(record)
        report = validate_fit_file(builder.build(), levels={ConformanceLevel.FILE_TYPE})
        self.assertTrue(report.has_errors)
        self.assertTrue(
            any('precede the timer stop' in f.message for f in report.errors),
            [f.message for f in report.errors],
        )

    def test_course_missing_name_reports_file_type_error(self):
        builder = FitFileBuilder()
        file_id = FileIdMessage()
        file_id.type = FileType.COURSE
        file_id.manufacturer = Manufacturer.DEVELOPMENT.value
        file_id.product = 0
        file_id.serial_number = 1234
        file_id.time_created = 1_700_000_000_000
        builder.add(file_id)
        course = CourseMessage()
        course.sport = Sport.CYCLING  # name left unset
        builder.add(course)
        lap = LapMessage()
        lap.timestamp = 1_700_000_001_000
        lap.start_time = 1_700_000_000_000
        lap.total_elapsed_time = 1.0
        builder.add(lap)
        start = EventMessage()
        start.event = Event.TIMER
        start.event_type = EventType.START
        start.timestamp = 1_700_000_000_000
        builder.add(start)
        record = RecordMessage()
        record.timestamp = 1_700_000_000_000
        builder.add(record)
        stop = EventMessage()
        stop.event = Event.TIMER
        stop.event_type = EventType.STOP_DISABLE_ALL
        stop.timestamp = 1_700_000_001_000
        builder.add(stop)
        fit_file = builder.build()

        report = validate_fit_file(fit_file, levels={ConformanceLevel.FILE_TYPE})

        self.assertTrue(report.has_errors)
        self.assertTrue(any('course_name' in f.message for f in report.errors))

    def test_course_fixture_stages_link_passes_file_type(self):
        path = os.path.join(os.path.dirname(__file__), 'data', 'stagesLink_28832.fit')
        fit_file = FitFile.from_file(path)

        report = validate_fit_file(fit_file, levels={ConformanceLevel.FILE_TYPE})

        self.assertFalse(report.has_errors, msg=report.findings)

    def test_course_accepts_stop_disable_all_timer_event(self):
        """Real Garmin courses often use STOP_DISABLE_ALL (9) instead of STOP_ALL."""
        builder = FitFileBuilder()
        add_minimal_course_messages(builder, include_timer_stop=False)
        stop = EventMessage()
        stop.event = Event.TIMER
        stop.event_type = EventType.STOP_DISABLE_ALL
        stop.timestamp = 1_700_000_001_000
        builder.add(stop)
        fit_file = builder.build()

        report = validate_fit_file(fit_file, levels={ConformanceLevel.FILE_TYPE})

        self.assertFalse(report.has_errors, msg=report.findings)

    def test_activity_file_type_unchanged_with_course_rules(self):
        builder = FitFileBuilder()
        add_minimal_activity_messages(builder)
        fit_file = builder.build()

        report = validate_fit_file(fit_file, levels={ConformanceLevel.FILE_TYPE})

        self.assertFalse(report.has_errors)

    def test_file_type_findings_structure_errors(self):
        from fit_tool.profile.messages.file_id_message import FileIdMessage
        from fit_tool.profile.messages.record_message import RecordMessage
        from fit_tool.record import Record

        # No data messages
        report = validate_fit_file([], levels={ConformanceLevel.FILE_TYPE})
        self.assertTrue(any('must contain data messages' in f.message for f in report.errors))

        # Two file_id messages
        f1 = FileIdMessage()
        f1.type = FileType.ACTIVITY
        f1.manufacturer = Manufacturer.DEVELOPMENT.value
        f1.product = 0
        f1.serial_number = 1
        f1.time_created = 1_700_000_000_000
        f2 = FileIdMessage()
        f2.type = FileType.ACTIVITY
        f2.manufacturer = Manufacturer.DEVELOPMENT.value
        f2.product = 0
        f2.serial_number = 2
        f2.time_created = 1_700_000_001_000
        report2 = validate_fit_file(
            [Record.from_message(f1), Record.from_message(f2)],
            levels={ConformanceLevel.FILE_TYPE},
        )
        self.assertTrue(any('exactly one file_id' in f.message for f in report2.errors))

        # file_id not first
        record = RecordMessage()
        record.timestamp = 1_700_000_000_000
        report3 = validate_fit_file(
            [Record.from_message(record), Record.from_message(f1)],
            levels={ConformanceLevel.FILE_TYPE},
        )
        self.assertTrue(any('first data message' in f.message for f in report3.errors))

        # file_id.type missing
        bare = FileIdMessage()
        bare.manufacturer = Manufacturer.DEVELOPMENT.value
        bare.product = 0
        bare.serial_number = 1
        bare.time_created = 1_700_000_000_000
        report4 = validate_fit_file(
            [Record.from_message(bare)],
            levels={ConformanceLevel.FILE_TYPE},
        )
        self.assertTrue(any('file_id.type is required' in f.message for f in report4.errors))

        # Missing required activity fields
        builder = FitFileBuilder()
        file_id = FileIdMessage()
        file_id.type = FileType.ACTIVITY
        file_id.manufacturer = Manufacturer.DEVELOPMENT.value
        file_id.product = 0
        file_id.serial_number = 1234
        file_id.time_created = 1_700_000_000_000
        builder.add(file_id)
        incomplete_record = RecordMessage()  # no timestamp
        builder.add(incomplete_record)
        from fit_tool.profile.messages.lap_message import LapMessage
        from fit_tool.profile.profile_type import Sport

        lap = LapMessage()
        lap.message_index = 0
        # missing other required fields
        builder.add(lap)
        session = SessionMessage()
        session.message_index = 0
        session.sport = Sport.CYCLING
        builder.add(session)
        activity = ActivityMessage()
        builder.add(activity)
        fit = builder.build()
        report5 = validate_fit_file(fit, levels={ConformanceLevel.FILE_TYPE})
        self.assertTrue(report5.has_errors)
        self.assertTrue(any('missing required field' in f.message for f in report5.errors))
