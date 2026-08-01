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
from fit_tool.validation import (
    ConformanceLevel,
    FitFileValidator,
    Severity,
    validate_fit_file,
)


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

    def test_validate_fit_file_report_mode_on_fit_file(self):
        builder = FitFileBuilder()
        add_minimal_activity_messages(builder)
        fit_file = builder.build()

        report = validate_fit_file(fit_file)

        self.assertTrue(report)
        self.assertFalse(report.has_errors)
        self.assertEqual(report.findings, [])

    def test_validate_fit_file_raise_mode_matches_strict_builder(self):
        builder = FitFileBuilder()
        file_id = FileIdMessage()
        file_id.type = FileType.ACTIVITY
        file_id.manufacturer = Manufacturer.DEVELOPMENT.value
        file_id.product = 0
        file_id.serial_number = 1234
        file_id.time_created = 1_700_000_000_000
        builder.add(file_id)
        fit_file = builder.build()

        with self.assertRaisesRegex(FitValidationError, 'record'):
            validate_fit_file(fit_file, raise_on_error=True)

        report = fit_file.validate()
        self.assertTrue(report.has_errors)
        self.assertEqual(report.errors[0].level, ConformanceLevel.FILE_TYPE)
        self.assertEqual(report.errors[0].severity, Severity.ERROR)
        self.assertIn('record', report.errors[0].message)

    def test_validate_wire_only_skips_file_type_rules(self):
        builder = FitFileBuilder()
        file_id = FileIdMessage()
        file_id.type = FileType.WORKOUT
        file_id.manufacturer = Manufacturer.DEVELOPMENT.value
        file_id.product = 0
        file_id.serial_number = 1234
        file_id.time_created = 1_700_000_000_000
        builder.add(file_id)
        fit_file = builder.build()

        wire_report = validate_fit_file(fit_file, levels={ConformanceLevel.WIRE})
        self.assertFalse(wire_report.has_errors)

        full_report = fit_file.validate()
        self.assertTrue(full_report.has_errors)
        self.assertTrue(
            any('not implemented' in finding.message for finding in full_report.errors)
        )

    def test_fit_file_validator_legacy_facade(self):
        builder = FitFileBuilder()
        add_minimal_activity_messages(builder)
        FitFileValidator(builder.records).validate()

        incomplete = FitFileBuilder()
        file_id = FileIdMessage()
        file_id.type = FileType.ACTIVITY
        file_id.manufacturer = Manufacturer.DEVELOPMENT.value
        file_id.product = 0
        file_id.serial_number = 1234
        file_id.time_created = 1_700_000_000_000
        incomplete.add(file_id)

        with self.assertRaisesRegex(FitValidationError, 'record'):
            FitFileValidator(incomplete.records).validate()

    def test_public_api_exports_validation_symbols(self):
        from fit_tool import (
            ConformanceLevel as RootLevel,
        )
        from fit_tool import (
            ValidationReport,
        )
        from fit_tool import (
            validate_fit_file as root_validate,
        )

        self.assertIs(RootLevel, ConformanceLevel)
        self.assertIs(root_validate, validate_fit_file)
        self.assertTrue(callable(ValidationReport))


class TestValidationCoverage(unittest.TestCase):
    """Additional branches for wire, profile, and file-type validation."""

    def test_finding_str_and_report_warnings(self):
        from fit_tool.validation import ValidationFinding, ValidationReport

        finding = ValidationFinding(
            level=ConformanceLevel.WIRE,
            severity=Severity.WARNING,
            message='soft issue',
            record_index=3,
        )
        self.assertIn('record 3', str(finding))
        self.assertIn('wire', str(finding))
        self.assertIn('soft issue', str(finding))

        report = ValidationReport([finding])
        self.assertEqual(len(report.warnings), 1)
        self.assertFalse(report.has_errors)
        self.assertTrue(bool(report))
        report.raise_for_errors()  # no-op when only warnings

    def test_normalize_levels_rejects_empty_and_unknown(self):
        with self.assertRaisesRegex(ValueError, 'at least one'):
            validate_fit_file([], levels=set())

        class FakeLevel:
            value = 'preservation'

        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            validate_fit_file([], levels={FakeLevel()})  # type: ignore[arg-type]

    def test_validate_message_header_rejects_bad_global_id(self):
        from fit_tool.message import Message
        from fit_tool.validation import validate_message_header

        message = Message(local_id=0, global_id=70_000)
        with self.assertRaisesRegex(FitValidationError, 'global_id'):
            validate_message_header(message)

        message = Message(local_id=0, global_id=-1)
        with self.assertRaisesRegex(FitValidationError, 'global_id'):
            validate_message_header(message)

    def test_validate_definition_rejects_field_and_developer_constraints(self):
        from fit_tool.definition_message import DefinitionMessage
        from fit_tool.developer_field_definition import DeveloperFieldDefinition
        from fit_tool.field_definition import FieldDefinition
        from fit_tool.validation import validate_definition

        too_many = DefinitionMessage(
            field_definitions=[
                FieldDefinition(field_id=i, size=1, base_type=BaseType.UINT8)
                for i in range(256)
            ]
        )
        with self.assertRaisesRegex(FitValidationError, 'at most 255 native'):
            validate_definition(too_many)

        too_many_dev = DefinitionMessage(
            field_definitions=[FieldDefinition(field_id=1, size=1, base_type=BaseType.UINT8)],
            developer_field_definitions=[
                DeveloperFieldDefinition(field_id=i, size=1, developer_data_index=0)
                for i in range(256)
            ],
        )
        with self.assertRaisesRegex(FitValidationError, 'at most 255 developer'):
            validate_definition(too_many_dev)

        bad_field_id = DefinitionMessage(
            field_definitions=[FieldDefinition(field_id=300, size=1, base_type=BaseType.UINT8)]
        )
        with self.assertRaisesRegex(FitValidationError, 'Field number'):
            validate_definition(bad_field_id)

        bad_size = DefinitionMessage(
            field_definitions=[FieldDefinition(field_id=1, size=0, base_type=BaseType.UINT8)]
        )
        with self.assertRaisesRegex(FitValidationError, 'Field size'):
            validate_definition(bad_size)

        duplicate = DefinitionMessage(
            field_definitions=[
                FieldDefinition(field_id=1, size=1, base_type=BaseType.UINT8),
                FieldDefinition(field_id=1, size=1, base_type=BaseType.UINT8),
            ]
        )
        with self.assertRaisesRegex(FitValidationError, 'Duplicate native'):
            validate_definition(duplicate)

        not_multiple = DefinitionMessage(
            field_definitions=[FieldDefinition(field_id=1, size=3, base_type=BaseType.UINT16)]
        )
        with self.assertRaisesRegex(FitValidationError, 'not a multiple'):
            validate_definition(not_multiple)

        bad_dev_index = DefinitionMessage(
            field_definitions=[FieldDefinition(field_id=1, size=1, base_type=BaseType.UINT8)],
            developer_field_definitions=[
                DeveloperFieldDefinition(field_id=1, size=1, developer_data_index=300)
            ],
        )
        with self.assertRaisesRegex(FitValidationError, 'developer_data_index'):
            validate_definition(bad_dev_index)

        dup_dev = DefinitionMessage(
            field_definitions=[FieldDefinition(field_id=1, size=1, base_type=BaseType.UINT8)],
            developer_field_definitions=[
                DeveloperFieldDefinition(field_id=1, size=1, developer_data_index=0),
                DeveloperFieldDefinition(field_id=1, size=1, developer_data_index=0),
            ],
        )
        with self.assertRaisesRegex(FitValidationError, 'Duplicate developer field'):
            validate_definition(dup_dev)

    def test_validate_data_message_rejects_unsupported_definition(self):
        from fit_tool.definition_message import DefinitionMessage
        from fit_tool.field_definition import FieldDefinition
        from fit_tool.profile.messages.record_message import RecordMessage
        from fit_tool.validation import validate_data_message

        record = RecordMessage()
        record.timestamp = 1_700_000_000_000
        # Different global_id so supports() fails
        other = DefinitionMessage(
            global_id=record.global_id + 1,
            field_definitions=[FieldDefinition(field_id=253, size=4, base_type=BaseType.UINT32)],
        )
        with self.assertRaisesRegex(FitValidationError, 'does not support'):
            validate_data_message(record, other)

        # Force size mismatch by shrinking definition size after projection shape differs
        tiny = DefinitionMessage(
            global_id=record.global_id,
            local_id=record.local_id,
            field_definitions=[FieldDefinition(field_id=253, size=1, base_type=BaseType.UINT8)],
        )
        # supports may fail first on size; either error path is coverage for validation
        with self.assertRaises(FitValidationError):
            validate_data_message(record, tiny)

    def test_wire_findings_empty_definition_and_undefined_local_id(self):
        from fit_tool.definition_message import DefinitionMessage
        from fit_tool.field_definition import FieldDefinition
        from fit_tool.profile.messages.record_message import RecordMessage
        from fit_tool.record import Record

        empty_def = DefinitionMessage(local_id=0, global_id=20, field_definitions=[])
        record_msg = RecordMessage(local_id=1)
        record_msg.timestamp = 1_700_000_000_000

        records = [
            Record.from_message(empty_def),
            Record.from_message(record_msg),
        ]
        report = validate_fit_file(records, levels={ConformanceLevel.WIRE})
        messages = [f.message for f in report.errors]
        self.assertTrue(any('empty definition' in m for m in messages))
        self.assertTrue(any('undefined local_id' in m for m in messages))

        # Invalid definition (duplicate field) collected as wire finding
        bad_def = DefinitionMessage(
            local_id=2,
            global_id=20,
            field_definitions=[
                FieldDefinition(field_id=1, size=1, base_type=BaseType.UINT8),
                FieldDefinition(field_id=1, size=1, base_type=BaseType.UINT8),
            ],
        )
        report2 = validate_fit_file(
            [Record.from_message(bad_def)],
            levels={ConformanceLevel.WIRE},
        )
        self.assertTrue(report2.has_errors)
        self.assertTrue(any('Duplicate' in f.message for f in report2.errors))

    def test_profile_developer_field_edge_cases(self):
        from fit_tool.fit_file_builder import FitFileBuilder
        from fit_tool.profile.messages.activity_message import ActivityMessage
        from fit_tool.profile.messages.developer_data_id_message import DeveloperDataIdMessage
        from fit_tool.profile.messages.field_description_message import FieldDescriptionMessage
        from fit_tool.profile.messages.file_id_message import FileIdMessage
        from fit_tool.profile.messages.lap_message import LapMessage
        from fit_tool.profile.messages.record_message import RecordMessage
        from fit_tool.profile.messages.session_message import SessionMessage
        from fit_tool.profile.profile_type import Sport

        def build_with_messages(*extra_before_record, record=None):
            builder = FitFileBuilder()
            file_id = FileIdMessage()
            file_id.type = FileType.ACTIVITY
            file_id.manufacturer = Manufacturer.DEVELOPMENT.value
            file_id.product = 0
            file_id.serial_number = 1234
            file_id.time_created = 1_700_000_000_000
            builder.add(file_id)
            for message in extra_before_record:
                builder.add(message)
            if record is None:
                record = RecordMessage()
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
            return builder.build()

        # Missing developer_data_index on developer_data_id
        dev_id = DeveloperDataIdMessage()
        # leave developer_data_index unset
        fit = build_with_messages(dev_id)
        report = validate_fit_file(fit, levels={ConformanceLevel.PROFILE})
        self.assertTrue(any('missing developer_data_index' in f.message for f in report.errors))

        # Bad application_id length
        dev_id2 = DeveloperDataIdMessage()
        dev_id2.developer_data_index = 0
        dev_id2.application_id = bytes(range(8))  # not 16
        fit2 = build_with_messages(dev_id2)
        report2 = validate_fit_file(fit2, levels={ConformanceLevel.PROFILE})
        self.assertTrue(any('16 bytes' in f.message for f in report2.errors))

        # Duplicate developer_data_id
        d1 = DeveloperDataIdMessage()
        d1.developer_data_index = 0
        d1.application_id = bytes(range(16))
        d2 = DeveloperDataIdMessage()
        d2.developer_data_index = 0
        d2.application_id = bytes(range(16))
        fit3 = build_with_messages(d1, d2)
        report3 = validate_fit_file(fit3, levels={ConformanceLevel.PROFILE})
        self.assertTrue(any('Duplicate developer_data_id' in f.message for f in report3.errors))

        # field_description before developer_data_id
        fd = FieldDescriptionMessage()
        fd.developer_data_index = 0
        fd.field_definition_number = 1
        fd.fit_base_type_id = BaseType.SINT8
        fit4 = build_with_messages(fd)
        report4 = validate_fit_file(fit4, levels={ConformanceLevel.PROFILE})
        self.assertTrue(any('before its developer_data_id' in f.message for f in report4.errors))

        # field_description missing field_definition_number
        d_ok = DeveloperDataIdMessage()
        d_ok.developer_data_index = 0
        d_ok.application_id = bytes(range(16))
        fd_missing = FieldDescriptionMessage()
        fd_missing.developer_data_index = 0
        # field_definition_number and fit_base_type_id left unset
        fit5 = build_with_messages(d_ok, fd_missing)
        report5 = validate_fit_file(fit5, levels={ConformanceLevel.PROFILE})
        self.assertTrue(
            any('field_definition_number and fit_base_type_id' in f.message for f in report5.errors)
        )

        # Unknown fit_base_type_id
        fd_bad_type = FieldDescriptionMessage()
        fd_bad_type.developer_data_index = 0
        fd_bad_type.field_definition_number = 1
        fd_bad_type.fit_base_type_id = 250  # not a BaseType
        fit6 = build_with_messages(d_ok, fd_bad_type)
        report6 = validate_fit_file(fit6, levels={ConformanceLevel.PROFILE})
        self.assertTrue(any('unknown fit_base_type_id' in f.message for f in report6.errors))

        # Duplicate field_description
        fd_a = FieldDescriptionMessage()
        fd_a.developer_data_index = 0
        fd_a.field_definition_number = 1
        fd_a.fit_base_type_id = BaseType.SINT8
        fd_b = FieldDescriptionMessage()
        fd_b.developer_data_index = 0
        fd_b.field_definition_number = 1
        fd_b.fit_base_type_id = BaseType.SINT8
        fit7 = build_with_messages(d_ok, fd_a, fd_b)
        report7 = validate_fit_file(fit7, levels={ConformanceLevel.PROFILE})
        self.assertTrue(any('Duplicate field_description' in f.message for f in report7.errors))

        # Base type mismatch vs field_description
        fd_u8 = FieldDescriptionMessage()
        fd_u8.developer_data_index = 0
        fd_u8.field_definition_number = 1
        fd_u8.fit_base_type_id = BaseType.UINT8
        dev_field = DeveloperField(
            developer_data_index=0,
            field_id=1,
            base_type=BaseType.SINT8,
            size=1,
        )
        dev_field.set_value(0, 5)
        record = RecordMessage(developer_fields=[dev_field])
        record.timestamp = 1_700_000_000_000
        fit8 = build_with_messages(d_ok, fd_u8, record=record)
        report8 = validate_fit_file(fit8, levels={ConformanceLevel.PROFILE})
        self.assertTrue(any('uses SINT8' in f.message for f in report8.errors))

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
        from fit_tool.profile.messages.activity_message import ActivityMessage
        from fit_tool.profile.messages.lap_message import LapMessage
        from fit_tool.profile.messages.session_message import SessionMessage
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

    def test_legacy_validator_helpers(self):
        builder = FitFileBuilder()
        add_minimal_activity_messages(builder)
        validator = FitFileValidator(builder.records)
        validator._validate_definitions_and_data()
        validator._validate_developer_fields()
        validator._validate_file_type()

        incomplete = FitFileBuilder()
        file_id = FileIdMessage()
        file_id.type = FileType.ACTIVITY
        file_id.manufacturer = Manufacturer.DEVELOPMENT.value
        file_id.product = 0
        file_id.serial_number = 1234
        file_id.time_created = 1_700_000_000_000
        incomplete.add(file_id)
        with self.assertRaises(FitValidationError):
            FitFileValidator(incomplete.records)._validate_file_type()


class TestValidationRemainingEdges(unittest.TestCase):
    def test_data_message_size_mismatch_when_definition_supports(self):
        from fit_tool.definition_message import DefinitionMessage
        from fit_tool.field_definition import FieldDefinition
        from fit_tool.profile.messages.record_message import RecordMessage
        from fit_tool.validation import validate_data_message

        record = RecordMessage()
        record.timestamp = 1_700_000_000_000
        # Larger allocated size than the authored field encodes
        definition = DefinitionMessage(
            global_id=record.global_id,
            local_id=record.local_id,
            field_definitions=[
                FieldDefinition(field_id=253, size=8, base_type=BaseType.UINT32),
            ],
        )
        with self.assertRaisesRegex(FitValidationError, 'encodes'):
            validate_data_message(record, definition)

    def test_profile_skips_invalid_developer_fields(self):
        from fit_tool.profile.messages.file_id_message import FileIdMessage
        from fit_tool.profile.messages.record_message import RecordMessage
        from fit_tool.record import Record

        invalid_dev = DeveloperField(
            developer_data_index=0,
            field_id=1,
            base_type=BaseType.SINT8,
            size=0,
        )
        record = RecordMessage(developer_fields=[invalid_dev])
        record.timestamp = 1_700_000_000_000
        file_id = FileIdMessage()
        file_id.type = FileType.ACTIVITY
        file_id.manufacturer = Manufacturer.DEVELOPMENT.value
        file_id.product = 0
        file_id.serial_number = 1
        file_id.time_created = 1_700_000_000_000
        report = validate_fit_file(
            [Record.from_message(file_id), Record.from_message(record)],
            levels={ConformanceLevel.PROFILE},
        )
        # size 0 field is skipped (is_valid False), so no undeclared-field error
        self.assertFalse(any('used before' in f.message for f in report.errors))

    def test_wire_collects_data_message_validation_error(self):
        from fit_tool.definition_message import DefinitionMessage
        from fit_tool.profile.messages.record_message import RecordMessage
        from fit_tool.profile.messages.workout_step_message import WorkoutStepMessage
        from fit_tool.record import Record

        # Workout-step definition vs record data on the same local_id
        record = RecordMessage(local_id=0)
        record.timestamp = 1_700_000_000_000
        step = WorkoutStepMessage(local_id=0)
        step.workout_step_name = 'x'
        step_def = DefinitionMessage.from_data_message(step)
        step_def.local_id = 0
        report = validate_fit_file(
            [Record.from_message(step_def), Record.from_message(record)],
            levels={ConformanceLevel.WIRE},
        )
        self.assertTrue(report.has_errors)
