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


class MetZoneMessage(DataMessage):
    ID = 10
    NAME = 'met_zone'

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
        super().__init__(name=MetZoneMessage.NAME,
                         global_id=MetZoneMessage.ID,
                         local_id=definition_message.local_id if definition_message else local_id,
                         endian=definition_message.endian if definition_message else endian,
                         definition_message=definition_message,
                         developer_fields=developer_fields,
                         fields=[
        MessageIndexField(
            size=self.__get_field_size(definition_message, MessageIndexField.ID),
            growable=definition_message is None), 
        MetZoneHighBpmField(
            size=self.__get_field_size(definition_message, MetZoneHighBpmField.ID),
            growable=definition_message is None), 
        MetZoneCaloriesField(
            size=self.__get_field_size(definition_message, MetZoneCaloriesField.ID),
            growable=definition_message is None), 
        MetZoneFatCaloriesField(
            size=self.__get_field_size(definition_message, MetZoneFatCaloriesField.ID),
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
    def high_bpm(self) -> Optional[int]:
        field = self.get_field(MetZoneHighBpmField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @high_bpm.setter
    def high_bpm(self, value: int):
        field = self.get_field(MetZoneHighBpmField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def calories(self) -> Optional[float]:
        field = self.get_field(MetZoneCaloriesField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @calories.setter
    def calories(self, value: float):
        field = self.get_field(MetZoneCaloriesField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def fat_calories(self) -> Optional[float]:
        field = self.get_field(MetZoneFatCaloriesField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @fat_calories.setter
    def fat_calories(self, value: float):
        field = self.get_field(MetZoneFatCaloriesField.ID)

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


class MetZoneHighBpmField(Field):
    ID = 1

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='high_bpm',
            field_id=self.ID,
            base_type=BaseType.UINT8,
        offset = 0,
                 scale = 1,
                         size = size,
        growable = growable,
                   sub_fields = [
        ]
        )


class MetZoneCaloriesField(Field):
    ID = 2

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='calories',
            field_id=self.ID,
            base_type=BaseType.UINT16,
        offset = 0,
                 scale = 10,
                         size = size,
        units = 'kcal / min',
        type_name = '',
        growable = growable,
                   sub_fields = [
        ]
        )


class MetZoneFatCaloriesField(Field):
    ID = 3

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='fat_calories',
            field_id=self.ID,
            base_type=BaseType.UINT8,
        offset = 0,
                 scale = 10,
                         size = size,
        units = 'kcal / min',
        type_name = '',
        growable = growable,
                   sub_fields = [
        ]
        )