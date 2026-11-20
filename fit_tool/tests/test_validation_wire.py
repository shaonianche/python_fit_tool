"""WIRE-level validation: headers, definitions, and data records."""

import os
import struct
import unittest

from fit_tool.base_type import BaseType
from fit_tool.definition_message import DefinitionMessage
from fit_tool.exceptions import FitValidationError
from fit_tool.fit_file import FitFile
from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.fit_file_header import FitFileHeader
from fit_tool.profile.messages.record_message import RecordMessage
from fit_tool.profile.messages.workout_step_message import WorkoutStepMessage
from fit_tool.utils.crc import crc16
from fit_tool.validation import (
    ConformanceLevel,
    validate_data_message,
    validate_fit_file,
)

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


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


def _load_activity_bytes() -> bytes:
    with open(os.path.join(DATA_DIR, 'sdk', 'Activity.fit'), 'rb') as file_object:
        return file_object.read()


def _definition_record(local_id: int, global_id: int, fields: list) -> bytes:
    record = bytes([0x40 | local_id, 0, 0]) + struct.pack('<H', global_id) + bytes([len(fields)])
    for field_id, size, base_type in fields:
        record += bytes([field_id, size, base_type])
    return record


def _compressed_timestamp_file() -> bytes:
    """Garmin's recommended pattern: a normal record, then a compressed one.

    Local 0 defines ``timestamp`` + ``heart_rate``; local 1 defines only
    ``heart_rate`` and its data record uses a compressed-timestamp header, so
    the decoder reconstructs field 253 for a record whose definition is 1 byte.
    """
    uint32, uint8 = 0x86, 0x02
    records = _definition_record(0, 20, [(253, 4, uint32), (3, 1, uint8)])
    records += bytes([0x00]) + struct.pack('<I', 1_000_000_000) + bytes([140])
    records += _definition_record(1, 20, [(3, 1, uint8)])
    records += bytes([0x80 | (1 << 5) | 10]) + bytes([141])

    raw = FitFileHeader(records_size=len(records)).to_bytes() + records
    return raw + struct.pack('<H', crc16(raw))


class TestWireRecordSizeCheck(unittest.TestCase):
    """A record's size check compares wire payload, not projected fields."""

    def _first_expanded_record(self, fit_file: FitFile):
        return next(
            record.message for record in fit_file.records
            if getattr(record.message, 'name', '') == 'record'
            and any(field.is_expanded_field and field.size for field in record.message.fields)
        )

    def test_standard_garmin_activity_validates_clean_under_strict_mode(self):
        raw = _load_activity_bytes()
        fit_file = FitFile.from_bytes(raw)

        report = fit_file.validate()
        self.assertFalse(
            report.has_errors,
            [finding.message for finding in report.errors[:5]],
        )

        # strict forces a canonical rebuild of every record, expanded fields included
        self.assertEqual(fit_file.to_bytes(strict=True), raw)

        builder = FitFileBuilder(strict=True)
        for record in fit_file.records:
            builder.add(record.message)
        self.assertIsNotNone(builder.build())

    def test_component_expanded_fields_are_not_counted_as_payload(self):
        fit_file = FitFile.from_bytes(_load_activity_bytes())
        record = self._first_expanded_record(fit_file)
        definition = record.definition_message

        # enhanced_speed/enhanced_altitude are projected from packed fields and
        # never written under this definition.
        self.assertGreater(record.size, definition.defined_data_size)
        validate_data_message(record, definition)

    def test_definition_field_missing_from_message_is_reported(self):
        fit_file = FitFile.from_bytes(_load_activity_bytes())
        record = self._first_expanded_record(fit_file)
        definition = record.definition_message

        # A projection that lost a field its definition still lists must not be
        # sized from the fields it kept.
        record.fields = [field for field in record.fields if field.field_id != 3]
        with self.assertRaisesRegex(FitValidationError, 'encodes'):
            validate_data_message(record, definition)

    def test_developer_field_payload_is_counted(self):
        fit_file = FitFile.from_file(os.path.join(DATA_DIR, 'sdk', 'activity_developerdata.fit'))
        record = next(
            candidate.message for candidate in fit_file.records
            if getattr(candidate.message, 'developer_fields', None)
        )
        definition = record.definition_message
        validate_data_message(record, definition)

        record.developer_fields.pop()
        with self.assertRaisesRegex(FitValidationError, 'encodes'):
            validate_data_message(record, definition)

    def test_corrupted_definition_size_is_still_reported(self):
        fit_file = FitFile.from_bytes(_load_activity_bytes())
        record = self._first_expanded_record(fit_file)

        # Make the active definition claim 4 more bytes for the timestamp field.
        definition_record = next(
            candidate.message for candidate in fit_file.records
            if isinstance(candidate.message, DefinitionMessage)
            and candidate.message.local_id == record.local_id
            and candidate.message.global_id == record.global_id
        )
        timestamp_definition = definition_record.get_field_definition(253)
        timestamp_definition.size += 4

        report = validate_fit_file(fit_file.records, levels={ConformanceLevel.WIRE})
        self.assertTrue(
            any('encodes' in finding.message for finding in report.errors),
            [finding.message for finding in report.errors],
        )

    def test_compressed_timestamp_record_is_not_flagged_and_corruption_is(self):
        raw = _compressed_timestamp_file()
        fit_file = FitFile.from_bytes(raw)

        compressed = fit_file.records[-1].message
        self.assertTrue(fit_file.records[-1].header.is_time_compressed)
        self.assertEqual(compressed.definition_message.defined_data_size, 1)
        # The reconstructed timestamp is projected but not on the wire.
        self.assertGreater(compressed.size, 1)
        self.assertEqual(fit_file.to_bytes(), raw)
        self.assertEqual(fit_file.validate(levels={ConformanceLevel.WIRE}).errors, [])
        validate_data_message(compressed, compressed.definition_message)

        compressed.definition_message.field_definitions[0].size = 2
        with self.assertRaisesRegex(FitValidationError, 'encodes 1 bytes'):
            validate_data_message(compressed, compressed.definition_message)

