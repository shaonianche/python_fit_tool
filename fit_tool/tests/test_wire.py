"""Unit tests for the wire-layer MVP (raw models + decoder + FitFile facade)."""

from __future__ import annotations

import copy
import struct
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from fit_tool.compatibility import definition_from_raw, project_segment
from fit_tool.definition_message import DefinitionMessage
from fit_tool.exceptions import FitCRCError, FitHeaderError, FitRecordError
from fit_tool.fit_file import FitFile
from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.messages.workout_step_message import WorkoutStepMessage
from fit_tool.profile.profile_type import Manufacturer, WorkoutStepDuration
from fit_tool.wire import (
    RawDataRecord,
    RawDefinitionRecord,
    WireDecoder,
    decode_bytes,
)
from fit_tool.wire.model import RawDeveloperFieldDefinition, RawFieldDefinition, RawRecordHeader

DATA_DIR = Path(__file__).resolve().parent / 'data'


class TestWireDecoder(unittest.TestCase):
    def _build_simple_fit_bytes(self) -> bytes:
        mesg = WorkoutStepMessage(local_id=0)
        mesg.workout_step_name = '1st step'
        mesg.duration_type = WorkoutStepDuration.DISTANCE
        builder = FitFileBuilder(auto_define=True)
        builder.add(mesg)
        return builder.build().to_bytes()

    def test_decode_bytes_returns_single_segment(self):
        raw = self._build_simple_fit_bytes()
        document = decode_bytes(raw)

        self.assertEqual(len(document.segments), 1)
        segment = document.first_segment
        self.assertIsNotNone(segment)
        assert segment is not None
        self.assertGreaterEqual(len(segment.records), 2)
        self.assertEqual(segment.calculated_crc, segment.stored_crc)
        self.assertTrue(segment.header.source_bytes.startswith(bytes([segment.header.header_size])))
        self.assertEqual(segment.header.data_type, b'.FIT')

    def test_decode_preserves_definition_and_data_source_bytes(self):
        raw = self._build_simple_fit_bytes()
        segment = WireDecoder().decode(raw).first_segment
        assert segment is not None

        definitions = [r for r in segment.records if isinstance(r, RawDefinitionRecord)]
        data_records = [r for r in segment.records if isinstance(r, RawDataRecord)]
        self.assertEqual(len(definitions), 1)
        self.assertEqual(len(data_records), 1)

        definition = definitions[0]
        data = data_records[0]
        self.assertEqual(raw[definition.source_offset:definition.source_offset + definition.size], definition.source_bytes)
        self.assertEqual(raw[data.source_offset:data.source_offset + data.size], data.source_bytes)
        self.assertEqual(data.payload, data.source_bytes[1:])
        self.assertIs(data.definition, definition)

    def test_definition_redefinition_keeps_prior_snapshot(self):
        """Redefining local_id must not mutate the snapshot held by earlier data records."""
        # Build a minimal multi-definition buffer via FitFileBuilder using two
        # different message types on the same local_id.
        step = WorkoutStepMessage(local_id=0)
        step.workout_step_name = 'step'
        step.duration_type = WorkoutStepDuration.DISTANCE

        file_id = FileIdMessage(local_id=0)
        file_id.manufacturer = Manufacturer.DEVELOPMENT
        file_id.type = 4  # workout

        builder = FitFileBuilder(auto_define=True)
        builder.add(step)
        # Force a second definition for local_id 0 by adding a different message type.
        builder.add(file_id)
        fit_bytes = builder.build().to_bytes()

        segment = WireDecoder().decode(fit_bytes).first_segment
        assert segment is not None

        definition_records = [r for r in segment.records if isinstance(r, RawDefinitionRecord)]
        data_records = [r for r in segment.records if isinstance(r, RawDataRecord)]
        self.assertGreaterEqual(len(definition_records), 2)
        self.assertGreaterEqual(len(data_records), 2)

        first_def = definition_records[0]
        second_def = definition_records[1]
        self.assertEqual(first_def.local_id, second_def.local_id)
        self.assertNotEqual(first_def.global_id, second_def.global_id)

        # Each data record keeps the definition snapshot active when it was decoded.
        first_data = data_records[0]
        second_data = data_records[1]
        self.assertIs(first_data.definition, first_def)
        self.assertIs(second_data.definition, second_def)
        self.assertEqual(first_data.definition.global_id, first_def.global_id)
        self.assertEqual(second_data.definition.global_id, second_def.global_id)

        # Frozen snapshots cannot be mutated in place.
        with self.assertRaises(FrozenInstanceError):
            first_def.global_id = 999  # type: ignore[misc]

        # Replacing the "table" view (second def) does not change the first snapshot object.
        self.assertEqual(first_data.definition.field_definitions, first_def.field_definitions)

    def test_projected_definition_is_independent_copy(self):
        raw = self._build_simple_fit_bytes()
        segment = WireDecoder().decode(raw).first_segment
        assert segment is not None
        definition_raw = next(r for r in segment.records if isinstance(r, RawDefinitionRecord))

        message_a = definition_from_raw(definition_raw)
        message_b = definition_from_raw(definition_raw)
        self.assertEqual(message_a.global_id, message_b.global_id)
        self.assertIsNot(message_a.field_definitions, message_b.field_definitions)

        message_a.field_definitions.clear()
        self.assertNotEqual(len(message_a.field_definitions), len(message_b.field_definitions))
        # Wire snapshot unchanged.
        self.assertGreater(len(definition_raw.field_definitions), 0)

    def test_invalid_crc_raises(self):
        raw = bytearray(self._build_simple_fit_bytes())
        stored, = struct.unpack_from('<H', raw, len(raw) - 2)
        struct.pack_into('<H', raw, len(raw) - 2, (stored + 1) % 65536)

        with self.assertRaises(FitCRCError):
            decode_bytes(bytes(raw), check_crc=True)

        document = decode_bytes(bytes(raw), check_crc=False)
        segment = document.first_segment
        assert segment is not None
        self.assertNotEqual(segment.calculated_crc, segment.stored_crc)

    def test_empty_buffer_raises_header_error(self):
        with self.assertRaises(FitHeaderError):
            decode_bytes(b'')

    def test_data_without_definition_raises(self):
        # 14-byte header, one data record header byte with no prior definition, CRC placeholder.
        header = bytearray(14)
        header[0] = 14
        header[8:12] = b'.FIT'
        # records_size = 1
        struct.pack_into('<I', header, 4, 1)
        body = bytes(header) + bytes([0x00]) + struct.pack('<H', 0)
        with self.assertRaises(FitRecordError):
            WireDecoder(check_crc=False).decode(body)

    def test_sdk_activity_decodes(self):
        path = DATA_DIR / 'sdk' / 'Activity.fit'
        if not path.exists():
            self.skipTest('SDK Activity.fit fixture missing')
        document = decode_bytes(path.read_bytes())
        segment = document.first_segment
        assert segment is not None
        self.assertGreater(len(segment.records), 10)
        self.assertTrue(any(isinstance(r, RawDefinitionRecord) for r in segment.records))
        self.assertTrue(any(isinstance(r, RawDataRecord) for r in segment.records))


class TestFitFileWireFacade(unittest.TestCase):
    def test_from_bytes_round_trip_compatible(self):
        mesg = WorkoutStepMessage(local_id=0)
        mesg.workout_step_name = '1st step'
        mesg.duration_type = WorkoutStepDuration.DISTANCE
        builder = FitFileBuilder(auto_define=True)
        builder.add(mesg)
        original = builder.build()
        bytes1 = original.to_bytes()

        reparsed = FitFile.from_bytes(bytes1)
        bytes2 = reparsed.to_bytes()
        self.assertEqual(bytes2, bytes1)

    def test_from_bytes_projects_typed_messages(self):
        mesg = WorkoutStepMessage(local_id=0)
        mesg.workout_step_name = '1st step'
        mesg.duration_type = WorkoutStepDuration.DISTANCE
        builder = FitFileBuilder(auto_define=True)
        builder.add(mesg)
        fit_file = FitFile.from_bytes(builder.build().to_bytes())

        data_messages = [r.message for r in fit_file.records if not r.is_definition]
        self.assertEqual(len(data_messages), 1)
        self.assertIsInstance(data_messages[0], WorkoutStepMessage)
        self.assertEqual(data_messages[0].workout_step_name, '1st step')

    def test_project_segment_definition_local_id(self):
        mesg = WorkoutStepMessage(local_id=3)
        mesg.workout_step_name = 'step'
        mesg.duration_type = WorkoutStepDuration.DISTANCE
        builder = FitFileBuilder(auto_define=True)
        builder.add(mesg)
        segment = WireDecoder().decode(builder.build().to_bytes()).first_segment
        assert segment is not None
        records = project_segment(segment)
        definitions = [r for r in records if r.is_definition]
        self.assertEqual(len(definitions), 1)
        self.assertEqual(definitions[0].local_id, 3)
        self.assertIsInstance(definitions[0].message, DefinitionMessage)
        self.assertEqual(definitions[0].message.local_id, 3)


class TestRawModelBasics(unittest.TestCase):
    def test_raw_field_definition_is_frozen(self):
        field_def = RawFieldDefinition(field_id=1, size=2, base_type=132)
        with self.assertRaises(FrozenInstanceError):
            field_def.size = 4  # type: ignore[misc]

    def test_deepcopy_definition_snapshot_is_equal(self):
        field_def = RawFieldDefinition(field_id=1, size=2, base_type=132)
        self.assertEqual(copy.deepcopy(field_def), field_def)


if __name__ == '__main__':
    unittest.main()


class TestWireDecoderEdgeCases(unittest.TestCase):
    def test_invalid_architecture_raises(self):
        # Craft a definition with architecture=2
        # 14-byte header + definition with bad architecture
        header = bytearray(14)
        header[0] = 14
        header[1] = 0x20
        header[8:12] = b'.FIT'
        # records_size: 1 header + 5 prefix + 0 fields = 6, plus we'll set carefully
        # Minimal: normal definition header 0x40, reserved, arch=2, global_id, field_count=0
        definition = bytes([0x40, 0x00, 0x02, 0x00, 0x00, 0x00])  # arch=2 invalid
        records_size = len(definition)
        struct.pack_into('<I', header, 4, records_size)
        body = bytes(header) + definition
        # append dummy CRC (won't be reached if architecture fails first)
        body = body + struct.pack('<H', 0)
        with self.assertRaises(FitRecordError):
            WireDecoder(check_crc=False).decode(body)

    def test_header_too_small_raises(self):
        with self.assertRaises(FitHeaderError):
            WireDecoder(check_crc=False).decode(bytes([8]) + b'\x00' * 20)

    def test_raw_definition_defined_data_size(self):
        header = RawRecordHeader(
            is_time_compressed=False,
            is_definition=True,
            has_developer_fields=True,
            local_id=0,
            time_offset_seconds=0,
            source_offset=0,
            source_bytes=b'\x60',
        )
        definition = RawDefinitionRecord(
            header=header,
            reserved=0,
            architecture=0,
            global_id=20,
            field_definitions=(RawFieldDefinition(1, 4, 132),),
            developer_field_definitions=(RawDeveloperFieldDefinition(1, 2, 0),),
            source_offset=0,
            source_bytes=b'\x60' + b'\x00' * 10,
        )
        self.assertEqual(definition.defined_data_size, 6)
        self.assertEqual(definition.size, len(definition.source_bytes))
        self.assertEqual(definition.local_id, 0)

        data = RawDataRecord(
            header=RawRecordHeader(
                is_time_compressed=False,
                is_definition=False,
                has_developer_fields=False,
                local_id=0,
                time_offset_seconds=0,
                source_offset=0,
                source_bytes=b'\x00\x01\x02',
            ),
            definition=definition,
            payload=b'\x01\x02',
            source_offset=0,
            source_bytes=b'\x00\x01\x02',
        )
        self.assertEqual(data.size, 3)
        self.assertEqual(data.local_id, 0)
