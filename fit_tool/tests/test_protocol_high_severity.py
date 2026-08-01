"""Tests for high-severity protocol fixes: timestamps, chained FIT, components, preserve."""

from __future__ import annotations

import unittest

from fit_tool.components import expand_message_components
from fit_tool.exceptions import FitParseError, FitRecordError
from fit_tool.fit_file import FitFile
from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.profile.messages.record_message import RecordMessage
from fit_tool.profile.messages.workout_step_message import WorkoutStepMessage
from fit_tool.profile.profile_type import WorkoutStepDuration
from fit_tool.wire.decoder import WireDecoder, decode_bytes
from fit_tool.wire.timestamp import apply_compressed_time_offset


class TestCompressedTimestamp(unittest.TestCase):
    def test_apply_offset_without_rollover(self):
        previous = 0x1000001A  # low 5 bits = 26
        self.assertEqual(apply_compressed_time_offset(previous, 30), 0x1000001E)

    def test_apply_offset_with_rollover(self):
        previous = 0x1000001E  # low 5 bits = 30
        self.assertEqual(apply_compressed_time_offset(previous, 1), 0x10000021)

    def test_compressed_header_requires_prior_timestamp(self):
        # Craft: definition for empty local 0 + compressed data header with no prior ts
        # Minimal invalid file is hard; use decoder unit on synthetic sequence via WireDecoder
        # by building a normal file then patching is expensive — test FitRecordError path
        # through apply + WireDecoder last_timestamp only.
        decoder = WireDecoder()
        decoder.last_timestamp = None
        from fit_tool.wire.model import RawDataRecord, RawDefinitionRecord, RawRecordHeader

        header = RawRecordHeader(
            is_time_compressed=True,
            is_definition=False,
            has_developer_fields=False,
            local_id=0,
            time_offset_seconds=5,
            source_offset=0,
            source_bytes=b'\x85',
        )
        definition = RawDefinitionRecord(
            header=RawRecordHeader(
                is_time_compressed=False,
                is_definition=True,
                has_developer_fields=False,
                local_id=0,
                time_offset_seconds=0,
                source_offset=0,
                source_bytes=b'\x40',
            ),
            reserved=0,
            architecture=0,
            global_id=20,
            field_definitions=(),
            developer_field_definitions=(),
            source_offset=0,
            source_bytes=b'\x40\x00\x00\x14\x00\x00',
        )
        raw = RawDataRecord(
            header=header,
            definition=definition,
            payload=b'',
            source_offset=0,
            source_bytes=b'\x85',
        )
        with self.assertRaises(FitRecordError):
            decoder._apply_timestamp_state(raw, 0)

    def test_compressed_header_resolves_timestamp(self):
        decoder = WireDecoder()
        decoder.last_timestamp = 1000
        from fit_tool.wire.model import RawDataRecord, RawDefinitionRecord, RawRecordHeader

        header = RawRecordHeader(
            is_time_compressed=True,
            is_definition=False,
            has_developer_fields=False,
            local_id=0,
            time_offset_seconds=10,
            source_offset=0,
            source_bytes=b'\x8a',
        )
        definition = RawDefinitionRecord(
            header=RawRecordHeader(
                False, True, False, 0, 0, 0, b'\x40',
            ),
            reserved=0,
            architecture=0,
            global_id=20,
            field_definitions=(),
            developer_field_definitions=(),
            source_offset=0,
            source_bytes=b'\x40',
        )
        raw = RawDataRecord(header, definition, b'', 0, b'\x8a')
        out = decoder._apply_timestamp_state(raw, 1)
        self.assertEqual(out.resolved_timestamp, apply_compressed_time_offset(1000, 10))
        self.assertEqual(decoder.last_timestamp, out.resolved_timestamp)


class TestChainedAndTrailing(unittest.TestCase):
    def _bytes(self) -> bytes:
        mesg = WorkoutStepMessage(local_id=0)
        mesg.workout_step_name = 'step'
        mesg.duration_type = WorkoutStepDuration.DISTANCE
        builder = FitFileBuilder(auto_define=True)
        builder.add(mesg)
        return builder.build().to_bytes()

    def test_chained_two_segments_decode(self):
        single = self._bytes()
        chained = single + single
        document = decode_bytes(chained)
        self.assertEqual(len(document.segments), 2)
        self.assertTrue(document.is_chained)

        fit = FitFile.from_bytes(chained)
        # Two segments × (definition + data)
        self.assertEqual(len(fit.records), 4)
        self.assertIsNotNone(fit.wire_document)
        self.assertEqual(len(fit.wire_document.segments), 2)

    def test_trailing_garbage_raises(self):
        single = self._bytes()
        with self.assertRaises(FitParseError):
            FitFile.from_bytes(single + b'\x00\x01\x02')

    def test_trailing_garbage_allowed(self):
        single = self._bytes()
        fit = FitFile.from_bytes(single + b'\x00\x01', allow_trailing_bytes=True)
        self.assertEqual(len(fit.records), 2)


class TestComponents(unittest.TestCase):
    def test_expand_compressed_speed_distance(self):
        # 12-bit speed=1000 (encoded), 12-bit distance=32 → raw LE 24-bit
        # speed in low 12 bits = 1000, distance next 12 = 32
        packed = 1000 | (32 << 12)
        message = RecordMessage()
        source = message.get_field(8)  # compressed_speed_distance
        assert source is not None
        source.size = 3
        source.encoded_values = [
            packed & 0xFF,
            (packed >> 8) & 0xFF,
            (packed >> 16) & 0xFF,
        ]
        expand_message_components(message)
        speed = message.get_field(6)
        distance = message.get_field(5)
        assert speed is not None and distance is not None
        # Component scale 100 → 10 m/s; record.speed field scale 1000 → encoded 10000
        self.assertAlmostEqual(speed.get_value(), 10.0)
        self.assertAlmostEqual(distance.get_value(), 2.0)  # 32/16

    def test_accumulate_component(self):
        message = RecordMessage()
        source = message.get_field(28)
        assert source is not None
        source.size = 2
        source.encoded_values = [10, 0]  # little-endian 10
        acc: dict = {}
        expand_message_components(message, acc)
        expand_message_components(message, acc)  # same value → delta 0
        source.encoded_values = [12, 0]
        expand_message_components(message, acc)
        power = message.get_field(29)
        assert power is not None
        self.assertEqual(power.get_value(), 12)
        self.assertEqual(acc[(20, 29)], 12)


class TestPreservationEncode(unittest.TestCase):
    def test_untouched_round_trip_identity(self):
        mesg = WorkoutStepMessage(local_id=0)
        mesg.workout_step_name = 'round'
        mesg.duration_type = WorkoutStepDuration.DISTANCE
        builder = FitFileBuilder(auto_define=True)
        builder.add(mesg)
        original = builder.build().to_bytes()

        fit = FitFile.from_bytes(original)
        self.assertIsNotNone(fit.wire_document)
        preserved = fit.to_bytes(preserve=True)
        self.assertEqual(preserved, original)

    def test_chained_preserve_identity(self):
        mesg = WorkoutStepMessage(local_id=0)
        mesg.workout_step_name = 'a'
        mesg.duration_type = WorkoutStepDuration.DISTANCE
        one = FitFileBuilder(auto_define=True)
        one.add(mesg)
        blob = one.build().to_bytes()
        chained = blob + blob
        fit = FitFile.from_bytes(chained)
        self.assertEqual(fit.to_bytes(preserve=True), chained)

    def test_edit_disables_preserve(self):
        mesg = WorkoutStepMessage(local_id=0)
        mesg.workout_step_name = 'edit'
        mesg.duration_type = WorkoutStepDuration.DISTANCE
        builder = FitFileBuilder(auto_define=True)
        builder.add(mesg)
        original = builder.build().to_bytes()
        fit = FitFile.from_bytes(original)
        fit.mark_dirty()
        self.assertIsNone(fit.wire_document)
        rebuilt = fit.to_bytes()
        # Still valid FIT (CRC ok)
        again = FitFile.from_bytes(rebuilt)
        self.assertGreaterEqual(len(again.records), 1)


if __name__ == '__main__':
    unittest.main()
