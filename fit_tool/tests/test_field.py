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
