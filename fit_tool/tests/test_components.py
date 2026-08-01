"""Component registry coverage, nested expansion, and accumulator rollover (SHA-15)."""

from __future__ import annotations

import struct
import unittest

from fit_tool.base_type import BaseType
from fit_tool.components import (
    PROFILE_COMPONENTS,
    components_for_field,
    expand_message_components,
    registry_coverage,
)
from fit_tool.field_component import FieldComponent
from fit_tool.field_definition import FieldDefinition
from fit_tool.fit_file import FitFile
from fit_tool.profile.messages.record_message import RecordMessage
from fit_tool.tests.protocol_fixture_helpers import (
    build_record_with_compressed_speed_distance,
    definition_and_data,
    wrap_records,
)


class TestRegistryCoverage(unittest.TestCase):
    def test_full_main_field_coverage(self):
        coverage = registry_coverage()
        self.assertEqual(coverage['profile_main_field_sources'], 37)
        self.assertEqual(coverage['registry_entries'], 37)
        self.assertEqual(coverage['coverage_ratio'], 1.0)
        self.assertIn('subfield', str(coverage['subfield_components']).lower())

    def test_known_record_packed_fields_present(self):
        # compressed_speed_distance and compressed_accumulated_power
        self.assertIn((20, 8), PROFILE_COMPONENTS)
        self.assertIn((20, 28), PROFILE_COMPONENTS)
        # enhanced expansion sources
        self.assertIn((20, 2), PROFILE_COMPONENTS)  # altitude → enhanced_altitude
        self.assertIn((20, 6), PROFILE_COMPONENTS)  # speed → enhanced_speed
        # accumulate cycles
        self.assertIn((20, 18), PROFILE_COMPONENTS)

    def test_distance_component_accumulates_per_profile(self):
        """Profile marks distance in compressed_speed_distance as accumulate=1."""
        components = PROFILE_COMPONENTS[(20, 8)]
        self.assertEqual(len(components), 2)
        self.assertEqual(components[0].field_id, 6)  # speed
        self.assertFalse(components[0].accumulate)
        self.assertEqual(components[1].field_id, 5)  # distance
        self.assertTrue(components[1].accumulate)


class TestNestedAndEnhancedExpansion(unittest.TestCase):
    def test_nested_compressed_speed_distance_to_enhanced_speed(self):
        """compressed_speed_distance → speed → enhanced_speed (nested)."""
        packed = 1000 | (32 << 12)
        message = RecordMessage()
        source = message.get_field(8)
        assert source is not None
        source.size = 3
        source.encoded_values = [
            packed & 0xFF,
            (packed >> 8) & 0xFF,
            (packed >> 16) & 0xFF,
        ]
        expand_message_components(message)

        speed = message.get_field(6)
        enhanced = message.get_field(73)
        distance = message.get_field(5)
        assert speed is not None and enhanced is not None and distance is not None
        self.assertAlmostEqual(speed.get_value(), 10.0)
        self.assertAlmostEqual(enhanced.get_value(), 10.0)
        self.assertAlmostEqual(distance.get_value(), 2.0)
        self.assertTrue(speed.is_expanded_field)
        self.assertTrue(enhanced.is_expanded_field)

    def test_wire_decode_nested_enhanced_speed(self):
        raw = build_record_with_compressed_speed_distance(
            speed_encoded_12bit=1000,
            distance_encoded_12bit=32,
        )
        fit = FitFile.from_bytes(raw)
        message = next(r.message for r in fit.records if not r.header.is_definition)
        self.assertIsInstance(message, RecordMessage)
        enhanced = message.get_field(73)
        assert enhanced is not None
        self.assertAlmostEqual(enhanced.get_value(), 10.0)

    def test_altitude_expands_to_enhanced_altitude(self):
        # altitude encoded = (meters + 500) * 5 → 2500 m → 15000
        message = RecordMessage()
        altitude = message.get_field(2)
        assert altitude is not None
        altitude.size = 2
        altitude.encoded_values = [15000]
        expand_message_components(message)
        enhanced = message.get_field(78)
        assert enhanced is not None
        self.assertAlmostEqual(enhanced.get_value(), 2500.0)
        self.assertTrue(enhanced.is_expanded_field)

    def test_wire_enhanced_not_overwritten_by_base_component(self):
        """When enhanced_speed is already on the wire, base speed expansion skips it."""
        # speed encoded 1000 → 1.0 m/s; enhanced_speed encoded 5000 → 5.0 m/s
        payload = (
            struct.pack('<I', 1000)
            + struct.pack('<H', 1000)  # speed field 6
            + struct.pack('<I', 5000)  # enhanced_speed field 73
        )
        records = definition_and_data(
            global_id=20,
            field_definitions=[
                FieldDefinition(field_id=253, size=4, base_type=BaseType.UINT32),
                FieldDefinition(field_id=6, size=2, base_type=BaseType.UINT16),
                FieldDefinition(field_id=73, size=4, base_type=BaseType.UINT32),
            ],
            payload=payload,
        )
        fit = FitFile.from_bytes(wrap_records(records))
        message = next(r.message for r in fit.records if not r.header.is_definition)
        enhanced = message.get_field(73)
        assert enhanced is not None
        self.assertAlmostEqual(enhanced.get_value(), 5.0)
        self.assertFalse(enhanced.is_expanded_field)

    def test_field_attached_components_still_honoured(self):
        message = RecordMessage()
        empty = message.get_field(0)
        assert empty is not None
        self.assertEqual(components_for_field(20, empty), ())

        source = message.get_field(8)
        assert source is not None
        source.components = [
            FieldComponent(field_id=6, accumulate=False, bits=12, scale=100.0, offset=0.0),
        ]
        self.assertEqual(len(components_for_field(20, source)), 1)


class TestAccumulatorRollover(unittest.TestCase):
    def test_16bit_power_rollover(self):
        message = RecordMessage()
        source = message.get_field(28)
        assert source is not None
        source.size = 2
        acc: dict[tuple[int, int], int] = {}

        source.encoded_values = [65535]
        expand_message_components(message, acc)
        self.assertEqual(acc[(20, 29)], 65535)

        source.encoded_values = [1]
        expand_message_components(message, acc)
        power = message.get_field(29)
        assert power is not None
        self.assertEqual(acc[(20, 29)], 65537)
        self.assertEqual(power.get_value(), 65537)

    def test_8bit_cycles_accumulate_to_total_cycles(self):
        message = RecordMessage()
        source = message.get_field(18)  # cycles
        assert source is not None
        source.size = 1
        acc: dict[tuple[int, int], int] = {}

        source.encoded_values = [250]
        expand_message_components(message, acc)
        self.assertEqual(acc[(20, 19)], 250)

        source.encoded_values = [10]  # wrap: delta = (10 - 250) % 256 = 16
        expand_message_components(message, acc)
        total = message.get_field(19)
        assert total is not None
        self.assertEqual(acc[(20, 19)], 266)
        self.assertEqual(total.get_value(), 266)

    def test_distance_accumulate_across_records(self):
        """compressed_speed_distance.distance accumulates across records."""
        message = RecordMessage()
        source = message.get_field(8)
        assert source is not None
        source.size = 3
        acc: dict[tuple[int, int], int] = {}

        def set_packed(speed_12: int, distance_12: int) -> None:
            packed = (speed_12 & 0xFFF) | ((distance_12 & 0xFFF) << 12)
            source.encoded_values = [
                packed & 0xFF,
                (packed >> 8) & 0xFF,
                (packed >> 16) & 0xFF,
            ]

        set_packed(100, 16)  # distance raw 16 → 1.0 m at scale 16
        expand_message_components(message, acc)
        self.assertEqual(acc[(20, 5)], 16)

        set_packed(100, 20)  # delta 4
        expand_message_components(message, acc)
        self.assertEqual(acc[(20, 5)], 20)

        set_packed(100, 2)  # wrap 12-bit: (2 - 20) % 4096 = 4078 → total 20+4078
        expand_message_components(message, acc)
        self.assertEqual(acc[(20, 5)], 20 + 4078)
        distance = message.get_field(5)
        assert distance is not None
        # Component scale 16 → meters; destination re-encodes with scale 100
        # (integer round-trip can lose 1/100 m).
        self.assertAlmostEqual(distance.get_value(), (20 + 4078) / 16.0, places=2)


if __name__ == '__main__':
    unittest.main()


class TestVariableLengthPayload(unittest.TestCase):
    """Codex P1: do not invent components past source.size * 8 bits."""

    def test_variable_length_stops_at_payload_bits(self):
        from types import SimpleNamespace

        from fit_tool.field import Field

        source = Field(
            field_id=1,
            name='packed',
            base_type=BaseType.BYTE,
            size=3,
            growable=False,
            components=[
                FieldComponent(field_id=2, accumulate=False, bits=12, scale=1.0, offset=0.0)
                for _ in range(10)
            ],
        )
        source.set_encoded_value(0, 0x11)
        source.set_encoded_value(1, 0x22)
        source.set_encoded_value(2, 0x33)
        dest = Field(
            field_id=2,
            name='slot',
            base_type=BaseType.UINT16,
            size=2,
            growable=True,
        )
        if hasattr(dest, 'clear'):
            dest.clear()
        msg = SimpleNamespace(global_id=999, fields=[source, dest])
        expand_message_components(msg)
        values = [v for v in dest.encoded_values if v is not None]
        self.assertEqual(len(values), 2)
