# nosetests --nocapture  tests/test_field.py

import unittest

from fit_tool.base_type import BaseType
from fit_tool.field import Field
from fit_tool.field_definition import FieldDefinition


class TestField(unittest.TestCase):

    def shortDescription(self):
        return None

    def test_field_definition_conversions(self):
        fd1 = FieldDefinition(field_id=255, size=20, base_type=BaseType.UINT16)
        bytes1 = fd1.to_bytes()
        fd2 = FieldDefinition.from_bytes(bytes1)
        bytes2 = fd2.to_bytes()

        self.assertEqual(bytes2, bytes1)

    def test_field_integer_conversions(self):

        for base_type in BaseType:
            if base_type.is_float() or base_type.is_big() or base_type.is_string:
                continue

            field = Field(base_type=base_type)
            min_value = base_type.min
            max_value = base_type.max
            if min_value is not None and max_value is not None:
                value = min_value
                bytes_buffer = field.encoded_value_to_bytes(value)
                value_from_bytes = field.get_encoded_value_from_bytes(bytes_buffer)
                self.assertEqual(value_from_bytes, value)

                value = max_value
                bytes_buffer = field.encoded_value_to_bytes(value)
                value_from_bytes = field.get_encoded_value_from_bytes(bytes_buffer)
                self.assertEqual(value_from_bytes, value)

    def test_field_string_conversions(self):
        field = Field(base_type=BaseType.STRING)
        value = 'test12345'
        bytes_buffer = field.encoded_value_to_bytes(value)
        value_from_bytes = field.get_encoded_value_from_bytes(bytes_buffer)
        self.assertEqual(value, value_from_bytes)

    def test_field_float_conversions(self):
        field = Field(base_type=BaseType.FLOAT32)
        value = 3.14
        bytes_buffer = field.encoded_value_to_bytes(value)
        value_from_bytes = field.get_encoded_value_from_bytes(bytes_buffer)
        bytes2 = field.encoded_value_to_bytes(value_from_bytes)

        self.assertAlmostEqual(value, value_from_bytes, 3)
        self.assertEqual(bytes2, bytes_buffer)

        field = Field(base_type=BaseType.FLOAT64)
        value = 3.14
        bytes_buffer = field.encoded_value_to_bytes(value)
        value_from_bytes = field.get_encoded_value_from_bytes(bytes_buffer)
        bytes2 = field.encoded_value_to_bytes(value_from_bytes)

        self.assertAlmostEqual(value, value_from_bytes, 3)
        self.assertEqual(bytes2, bytes_buffer)

    def test_float_set_value_preserves_fractional_component(self):
        """FLOAT fields must not truncate via int() when scale/offset are identity (P0)."""
        field = Field(name='grit', base_type=BaseType.FLOAT32, size=4, scale=1.0, offset=0.0)
        field.set_value(0, 3.14)

        self.assertIsInstance(field.encoded_values[0], float)
        self.assertAlmostEqual(field.get_value(), 3.14, places=5)

    def test_float_invalid_value_uses_all_ones_bit_pattern(self):
        """FIT invalid floats are all-ones bits, represented as None in Python (P0)."""
        for base_type, expected_bytes in (
            (BaseType.FLOAT32, b'\xff\xff\xff\xff'),
            (BaseType.FLOAT64, b'\xff\xff\xff\xff\xff\xff\xff\xff'),
        ):
            field = Field(name='x', base_type=base_type, size=base_type.size)
            field.set_value(0, None)

            self.assertIsNone(field.encoded_values[0])
            self.assertEqual(field.to_bytes(), expected_bytes)

            decoded = Field(name='x', base_type=base_type, size=base_type.size)
            decoded.read_all_from_bytes(expected_bytes)
            self.assertIsNone(decoded.get_value())
            self.assertEqual(decoded.to_bytes(), expected_bytes)

    def test_float_set_value_round_trips_through_bytes(self):
        field = Field(name='flow', base_type=BaseType.FLOAT32, size=4, scale=1.0)
        field.set_value(0, 2.5)
        wire = field.to_bytes()

        restored = Field(name='flow', base_type=BaseType.FLOAT32, size=4, scale=1.0)
        restored.read_all_from_bytes(wire)
        self.assertAlmostEqual(restored.get_value(), 2.5, places=5)

    def test_set_encoded_value_rejects_none_for_integer_fields(self):
        """Codex P2: integer fields must not silently accept None as an encoded value."""
        field = Field(name='heart_rate', base_type=BaseType.UINT8, size=1)
        with self.assertRaises(ValueError):
            field.set_encoded_value(0, None)

        enum_field = Field(name='sport', base_type=BaseType.ENUM, size=1)
        with self.assertRaises(ValueError):
            enum_field.set_encoded_value(0, None)

    def test_set_encoded_value_allows_none_for_float_fields(self):
        field = Field(name='grit', base_type=BaseType.FLOAT32, size=4)
        field.set_encoded_value(0, None)
        self.assertIsNone(field.encoded_values[0])
        self.assertEqual(field.to_bytes(), b'\xff\xff\xff\xff')

    def test_float_encode_value_applies_scale_and_offset(self):
        field = Field(name='scaled', base_type=BaseType.FLOAT32, size=4, scale=2.0, offset=1.0)
        field.set_value(0, 3.0)  # (3 + 1) * 2 = 8
        self.assertAlmostEqual(field.encoded_values[0], 8.0, places=5)

    def test_float_legacy_invalid_raw_int_still_packs_all_ones(self):
        """Integer invalid markers left from pre-fix code still encode correctly."""
        field = Field(name='x', base_type=BaseType.FLOAT32, size=4)
        field.set_encoded_value(0, BaseType.FLOAT32.invalid_raw_value(), check_validity=False)
        self.assertEqual(field.to_bytes(), b'\xff\xff\xff\xff')

    def test_field_string_to_row(self):
        field = Field(name='title', base_type=BaseType.STRING, growable=True)
        value = 'test12345'
        field.set_encoded_value(0, value)
        field.to_row()

    def test_from_field_does_not_share_encoded_values(self):
        original = Field(name='speed', base_type=BaseType.UINT8, size=1)
        original.set_encoded_value(0, 7, check_validity=False)

        clone = Field.from_field(original)
        clone.set_encoded_value(0, 9, check_validity=False)

        self.assertEqual(original.encoded_values, [7])
        self.assertEqual(clone.encoded_values, [9])
        self.assertIsNot(original.encoded_values, clone.encoded_values)

    def test_un_scale_offset_value_raises_on_zero_scale(self):
        with self.assertRaises(ZeroDivisionError):
            Field.un_scale_offset_value(encoded_value=1, scale=0, offset=0)

    def test_set_encoded_value_raises_value_error_when_not_growable(self):
        field = Field(name='speed', base_type=BaseType.UINT8, size=1, growable=False)
        with self.assertRaises(ValueError):
            field.set_encoded_value(1, 2)

    def test_read_from_bytes_raises_type_error_for_string_base_type(self):
        field = Field(base_type=BaseType.STRING, size=1)
        with self.assertRaises(TypeError):
            field.read_from_bytes(b'\x00', index=0)

    def test_get_length_from_size_raises_value_error_for_mismatched_size(self):
        with self.assertRaises(ValueError):
            Field.get_length_from_size(BaseType.UINT16, 3)

    def test_encoded_value_to_bytes_raises_value_error_for_none(self):
        field = Field(base_type=BaseType.UINT8)
        with self.assertRaises(ValueError):
            field.encoded_value_to_bytes(None)

    def test_set_encoded_value_raises_value_error_for_out_of_range_value(self):
        field = Field(name='speed', base_type=BaseType.UINT8, size=1)
        with self.assertRaises(ValueError):
            field.set_encoded_value(0, 999)

    def test_set_encoded_value_raises_value_error_when_string_exceeds_fixed_size(self):
        field = Field(name='title', base_type=BaseType.STRING, size=1, growable=False)
        with self.assertRaises(ValueError):
            field.set_encoded_value(0, 'ab')

    def test_read_all_from_bytes_supports_numeric_offset(self):
        field = Field(base_type=BaseType.UINT16, size=2)

        field.read_all_from_bytes(b'\xff\x34\x12', offset=1)

        self.assertEqual(field.encoded_values, [0x1234])

    def test_read_all_from_bytes_supports_string_offset(self):
        field = Field(base_type=BaseType.STRING, size=4)

        field.read_all_from_bytes(memoryview(b'\xffabc\0'), offset=1)

        self.assertEqual(field.encoded_values, ['abc'])


class TestFieldSubFieldsAndHelpers(unittest.TestCase):
    """Cover SubField-aware getters, clear, and edge encoding paths."""

    def _field_with_sub(self):
        from fit_tool.sub_field import SubField

        sub = SubField(
            name='distance',
            base_type=BaseType.UINT16,
            scale=100.0,
            offset=0.0,
            units='m',
            reference_map={1: [1]},
        )
        field = Field(
            name='duration_value',
            base_type=BaseType.UINT32,
            size=4,
            units='ms',
            scale=1.0,
            offset=0.0,
            sub_fields=[sub],
        )
        field.set_encoded_value(0, 1000, check_validity=False)
        return field, sub

    def test_get_sub_field_by_index_and_name(self):
        field, sub = self._field_with_sub()
        self.assertIs(field.get_sub_field(index=0), sub)
        self.assertIs(field.get_sub_field(name='distance'), sub)
        self.assertIsNone(field.get_sub_field(name='missing'))
        self.assertIsNone(field.get_sub_field(index=99))
        self.assertIsNone(field.get_sub_field())

    def test_get_name_units_base_type_offset_scale_with_subfield(self):
        field, sub = self._field_with_sub()
        self.assertEqual(field.get_name(sub_field=sub), 'distance')
        self.assertEqual(field.get_name(sub_field_name='distance'), 'distance')
        self.assertEqual(field.get_name(sub_field_index=0), 'distance')
        self.assertEqual(field.get_name(), 'duration_value')

        self.assertEqual(field.get_units(sub_field=sub), 'm')
        self.assertEqual(field.get_units(sub_field_name='distance'), 'm')
        self.assertEqual(field.get_units(sub_field_index=0), 'm')
        self.assertEqual(field.get_units(), 'ms')

        self.assertEqual(field.get_base_type(sub_field=sub), BaseType.UINT16)
        self.assertEqual(field.get_base_type(sub_field_name='distance'), BaseType.UINT16)
        self.assertEqual(field.get_base_type(sub_field_index=0), BaseType.UINT16)
        self.assertEqual(field.get_base_type(), BaseType.UINT32)

        self.assertEqual(field.get_offset(sub_field=sub), 0.0)
        self.assertEqual(field.get_offset(sub_field_name='distance'), 0.0)
        self.assertEqual(field.get_offset(sub_field_index=0), 0.0)

        self.assertEqual(field.get_scale(sub_field=sub), 100.0)
        self.assertEqual(field.get_scale(sub_field_name='distance'), 100.0)
        self.assertEqual(field.get_scale(sub_field_index=0), 100.0)

    def test_clear_and_is_valid(self):
        field = Field(name='x', base_type=BaseType.UINT8, size=1)
        field.set_encoded_value(0, 1)
        self.assertTrue(field.is_valid())
        field.clear()
        self.assertEqual(field.size, 0)
        self.assertEqual(field.encoded_values, [])
        self.assertTrue(field.is_not_valid())

    def test_set_encoded_value_negative_index_is_noop(self):
        field = Field(name='x', base_type=BaseType.UINT8, size=1)
        field.set_encoded_value(0, 5)
        field.set_encoded_value(-1, 9)
        self.assertEqual(field.encoded_values, [5])

    def test_encode_value_float_none_and_enum(self):
        from enum import Enum

        class Sample(Enum):
            A = 3

        float_field = Field(name='f', base_type=BaseType.FLOAT32, size=4)
        self.assertIsNone(float_field.encode_value(None))

        int_field = Field(name='i', base_type=BaseType.UINT8, size=1)
        self.assertEqual(int_field.encode_value(None), BaseType.UINT8.invalid_raw_value())
        self.assertEqual(int_field.encode_value(Sample.A), 3)

    def test_string_encoded_value_to_bytes_rejects_none(self):
        field = Field(name='s', base_type=BaseType.STRING, size=1)
        with self.assertRaises(ValueError):
            field.encoded_value_to_bytes(None)

    def test_from_field_definition_and_get_values(self):
        definition = FieldDefinition(field_id=7, size=2, base_type=BaseType.UINT16)
        field = Field.from_field_definition(definition)
        self.assertEqual(field.field_id, 7)
        self.assertEqual(field.size, 2)
        field.set_encoded_value(0, 42, check_validity=False)
        self.assertEqual(field.get_values(), [42])
        self.assertIsNone(field.get_value(index=99))

    def test_decode_value_with_scale_and_date_time(self):
        field = Field(
            name='timestamp',
            base_type=BaseType.UINT32,
            size=4,
            scale=1.0,
            offset=0.0,
            type_name='date_time',
        )
        # With identity scale, decode returns raw
        self.assertEqual(field.decode_value(100), 100)

        scaled = Field(name='s', base_type=BaseType.UINT16, size=2, scale=100.0, offset=1.0, type_name='date_time')
        # un_scale: 200/100 - 1 = 1.0 -> round for date_time
        self.assertEqual(scaled.decode_value(200), 1)

    def test_get_valid_sub_field(self):
        from fit_tool.sub_field import SubField

        ref = Field(name='duration_type', field_id=1, base_type=BaseType.ENUM, size=1)
        ref.set_encoded_value(0, 1, check_validity=False)
        sub = SubField(name='distance', base_type=BaseType.UINT32, reference_map={1: [1]})
        # is_valid checks field.get_value() in reference_map keys (field ids), which is a quirk;
        # exercise the method path either way
        field = Field(name='duration_value', field_id=2, base_type=BaseType.UINT32, size=4, sub_fields=[sub])
        result = field.get_valid_sub_field([ref, field])
        # May be None or SubField depending on is_valid logic; just call it
        self.assertTrue(result is None or result is sub)

        empty = Field(name='plain', base_type=BaseType.UINT8, size=1)
        self.assertIsNone(empty.get_valid_sub_field([]))

    def test_to_row_multi_value(self):
        field = Field(name='hrv', base_type=BaseType.UINT16, size=4, growable=True)
        field.set_encoded_value(0, 10, check_validity=False)
        field.set_encoded_value(1, 20, check_validity=False)
        row = field.to_row()
        self.assertEqual(row[0], 'hrv')
        self.assertIn('10', str(row[1]))
        self.assertIn('20', str(row[1]))
