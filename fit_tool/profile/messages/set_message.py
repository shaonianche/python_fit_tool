# Autogenerated. Do not modify.
#
# Profile: 21.171.00
from typing import Optional

from fit_tool.base_type import BaseType
from fit_tool.data_message import DataMessage
from fit_tool.definition_message import DefinitionMessage
from fit_tool.developer_field import DeveloperField
from fit_tool.endian import Endian
from fit_tool.field import Field
from fit_tool.sub_field import SubField
from fit_tool.profile.profile_type import *
from typing import List as list
from typing import Dict as dict


class SetMessage(DataMessage):
    ID = 225
    NAME = 'set'

    @staticmethod
    def __get_field_size(definition_message: DefinitionMessage, field_id: int) -> int:
        size = 0
        if definition_message:
            field_definition = definition_message.get_field_definition(field_id)
            if field_definition:
                size = field_definition.size

        return size

    def __init__(self, definition_message=None, developer_fields=None, local_id: int = 0,
                 endian: Endian = Endian.LITTLE):
        super().__init__(name=SetMessage.NAME,
                         global_id=SetMessage.ID,
                         local_id=definition_message.local_id if definition_message else local_id,
                         endian=definition_message.endian if definition_message else endian,
                         definition_message=definition_message,
                         developer_fields=developer_fields,
                         fields=[
        TimestampField(
            size=self.__get_field_size(definition_message, TimestampField.ID),
            growable=definition_message is None), 
        SetDurationField(
            size=self.__get_field_size(definition_message, SetDurationField.ID),
            growable=definition_message is None), 
        SetRepetitionsField(
            size=self.__get_field_size(definition_message, SetRepetitionsField.ID),
            growable=definition_message is None), 
        SetWeightField(
            size=self.__get_field_size(definition_message, SetWeightField.ID),
            growable=definition_message is None), 
        SetSetTypeField(
            size=self.__get_field_size(definition_message, SetSetTypeField.ID),
            growable=definition_message is None), 
        SetStartTimeField(
            size=self.__get_field_size(definition_message, SetStartTimeField.ID),
            growable=definition_message is None), 
        SetCategoryField(
            size=self.__get_field_size(definition_message, SetCategoryField.ID),
            growable=definition_message is None), 
        SetCategorySubtypeField(
            size=self.__get_field_size(definition_message, SetCategorySubtypeField.ID),
            growable=definition_message is None), 
        SetWeightDisplayUnitField(
            size=self.__get_field_size(definition_message, SetWeightDisplayUnitField.ID),
            growable=definition_message is None), 
        SetMessageIndexField(
            size=self.__get_field_size(definition_message, SetMessageIndexField.ID),
            growable=definition_message is None), 
        SetWorkoutStepIndexField(
            size=self.__get_field_size(definition_message, SetWorkoutStepIndexField.ID),
            growable=definition_message is None)
        ])

        self.growable = self.definition_message is None

    @classmethod
    def from_bytes(cls, definition_message: DefinitionMessage, developer_fields: list[DeveloperField],
                   bytes_buffer: bytes, offset: int = 0):
        message = cls(definition_message=definition_message, developer_fields=developer_fields)
        message.read_from_bytes(bytes_buffer, offset)
        return message



# timestamp : milliseconds from January 1st, 1970 at 00:00:00 UTC

    @property
    def timestamp(self) -> Optional[int]:
        field = self.get_field(TimestampField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None


    # timestamp : milliseconds from January 1st, 1970 at 00:00:00 UTC

    @timestamp.setter
    def timestamp(self, value: int):
        field = self.get_field(TimestampField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def duration(self) -> Optional[float]:
        field = self.get_field(SetDurationField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @duration.setter
    def duration(self, value: float):
        field = self.get_field(SetDurationField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def repetitions(self) -> Optional[int]:
        field = self.get_field(SetRepetitionsField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @repetitions.setter
    def repetitions(self, value: int):
        field = self.get_field(SetRepetitionsField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def weight(self) -> Optional[float]:
        field = self.get_field(SetWeightField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @weight.setter
    def weight(self, value: float):
        field = self.get_field(SetWeightField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def set_type(self) -> Optional[int]:
        field = self.get_field(SetSetTypeField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @set_type.setter
    def set_type(self, value: int):
        field = self.get_field(SetSetTypeField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    
# timestamp : milliseconds from January 1st, 1970 at 00:00:00 UTC

    @property
    def start_time(self) -> Optional[int]:
        field = self.get_field(SetStartTimeField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None


    # timestamp : milliseconds from January 1st, 1970 at 00:00:00 UTC

    @start_time.setter
    def start_time(self, value: int):
        field = self.get_field(SetStartTimeField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def category(self) -> Optional[list[int]]:
        field = self.get_field(SetCategoryField.ID)
        if field and field.is_valid():
            return field.get_values()
        else:
            return None



    @category.setter
    def category(self, value: list[int]):
        field = self.get_field(SetCategoryField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                field.set_values(value)

    

    @property
    def category_subtype(self) -> Optional[list[int]]:
        field = self.get_field(SetCategorySubtypeField.ID)
        if field and field.is_valid():
            return field.get_values()
        else:
            return None



    @category_subtype.setter
    def category_subtype(self, value: list[int]):
        field = self.get_field(SetCategorySubtypeField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                field.set_values(value)

    

    @property
    def weight_display_unit(self) -> Optional[int]:
        field = self.get_field(SetWeightDisplayUnitField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @weight_display_unit.setter
    def weight_display_unit(self, value: int):
        field = self.get_field(SetWeightDisplayUnitField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def message_index(self) -> Optional[int]:
        field = self.get_field(SetMessageIndexField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @message_index.setter
    def message_index(self, value: int):
        field = self.get_field(SetMessageIndexField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def workout_step_index(self) -> Optional[int]:
        field = self.get_field(SetWorkoutStepIndexField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @workout_step_index.setter
    def workout_step_index(self, value: int):
        field = self.get_field(SetWorkoutStepIndexField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    





class TimestampField(Field):
    ID = 254

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='timestamp',
            field_id=self.ID,
            base_type=BaseType.UINT32,
        offset = -631065600000,
                 scale = 0.001,
                         size = size,
        units = 'ms',
        type_name = 'date_time',
        growable = growable,
                   sub_fields = [
        ]
        )


class SetDurationField(Field):
    ID = 0

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='duration',
            field_id=self.ID,
            base_type=BaseType.UINT32,
        offset = 0,
                 scale = 1000,
                         size = size,
        units = 's',
        type_name = '',
        growable = growable,
                   sub_fields = [
        ]
        )


class SetRepetitionsField(Field):
    ID = 3

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='repetitions',
            field_id=self.ID,
            base_type=BaseType.UINT16,
        offset = 0,
                 scale = 1,
                         size = size,
        growable = growable,
                   sub_fields = [
        ]
        )


class SetWeightField(Field):
    ID = 4

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='weight',
            field_id=self.ID,
            base_type=BaseType.UINT16,
        offset = 0,
                 scale = 16,
                         size = size,
        units = 'kg',
        type_name = '',
        growable = growable,
                   sub_fields = [
        ]
        )


class SetSetTypeField(Field):
    ID = 5

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='set_type',
            field_id=self.ID,
            base_type=BaseType.UINT8,
        offset = 0,
                 scale = 1,
                         size = size,
        growable = growable,
                   sub_fields = [
        ]
        )


class SetStartTimeField(Field):
    ID = 6

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='start_time',
            field_id=self.ID,
            base_type=BaseType.UINT32,
        offset = -631065600000,
                 scale = 0.001,
                         size = size,
        units = 'ms',
        type_name = 'date_time',
        growable = growable,
                   sub_fields = [
        ]
        )


class SetCategoryField(Field):
    ID = 7

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='category',
            field_id=self.ID,
            base_type=BaseType.UINT16,
        offset = 0,
                 scale = 1,
                         size = size,
        growable = growable,
                   sub_fields = [
        ]
        )


class SetCategorySubtypeField(Field):
    ID = 8

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='category_subtype',
            field_id=self.ID,
            base_type=BaseType.UINT16,
        offset = 0,
                 scale = 1,
                         size = size,
        growable = growable,
                   sub_fields = [
        ]
        )


class SetWeightDisplayUnitField(Field):
    ID = 9

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='weight_display_unit',
            field_id=self.ID,
            base_type=BaseType.UINT16,
        offset = 0,
                 scale = 1,
                         size = size,
        growable = growable,
                   sub_fields = [
        ]
        )


class SetMessageIndexField(Field):
    ID = 10

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='message_index',
            field_id=self.ID,
            base_type=BaseType.UINT16,
        offset = 0,
                 scale = 1,
                         size = size,
        growable = growable,
                   sub_fields = [
        ]
        )


class SetWorkoutStepIndexField(Field):
    ID = 11

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='wkt_step_index',
            field_id=self.ID,
            base_type=BaseType.UINT16,
        offset = 0,
                 scale = 1,
                         size = size,
        growable = growable,
                   sub_fields = [
        ]
        )