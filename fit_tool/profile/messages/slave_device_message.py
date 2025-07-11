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


class SlaveDeviceMessage(DataMessage):
    ID = 106
    NAME = 'slave_device'

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
        super().__init__(name=SlaveDeviceMessage.NAME,
                         global_id=SlaveDeviceMessage.ID,
                         local_id=definition_message.local_id if definition_message else local_id,
                         endian=definition_message.endian if definition_message else endian,
                         definition_message=definition_message,
                         developer_fields=developer_fields,
                         fields=[
        SlaveDeviceManufacturerField(
            size=self.__get_field_size(definition_message, SlaveDeviceManufacturerField.ID),
            growable=definition_message is None), 
        SlaveDeviceProductField(
            size=self.__get_field_size(definition_message, SlaveDeviceProductField.ID),
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
    def manufacturer(self) -> Optional[int]:
        field = self.get_field(SlaveDeviceManufacturerField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @manufacturer.setter
    def manufacturer(self, value: int):
        field = self.get_field(SlaveDeviceManufacturerField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def product(self) -> Optional[int]:
        field = self.get_field(SlaveDeviceProductField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @product.setter
    def product(self, value: int):
        field = self.get_field(SlaveDeviceProductField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    


    @property
    def favero_product(self) -> Optional[int]:
        field = self.get_field(SlaveDeviceProductField.ID)
        type_field = self.get_field(SlaveDeviceManufacturerField.ID)

        is_sub_field_valid = type_field and type_field.get_value() in [263]
        if field and field.is_valid() and is_sub_field_valid:
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None

    @favero_product.setter
    def favero_product(self, value: int):
        field = self.get_field(SlaveDeviceProductField.ID)
        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)


    @property
    def garmin_product(self) -> Optional[int]:
        field = self.get_field(SlaveDeviceProductField.ID)
        type_field = self.get_field(SlaveDeviceManufacturerField.ID)

        is_sub_field_valid = type_field and type_field.get_value() in [1, 15, 13, 89]
        if field and field.is_valid() and is_sub_field_valid:
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None

    @garmin_product.setter
    def garmin_product(self, value: int):
        field = self.get_field(SlaveDeviceProductField.ID)
        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)





class SlaveDeviceManufacturerField(Field):
    ID = 0

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='manufacturer',
            field_id=self.ID,
            base_type=BaseType.UINT16,
        offset = 0,
                 scale = 1,
                         size = size,
        growable = growable,
                   sub_fields = [
        ]
        )


class SlaveDeviceProductField(Field):
    ID = 1

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='product',
            field_id=self.ID,
            base_type=BaseType.UINT16,
        offset = 0,
                 scale = 1,
                         size = size,
        growable = growable,
                   sub_fields = [
        SubField(
            name='favero_product',
            base_type=BaseType.UINT16,
        scale = 1,
                offset = 0,
        reference_map = {
        SlaveDeviceManufacturerField.ID: [263]
        }), 
        SubField(
            name='garmin_product',
            base_type=BaseType.UINT16,
        scale = 1,
                offset = 0,
        reference_map = {
        SlaveDeviceManufacturerField.ID: [1, 15, 13, 89]
        })
        ]
        )