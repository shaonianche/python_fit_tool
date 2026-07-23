# nosetests --nocapture  tests/test_field.py

import unittest

from fit_tool.base_type import BaseType
from fit_tool.definition_message import DefinitionMessage
from fit_tool.developer_field import DeveloperField
from fit_tool.developer_field_definition import DeveloperFieldDefinition
from fit_tool.endian import Endian
from fit_tool.field_definition import FieldDefinition
from fit_tool.profile.messages.workout_step_message import WorkoutStepMessage
from fit_tool.profile.profile_type import WorkoutStepDuration


class TestDefinitionMessage(unittest.TestCase):

    def shortDescription(self):
        return None

    def test_definition_message_conversions(self):
        dm1 = DefinitionMessage(global_id=555, local_id=20,
                                field_definitions=[FieldDefinition(field_id=100, size=5, base_type=BaseType.STRING)])
        bytes1 = dm1.to_bytes()
        dm2 = DefinitionMessage.from_bytes(bytes1)
        bytes2 = dm2.to_bytes()

        self.assertEqual(bytes2, bytes1)

    def test_big_endian_conversion(self):
        dm1 = DefinitionMessage(global_id=555, local_id=20,
                                endian=Endian.BIG,
                                field_definitions=[FieldDefinition(field_id=100, size=5, base_type=BaseType.STRING)])

        bytes1 = dm1.to_bytes()
        dm2 = DefinitionMessage.from_bytes(bytes1)
        bytes2 = dm2.to_bytes()

        self.assertEqual(bytes2, bytes1)
        self.assertEqual(dm2.endian, Endian.BIG)

    def test_to_row(self):
        dm1 = WorkoutStepMessage()
        dm1.workoutStepName = 'test'
        dm1.durationType = WorkoutStepDuration.DISTANCE

        definition = DefinitionMessage.from_data_message(dm1)
        row = definition.to_row()
        print(row)

    def test_get_developer_fields_requires_mapping(self):
        definition = DefinitionMessage(
            developer_field_definitions=[DeveloperFieldDefinition(field_id=1, size=1, developer_data_index=0)]
        )
        with self.assertRaises(ValueError):
            definition.get_developer_fields({})

    def test_get_developer_fields_requires_field_id_mapping(self):
        definition = DefinitionMessage(
            developer_field_definitions=[DeveloperFieldDefinition(field_id=1, size=1, developer_data_index=0)]
        )
        with self.assertRaises(ValueError):
            definition.get_developer_fields({0: {}})

    def test_get_developer_fields_returns_sized_developer_field(self):
        definition = DefinitionMessage(
            developer_field_definitions=[DeveloperFieldDefinition(field_id=1, size=2, developer_data_index=0)]
        )
        source_field = DeveloperField(
            field_id=1,
            name='dev',
            developer_data_index=0,
            base_type=BaseType.UINT8,
            size=1,
        )

        result = definition.get_developer_fields({0: {1: source_field}})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].size, 2)

    def test_add_field_definition_updates_size(self):
        definition = DefinitionMessage()
        original_size = definition.size

        definition.add_field_definition(FieldDefinition(field_id=1, size=2, base_type=BaseType.UINT16))

        self.assertEqual(definition.size, original_size + FieldDefinition.field_definition_size())

    def test_add_developer_field_definition_updates_size(self):
        definition = DefinitionMessage()

        definition.add_developer_field_definition(
            DeveloperFieldDefinition(field_id=1, size=2, developer_data_index=0)
        )

        self.assertEqual(definition.size, 6 + DeveloperFieldDefinition.field_definition_size())

    def test_supports_rejects_different_developer_data_index(self):
        first = DefinitionMessage(
            developer_field_definitions=[
                DeveloperFieldDefinition(field_id=1, size=2, developer_data_index=0)
            ]
        )
        second = DefinitionMessage(
            developer_field_definitions=[
                DeveloperFieldDefinition(field_id=1, size=2, developer_data_index=1)
            ]
        )

        self.assertFalse(first.supports(second))
