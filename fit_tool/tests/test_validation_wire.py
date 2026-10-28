"""WIRE-level validation: headers, definitions, and data records."""

import unittest

from fit_tool.base_type import BaseType
from fit_tool.exceptions import FitValidationError
from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.profile.messages.record_message import RecordMessage
from fit_tool.profile.messages.workout_step_message import WorkoutStepMessage
from fit_tool.validation import (
    ConformanceLevel,
    validate_fit_file,
)


class TestValidationWire(unittest.TestCase):

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

    def test_data_message_size_mismatch_when_definition_supports(self):
        from fit_tool.definition_message import DefinitionMessage
        from fit_tool.field_definition import FieldDefinition
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

    def test_wire_collects_data_message_validation_error(self):
        from fit_tool.definition_message import DefinitionMessage
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
