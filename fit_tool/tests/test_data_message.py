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
        dm2 = WorkoutStepMessage.from_definition(definition_message)
        dm2.read_from_bytes(bytes1)
        bytes2 = dm2.to_bytes()

        self.assertEqual('test', dm2.workout_step_name)

        self.assertEqual(bytes2, bytes1)

    def test_create_vs_from_definition_paths(self):
        """Blank create is growable; from_definition freezes field sizes."""
        created = WorkoutStepMessage()
        self.assertIsNone(created.definition_message)
        self.assertTrue(created.growable)
        name_field = created.get_field_by_name('wkt_step_name')
        self.assertIsNotNone(name_field)
        self.assertEqual(0, name_field.size)
        self.assertTrue(name_field.growable)

        created.workout_step_name = 'authored'
        definition = DefinitionMessage.from_data_message(created)
        projected = WorkoutStepMessage.from_definition(definition)
        self.assertIs(definition, projected.definition_message)
        self.assertFalse(projected.growable)
        projected_name = projected.get_field_by_name('wkt_step_name')
        self.assertIsNotNone(projected_name)
        self.assertFalse(projected_name.growable)
        self.assertEqual(
            definition.get_field_definition(projected_name.field_id).size,
            projected_name.size,
        )

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


class TestDataMessageCoverage(unittest.TestCase):
    def test_clear_and_remove_field(self):
        message = WorkoutStepMessage()
        message.workout_step_name = 'step'
        definition = DefinitionMessage.from_data_message(message)
        message.set_definition_message(definition)
        field_id = message.get_field_by_name('wkt_step_name').field_id
        self.assertTrue(message.get_field(field_id).is_valid())
        message.clear_field_by_id(field_id)
        self.assertTrue(message.get_field(field_id).is_not_valid())
        # remove_field aliases clear
        message.workout_step_name = 'again'
        definition2 = DefinitionMessage.from_data_message(message)
        message.set_definition_message(definition2)
        message.remove_field(field_id)

    def test_set_definition_clears_unmapped_developer_field(self):
        dev = DeveloperField(
            developer_data_index=0,
            field_id=1,
            base_type=BaseType.UINT8,
            size=1,
        )
        dev.set_value(0, 3)
        message = WorkoutStepMessage(developer_fields=[dev])
        message.workout_step_name = 'x'
        # Definition without the developer field clears developer field size
        definition = DefinitionMessage.from_data_message(WorkoutStepMessage())
        message.set_definition_message(definition)
        self.assertEqual(dev.size, 0)

    def test_to_bytes_and_to_row_include_developer_fields_without_definition(self):
        dev = DeveloperField(
            developer_data_index=0,
            field_id=1,
            base_type=BaseType.UINT8,
            size=1,
            name='custom',
        )
        dev.set_value(0, 9)
        message = WorkoutStepMessage(developer_fields=[dev])
        message.workout_step_name = 'named'
        wire = message.to_bytes()
        self.assertGreater(len(wire), 0)
        row = message.to_row()
        self.assertIn('workout_step', row[0] if row else '')

    def test_generic_message_from_bytes(self):
        from fit_tool.generic_message import GenericMessage

        definition = DefinitionMessage(
            global_id=9999,
            field_definitions=[FieldDefinition(field_id=1, size=1, base_type=BaseType.UINT8)],
        )
        message = GenericMessage.from_bytes(definition, [], b'\x05')
        self.assertEqual(message.name, 'generic')
        self.assertEqual(message.get_field(1).get_value(), 5)
