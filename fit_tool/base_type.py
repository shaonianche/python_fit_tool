from __future__ import annotations

from enum import Enum, unique


@unique
class BaseType(Enum):
    ENUM = 0
    SINT8 = 1
    UINT8 = 2
    SINT16 = 131
    UINT16 = 132
    SINT32 = 133
    UINT32 = 134
    STRING = 7
    FLOAT32 = 136
    FLOAT64 = 137
    UINT8Z = 10
    UINT16Z = 139
    UINT32Z = 140
    BYTE = 13
    SINT64 = 142
    UINT64 = 143
    UINT64Z = 144

    @property
    def size(self) -> int:
        return _BASE_TYPE_INFO[self][0]

    @property
    def struct_format(self) -> str | None:
        return _BASE_TYPE_INFO[self][1]

    def is_integer(self) -> bool:
        return self in _INTEGER_BASE_TYPES

    def is_signed_integer(self) -> bool:
        return self in _SIGNED_INTEGER_BASE_TYPES

    def is_big(self) -> bool:
        return self in _BIG_BASE_TYPES

    def is_string(self) -> bool:
        return self == BaseType.STRING

    def is_float(self) -> bool:
        return self in _FLOAT_BASE_TYPES

    def is_valid(self, value) -> bool:
        if value is None:
            return False

        if self.min is None or self.max is None:
            return True

        return self.min <= value <= self.max

    def invalid_raw_value(self) -> int:
        return _BASE_TYPE_INFO[self][2]

    @property
    def max(self) -> int | None:
        return _BASE_TYPE_INFO[self][4]

    @property
    def min(self) -> int | None:
        return _BASE_TYPE_INFO[self][3]

    @classmethod
    def from_name(cls, name: str):
        return _BASE_TYPE_BY_NAME.get(name)


_BASE_TYPE_INFO = {
    BaseType.ENUM: (1, 'B', 0xff, 0x00, 0xff),
    BaseType.SINT8: (1, 'b', 0x7f, -0x80, 0x7f),
    BaseType.UINT8: (1, 'B', 0xff, 0x00, 0xff),
    BaseType.SINT16: (2, 'h', 0x7fff, -0x8000, 0x7fff),
    BaseType.UINT16: (2, 'H', 0xffff, 0x0000, 0xffff),
    BaseType.SINT32: (4, 'i', 0x7fffffff, -0x80000000, 0x7fffffff),
    BaseType.UINT32: (4, 'I', 0xffffffff, 0x00000000, 0xffffffff),
    BaseType.STRING: (1, None, 0x00, None, None),
    BaseType.FLOAT32: (4, 'f', 0xffffffff, None, None),
    BaseType.FLOAT64: (8, 'd', 0xffffffffffffffff, None, None),
    BaseType.UINT8Z: (1, 'B', 0x00, 0x00, 0xff),
    BaseType.UINT16Z: (2, 'H', 0x0000, 0x0000, 0xffff),
    BaseType.UINT32Z: (4, 'I', 0x00000000, 0x00000000, 0xffffffff),
    BaseType.BYTE: (1, 'B', 0xff, 0x00, 0xff),
    BaseType.SINT64: (8, 'q', 0x7fffffffffffffff, -0x8000000000000000, 0x7fffffffffffffff),
    BaseType.UINT64: (8, 'Q', 0xffffffffffffffff, 0x0000000000000000, 0xffffffffffffffff),
    BaseType.UINT64Z: (8, 'Q', 0x0000000000000000, 0x0000000000000000, 0xffffffffffffffff),
}

_INTEGER_BASE_TYPES = frozenset({
    BaseType.SINT8, BaseType.UINT8, BaseType.SINT16, BaseType.UINT16, BaseType.UINT16Z,
    BaseType.SINT32, BaseType.UINT32, BaseType.UINT32Z, BaseType.SINT64, BaseType.UINT64,
    BaseType.UINT64Z,
})
_SIGNED_INTEGER_BASE_TYPES = frozenset({BaseType.SINT8, BaseType.SINT16, BaseType.SINT32, BaseType.SINT64})
_BIG_BASE_TYPES = frozenset({BaseType.SINT64, BaseType.UINT64, BaseType.UINT64Z})
_FLOAT_BASE_TYPES = frozenset({BaseType.FLOAT32, BaseType.FLOAT64})
_BASE_TYPE_BY_NAME = {base_type.name.lower(): base_type for base_type in BaseType}


class FieldType:

    def __init__(self, name: str, base_type: BaseType):
        self.name = name
        self.base_type = base_type
        self.names_by_value = {}
        self.values_by_name = {}

    def add_value(self, name, value):
        self.names_by_value[value] = name
        self.values_by_name[name] = value

    def get_value_by_name(self, name):
        return self.values_by_name.get(name)

    def get_name_by_value(self, value):
        return self.names_by_value.get(value)
