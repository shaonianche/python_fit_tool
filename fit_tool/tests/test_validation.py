import unittest

from fit_tool.base_type import BaseType
from fit_tool.developer_field import DeveloperField
from fit_tool.exceptions import FitValidationError
from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.profile.messages.activity_message import ActivityMessage
from fit_tool.profile.messages.developer_data_id_message import DeveloperDataIdMessage
from fit_tool.profile.messages.field_description_message import FieldDescriptionMessage
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.messages.lap_message import LapMessage
from fit_tool.profile.messages.record_message import RecordMessage
from fit_tool.profile.messages.session_message import SessionMessage
from fit_tool.profile.messages.workout_step_message import WorkoutStepMessage
from fit_tool.profile.profile_type import FileType, Manufacturer, Sport


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


class TestFitValidation(unittest.TestCase):

    def test_builder_rejects_local_id_outside_wire_range(self):
        message = WorkoutStepMessage(local_id=16)
        message.workout_step_name = 'step'

        with self.assertRaisesRegex(FitValidationError, 'local_id'):
            FitFileBuilder().add(message)

    def test_builder_rejects_field_larger_than_definition_limit(self):
        message = WorkoutStepMessage()
        message.workout_step_name = 'x' * 256

        with self.assertRaisesRegex(FitValidationError, 'size'):
            FitFileBuilder().add(message)

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
        file_id.type = FileType.WORKOUT
        file_id.manufacturer = Manufacturer.DEVELOPMENT.value
        file_id.product = 0
        file_id.serial_number = 1234
        file_id.time_created = 1_700_000_000_000
        builder.add(file_id)

        with self.assertRaisesRegex(FitValidationError, 'not implemented'):
            builder.build_bytes()

    def test_strict_validation_rejects_undeclared_developer_field(self):
        developer_field = DeveloperField(
            developer_data_index=0,
            field_id=1,
            base_type=BaseType.SINT8,
            size=1,
        )
        developer_field.set_value(0, 5)
        record = RecordMessage(developer_fields=[developer_field])

        builder = FitFileBuilder(strict=True)
        add_minimal_activity_messages(builder, record_message=record)

        with self.assertRaisesRegex(FitValidationError, 'field_description'):
            builder.build_bytes()

    def test_strict_validation_accepts_declared_developer_field(self):
        builder = FitFileBuilder(strict=True)

        file_id = FileIdMessage()
        file_id.type = FileType.ACTIVITY
        file_id.manufacturer = Manufacturer.DEVELOPMENT.value
        file_id.product = 0
        file_id.serial_number = 1234
        file_id.time_created = 1_700_000_000_000
        builder.add(file_id)

        developer_data_id = DeveloperDataIdMessage()
        developer_data_id.developer_data_index = 0
        developer_data_id.application_id = bytes(range(16))
        builder.add(developer_data_id)

        field_description = FieldDescriptionMessage()
        field_description.developer_data_index = 0
        field_description.field_definition_number = 1
        field_description.fit_base_type_id = BaseType.SINT8
        builder.add(field_description)

        developer_field = DeveloperField(
            developer_data_index=0,
            field_id=1,
            base_type=BaseType.SINT8,
            size=1,
        )
        developer_field.set_value(0, 5)
        record = RecordMessage(developer_fields=[developer_field])
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

        self.assertGreater(len(builder.build_bytes()), 0)
