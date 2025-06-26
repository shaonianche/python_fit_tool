from fit_tool.base_type import BaseType
from fit_tool.field import Field
from fit_tool.field_definition import FieldDefinition


def test_field_definition_conversions():
    fd1 = FieldDefinition(field_id=255, size=20, base_type=BaseType.UINT16)
    bytes1 = fd1.to_bytes()
    fd2 = FieldDefinition.from_bytes(bytes1)
    bytes2 = fd2.to_bytes()

    assert bytes2 == bytes1


def test_field_integer_conversions():
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
            assert value_from_bytes == value

            value = max_value
            bytes_buffer = field.encoded_value_to_bytes(value)
            value_from_bytes = field.get_encoded_value_from_bytes(bytes_buffer)
            assert value_from_bytes == value


def test_field_string_conversions():
    field = Field(base_type=BaseType.STRING)
    value = "test12345"
    bytes_buffer = field.encoded_value_to_bytes(value)
    value_from_bytes = field.get_encoded_value_from_bytes(bytes_buffer)
    assert value == value_from_bytes


def test_field_float_conversions():
    field = Field(base_type=BaseType.FLOAT32)
    value = 3.14
    bytes_buffer = field.encoded_value_to_bytes(value)
    value_from_bytes = field.get_encoded_value_from_bytes(bytes_buffer)
    bytes2 = field.encoded_value_to_bytes(value_from_bytes)

    assert abs(value - value_from_bytes) < 1e-3
    assert bytes2 == bytes_buffer

    field = Field(base_type=BaseType.FLOAT64)
    value = 3.14
    bytes_buffer = field.encoded_value_to_bytes(value)
    value_from_bytes = field.get_encoded_value_from_bytes(bytes_buffer)
    bytes2 = field.encoded_value_to_bytes(value_from_bytes)

    assert abs(value - value_from_bytes) < 1e-3
    assert bytes2 == bytes_buffer


def test_field_string_to_row():
    field = Field(name="title", base_type=BaseType.STRING, growable=True)
    value = "test12345"
    field.set_encoded_value(0, value)
    field.to_row()
