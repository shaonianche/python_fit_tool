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


class SplitSummaryMessage(DataMessage):
    ID = 313
    NAME = 'split_summary'

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
        super().__init__(name=SplitSummaryMessage.NAME,
                         global_id=SplitSummaryMessage.ID,
                         local_id=definition_message.local_id if definition_message else local_id,
                         endian=definition_message.endian if definition_message else endian,
                         definition_message=definition_message,
                         developer_fields=developer_fields,
                         fields=[
        MessageIndexField(
            size=self.__get_field_size(definition_message, MessageIndexField.ID),
            growable=definition_message is None), 
        SplitSummarySplitTypeField(
            size=self.__get_field_size(definition_message, SplitSummarySplitTypeField.ID),
            growable=definition_message is None), 
        SplitSummaryNumSplitsField(
            size=self.__get_field_size(definition_message, SplitSummaryNumSplitsField.ID),
            growable=definition_message is None), 
        SplitSummaryTotalTimerTimeField(
            size=self.__get_field_size(definition_message, SplitSummaryTotalTimerTimeField.ID),
            growable=definition_message is None), 
        SplitSummaryTotalDistanceField(
            size=self.__get_field_size(definition_message, SplitSummaryTotalDistanceField.ID),
            growable=definition_message is None), 
        SplitSummaryAvgSpeedField(
            size=self.__get_field_size(definition_message, SplitSummaryAvgSpeedField.ID),
            growable=definition_message is None), 
        SplitSummaryMaxSpeedField(
            size=self.__get_field_size(definition_message, SplitSummaryMaxSpeedField.ID),
            growable=definition_message is None), 
        SplitSummaryTotalAscentField(
            size=self.__get_field_size(definition_message, SplitSummaryTotalAscentField.ID),
            growable=definition_message is None), 
        SplitSummaryTotalDescentField(
            size=self.__get_field_size(definition_message, SplitSummaryTotalDescentField.ID),
            growable=definition_message is None), 
        SplitSummaryAvgHeartRateField(
            size=self.__get_field_size(definition_message, SplitSummaryAvgHeartRateField.ID),
            growable=definition_message is None), 
        SplitSummaryMaxHeartRateField(
            size=self.__get_field_size(definition_message, SplitSummaryMaxHeartRateField.ID),
            growable=definition_message is None), 
        SplitSummaryAvgVertSpeedField(
            size=self.__get_field_size(definition_message, SplitSummaryAvgVertSpeedField.ID),
            growable=definition_message is None), 
        SplitSummaryTotalCaloriesField(
            size=self.__get_field_size(definition_message, SplitSummaryTotalCaloriesField.ID),
            growable=definition_message is None), 
        SplitSummaryTotalMovingTimeField(
            size=self.__get_field_size(definition_message, SplitSummaryTotalMovingTimeField.ID),
            growable=definition_message is None)
        ])

        self.growable = self.definition_message is None

    @classmethod
    def from_bytes(cls, definition_message: DefinitionMessage, developer_fields: list[DeveloperField],
                   bytes_buffer: bytes, offset: int = 0):
        message = cls(definition_message=definition_message, developer_fields=developer_fields)
        message.read_from_bytes(bytes_buffer, offset)
        return message




    @property
    def message_index(self) -> Optional[int]:
        field = self.get_field(MessageIndexField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @message_index.setter
    def message_index(self, value: int):
        field = self.get_field(MessageIndexField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def split_type(self) -> Optional[SplitType]:
        field = self.get_field(SplitSummarySplitTypeField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @split_type.setter
    def split_type(self, value: SplitType):
        field = self.get_field(SplitSummarySplitTypeField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def num_splits(self) -> Optional[int]:
        field = self.get_field(SplitSummaryNumSplitsField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @num_splits.setter
    def num_splits(self, value: int):
        field = self.get_field(SplitSummaryNumSplitsField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def total_timer_time(self) -> Optional[float]:
        field = self.get_field(SplitSummaryTotalTimerTimeField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @total_timer_time.setter
    def total_timer_time(self, value: float):
        field = self.get_field(SplitSummaryTotalTimerTimeField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def total_distance(self) -> Optional[float]:
        field = self.get_field(SplitSummaryTotalDistanceField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @total_distance.setter
    def total_distance(self, value: float):
        field = self.get_field(SplitSummaryTotalDistanceField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def avg_speed(self) -> Optional[float]:
        field = self.get_field(SplitSummaryAvgSpeedField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @avg_speed.setter
    def avg_speed(self, value: float):
        field = self.get_field(SplitSummaryAvgSpeedField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def max_speed(self) -> Optional[float]:
        field = self.get_field(SplitSummaryMaxSpeedField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @max_speed.setter
    def max_speed(self, value: float):
        field = self.get_field(SplitSummaryMaxSpeedField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def total_ascent(self) -> Optional[int]:
        field = self.get_field(SplitSummaryTotalAscentField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @total_ascent.setter
    def total_ascent(self, value: int):
        field = self.get_field(SplitSummaryTotalAscentField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def total_descent(self) -> Optional[int]:
        field = self.get_field(SplitSummaryTotalDescentField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @total_descent.setter
    def total_descent(self, value: int):
        field = self.get_field(SplitSummaryTotalDescentField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def avg_heart_rate(self) -> Optional[int]:
        field = self.get_field(SplitSummaryAvgHeartRateField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @avg_heart_rate.setter
    def avg_heart_rate(self, value: int):
        field = self.get_field(SplitSummaryAvgHeartRateField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def max_heart_rate(self) -> Optional[int]:
        field = self.get_field(SplitSummaryMaxHeartRateField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @max_heart_rate.setter
    def max_heart_rate(self, value: int):
        field = self.get_field(SplitSummaryMaxHeartRateField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def avg_vert_speed(self) -> Optional[float]:
        field = self.get_field(SplitSummaryAvgVertSpeedField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @avg_vert_speed.setter
    def avg_vert_speed(self, value: float):
        field = self.get_field(SplitSummaryAvgVertSpeedField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def total_calories(self) -> Optional[int]:
        field = self.get_field(SplitSummaryTotalCaloriesField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @total_calories.setter
    def total_calories(self, value: int):
        field = self.get_field(SplitSummaryTotalCaloriesField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def total_moving_time(self) -> Optional[float]:
        field = self.get_field(SplitSummaryTotalMovingTimeField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @total_moving_time.setter
    def total_moving_time(self, value: float):
        field = self.get_field(SplitSummaryTotalMovingTimeField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    





class MessageIndexField(Field):
    ID = 254

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


class SplitSummarySplitTypeField(Field):
    ID = 0

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='split_type',
            field_id=self.ID,
            base_type=BaseType.ENUM,
        offset = 0,
                 scale = 1,
                         size = size,
        growable = growable,
                   sub_fields = [
        ]
        )


class SplitSummaryNumSplitsField(Field):
    ID = 3

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='num_splits',
            field_id=self.ID,
            base_type=BaseType.UINT16,
        offset = 0,
                 scale = 1,
                         size = size,
        growable = growable,
                   sub_fields = [
        ]
        )


class SplitSummaryTotalTimerTimeField(Field):
    ID = 4

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='total_timer_time',
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


class SplitSummaryTotalDistanceField(Field):
    ID = 5

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='total_distance',
            field_id=self.ID,
            base_type=BaseType.UINT32,
        offset = 0,
                 scale = 100,
                         size = size,
        units = 'm',
        type_name = '',
        growable = growable,
                   sub_fields = [
        ]
        )


class SplitSummaryAvgSpeedField(Field):
    ID = 6

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='avg_speed',
            field_id=self.ID,
            base_type=BaseType.UINT32,
        offset = 0,
                 scale = 1000,
                         size = size,
        units = 'm/s',
        type_name = '',
        growable = growable,
                   sub_fields = [
        ]
        )


class SplitSummaryMaxSpeedField(Field):
    ID = 7

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='max_speed',
            field_id=self.ID,
            base_type=BaseType.UINT32,
        offset = 0,
                 scale = 1000,
                         size = size,
        units = 'm/s',
        type_name = '',
        growable = growable,
                   sub_fields = [
        ]
        )


class SplitSummaryTotalAscentField(Field):
    ID = 8

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='total_ascent',
            field_id=self.ID,
            base_type=BaseType.UINT16,
        offset = 0,
                 scale = 1,
                         size = size,
        units = 'm',
        type_name = '',
        growable = growable,
                   sub_fields = [
        ]
        )


class SplitSummaryTotalDescentField(Field):
    ID = 9

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='total_descent',
            field_id=self.ID,
            base_type=BaseType.UINT16,
        offset = 0,
                 scale = 1,
                         size = size,
        units = 'm',
        type_name = '',
        growable = growable,
                   sub_fields = [
        ]
        )


class SplitSummaryAvgHeartRateField(Field):
    ID = 10

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='avg_heart_rate',
            field_id=self.ID,
            base_type=BaseType.UINT8,
        offset = 0,
                 scale = 1,
                         size = size,
        units = 'bpm',
        type_name = '',
        growable = growable,
                   sub_fields = [
        ]
        )


class SplitSummaryMaxHeartRateField(Field):
    ID = 11

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='max_heart_rate',
            field_id=self.ID,
            base_type=BaseType.UINT8,
        offset = 0,
                 scale = 1,
                         size = size,
        units = 'bpm',
        type_name = '',
        growable = growable,
                   sub_fields = [
        ]
        )


class SplitSummaryAvgVertSpeedField(Field):
    ID = 12

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='avg_vert_speed',
            field_id=self.ID,
            base_type=BaseType.SINT32,
        offset = 0,
                 scale = 1000,
                         size = size,
        units = 'm/s',
        type_name = '',
        growable = growable,
                   sub_fields = [
        ]
        )


class SplitSummaryTotalCaloriesField(Field):
    ID = 13

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='total_calories',
            field_id=self.ID,
            base_type=BaseType.UINT32,
        offset = 0,
                 scale = 1,
                         size = size,
        units = 'kcal',
        type_name = '',
        growable = growable,
                   sub_fields = [
        ]
        )


class SplitSummaryTotalMovingTimeField(Field):
    ID = 77

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='total_moving_time',
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