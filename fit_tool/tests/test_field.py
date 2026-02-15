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
                value_from_bytes = field.get_encoded_value_from_bytes(bytes_buffer);
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
