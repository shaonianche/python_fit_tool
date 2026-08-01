"""Tests for the unified FitDecoder / stream-memory parity (Stage 3)."""

from __future__ import annotations

import io
import struct
import unittest
from pathlib import Path

from fit_tool.base_type import BaseType
from fit_tool.decoder import FitDecoder, iter_fit_records
from fit_tool.developer_field import DeveloperField
from fit_tool.exceptions import FitCRCError, FitHeaderError, FitRecordError
from fit_tool.fit_file import FitFile
from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.profile.messages.developer_data_id_message import DeveloperDataIdMessage
from fit_tool.profile.messages.field_description_message import FieldDescriptionMessage
from fit_tool.profile.messages.record_message import RecordMessage
from fit_tool.profile.messages.workout_step_message import WorkoutStepMessage
from fit_tool.profile.profile_type import WorkoutStepDuration
from fit_tool.wire import WireDecoder
from fit_tool.wire.model import RawDataRecord, RawDefinitionRecord

DATA_DIR = Path(__file__).resolve().parent / 'data'


def _simple_workout_bytes() -> bytes:
    message = WorkoutStepMessage(local_id=0)
    message.workout_step_name = 'step'
    message.duration_type = WorkoutStepDuration.DISTANCE
    builder = FitFileBuilder(auto_define=True)
    builder.add(message)
    return builder.build().to_bytes()


def _activity_with_developer_fields() -> bytes:
    builder = FitFileBuilder(auto_define=True, min_string_size=50)

    developer_data_id = DeveloperDataIdMessage()
    developer_data_id.developer_data_index = 0
    developer_data_id.application_id = bytes(range(16))
    builder.add(developer_data_id)

    field_description = FieldDescriptionMessage()
    field_description.developer_data_index = 0
    field_description.field_definition_number = 0
    field_description.fit_base_type_id = BaseType.UINT8.value
    field_description.field_name = 'doughnuts_earned'
    field_description.units = 'doughnuts'
    builder.add(field_description)

    dev_field = DeveloperField(
        developer_data_index=0,
        field_id=0,
        size=1,
        base_type=BaseType.UINT8,
        name='doughnuts_earned',
        units='doughnuts',
    )
    dev_field.set_value(0, 1)
    record = RecordMessage(developer_fields=[dev_field])
    record.distance = 0
    record.power = 100
    builder.add(record)

    return builder.build().to_bytes()


class TestFitDecoderParity(unittest.TestCase):
    def test_stream_and_from_bytes_record_bytes_match(self):
        fit_bytes = _simple_workout_bytes()

        full = FitFile.from_bytes(fit_bytes)
        streamed = list(FitFile.iter_stream(io.BytesIO(fit_bytes)))

        self.assertEqual(
            [record.to_bytes() for record in streamed],
            [record.to_bytes() for record in full.records],
        )

    def test_iter_fit_records_matches_from_bytes_on_bytes_and_stream(self):
        fit_bytes = _simple_workout_bytes()

        from_bytes_records = FitFile.from_bytes(fit_bytes).records
        from_buffer = list(iter_fit_records(fit_bytes))
        from_stream = list(iter_fit_records(io.BytesIO(fit_bytes)))

        self.assertEqual(
            [r.to_bytes() for r in from_buffer],
            [r.to_bytes() for r in from_bytes_records],
        )
        self.assertEqual(
            [r.to_bytes() for r in from_stream],
            [r.to_bytes() for r in from_bytes_records],
        )

    def test_developer_field_registration_parity(self):
        fit_bytes = _activity_with_developer_fields()

        full_decoder = FitDecoder()
        full_records = list(full_decoder.iter_records(fit_bytes))

        stream_decoder = FitDecoder()
        stream_records = list(stream_decoder.iter_records(io.BytesIO(fit_bytes)))

        self.assertEqual(
            full_decoder.developer_fields_by_data_index.keys(),
            stream_decoder.developer_fields_by_data_index.keys(),
        )
        full_dev = full_decoder.developer_fields_by_data_index[0][0]
        stream_dev = stream_decoder.developer_fields_by_data_index[0][0]
        self.assertEqual(full_dev.name, stream_dev.name)
        self.assertEqual(full_dev.field_id, stream_dev.field_id)
        self.assertEqual(full_dev.base_type, stream_dev.base_type)

        self.assertEqual(
            [r.to_bytes() for r in full_records],
            [r.to_bytes() for r in stream_records],
        )

        # Projected record carries the developer field value on both paths.
        data_messages = [
            r.message for r in full_records
            if not r.is_definition and isinstance(r.message, RecordMessage)
        ]
        self.assertEqual(len(data_messages), 1)
        self.assertEqual(len(data_messages[0].developer_fields), 1)
        self.assertEqual(data_messages[0].developer_fields[0].get_value(0), 1)

    def test_crc_mismatch_parity(self):
        fit_bytes = bytearray(_simple_workout_bytes())
        fit_bytes[-1] ^= 0xFF
        corrupted = bytes(fit_bytes)

        with self.assertRaises(FitCRCError):
            FitFile.from_bytes(corrupted)
        with self.assertRaises(FitCRCError):
            list(FitFile.iter_stream(io.BytesIO(corrupted)))

        # check_crc=False: both paths succeed and leave CRC mismatch visible.
        full = FitFile.from_bytes(corrupted, check_crc=False)
        streamed = list(FitFile.iter_stream(io.BytesIO(corrupted), check_crc=False))
        self.assertEqual(
            [r.to_bytes() for r in streamed],
            [r.to_bytes() for r in full.records],
        )

    def test_sdk_developer_data_stream_matches_from_bytes(self):
        path = DATA_DIR / 'sdk' / 'DeveloperData.fit'
        if not path.exists():
            self.skipTest('DeveloperData.fit fixture missing')
        fit_bytes = path.read_bytes()

        full = FitFile.from_bytes(fit_bytes)
        streamed = list(FitFile.iter_stream(io.BytesIO(fit_bytes)))
        self.assertEqual(
            [r.to_bytes() for r in streamed],
            [r.to_bytes() for r in full.records],
        )


class TestDecodeErrorParity(unittest.TestCase):
    def test_truncated_stream_raises_parse_error(self):
        fit_bytes = _simple_workout_bytes()
        truncated = fit_bytes[:-5]

        with self.assertRaises((FitHeaderError, FitRecordError)):
            FitFile.from_bytes(truncated)
        with self.assertRaises((FitHeaderError, FitRecordError)):
            list(FitFile.iter_stream(io.BytesIO(truncated)))

    def test_truncated_mid_record_stream(self):
        fit_bytes = _simple_workout_bytes()
        # Keep header + first few record bytes only.
        header_size = fit_bytes[0]
        partial = fit_bytes[: header_size + 3]

        with self.assertRaises(FitRecordError):
            list(FitFile.iter_stream(io.BytesIO(partial)))
        with self.assertRaises((FitHeaderError, FitRecordError)):
            FitFile.from_bytes(partial)

    def test_missing_definition_raises_fit_record_error(self):
        header = bytearray(14)
        header[0] = 14
        header[8:12] = b'.FIT'
        struct.pack_into('<I', header, 4, 1)
        body = bytes(header) + bytes([0x00]) + struct.pack('<H', 0)

        with self.assertRaises(FitRecordError) as full_ctx:
            FitFile.from_bytes(body, check_crc=False)
        with self.assertRaises(FitRecordError) as stream_ctx:
            list(FitFile.iter_stream(io.BytesIO(body), check_crc=False))

        self.assertIn('local_id', str(full_ctx.exception))
        self.assertIn('local_id', str(stream_ctx.exception))

    def test_empty_input_raises_header_error_on_both_paths(self):
        with self.assertRaises(FitHeaderError):
            FitFile.from_bytes(b'')
        with self.assertRaises(FitHeaderError):
            list(FitFile.iter_stream(io.BytesIO(b'')))


class TestWireStreamingSession(unittest.TestCase):
    def test_wire_iter_raw_records_matches_decode(self):
        fit_bytes = _simple_workout_bytes()

        document = WireDecoder().decode(fit_bytes)
        segment = document.first_segment
        assert segment is not None

        stream_decoder = WireDecoder()
        streamed = list(stream_decoder.iter_raw_records(io.BytesIO(fit_bytes)))

        self.assertEqual(len(streamed), len(segment.records))
        for left, right in zip(streamed, segment.records):
            self.assertEqual(type(left), type(right))
            self.assertEqual(left.source_bytes, right.source_bytes)

        self.assertEqual(stream_decoder.calculated_crc, segment.calculated_crc)
        self.assertEqual(stream_decoder.stored_crc, segment.stored_crc)
        self.assertIsNotNone(stream_decoder.header)
        self.assertEqual(stream_decoder.last_timestamp, None)

    def test_definition_snapshots_independent_on_stream_path(self):
        fit_bytes = _simple_workout_bytes()
        # Two messages on same local_id force redefinition when types differ —
        # reuse workout builder double-add of same type still one definition.
        decoder = WireDecoder()
        records = list(decoder.iter_raw_records(fit_bytes))
        definitions = [r for r in records if isinstance(r, RawDefinitionRecord)]
        data = [r for r in records if isinstance(r, RawDataRecord)]
        self.assertGreaterEqual(len(definitions), 1)
        self.assertGreaterEqual(len(data), 1)
        self.assertIs(data[0].definition, definitions[0])


if __name__ == '__main__':
    unittest.main()
