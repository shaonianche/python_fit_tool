"""Edge-path coverage for smaller modules."""

from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

from fit_tool.base_type import BaseType
from fit_tool.definition_message import DefinitionMessage
from fit_tool.developer_field import DeveloperField
from fit_tool.developer_field_definition import DeveloperFieldDefinition
from fit_tool.field import Field
from fit_tool.field_definition import FieldDefinition
from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.fit_file_stream import iter_fit_file, iter_fit_stream
from fit_tool.profile.messages.workout_step_message import WorkoutStepMessage
from fit_tool.profile.profile_type import WorkoutStepDuration
from fit_tool.record import Record
from fit_tool.sub_field import SubField
from fit_tool.utils.crc import crc16
from fit_tool.wire.model import RawFileHeader, RawRecordHeader


class TestDeveloperAndFieldDefinition(unittest.TestCase):
    def test_developer_field_definition_roundtrip_and_from_field(self):
        definition = DeveloperFieldDefinition(field_id=3, size=4, developer_data_index=1)
        raw = definition.to_bytes()
        restored = DeveloperFieldDefinition.from_bytes(raw)
        self.assertEqual(restored.field_id, 3)
        self.assertEqual(restored.size, 4)
        self.assertEqual(restored.developer_data_index, 1)

        string_field = DeveloperField(
            field_id=2,
            developer_data_index=0,
            base_type=BaseType.STRING,
            size=3,
        )
        from_string = DeveloperFieldDefinition.from_field(string_field, min_string_size=10)
        self.assertEqual(from_string.size, 10)

        uint_field = DeveloperField(
            field_id=2,
            developer_data_index=0,
            base_type=BaseType.UINT8,
            size=1,
        )
        from_uint = DeveloperFieldDefinition.from_field(uint_field)
        self.assertEqual(from_uint.size, 1)

    def test_field_definition_eq_and_from_field_string(self):
        fd1 = FieldDefinition(field_id=1, size=2, base_type=BaseType.UINT16)
        fd2 = FieldDefinition(field_id=1, size=2, base_type=BaseType.UINT16)
        self.assertEqual(fd1, fd2)

        string_field = Field(name='s', base_type=BaseType.STRING, size=2, growable=True)
        string_field.set_encoded_value(0, 'ab')
        from_field = FieldDefinition.from_field(string_field, min_string_size=8)
        self.assertEqual(from_field.size, 8)


class TestCrcUtils(unittest.TestCase):
    def test_crc16_empty_buffer(self):
        self.assertEqual(crc16(b''), 0)
        self.assertEqual(crc16(b'', crc=0x1234), 0x1234)


class TestFitFileStream(unittest.TestCase):
    def test_iter_fit_file_and_stream(self):
        mesg = WorkoutStepMessage(local_id=0)
        mesg.workout_step_name = 's'
        mesg.duration_type = WorkoutStepDuration.DISTANCE
        builder = FitFileBuilder(auto_define=True)
        builder.add(mesg)
        raw = builder.build().to_bytes()

        stream_records = list(iter_fit_stream(io.BytesIO(raw)))
        self.assertGreaterEqual(len(stream_records), 2)

        with tempfile.NamedTemporaryFile(suffix='.fit', delete=False) as tmp:
            path = tmp.name
            tmp.write(raw)
        try:
            file_records = list(iter_fit_file(path))
            self.assertEqual(len(file_records), len(stream_records))
        finally:
            Path(path).unlink()


class TestRecordHelpers(unittest.TestCase):
    def test_from_bytes_undefined_local_id(self):
        # data record header local_id=0, no definition map entry
        header_byte = bytes([0x00])  # data message, local_id 0
        payload = b'\x00'
        with self.assertRaisesRegex(ValueError, 'DefinitionMessage not defined'):
            Record.from_bytes({}, header_byte + payload)

    def test_defined_size_paths(self):
        mesg = WorkoutStepMessage(local_id=0)
        mesg.workout_step_name = 's'
        definition = DefinitionMessage.from_data_message(mesg)
        def_record = Record.from_message(definition)
        self.assertEqual(def_record.defined_size(), def_record.size)

        data_record = Record.from_message(mesg)
        self.assertEqual(data_record.defined_size(), 0)
        self.assertEqual(
            data_record.defined_size(definition),
            data_record.header.size + definition.defined_data_size,
        )


class TestSubFieldHelpers(unittest.TestCase):
    def test_add_component_and_is_valid_paths(self):
        sub = SubField(name='x', reference_map={1: [2]})
        ref = Field(field_id=1, name='ref', base_type=BaseType.ENUM, size=1)
        ref.set_encoded_value(0, 1, check_validity=False)
        # is_valid returns True when field value is a key in reference_map
        self.assertTrue(sub.is_valid([ref]))
        self.assertFalse(sub.is_valid([]))


class TestWireModelProperties(unittest.TestCase):
    def test_raw_header_and_file_header_size(self):
        header = RawRecordHeader(
            is_time_compressed=False,
            is_definition=True,
            has_developer_fields=False,
            local_id=0,
            time_offset_seconds=0,
            source_offset=0,
            source_bytes=b'\x40',
        )
        self.assertEqual(header.size, 1)

        file_header = RawFileHeader(
            header_size=14,
            protocol_version=0x20,
            profile_version=0,
            records_size=0,
            data_type=b'.FIT',
            crc=None,
            source_offset=0,
            source_bytes=b'\x00' * 14,
        )
        self.assertEqual(file_header.size, 14)


class TestCompatibilityEdges(unittest.TestCase):
    def test_project_records_empty(self):
        from fit_tool.compatibility import project_records

        self.assertEqual(project_records([]), [])

    def test_register_developer_field_missing_metadata(self):
        from fit_tool.compatibility import register_developer_field
        from fit_tool.exceptions import FitRecordError
        from fit_tool.profile.messages.field_description_message import FieldDescriptionMessage

        message = FieldDescriptionMessage()
        # leave required metadata unset
        record = Record.from_message(message)
        with self.assertRaises(FitRecordError):
            register_developer_field(record, {})

    def test_project_segment_unsupported_type(self):
        from fit_tool.compatibility import project_segment
        from fit_tool.exceptions import FitRecordError
        from fit_tool.wire.model import FitSegment

        segment = FitSegment(
            header=RawFileHeader(
                header_size=14,
                protocol_version=0x20,
                profile_version=0,
                records_size=0,
                data_type=b'.FIT',
                crc=None,
                source_offset=0,
                source_bytes=b'',
            ),
            records=['not-a-record'],  # type: ignore[list-item]
        )
        with self.assertRaises(FitRecordError):
            project_segment(segment)


class TestRecordDeveloperFromBytes(unittest.TestCase):
    def test_from_bytes_with_developer_fields_registry(self):
        definition = DefinitionMessage(
            local_id=0,
            global_id=20,
            field_definitions=[FieldDefinition(field_id=253, size=4, base_type=BaseType.UINT32)],
            developer_field_definitions=[
                DeveloperFieldDefinition(field_id=1, size=1, developer_data_index=0),
            ],
        )
        # Build definition record bytes with developer fields header flag
        def_body = definition.to_bytes()
        def_header = bytes([0x40 | 0x20])  # definition + has developer fields
        def_bytes = def_header + def_body

        definitions = {}
        def_record = Record.from_bytes(definitions, def_bytes)
        definitions[0] = def_record.message

        dev = DeveloperField(
            developer_data_index=0,
            field_id=1,
            base_type=BaseType.UINT8,
            size=1,
        )
        registry = {0: {1: dev}}

        # data header local_id 0 + payload 4 bytes timestamp + 1 byte dev
        data_bytes = bytes([0x00]) + b'\x01\x00\x00\x00' + b'\x07'
        data_record = Record.from_bytes(definitions, data_bytes, developer_fields_by_data_index=registry)
        self.assertFalse(data_record.header.is_definition)
        self.assertEqual(len(data_record.message.developer_fields), 1)
