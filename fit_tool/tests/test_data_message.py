# nosetests --nocapture  tests/test_field.py

import unittest

from fit_tool.base_type import BaseType
from fit_tool.data_message import DataMessage
from fit_tool.definition_message import DefinitionMessage
from fit_tool.developer_field import DeveloperField
from fit_tool.developer_field_definition import DeveloperFieldDefinition
from fit_tool.field import Field
from fit_tool.field_definition import FieldDefinition
from fit_tool.profile.messages.workout_step_message import WorkoutStepMessage
from fit_tool.profile.profile_type import WorkoutStepDuration


class TestDataMessage(unittest.TestCase):

    def shortDescription(self):
        return None

    def test_data_message_conversions(self):
        dm1 = WorkoutStepMessage()
        dm1.workout_step_name = 'test'
        self.assertEqual('test', dm1.workout_step_name)

        bytes1 = dm1.to_bytes()

        definition_message = DefinitionMessage.from_data_message(dm1)
        dm2 = WorkoutStepMessage(definition_message=definition_message)
        dm2.read_from_bytes(bytes1)
        bytes2 = dm2.to_bytes()

        self.assertEqual('test', dm2.workout_step_name)

        self.assertEqual(bytes2, bytes1)

    def test_to_row(self):
        dm1 = WorkoutStepMessage()
        dm1.workout_step_name = 'test'
        dm1.duration_type = WorkoutStepDuration.DISTANCE

        row = dm1.to_row()
        print(row)

    def test_size_is_read_only(self):
        dm1 = WorkoutStepMessage()
        with self.assertRaises(AttributeError):
            dm1.size = 1

    def test_read_from_bytes_requires_definition(self):
        dm1 = WorkoutStepMessage()
        with self.assertRaises(ValueError):
            dm1.read_from_bytes(b'')

    def test_read_from_bytes_raises_for_empty_regular_field(self):
        definition = DefinitionMessage(field_definitions=[FieldDefinition(field_id=1, size=1, base_type=BaseType.UINT8)])
        message = DataMessage(
            name='sample',
            definition_message=definition,
            fields=[Field(field_id=1, name='sample_field', base_type=BaseType.UINT8, size=0)],
        )
        with self.assertRaises(ValueError):
            message.read_from_bytes(b'\x00')

    def test_read_from_bytes_raises_for_empty_developer_field(self):
        definition = DefinitionMessage(
            developer_field_definitions=[DeveloperFieldDefinition(field_id=1, size=1, developer_data_index=0)]
        )
        message = DataMessage(
            name='sample',
            definition_message=definition,
            developer_fields=[
                DeveloperField(
                    field_id=1,
                    name='dev_field',
                    developer_data_index=0,
                    base_type=BaseType.UINT8,
                    size=0,
                )
            ],
        )
        with self.assertRaises(ValueError):
            message.read_from_bytes(b'\x00')

    def test_to_row_and_to_bytes_raise_for_invalid_regular_field(self):
        definition = DefinitionMessage(field_definitions=[FieldDefinition(field_id=1, size=1, base_type=BaseType.UINT8)])
        message = DataMessage(
            name='sample',
            definition_message=definition,
            fields=[Field(field_id=1, name='sample_field', base_type=BaseType.UINT8, size=0)],
        )
        with self.assertRaises(ValueError):
            message.to_row()
        with self.assertRaises(ValueError):
            message.to_bytes()

    def test_to_row_and_to_bytes_raise_for_missing_developer_field(self):
        definition = DefinitionMessage(
            developer_field_definitions=[DeveloperFieldDefinition(field_id=1, size=1, developer_data_index=0)]
        )
        message = DataMessage(name='sample', definition_message=definition, developer_fields=[])
        with self.assertRaises(ValueError):
            message.to_row()
        with self.assertRaises(ValueError):
            message.to_bytes()

    def test_to_row_and_to_bytes_raise_for_invalid_developer_field(self):
        definition = DefinitionMessage(
            developer_field_definitions=[DeveloperFieldDefinition(field_id=1, size=1, developer_data_index=0)]
        )
        message = DataMessage(
            name='sample',
            definition_message=definition,
            developer_fields=[
                DeveloperField(
                    field_id=1,
                    name='dev_field',
                    developer_data_index=0,
                    base_type=BaseType.UINT8,
                    size=0,
                )
            ],
        )
        with self.assertRaises(ValueError):
            message.to_row()
        with self.assertRaises(ValueError):
            message.to_bytes()
