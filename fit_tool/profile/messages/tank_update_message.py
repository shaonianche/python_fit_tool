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


class TankUpdateMessage(DataMessage):
    ID = 319
    NAME = 'tank_update'

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
        super().__init__(name=TankUpdateMessage.NAME,
                         global_id=TankUpdateMessage.ID,
                         local_id=definition_message.local_id if definition_message else local_id,
                         endian=definition_message.endian if definition_message else endian,
                         definition_message=definition_message,
                         developer_fields=developer_fields,
                         fields=[
        TimestampField(
            size=self.__get_field_size(definition_message, TimestampField.ID),
            growable=definition_message is None), 
        TankUpdateSensorField(
            size=self.__get_field_size(definition_message, TankUpdateSensorField.ID),
            growable=definition_message is None), 
        TankUpdatePressureField(
            size=self.__get_field_size(definition_message, TankUpdatePressureField.ID),
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
    def sensor(self) -> Optional[int]:
        field = self.get_field(TankUpdateSensorField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @sensor.setter
    def sensor(self, value: int):
        field = self.get_field(TankUpdateSensorField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def pressure(self) -> Optional[float]:
        field = self.get_field(TankUpdatePressureField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @pressure.setter
    def pressure(self, value: float):
        field = self.get_field(TankUpdatePressureField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    





class TimestampField(Field):
    ID = 253

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


class TankUpdateSensorField(Field):
    ID = 0

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='sensor',
            field_id=self.ID,
            base_type=BaseType.UINT32Z,
        offset = 0,
                 scale = 1,
                         size = size,
        growable = growable,
                   sub_fields = [
        ]
        )


class TankUpdatePressureField(Field):
    ID = 1

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='pressure',
            field_id=self.ID,
            base_type=BaseType.UINT16,
        offset = 0,
                 scale = 100,
                         size = size,
        units = 'bar',
        type_name = '',
        growable = growable,
                   sub_fields = [
        ]
        )