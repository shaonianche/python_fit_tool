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


class AntChannelIdMessage(DataMessage):
    ID = 82
    NAME = 'ant_channel_id'

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
        super().__init__(name=AntChannelIdMessage.NAME,
                         global_id=AntChannelIdMessage.ID,
                         local_id=definition_message.local_id if definition_message else local_id,
                         endian=definition_message.endian if definition_message else endian,
                         definition_message=definition_message,
                         developer_fields=developer_fields,
                         fields=[
        AntChannelIdChannelNumberField(
            size=self.__get_field_size(definition_message, AntChannelIdChannelNumberField.ID),
            growable=definition_message is None), 
        AntChannelIdDeviceTypeField(
            size=self.__get_field_size(definition_message, AntChannelIdDeviceTypeField.ID),
            growable=definition_message is None), 
        AntChannelIdDeviceNumberField(
            size=self.__get_field_size(definition_message, AntChannelIdDeviceNumberField.ID),
            growable=definition_message is None), 
        AntChannelIdTransmissionTypeField(
            size=self.__get_field_size(definition_message, AntChannelIdTransmissionTypeField.ID),
            growable=definition_message is None), 
        AntChannelIdDeviceIndexField(
            size=self.__get_field_size(definition_message, AntChannelIdDeviceIndexField.ID),
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
    def channel_number(self) -> Optional[int]:
        field = self.get_field(AntChannelIdChannelNumberField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @channel_number.setter
    def channel_number(self, value: int):
        field = self.get_field(AntChannelIdChannelNumberField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def device_type(self) -> Optional[int]:
        field = self.get_field(AntChannelIdDeviceTypeField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @device_type.setter
    def device_type(self, value: int):
        field = self.get_field(AntChannelIdDeviceTypeField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def device_number(self) -> Optional[int]:
        field = self.get_field(AntChannelIdDeviceNumberField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @device_number.setter
    def device_number(self, value: int):
        field = self.get_field(AntChannelIdDeviceNumberField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def transmission_type(self) -> Optional[int]:
        field = self.get_field(AntChannelIdTransmissionTypeField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @transmission_type.setter
    def transmission_type(self, value: int):
        field = self.get_field(AntChannelIdTransmissionTypeField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def device_index(self) -> Optional[int]:
        field = self.get_field(AntChannelIdDeviceIndexField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @device_index.setter
    def device_index(self, value: int):
        field = self.get_field(AntChannelIdDeviceIndexField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    





class AntChannelIdChannelNumberField(Field):
    ID = 0

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='channel_number',
            field_id=self.ID,
            base_type=BaseType.UINT8,
        offset = 0,
                 scale = 1,
                         size = size,
        growable = growable,
                   sub_fields = [
        ]
        )


class AntChannelIdDeviceTypeField(Field):
    ID = 1

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='device_type',
            field_id=self.ID,
            base_type=BaseType.UINT8Z,
        offset = 0,
                 scale = 1,
                         size = size,
        growable = growable,
                   sub_fields = [
        ]
        )


class AntChannelIdDeviceNumberField(Field):
    ID = 2

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='device_number',
            field_id=self.ID,
            base_type=BaseType.UINT16Z,
        offset = 0,
                 scale = 1,
                         size = size,
        growable = growable,
                   sub_fields = [
        ]
        )


class AntChannelIdTransmissionTypeField(Field):
    ID = 3

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='transmission_type',
            field_id=self.ID,
            base_type=BaseType.UINT8Z,
        offset = 0,
                 scale = 1,
                         size = size,
        growable = growable,
                   sub_fields = [
        ]
        )


class AntChannelIdDeviceIndexField(Field):
    ID = 4

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='device_index',
            field_id=self.ID,
            base_type=BaseType.UINT8,
        offset = 0,
                 scale = 1,
                         size = size,
        growable = growable,
                   sub_fields = [
        ]
        )