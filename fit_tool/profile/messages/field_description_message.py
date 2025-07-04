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


class FieldDescriptionMessage(DataMessage):
    ID = 206
    NAME = 'field_description'

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
        super().__init__(name=FieldDescriptionMessage.NAME,
                         global_id=FieldDescriptionMessage.ID,
                         local_id=definition_message.local_id if definition_message else local_id,
                         endian=definition_message.endian if definition_message else endian,
                         definition_message=definition_message,
                         developer_fields=developer_fields,
                         fields=[
        FieldDescriptionDeveloperDataIndexField(
            size=self.__get_field_size(definition_message, FieldDescriptionDeveloperDataIndexField.ID),
            growable=definition_message is None), 
        FieldDescriptionFieldDefinitionNumberField(
            size=self.__get_field_size(definition_message, FieldDescriptionFieldDefinitionNumberField.ID),
            growable=definition_message is None), 
        FieldDescriptionFitBaseTypeIdField(
            size=self.__get_field_size(definition_message, FieldDescriptionFitBaseTypeIdField.ID),
            growable=definition_message is None), 
        FieldDescriptionFieldNameField(
            size=self.__get_field_size(definition_message, FieldDescriptionFieldNameField.ID),
            growable=definition_message is None), 
        FieldDescriptionArrayField(
            size=self.__get_field_size(definition_message, FieldDescriptionArrayField.ID),
            growable=definition_message is None), 
        FieldDescriptionComponentsField(
            size=self.__get_field_size(definition_message, FieldDescriptionComponentsField.ID),
            growable=definition_message is None), 
        FieldDescriptionScaleField(
            size=self.__get_field_size(definition_message, FieldDescriptionScaleField.ID),
            growable=definition_message is None), 
        FieldDescriptionOffsetField(
            size=self.__get_field_size(definition_message, FieldDescriptionOffsetField.ID),
            growable=definition_message is None), 
        FieldDescriptionUnitsField(
            size=self.__get_field_size(definition_message, FieldDescriptionUnitsField.ID),
            growable=definition_message is None), 
        FieldDescriptionBitsField(
            size=self.__get_field_size(definition_message, FieldDescriptionBitsField.ID),
            growable=definition_message is None), 
        FieldDescriptionAccumulateField(
            size=self.__get_field_size(definition_message, FieldDescriptionAccumulateField.ID),
            growable=definition_message is None), 
        FieldDescriptionFitBaseUnitIdField(
            size=self.__get_field_size(definition_message, FieldDescriptionFitBaseUnitIdField.ID),
            growable=definition_message is None), 
        FieldDescriptionNativeMesgNumField(
            size=self.__get_field_size(definition_message, FieldDescriptionNativeMesgNumField.ID),
            growable=definition_message is None), 
        FieldDescriptionNativeFieldNumField(
            size=self.__get_field_size(definition_message, FieldDescriptionNativeFieldNumField.ID),
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
    def developer_data_index(self) -> Optional[int]:
        field = self.get_field(FieldDescriptionDeveloperDataIndexField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @developer_data_index.setter
    def developer_data_index(self, value: int):
        field = self.get_field(FieldDescriptionDeveloperDataIndexField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def field_definition_number(self) -> Optional[int]:
        field = self.get_field(FieldDescriptionFieldDefinitionNumberField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @field_definition_number.setter
    def field_definition_number(self, value: int):
        field = self.get_field(FieldDescriptionFieldDefinitionNumberField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def fit_base_type_id(self) -> Optional[int]:
        field = self.get_field(FieldDescriptionFitBaseTypeIdField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @fit_base_type_id.setter
    def fit_base_type_id(self, value: int):
        field = self.get_field(FieldDescriptionFitBaseTypeIdField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def field_name(self) -> Optional[str]:
        field = self.get_field(FieldDescriptionFieldNameField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @field_name.setter
    def field_name(self, value: str):
        field = self.get_field(FieldDescriptionFieldNameField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def array(self) -> Optional[int]:
        field = self.get_field(FieldDescriptionArrayField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @array.setter
    def array(self, value: int):
        field = self.get_field(FieldDescriptionArrayField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def components(self) -> Optional[str]:
        field = self.get_field(FieldDescriptionComponentsField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @components.setter
    def components(self, value: str):
        field = self.get_field(FieldDescriptionComponentsField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def scale(self) -> Optional[int]:
        field = self.get_field(FieldDescriptionScaleField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @scale.setter
    def scale(self, value: int):
        field = self.get_field(FieldDescriptionScaleField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def offset(self) -> Optional[int]:
        field = self.get_field(FieldDescriptionOffsetField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @offset.setter
    def offset(self, value: int):
        field = self.get_field(FieldDescriptionOffsetField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def units(self) -> Optional[str]:
        field = self.get_field(FieldDescriptionUnitsField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @units.setter
    def units(self, value: str):
        field = self.get_field(FieldDescriptionUnitsField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def bits(self) -> Optional[str]:
        field = self.get_field(FieldDescriptionBitsField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @bits.setter
    def bits(self, value: str):
        field = self.get_field(FieldDescriptionBitsField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def accumulate(self) -> Optional[str]:
        field = self.get_field(FieldDescriptionAccumulateField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @accumulate.setter
    def accumulate(self, value: str):
        field = self.get_field(FieldDescriptionAccumulateField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def fit_base_unit_id(self) -> Optional[int]:
        field = self.get_field(FieldDescriptionFitBaseUnitIdField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @fit_base_unit_id.setter
    def fit_base_unit_id(self, value: int):
        field = self.get_field(FieldDescriptionFitBaseUnitIdField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def native_mesg_num(self) -> Optional[int]:
        field = self.get_field(FieldDescriptionNativeMesgNumField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @native_mesg_num.setter
    def native_mesg_num(self, value: int):
        field = self.get_field(FieldDescriptionNativeMesgNumField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    

    @property
    def native_field_num(self) -> Optional[int]:
        field = self.get_field(FieldDescriptionNativeFieldNumField.ID)
        if field and field.is_valid():
            sub_field = field.get_valid_sub_field(self.fields)
            return field.get_value(sub_field=sub_field)
        else:
            return None



    @native_field_num.setter
    def native_field_num(self, value: int):
        field = self.get_field(FieldDescriptionNativeFieldNumField.ID)

        if field:
            if value is None:
                field.clear()
            else:
                sub_field = field.get_valid_sub_field(self.fields)
                field.set_value(0, value, sub_field)

    





class FieldDescriptionDeveloperDataIndexField(Field):
    ID = 0

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='developer_data_index',
            field_id=self.ID,
            base_type=BaseType.UINT8,
        offset = 0,
                 scale = 1,
                         size = size,
        growable = growable,
                   sub_fields = [
        ]
        )


class FieldDescriptionFieldDefinitionNumberField(Field):
    ID = 1

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='field_definition_number',
            field_id=self.ID,
            base_type=BaseType.UINT8,
        offset = 0,
                 scale = 1,
                         size = size,
        growable = growable,
                   sub_fields = [
        ]
        )


class FieldDescriptionFitBaseTypeIdField(Field):
    ID = 2

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='fit_base_type_id',
            field_id=self.ID,
            base_type=BaseType.UINT8,
        offset = 0,
                 scale = 1,
                         size = size,
        growable = growable,
                   sub_fields = [
        ]
        )


class FieldDescriptionFieldNameField(Field):
    ID = 3

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='field_name',
            field_id=self.ID,
            base_type=BaseType.STRING,
        offset = 0,
                 scale = 1,
                         size = size,
        growable = growable,
                   sub_fields = [
        ]
        )


class FieldDescriptionArrayField(Field):
    ID = 4

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='array',
            field_id=self.ID,
            base_type=BaseType.UINT8,
        offset = 0,
                 scale = 1,
                         size = size,
        growable = growable,
                   sub_fields = [
        ]
        )


class FieldDescriptionComponentsField(Field):
    ID = 5

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='components',
            field_id=self.ID,
            base_type=BaseType.STRING,
        offset = 0,
                 scale = 1,
                         size = size,
        growable = growable,
                   sub_fields = [
        ]
        )


class FieldDescriptionScaleField(Field):
    ID = 6

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='scale',
            field_id=self.ID,
            base_type=BaseType.UINT8,
        offset = 0,
                 scale = 1,
                         size = size,
        growable = growable,
                   sub_fields = [
        ]
        )


class FieldDescriptionOffsetField(Field):
    ID = 7

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='offset',
            field_id=self.ID,
            base_type=BaseType.SINT8,
        offset = 0,
                 scale = 1,
                         size = size,
        growable = growable,
                   sub_fields = [
        ]
        )


class FieldDescriptionUnitsField(Field):
    ID = 8

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='units',
            field_id=self.ID,
            base_type=BaseType.STRING,
        offset = 0,
                 scale = 1,
                         size = size,
        growable = growable,
                   sub_fields = [
        ]
        )


class FieldDescriptionBitsField(Field):
    ID = 9

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='bits',
            field_id=self.ID,
            base_type=BaseType.STRING,
        offset = 0,
                 scale = 1,
                         size = size,
        growable = growable,
                   sub_fields = [
        ]
        )


class FieldDescriptionAccumulateField(Field):
    ID = 10

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='accumulate',
            field_id=self.ID,
            base_type=BaseType.STRING,
        offset = 0,
                 scale = 1,
                         size = size,
        growable = growable,
                   sub_fields = [
        ]
        )


class FieldDescriptionFitBaseUnitIdField(Field):
    ID = 13

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='fit_base_unit_id',
            field_id=self.ID,
            base_type=BaseType.UINT16,
        offset = 0,
                 scale = 1,
                         size = size,
        growable = growable,
                   sub_fields = [
        ]
        )


class FieldDescriptionNativeMesgNumField(Field):
    ID = 14

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='native_mesg_num',
            field_id=self.ID,
            base_type=BaseType.UINT16,
        offset = 0,
                 scale = 1,
                         size = size,
        growable = growable,
                   sub_fields = [
        ]
        )


class FieldDescriptionNativeFieldNumField(Field):
    ID = 15

    def __init__(self, size: int = 0, growable: bool = True):
        super().__init__(
            name='native_field_num',
            field_id=self.ID,
            base_type=BaseType.UINT8,
        offset = 0,
                 scale = 1,
                         size = size,
        growable = growable,
                   sub_fields = [
        ]
        )