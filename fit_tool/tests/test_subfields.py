"""Unit tests for Profile subfield resolution (Stage 2 D / design §5.6)."""

from __future__ import annotations

import unittest

from fit_tool.base_type import BaseType
from fit_tool.components import components_for_field, expand_message_components
from fit_tool.field import Field
from fit_tool.field_component import FieldComponent
from fit_tool.profile.messages.record_message import RecordMessage
from fit_tool.profile.messages.workout_step_message import WorkoutStepMessage
from fit_tool.profile.profile_type import WorkoutStepDuration
from fit_tool.record import Record
from fit_tool.sub_field import SubField, SubFieldResolution
from fit_tool.validation import ConformanceLevel, Severity, validate_fit_file


class TestSubFieldIsValid(unittest.TestCase):
    def _ref(self, field_id: int, value: int) -> Field:
        field = Field(name=f'ref_{field_id}', field_id=field_id, base_type=BaseType.ENUM, size=1)
        field.set_encoded_value(0, value, check_validity=False)
        return field

    def test_empty_reference_map_always_valid(self):
        self.assertTrue(SubField(name='free').is_valid([]))

    def test_single_ref_match_and_miss(self):
        sub = SubField(name='distance', reference_map={1: [1, 5]})
        self.assertTrue(sub.is_valid([self._ref(1, 1)]))
        self.assertTrue(sub.is_valid([self._ref(1, 5)]))
        self.assertFalse(sub.is_valid([self._ref(1, 0)]))
        self.assertFalse(sub.is_valid([]))

    def test_multi_ref_and_semantics(self):
        """All reference fields must match their permitted values."""
        sub = SubField(
            name='gated',
            reference_map={1: [1], 3: [2]},
        )
        ok = [self._ref(1, 1), self._ref(3, 2)]
        self.assertTrue(sub.is_valid(ok))
        self.assertFalse(sub.is_valid([self._ref(1, 1)]))  # missing ref 3
        self.assertFalse(sub.is_valid([self._ref(1, 1), self._ref(3, 0)]))
        self.assertFalse(sub.is_valid([self._ref(1, 0), self._ref(3, 2)]))

    def test_invalid_or_missing_ref_fails(self):
        sub = SubField(name='x', reference_map={1: [1]})
        empty_ref = Field(name='ref', field_id=1, base_type=BaseType.ENUM, size=0)
        self.assertFalse(sub.is_valid([empty_ref]))
        other = self._ref(9, 1)
        self.assertFalse(sub.is_valid([other]))

    def test_enum_value_comparable(self):
        sub = SubField(name='distance', reference_map={1: [WorkoutStepDuration.DISTANCE.value]})
        ref = Field(name='duration_type', field_id=1, base_type=BaseType.ENUM, size=1)
        ref.set_value(0, WorkoutStepDuration.DISTANCE)
        self.assertTrue(sub.is_valid([ref]))


class TestResolveSubField(unittest.TestCase):
    def test_first_match_is_selected(self):
        ref = Field(name='t', field_id=1, base_type=BaseType.ENUM, size=1)
        ref.set_encoded_value(0, 1, check_validity=False)
        a = SubField(name='a', reference_map={1: [1]}, scale=10)
        b = SubField(name='b', reference_map={1: [2]}, scale=100)
        field = Field(name='v', field_id=2, base_type=BaseType.UINT32, size=4, sub_fields=[a, b])
        resolution = field.resolve_sub_field([ref, field])
        self.assertIsInstance(resolution, SubFieldResolution)
        self.assertIs(resolution.selected, a)
        self.assertFalse(resolution.is_ambiguous)
        self.assertEqual(field.get_valid_sub_field([ref, field]), a)

    def test_no_match(self):
        ref = Field(name='t', field_id=1, base_type=BaseType.ENUM, size=1)
        ref.set_encoded_value(0, 9, check_validity=False)
        a = SubField(name='a', reference_map={1: [1]})
        field = Field(name='v', field_id=2, base_type=BaseType.UINT32, size=4, sub_fields=[a])
        resolution = field.resolve_sub_field([ref, field])
        self.assertIsNone(resolution.selected)
        self.assertFalse(resolution.has_match)
        self.assertFalse(resolution.is_ambiguous)


class TestWorkoutStepSubfieldsGolden(unittest.TestCase):
    def test_distance_and_time_scales(self):
        distance = WorkoutStepMessage()
        distance.duration_type = WorkoutStepDuration.DISTANCE
        distance.duration_value = 250.0
        self.assertEqual(distance.get_field(2).encoded_values[0], 25000)
        self.assertAlmostEqual(distance.duration_distance, 250.0)
        self.assertEqual(distance.get_field(2).get_units(
            sub_field=distance.get_field(2).get_valid_sub_field(distance.fields),
        ), 'm')

        time_step = WorkoutStepMessage()
        time_step.duration_type = WorkoutStepDuration.TIME
        time_step.duration_value = 2.5
        self.assertEqual(time_step.get_field(2).encoded_values[0], 2500)
        self.assertAlmostEqual(time_step.duration_time, 2.5)

    def test_duration_hr_permitted_values(self):
        # duration_hr permits types 2 and 3 (HR_LESS_THAN / HR_GREATER_THAN).
        message = WorkoutStepMessage()
        message.duration_type = WorkoutStepDuration.HR_LESS_THAN
        selected = message.get_field(2).get_valid_sub_field(message.fields)
        assert selected is not None
        self.assertEqual(selected.name, 'duration_hr')
        self.assertEqual(selected.units, '% or bpm')


class TestSubfieldComponents(unittest.TestCase):
    def test_components_from_active_subfield(self):
        message = RecordMessage()
        source = message.get_field(8)
        assert source is not None
        # Synthetic subfield-gated components (Profile does not emit these yet).
        sub = SubField(
            name='packed_when_flag',
            base_type=BaseType.BYTE,
            reference_map={253: [1000]},  # timestamp field as synthetic gate
            components=[
                FieldComponent(field_id=6, accumulate=False, bits=12, scale=100.0, offset=0.0),
                FieldComponent(field_id=5, accumulate=False, bits=12, scale=16.0, offset=0.0),
            ],
        )
        source.sub_fields = [sub]
        source.components = []  # force subfield path
        source.size = 3
        packed = 1000 | (32 << 12)
        source.encoded_values = [packed & 0xFF, (packed >> 8) & 0xFF, (packed >> 16) & 0xFF]

        ts = message.get_field(253)
        assert ts is not None
        ts.size = 4
        ts.encoded_values = [1000]

        components = components_for_field(20, source, message.fields)
        self.assertEqual(len(components), 2)

        expand_message_components(message)
        self.assertAlmostEqual(message.get_field(6).get_value(), 10.0)
        self.assertAlmostEqual(message.get_field(5).get_value(), 2.0)

    def test_inactive_subfield_components_not_used(self):
        message = RecordMessage()
        source = message.get_field(8)
        assert source is not None
        sub = SubField(
            name='packed_when_flag',
            reference_map={253: [999]},
            components=[
                FieldComponent(field_id=6, accumulate=False, bits=12, scale=100.0, offset=0.0),
            ],
        )
        source.sub_fields = [sub]
        source.components = []
        ts = message.get_field(253)
        assert ts is not None
        ts.size = 4
        ts.encoded_values = [1000]
        # Falls back to registry for record field 8.
        components = components_for_field(20, source, message.fields)
        self.assertEqual(len(components), 2)  # registry compressed_speed_distance


class TestSubfieldAmbiguityProfileValidation(unittest.TestCase):
    def test_ambiguous_subfields_are_profile_errors(self):
        message = WorkoutStepMessage()
        message.duration_type = WorkoutStepDuration.DISTANCE
        duration_value = message.get_field(2)
        assert duration_value is not None
        # Inject a duplicate-matching subfield to force ambiguity.
        clone = SubField(
            name='duration_distance_dup',
            base_type=BaseType.UINT32,
            scale=100,
            offset=0,
            units='m',
            reference_map={1: [WorkoutStepDuration.DISTANCE.value]},
        )
        duration_value.sub_fields = list(duration_value.sub_fields) + [clone]
        duration_value.size = 4
        duration_value.encoded_values = [50000]

        records = [Record.from_message(message)]
        report = validate_fit_file(records, levels={ConformanceLevel.PROFILE})
        ambiguous = [
            f for f in report.findings
            if f.level is ConformanceLevel.PROFILE
            and f.severity is Severity.ERROR
            and 'Ambiguous subfields' in f.message
        ]
        self.assertEqual(len(ambiguous), 1)
        self.assertIn('duration_distance', ambiguous[0].message)
        self.assertIn('duration_distance_dup', ambiguous[0].message)

        # Decode still uses the first match.
        selected = duration_value.get_valid_sub_field(message.fields)
        assert selected is not None
        self.assertEqual(selected.name, 'duration_distance')

    def test_unambiguous_workout_step_has_no_subfield_error(self):
        message = WorkoutStepMessage()
        message.duration_type = WorkoutStepDuration.DISTANCE
        message.duration_value = 10.0
        report = validate_fit_file(
            [Record.from_message(message)],
            levels={ConformanceLevel.PROFILE},
        )
        self.assertFalse(any('Ambiguous subfields' in f.message for f in report.findings))


if __name__ == '__main__':
    unittest.main()
