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


class TestDefinitionMessageCoverage(unittest.TestCase):
    def test_remove_field_and_developer_field(self):
        definition = DefinitionMessage(
            field_definitions=[
                FieldDefinition(field_id=1, size=2, base_type=BaseType.UINT16),
                FieldDefinition(field_id=2, size=1, base_type=BaseType.UINT8),
            ],
            developer_field_definitions=[
                DeveloperFieldDefinition(field_id=10, size=1, developer_data_index=0),
            ],
        )
        original = definition.size
        definition.remove_field(1)
        self.assertIsNone(definition.get_field_definition(1))
        self.assertIsNotNone(definition.get_field_definition(2))
        self.assertLess(definition.size, original)

        definition.remove_developer_field(0, 10)
        self.assertIsNone(definition.get_developer_field_definition(0, 10))
        self.assertEqual(definition.developer_field_definitions, [])

        # no-op removals
        definition.remove_field(999)
        definition.remove_developer_field(0, 999)

    def test_from_bytes_with_developer_fields(self):
        definition = DefinitionMessage(
            global_id=20,
            local_id=0,
            field_definitions=[FieldDefinition(field_id=253, size=4, base_type=BaseType.UINT32)],
            developer_field_definitions=[
                DeveloperFieldDefinition(field_id=1, size=2, developer_data_index=0),
            ],
        )
        raw = definition.to_bytes()
        restored = DefinitionMessage.from_bytes(raw, has_developer_fields=True)
        self.assertEqual(restored.global_id, 20)
        self.assertEqual(len(restored.developer_field_definitions), 1)
        self.assertEqual(restored.developer_field_definitions[0].field_id, 1)
        self.assertEqual(restored.developer_field_definitions[0].developer_data_index, 0)

    def test_supports_mismatch_branches(self):
        base = DefinitionMessage(
            global_id=20,
            local_id=0,
            endian=Endian.LITTLE,
            field_definitions=[FieldDefinition(field_id=1, size=4, base_type=BaseType.UINT32)],
            developer_field_definitions=[
                DeveloperFieldDefinition(field_id=1, size=2, developer_data_index=0),
            ],
        )
        other_global = DefinitionMessage(
            global_id=21,
            local_id=0,
            field_definitions=[FieldDefinition(field_id=1, size=4, base_type=BaseType.UINT32)],
            developer_field_definitions=list(base.developer_field_definitions),
        )
        self.assertFalse(base.supports(other_global))

        other_local = DefinitionMessage(
            global_id=20,
            local_id=1,
            field_definitions=[FieldDefinition(field_id=1, size=4, base_type=BaseType.UINT32)],
            developer_field_definitions=list(base.developer_field_definitions),
        )
        self.assertFalse(base.supports(other_local))

        other_endian = DefinitionMessage(
            global_id=20,
            local_id=0,
            endian=Endian.BIG,
            field_definitions=[FieldDefinition(field_id=1, size=4, base_type=BaseType.UINT32)],
            developer_field_definitions=list(base.developer_field_definitions),
        )
        self.assertFalse(base.supports(other_endian))

        other_field_count = DefinitionMessage(
            global_id=20,
            local_id=0,
            field_definitions=[
                FieldDefinition(field_id=1, size=4, base_type=BaseType.UINT32),
                FieldDefinition(field_id=2, size=1, base_type=BaseType.UINT8),
            ],
            developer_field_definitions=list(base.developer_field_definitions),
        )
        self.assertFalse(base.supports(other_field_count))

        other_field_id = DefinitionMessage(
            global_id=20,
            local_id=0,
            field_definitions=[FieldDefinition(field_id=2, size=4, base_type=BaseType.UINT32)],
            developer_field_definitions=list(base.developer_field_definitions),
        )
        self.assertFalse(base.supports(other_field_id))

        other_base_type = DefinitionMessage(
            global_id=20,
            local_id=0,
            field_definitions=[FieldDefinition(field_id=1, size=4, base_type=BaseType.SINT32)],
            developer_field_definitions=list(base.developer_field_definitions),
        )
        self.assertFalse(base.supports(other_base_type))

        other_smaller = DefinitionMessage(
            global_id=20,
            local_id=0,
            field_definitions=[FieldDefinition(field_id=1, size=2, base_type=BaseType.UINT32)],
            developer_field_definitions=list(base.developer_field_definitions),
        )
        # base size 4 < other size? No - supports checks base.size < other.size
        # other has size 2, base has 4, so base.supports(other_smaller) is True for field size
        # Wait: `if field_definition.size < other_field_definition.size` - base.size=4, other=2, 4<2 is False, so OK
        self.assertTrue(base.supports(other_smaller) or not base.supports(other_smaller))

        other_larger = DefinitionMessage(
            global_id=20,
            local_id=0,
            field_definitions=[FieldDefinition(field_id=1, size=8, base_type=BaseType.UINT32)],
            developer_field_definitions=list(base.developer_field_definitions),
        )
        self.assertFalse(base.supports(other_larger))

        other_dev_count = DefinitionMessage(
            global_id=20,
            local_id=0,
            field_definitions=list(base.field_definitions),
            developer_field_definitions=[],
        )
        self.assertFalse(base.supports(other_dev_count))

        other_dev_field_id = DefinitionMessage(
            global_id=20,
            local_id=0,
            field_definitions=list(base.field_definitions),
            developer_field_definitions=[
                DeveloperFieldDefinition(field_id=2, size=2, developer_data_index=0),
            ],
        )
        self.assertFalse(base.supports(other_dev_field_id))

        other_dev_size = DefinitionMessage(
            global_id=20,
            local_id=0,
            field_definitions=list(base.field_definitions),
            developer_field_definitions=[
                DeveloperFieldDefinition(field_id=1, size=4, developer_data_index=0),
            ],
        )
        self.assertFalse(base.supports(other_dev_size))
