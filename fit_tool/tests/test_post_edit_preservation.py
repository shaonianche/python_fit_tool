"""Post-edit PRESERVATION: dirty tracking + mixed re-encode (Stage 3 F / SHA-18)."""

from __future__ import annotations

import struct
import unittest

from fit_tool.field import UnknownField
from fit_tool.fit_file import FitFile
from fit_tool.profile.messages.record_message import RecordMessage
from fit_tool.profile.messages.workout_step_message import WorkoutStepMessage
from fit_tool.profile.profile_type import WorkoutStepDuration
from fit_tool.tests.protocol_fixture_helpers import (
    build_record_with_unknown_field,
    build_workout_step_with_duration,
    chain_segments,
    wrap_records,
)
from fit_tool.validation import ConformanceLevel, Severity, validate_fit_file
from fit_tool.wire.decoder import decode_bytes


class TestPostEditPreservation(unittest.TestCase):
    """Edit one field; unknown fields and other records survive."""

    UNKNOWN_ID = 250
    UNKNOWN_VALUE = 0xABCD

    def test_field_edit_marks_record_dirty_keeps_wire_document(self):
        raw = build_record_with_unknown_field(
            unknown_field_id=self.UNKNOWN_ID,
            unknown_value=self.UNKNOWN_VALUE,
            heart_rate=120,
        )
        fit = FitFile.from_bytes(raw)
        self.assertIsNotNone(fit.wire_document)
        data = next(r for r in fit.records if not r.is_definition)
        self.assertFalse(data.dirty)
        self.assertIsNotNone(data.source_bytes)

        assert isinstance(data.message, RecordMessage)
        data.message.heart_rate = 99

        self.assertTrue(data.dirty)
        self.assertTrue(fit.has_dirty_records())
        # Structural wire snapshot retained for mixed preserve.
        self.assertIsNotNone(fit.wire_document)

    def test_clearing_field_via_none_marks_dirty_and_removes_value(self):
        """Codex P1: generated setters use Field.clear() for None assignments."""
        raw = build_record_with_unknown_field(
            unknown_field_id=self.UNKNOWN_ID,
            unknown_value=self.UNKNOWN_VALUE,
            heart_rate=120,
        )
        fit = FitFile.from_bytes(raw)
        data = next(r for r in fit.records if not r.is_definition)
        assert isinstance(data.message, RecordMessage)
        self.assertEqual(data.message.heart_rate, 120)

        data.message.heart_rate = None  # type: ignore[assignment]

        self.assertTrue(data.dirty)
        self.assertTrue(fit.has_dirty_records())
        self.assertIsNone(data.message.heart_rate)

        out = fit.to_bytes(preserve=True)
        again = FitFile.from_bytes(out)
        message = next(r.message for r in again.records if not r.is_definition)
        assert isinstance(message, RecordMessage)
        # Cleared field must not reappear with the old wire value (120).
        # Slot is re-emitted as protocol-invalid so the definition still matches.
        self.assertNotEqual(message.heart_rate, 120)
        unknown = message.get_field(self.UNKNOWN_ID)
        assert unknown is not None
        self.assertEqual(unknown.get_value(), self.UNKNOWN_VALUE)

    def test_edit_one_field_unknown_field_bytes_survive(self):
        raw = build_record_with_unknown_field(
            unknown_field_id=self.UNKNOWN_ID,
            unknown_value=self.UNKNOWN_VALUE,
            heart_rate=120,
        )
        fit = FitFile.from_bytes(raw)
        data = next(r for r in fit.records if not r.is_definition)
        assert isinstance(data.message, RecordMessage)
        data.message.heart_rate = 99

        out = fit.to_bytes(preserve=True)
        again = FitFile.from_bytes(out)
        message = next(r.message for r in again.records if not r.is_definition)
        assert isinstance(message, RecordMessage)
        self.assertEqual(message.heart_rate, 99)
        unknown = message.get_field(self.UNKNOWN_ID)
        assert unknown is not None
        self.assertIsInstance(unknown, UnknownField)
        self.assertEqual(unknown.get_value(), self.UNKNOWN_VALUE)
        self.assertEqual(unknown.raw_bytes, self.UNKNOWN_VALUE.to_bytes(2, 'little'))

    def test_untouched_record_source_bytes_identical(self):
        """Two data records: edit only the second; first stays bit-identical."""
        # Build a single-segment file with two definition+data pairs by composing
        # definition/data payloads (local ids 0 and 1).
        from fit_tool.base_type import BaseType
        from fit_tool.field_definition import FieldDefinition
        from fit_tool.tests.protocol_fixture_helpers import definition_and_data

        name_a = b'keep-me\x00'
        payload_a = name_a + struct.pack('<B', 1) + struct.pack('<I', 1000)
        name_b = b'edit-me\x00'
        payload_b = name_b + struct.pack('<B', 1) + struct.pack('<I', 2000)
        fields = [
            FieldDefinition(field_id=0, size=len(name_a), base_type=BaseType.STRING),
            FieldDefinition(field_id=1, size=1, base_type=BaseType.ENUM),
            FieldDefinition(field_id=2, size=4, base_type=BaseType.UINT32),
        ]
        # Same field sizes for both (name lengths match).
        self.assertEqual(len(name_a), len(name_b))
        recs = definition_and_data(
            global_id=27, field_definitions=fields, payload=payload_a, local_id=0,
        ) + definition_and_data(
            global_id=27, field_definitions=fields, payload=payload_b, local_id=1,
        )
        raw = wrap_records(recs)
        fit = FitFile.from_bytes(raw)
        self.assertEqual(len(fit.records), 4)  # 2 defs + 2 data

        data_records = [r for r in fit.records if not r.is_definition]
        self.assertEqual(len(data_records), 2)
        first, second = data_records
        first_source = first.source_bytes
        assert first_source is not None

        assert isinstance(second.message, WorkoutStepMessage)
        second.message.workout_step_name = 'edited!'

        self.assertFalse(first.dirty)
        self.assertTrue(second.dirty)

        out = fit.to_bytes(preserve=True)
        document = decode_bytes(out)
        segment = document.first_segment
        assert segment is not None
        # Wire records: def0, data0, def1, data1
        untouched_data = segment.records[1]
        self.assertEqual(untouched_data.source_bytes, first_source)

        again = FitFile.from_bytes(out)
        names = [
            r.message.workout_step_name
            for r in again.records
            if not r.is_definition and isinstance(r.message, WorkoutStepMessage)
        ]
        self.assertEqual(names, ['keep-me', 'edited!'])

    def test_structural_mark_dirty_still_drops_wire_document(self):
        raw = build_record_with_unknown_field()
        fit = FitFile.from_bytes(raw)
        fit.mark_dirty()
        self.assertIsNone(fit.wire_document)
        rebuilt = fit.to_bytes()
        FitFile.from_bytes(rebuilt)  # CRC-valid

    def test_chained_edit_one_segment_record(self):
        # Names length-matched so fixed definition size accepts the edit.
        one = build_workout_step_with_duration(
            duration_type=WorkoutStepDuration.DISTANCE.value,
            duration_value_raw=5000,
            name='seg-a',
        )
        two = build_workout_step_with_duration(
            duration_type=WorkoutStepDuration.DISTANCE.value,
            duration_value_raw=6000,
            name='seg-b',
        )
        chained = chain_segments(one, two)
        fit = FitFile.from_bytes(chained)
        self.assertEqual(len(fit.wire_document.segments), 2)

        # Edit data message in first segment only (records: d0, data0 | d0, data0).
        first_data = fit.records[1]
        assert isinstance(first_data.message, WorkoutStepMessage)
        # Same byte length as 'seg-a\0' (6) so the definition size still fits.
        first_data.message.workout_step_name = 'edit!'

        out = fit.to_bytes(preserve=True)
        document = decode_bytes(out)
        self.assertEqual(len(document.segments), 2)
        # Second segment fully untouched → bit-identical to original second segment.
        self.assertEqual(
            document.segments[1].header.source_bytes + b''.join(
                r.source_bytes for r in document.segments[1].records
            ) + struct.pack('<H', document.segments[1].stored_crc),
            two,
        )

        again = FitFile.from_bytes(out)
        names = [
            r.message.workout_step_name
            for r in again.records
            if not r.is_definition and isinstance(r.message, WorkoutStepMessage)
        ]
        self.assertEqual(names, ['edit!', 'seg-b'])


class TestPreservationConformanceLevel(unittest.TestCase):
    def test_preservation_level_not_in_defaults(self):
        raw = build_record_with_unknown_field()
        fit = FitFile.from_bytes(raw)
        report = validate_fit_file(fit)
        self.assertFalse(
            any(f.level is ConformanceLevel.PRESERVATION for f in report.findings)
        )

    def test_unknown_field_intact_has_no_preservation_error(self):
        raw = build_record_with_unknown_field()
        fit = FitFile.from_bytes(raw)
        data = next(r for r in fit.records if not r.is_definition)
        assert isinstance(data.message, RecordMessage)
        data.message.heart_rate = 88
        report = validate_fit_file(fit, levels={ConformanceLevel.PRESERVATION})
        self.assertFalse(report.has_errors)

    def test_cleared_raw_bytes_reports_preservation_error(self):
        raw = build_record_with_unknown_field(
            unknown_field_id=250,
            unknown_value=0xABCD,
        )
        fit = FitFile.from_bytes(raw)
        data = next(r for r in fit.records if not r.is_definition)
        unknown = data.message.get_field(250)
        assert isinstance(unknown, UnknownField)
        # Mutating the unknown field clears raw_bytes (API path).
        unknown.set_value(0, 0x1111)
        self.assertIsNone(unknown.raw_bytes)

        report = validate_fit_file(fit, levels={ConformanceLevel.PRESERVATION})
        self.assertTrue(report.has_errors)
        self.assertEqual(report.errors[0].level, ConformanceLevel.PRESERVATION)
        self.assertEqual(report.errors[0].severity, Severity.ERROR)
        self.assertIn('raw_bytes', report.errors[0].message)


if __name__ == '__main__':
    unittest.main()
