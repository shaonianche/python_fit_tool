import pytest
from fit_tool.base_type import BaseType, FieldType


class TestBaseTypeSize:
    def test_size_1_byte_types(self):
        assert BaseType.ENUM.size == 1
        assert BaseType.SINT8.size == 1
        assert BaseType.UINT8.size == 1
        assert BaseType.STRING.size == 1
        assert BaseType.UINT8Z.size == 1
        assert BaseType.BYTE.size == 1

    def test_size_2_byte_types(self):
        assert BaseType.SINT16.size == 2
        assert BaseType.UINT16.size == 2
        assert BaseType.UINT16Z.size == 2

    def test_size_4_byte_types(self):
        assert BaseType.SINT32.size == 4
        assert BaseType.UINT32.size == 4
        assert BaseType.FLOAT32.size == 4
        assert BaseType.UINT32Z.size == 4

    def test_size_8_byte_types(self):
        assert BaseType.FLOAT64.size == 8
        assert BaseType.SINT64.size == 8
        assert BaseType.UINT64.size == 8
        assert BaseType.UINT64Z.size == 8


class TestBaseTypeIsInteger:
    def test_is_integer_true(self):
        integer_types = [
            BaseType.SINT8, BaseType.UINT8, BaseType.SINT16, BaseType.UINT16,
            BaseType.UINT16Z, BaseType.SINT32, BaseType.UINT32, BaseType.UINT32Z,
            BaseType.SINT64, BaseType.UINT64, BaseType.UINT64Z,
        ]
        for t in integer_types:
            assert t.is_integer() is True

    def test_is_integer_false(self):
        non_integer_types = [
            BaseType.ENUM, BaseType.STRING, BaseType.FLOAT32, BaseType.FLOAT64, BaseType.BYTE,
        ]
        for t in non_integer_types:
            assert t.is_integer() is False


class TestBaseTypeIsSignedInteger:
    def test_is_signed_integer_true(self):
        signed_types = [BaseType.SINT8, BaseType.SINT16, BaseType.SINT32, BaseType.SINT64]
        for t in signed_types:
            assert t.is_signed_integer() is True

    def test_is_signed_integer_false(self):
        unsigned_types = [
            BaseType.UINT8, BaseType.UINT16, BaseType.UINT32, BaseType.UINT64,
            BaseType.UINT8Z, BaseType.UINT16Z, BaseType.UINT32Z, BaseType.UINT64Z,
            BaseType.ENUM, BaseType.STRING, BaseType.FLOAT32, BaseType.FLOAT64, BaseType.BYTE,
        ]
        for t in unsigned_types:
            assert t.is_signed_integer() is False


class TestBaseTypeIsBig:
    def test_is_big_true(self):
        big_types = [BaseType.SINT64, BaseType.UINT64, BaseType.UINT64Z]
        for t in big_types:
            assert t.is_big() is True

    def test_is_big_false(self):
        small_types = [
            BaseType.ENUM, BaseType.SINT8, BaseType.UINT8, BaseType.SINT16,
            BaseType.UINT16, BaseType.SINT32, BaseType.UINT32, BaseType.STRING,
            BaseType.FLOAT32, BaseType.FLOAT64, BaseType.UINT8Z, BaseType.UINT16Z,
            BaseType.UINT32Z, BaseType.BYTE,
        ]
        for t in small_types:
            assert t.is_big() is False


class TestBaseTypeIsString:
    def test_is_string_true(self):
        assert BaseType.STRING.is_string() is True

    def test_is_string_false(self):
        for t in BaseType:
            if t != BaseType.STRING:
                assert t.is_string() is False


class TestBaseTypeIsFloat:
    def test_is_float_true(self):
        assert BaseType.FLOAT32.is_float() is True
        assert BaseType.FLOAT64.is_float() is True

    def test_is_float_false(self):
        non_float_types = [
            BaseType.ENUM, BaseType.SINT8, BaseType.UINT8, BaseType.SINT16,
            BaseType.UINT16, BaseType.SINT32, BaseType.UINT32, BaseType.STRING,
            BaseType.UINT8Z, BaseType.UINT16Z, BaseType.UINT32Z, BaseType.BYTE,
            BaseType.SINT64, BaseType.UINT64, BaseType.UINT64Z,
        ]
        for t in non_float_types:
            assert t.is_float() is False


class TestBaseTypeIsValid:
    def test_is_valid_none(self):
        assert BaseType.UINT8.is_valid(None) is False

    def test_is_valid_string_type(self):
        assert BaseType.STRING.is_valid("test") is True

    def test_is_valid_float_type(self):
        assert BaseType.FLOAT32.is_valid(3.14) is True
        assert BaseType.FLOAT64.is_valid(3.14159265359) is True

    def test_is_valid_in_range(self):
        assert BaseType.UINT8.is_valid(0) is True
        assert BaseType.UINT8.is_valid(255) is True
        assert BaseType.SINT8.is_valid(-128) is True
        assert BaseType.SINT8.is_valid(127) is True

    def test_is_valid_out_of_range(self):
        assert BaseType.UINT8.is_valid(-1) is False
        assert BaseType.UINT8.is_valid(256) is False
        assert BaseType.SINT8.is_valid(-129) is False
        assert BaseType.SINT8.is_valid(128) is False


class TestBaseTypeInvalidRawValue:
    def test_invalid_raw_value_1_byte(self):
        assert BaseType.ENUM.invalid_raw_value() == 0xff
        assert BaseType.SINT8.invalid_raw_value() == 0x7f
        assert BaseType.UINT8.invalid_raw_value() == 0xff
        assert BaseType.UINT8Z.invalid_raw_value() == 0x00
        assert BaseType.BYTE.invalid_raw_value() == 0xff

    def test_invalid_raw_value_2_byte(self):
        assert BaseType.SINT16.invalid_raw_value() == 0x7fff
        assert BaseType.UINT16.invalid_raw_value() == 0xffff
        assert BaseType.UINT16Z.invalid_raw_value() == 0x0000

    def test_invalid_raw_value_4_byte(self):
        assert BaseType.SINT32.invalid_raw_value() == 0x7fffffff
        assert BaseType.UINT32.invalid_raw_value() == 0xffffffff
        assert BaseType.UINT32Z.invalid_raw_value() == 0x00000000
        assert BaseType.FLOAT32.invalid_raw_value() == 0xffffffff

    def test_invalid_raw_value_8_byte(self):
        assert BaseType.SINT64.invalid_raw_value() == 0x7fffffffffffffff
        assert BaseType.UINT64.invalid_raw_value() == 0xffffffffffffffff
        assert BaseType.UINT64Z.invalid_raw_value() == 0x0000000000000000
        assert BaseType.FLOAT64.invalid_raw_value() == 0xffffffffffffffff

    def test_invalid_raw_value_string(self):
        assert BaseType.STRING.invalid_raw_value() == 0x00


class TestBaseTypeMinMax:
    def test_max_values(self):
        assert BaseType.ENUM.max == 0xff
        assert BaseType.SINT8.max == 0x7f
        assert BaseType.UINT8.max == 0xff
        assert BaseType.SINT16.max == 0x7fff
        assert BaseType.UINT16.max == 0xffff
        assert BaseType.SINT32.max == 0x7fffffff
        assert BaseType.UINT32.max == 0xffffffff
        assert BaseType.STRING.max is None
        assert BaseType.FLOAT32.max is None
        assert BaseType.FLOAT64.max is None
        assert BaseType.SINT64.max == 0x7fffffffffffffff
        assert BaseType.UINT64.max == 0xffffffffffffffff

    def test_min_values(self):
        assert BaseType.ENUM.min == 0x00
        assert BaseType.SINT8.min == -0x80
        assert BaseType.UINT8.min == 0x00
        assert BaseType.SINT16.min == -0x8000
        assert BaseType.UINT16.min == 0x0000
        assert BaseType.SINT32.min == -0x80000000
        assert BaseType.UINT32.min == 0x00000000
        assert BaseType.STRING.min is None
        assert BaseType.FLOAT32.min is None
        assert BaseType.FLOAT64.min is None
        assert BaseType.SINT64.min == -0x8000000000000000
        assert BaseType.UINT64.min == 0x0000000000000000


class TestBaseTypeFromName:
    def test_from_name_valid(self):
        assert BaseType.from_name('enum') == BaseType.ENUM
        assert BaseType.from_name('sint8') == BaseType.SINT8
        assert BaseType.from_name('uint8') == BaseType.UINT8
        assert BaseType.from_name('sint16') == BaseType.SINT16
        assert BaseType.from_name('uint16') == BaseType.UINT16
        assert BaseType.from_name('sint32') == BaseType.SINT32
        assert BaseType.from_name('uint32') == BaseType.UINT32
        assert BaseType.from_name('string') == BaseType.STRING
        assert BaseType.from_name('float32') == BaseType.FLOAT32
        assert BaseType.from_name('float64') == BaseType.FLOAT64
        assert BaseType.from_name('uint8z') == BaseType.UINT8Z
        assert BaseType.from_name('uint16z') == BaseType.UINT16Z
        assert BaseType.from_name('uint32z') == BaseType.UINT32Z
        assert BaseType.from_name('byte') == BaseType.BYTE
        assert BaseType.from_name('sint64') == BaseType.SINT64
        assert BaseType.from_name('uint64') == BaseType.UINT64
        assert BaseType.from_name('uint64z') == BaseType.UINT64Z

    def test_from_name_invalid(self):
        assert BaseType.from_name('invalid') is None
        assert BaseType.from_name('') is None
        assert BaseType.from_name('UINT8') is None


class TestFieldType:
    def test_init(self):
        ft = FieldType('test_type', BaseType.UINT8)
        assert ft.name == 'test_type'
        assert ft.base_type == BaseType.UINT8
        assert ft.names_by_value == {}
        assert ft.values_by_name == {}

    def test_add_value(self):
        ft = FieldType('activity_type', BaseType.ENUM)
        ft.add_value('running', 0)
        ft.add_value('cycling', 1)
        ft.add_value('swimming', 2)

        assert ft.names_by_value[0] == 'running'
        assert ft.names_by_value[1] == 'cycling'
        assert ft.names_by_value[2] == 'swimming'
        assert ft.values_by_name['running'] == 0
        assert ft.values_by_name['cycling'] == 1
        assert ft.values_by_name['swimming'] == 2

    def test_get_value_by_name(self):
        ft = FieldType('sport', BaseType.ENUM)
        ft.add_value('running', 0)
        ft.add_value('cycling', 1)

        assert ft.get_value_by_name('running') == 0
        assert ft.get_value_by_name('cycling') == 1
        assert ft.get_value_by_name('unknown') is None

    def test_get_name_by_value(self):
        ft = FieldType('sport', BaseType.ENUM)
        ft.add_value('running', 0)
        ft.add_value('cycling', 1)

        assert ft.get_name_by_value(0) == 'running'
        assert ft.get_name_by_value(1) == 'cycling'
        assert ft.get_name_by_value(99) is None
