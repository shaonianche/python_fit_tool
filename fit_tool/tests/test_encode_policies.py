"""Encode policies: PRESERVE vs CANONICAL (Stage 3 G / SHA-19)."""

from __future__ import annotations

import struct
import unittest

from fit_tool.base_type import BaseType
from fit_tool.encode import (
    EncodeMode,
    EncodeOptions,
    can_expand_compressed_to_normal,
    encode_record_projected,
    resolve_encode_options,
)
from fit_tool.exceptions import FitEncodingError, FitValidationError
from fit_tool.field import Field, UnknownField
from fit_tool.field_definition import FieldDefinition
from fit_tool.fit_file import FitFile
from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.profile.messages.record_message import RecordMessage
from fit_tool.profile.messages.workout_step_message import WorkoutStepMessage
from fit_tool.profile.profile_type import WorkoutStepDuration
from fit_tool.record import Record, RecordHeader
from fit_tool.tests.protocol_fixture_helpers import (
    build_record_with_compressed_speed_distance,
    build_record_with_unknown_field,
    definition_and_data,
    wrap_records,
)
from fit_tool.wire.decoder import decode_bytes


class TestResolveEncodeOptions(unittest.TestCase):
    def test_defaults_to_preserve(self):
        opts = resolve_encode_options()
        self.assertEqual(opts.mode, EncodeMode.PRESERVE)
        self.assertFalse(opts.strict)

    def test_preserve_false_is_canonical(self):
        opts = resolve_encode_options(preserve=False)
        self.assertEqual(opts.mode, EncodeMode.CANONICAL)

    def test_mode_overrides_preserve(self):
        opts = resolve_encode_options(mode=EncodeMode.CANONICAL, preserve=True)
        self.assertEqual(opts.mode, EncodeMode.CANONICAL)

    def test_strict_forces_canonical(self):
        opts = resolve_encode_options(preserve=True, strict=True)
        self.assertEqual(opts.mode, EncodeMode.CANONICAL)
        self.assertTrue(opts.strict)

    def test_mode_string(self):
        opts = resolve_encode_options(mode='canonical')
        self.assertEqual(opts.mode, EncodeMode.CANONICAL)


class TestPreserveModeInvariants(unittest.TestCase):
    def test_untouched_identity(self):
        raw = build_record_with_unknown_field(heart_rate=100)
        fit = FitFile.from_bytes(raw)
        self.assertEqual(fit.to_bytes(mode=EncodeMode.PRESERVE), raw)
        # Legacy alias
        self.assertEqual(fit.to_bytes(preserve=True), raw)

    def test_dirty_unknown_survives_preserve(self):
        raw = build_record_with_unknown_field(
            heart_rate=100, unknown_field_id=250, unknown_value=0xBEEF,
        )
        fit = FitFile.from_bytes(raw)
        data = next(r for r in fit.records if not r.is_definition)
        assert isinstance(data.message, RecordMessage)
        data.message.heart_rate = 88

        out = fit.to_bytes(mode=EncodeMode.PRESERVE)
        again = FitFile.from_bytes(out)
        message = next(r.message for r in again.records if not r.is_definition)
        assert isinstance(message, RecordMessage)
        self.assertEqual(message.heart_rate, 88)
        unknown = message.get_field(250)
        assert isinstance(unknown, UnknownField)
        self.assertEqual(unknown.get_value(), 0xBEEF)


class TestCanonicalModeInvariants(unittest.TestCase):
    def test_canonical_full_reproject_valid(self):
        mesg = WorkoutStepMessage(local_id=0)
        mesg.workout_step_name = 'canon'
        mesg.duration_type = WorkoutStepDuration.DISTANCE
        builder = FitFileBuilder(auto_define=True)
        builder.add(mesg)
        original = builder.build().to_bytes()

        fit = FitFile.from_bytes(original)
        out = fit.to_bytes(mode=EncodeMode.CANONICAL)
        # Must be valid FIT (CRC checks on load).
        again = FitFile.from_bytes(out)
        names = [
            r.message.workout_step_name
            for r in again.records
            if not r.is_definition and isinstance(r.message, WorkoutStepMessage)
        ]
        self.assertIn('canon', names)

    def test_preserve_false_alias(self):
        raw = build_record_with_unknown_field(heart_rate=55)
        fit = FitFile.from_bytes(raw)
        a = fit.to_bytes(mode=EncodeMode.CANONICAL)
        b = fit.to_bytes(preserve=False)
        self.assertEqual(a, b)

    def test_canonical_re_encodes_dirty_and_clean(self):
        """Canonical does not keep source_bytes for clean records."""
        raw = build_record_with_unknown_field(heart_rate=70)
        fit = FitFile.from_bytes(raw)
        # No dirty records, but CANONICAL still rebuilds.
        out = fit.to_bytes(mode=EncodeMode.CANONICAL)
        # May differ in layout but must round-trip heart rate.
        again = FitFile.from_bytes(out)
        message = next(r.message for r in again.records if not r.is_definition)
        assert isinstance(message, RecordMessage)
        self.assertEqual(message.heart_rate, 70)

    def test_strict_true_alone_forces_canonical(self):
        raw = build_record_with_unknown_field(heart_rate=40)
        fit = FitFile.from_bytes(raw)
        # strict=True without mode → canonical path; FILE_TYPE fails without file_id.
        with self.assertRaises(FitValidationError):
            fit.to_bytes(strict=True)
        # Non-strict canonical still works (no precheck).
        out = fit.to_bytes(mode=EncodeMode.CANONICAL, strict=False)
        FitFile.from_bytes(out)

    def test_options_object_canonical(self):
        raw = build_record_with_unknown_field(heart_rate=41)
        fit = FitFile.from_bytes(raw)
        out = fit.to_bytes(options=EncodeOptions(mode=EncodeMode.CANONICAL))
        FitFile.from_bytes(out)


class TestInvalidValuePolicy(unittest.TestCase):
    def test_out_of_range_rejected_at_set_not_clamped(self):
        field = Field(
            field_id=3, name='heart_rate', base_type=BaseType.UINT8, size=1, growable=False,
        )
        with self.assertRaises(FitEncodingError):
            field.set_encoded_value(0, 300)  # > UINT8 max

    def test_none_encodes_as_protocol_invalid(self):
        field = Field(
            field_id=3, name='heart_rate', base_type=BaseType.UINT8, size=1, growable=False,
        )
        field.set_value(0, None)
        self.assertEqual(field.encoded_values[0], BaseType.UINT8.invalid_raw_value())
        packed = field.to_bytes()
        self.assertEqual(packed, bytes([0xFF]))

    def test_cleared_field_on_definition_emits_invalid_fill(self):
        raw = build_record_with_unknown_field(heart_rate=120)
        fit = FitFile.from_bytes(raw)
        data = next(r for r in fit.records if not r.is_definition)
        assert isinstance(data.message, RecordMessage)
        data.message.heart_rate = None  # type: ignore[assignment]

        out = fit.to_bytes(mode=EncodeMode.PRESERVE)
        again = FitFile.from_bytes(out)
        message = next(r.message for r in again.records if not r.is_definition)
        assert isinstance(message, RecordMessage)
        self.assertNotEqual(message.heart_rate, 120)


class TestExpandedComponentsOnEncode(unittest.TestCase):
    def test_expanded_destinations_not_written_unless_on_definition(self):
        """Packed field 8 expands speed/distance at decode; re-encode keeps def slots."""
        raw = build_record_with_compressed_speed_distance(
            speed_encoded_12bit=1000, distance_encoded_12bit=32,
        )
        fit = FitFile.from_bytes(raw)
        data = next(r for r in fit.records if not r.is_definition)
        message = data.message
        assert isinstance(message, RecordMessage)
        # Expanded destinations exist in memory after decode.
        speed = message.get_field(6)
        distance = message.get_field(5)
        self.assertIsNotNone(speed)
        self.assertIsNotNone(distance)
        self.assertTrue(speed.is_expanded_field or speed.is_valid())

        # Preserve unedited: bit-identical (packed source only on wire).
        self.assertEqual(fit.to_bytes(mode=EncodeMode.PRESERVE), raw)

        # Canonical: only definition fields (timestamp + field 8) appear on wire.
        out = fit.to_bytes(mode=EncodeMode.CANONICAL)
        document = decode_bytes(out)
        segment = document.first_segment
        assert segment is not None
        data_raw = next(r for r in segment.records if not r.header.is_definition)
        # Payload = 4 (ts) + 3 (packed field 8) when definition matches builder.
        self.assertEqual(len(data_raw.payload), 7)


class TestCompressedTimestampOnEncode(unittest.TestCase):
    def _build_compressed_with_field_253(self) -> bytes:
        """Definition includes 253; data uses compressed header (empty body for 253)."""
        # Normal definition with only heart_rate (no 253) + compressed data is
        # the hard case. Prefer definition WITH 253 so expansion is possible:
        # For this test, craft def with 253+HR, then a normal data with ts+hr,
        # then a compressed data that omits body timestamp is non-trivial.
        # Use two records: full timestamp first, then compressed sibling.
        fields = [
            FieldDefinition(field_id=253, size=4, base_type=BaseType.UINT32),
            FieldDefinition(field_id=3, size=1, base_type=BaseType.UINT8),
        ]
        # First: normal data with full timestamp
        normal = definition_and_data(
            global_id=20,
            field_definitions=fields,
            payload=struct.pack('<IB', 1000, 60),
            local_id=0,
        )
        # Compressed header: local_id=0, offset=5 → byte 0x80 | (0<<5) | 5 = 0x85
        # Payload still carries fields per definition (wire decoder does not strip
        # 253 from payload). Use a second definition-less compressed record with
        # payload matching definition size so projection works.
        compressed_header = bytes([0x85])
        compressed_payload = struct.pack('<IB', 0xFFFFFFFF, 70)  # invalid ts slot + HR
        # Rebuild as: def+normal, then compressed data only
        body = normal + compressed_header + compressed_payload
        return wrap_records(body)

    def test_preserve_keeps_compressed_header_bytes(self):
        raw = self._build_compressed_with_field_253()
        fit = FitFile.from_bytes(raw)
        # Find a compressed projected record if any.
        compressed = [r for r in fit.records if r.header.is_time_compressed]
        if not compressed:
            self.skipTest('fixture did not produce compressed projection')
        out = fit.to_bytes(mode=EncodeMode.PRESERVE)
        self.assertEqual(out, raw)

    def test_canonical_expands_when_253_on_definition(self):
        raw = self._build_compressed_with_field_253()
        fit = FitFile.from_bytes(raw)
        compressed = [r for r in fit.records if r.header.is_time_compressed]
        if not compressed:
            self.skipTest('fixture did not produce compressed projection')
        self.assertTrue(can_expand_compressed_to_normal(compressed[0].message))

        out = fit.to_bytes(mode=EncodeMode.CANONICAL)
        again = FitFile.from_bytes(out)
        # After canonical, compressed headers should be gone (expanded).
        self.assertFalse(any(r.header.is_time_compressed for r in again.records))

    def test_strict_refuses_expand_without_253(self):
        """Definition without field 253 cannot expand compressed header in strict mode."""
        from fit_tool.data_message import DataMessage
        from fit_tool.definition_message import DefinitionMessage
        from fit_tool.endian import Endian

        definition = DefinitionMessage(
            local_id=0,
            global_id=20,
            endian=Endian.LITTLE,
            field_definitions=[
                FieldDefinition(field_id=3, size=1, base_type=BaseType.UINT8),
            ],
        )
        message = DataMessage(
            local_id=0,
            global_id=20,
            definition_message=definition,
            fields=[
                Field(field_id=3, name='heart_rate', base_type=BaseType.UINT8, size=1),
            ],
        )
        message.get_field(3).set_encoded_value(0, 70, check_validity=False)
        header = RecordHeader(
            is_time_compressed=True,
            is_definition=False,
            local_id=0,
            time_offset_seconds=3,
        )
        record = Record(header, message, dirty=True)
        options = EncodeOptions(mode=EncodeMode.CANONICAL, strict=True)
        with self.assertRaises(FitEncodingError):
            encode_record_projected(record, options=options)


class TestPublicApiEncodeSymbols(unittest.TestCase):
    def test_encode_mode_exported(self):
        from fit_tool import EncodeMode, EncodeOptions

        self.assertEqual(EncodeMode.PRESERVE.value, 'preserve')
        self.assertEqual(EncodeMode.CANONICAL.value, 'canonical')
        self.assertIsInstance(EncodeOptions(), EncodeOptions)


class TestScaleNormalizationPolicy(unittest.TestCase):
    def test_scale_rounds_on_encode(self):
        """Canonical scale path uses round(); not silent clamp of out-of-range."""
        field = Field(
            field_id=0,
            name='speed',
            base_type=BaseType.UINT16,
            scale=1000.0,
            offset=0.0,
            size=2,
            growable=False,
        )
        field.set_value(0, 1.23456)  # → round(1234.56) = 1235
        self.assertEqual(field.encoded_values[0], 1235)


if __name__ == '__main__':
    unittest.main()
