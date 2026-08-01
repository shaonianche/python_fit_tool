"""Golden / constructive fixtures for Stage-2 protocol gaps (Phase 0 characterize).

See ``fit_tool/tests/data/README.md`` for the gap inventory. Unknown-field
preservation (E) is implemented; component (C) and subfield (D) cases may still
use ``xfail`` until those stages land. No unexplained skips.
"""

from __future__ import annotations

import unittest


from fit_tool.components import expand_message_components
from fit_tool.exceptions import FitParseError
from fit_tool.fit_file import FitFile
from fit_tool.profile.messages.record_message import RecordMessage
from fit_tool.profile.messages.workout_step_message import WorkoutStepMessage
from fit_tool.profile.profile_type import WorkoutStepDuration
from fit_tool.tests.protocol_fixture_helpers import (
    build_record_with_compressed_speed_distance,
    build_record_with_unknown_field,
    build_workout_step_with_duration,
    chain_segments,
)
from fit_tool.wire.decoder import decode_bytes
from fit_tool.wire.model import RawDefinitionRecord


class TestComponentExpansionEdges(unittest.TestCase):
    """Additional packed-field cases beyond registry smoke in high-severity tests."""

    def test_wire_decode_expands_compressed_speed_distance(self):
        raw = build_record_with_compressed_speed_distance(
            speed_encoded_12bit=1000,
            distance_encoded_12bit=32,
        )
        fit = FitFile.from_bytes(raw)
        message = next(r.message for r in fit.records if not r.header.is_definition)
        self.assertIsInstance(message, RecordMessage)
        speed = message.get_field(6)
        distance = message.get_field(5)
        assert speed is not None and distance is not None
        self.assertAlmostEqual(speed.get_value(), 10.0)
        self.assertAlmostEqual(distance.get_value(), 2.0)

    def test_accumulate_16bit_rollover(self):
        """Unsigned modular delta when the packed 16-bit value wraps."""
        message = RecordMessage()
        source = message.get_field(28)
        assert source is not None
        source.size = 2
        acc: dict[tuple[int, int], int] = {}

        source.encoded_values = [65535]
        expand_message_components(message, acc)
        self.assertEqual(acc[(20, 29)], 65535)

        source.encoded_values = [1]  # wrap past 0xFFFF → modular delta 2
        expand_message_components(message, acc)
        power = message.get_field(29)
        assert power is not None
        self.assertEqual(acc[(20, 29)], 65537)
        self.assertEqual(power.get_value(), 65537)

    def test_nested_components_expanded(self):
        """Nested component graph (compressed_speed_distance → speed → enhanced)."""
        from fit_tool.components import components_for_field
        from fit_tool.field_component import FieldComponent

        message = RecordMessage()
        empty = message.get_field(0)  # position_lat — no components
        assert empty is not None
        self.assertEqual(components_for_field(20, empty), ())

        # Field-attached components still override the registry for that field.
        source = message.get_field(8)
        assert source is not None
        source.components = [
            FieldComponent(field_id=6, accumulate=False, bits=12, scale=100.0, offset=0.0),
            FieldComponent(field_id=5, accumulate=False, bits=12, scale=16.0, offset=0.0),
        ]
        self.assertEqual(len(components_for_field(20, source)), 2)

        # Registry path: nested expansion is covered in test_components.py (SHA-15).


class TestUnknownFieldOnKnownMessage(unittest.TestCase):
    """Unknown field ids on a known global message (Stage 2 E)."""

    UNKNOWN_ID = 250
    UNKNOWN_VALUE = 0xABCD

    def test_wire_definition_retains_unknown_field_id(self):
        raw = build_record_with_unknown_field(
            unknown_field_id=self.UNKNOWN_ID,
            unknown_value=self.UNKNOWN_VALUE,
        )
        document = decode_bytes(raw)
        definition = next(
            r for r in document.first_segment.records if isinstance(r, RawDefinitionRecord)
        )
        field_ids = [fd.field_id for fd in definition.field_definitions]
        self.assertEqual(field_ids, [253, self.UNKNOWN_ID, 3])

    def test_projection_retains_unknown_and_known_fields(self):
        raw = build_record_with_unknown_field(
            unknown_field_id=self.UNKNOWN_ID,
            unknown_value=self.UNKNOWN_VALUE,
            heart_rate=120,
        )
        fit = FitFile.from_bytes(raw)
        message = next(r.message for r in fit.records if not r.header.is_definition)
        self.assertIsInstance(message, RecordMessage)
        unknown = message.get_field(self.UNKNOWN_ID)
        assert unknown is not None
        self.assertEqual(unknown.get_value(), self.UNKNOWN_VALUE)
        hr = message.get_field(3)
        assert hr is not None
        self.assertEqual(hr.get_value(), 120)
        # Definition snapshot still lists the unknown id (structural truth).
        assert message.definition_message is not None
        def_ids = [fd.field_id for fd in message.definition_message.field_definitions]
        self.assertIn(self.UNKNOWN_ID, def_ids)

    def test_untouched_preserve_keeps_unknown_field_bytes(self):
        raw = build_record_with_unknown_field(
            unknown_field_id=self.UNKNOWN_ID,
            unknown_value=self.UNKNOWN_VALUE,
        )
        fit = FitFile.from_bytes(raw)
        self.assertEqual(fit.to_bytes(preserve=True), raw)

    def test_projected_message_exposes_unknown_field_value(self):
        from fit_tool.field import UnknownField

        raw = build_record_with_unknown_field(
            unknown_field_id=self.UNKNOWN_ID,
            unknown_value=self.UNKNOWN_VALUE,
        )
        fit = FitFile.from_bytes(raw)
        message = next(r.message for r in fit.records if not r.header.is_definition)
        unknown = message.get_field(self.UNKNOWN_ID)
        assert unknown is not None
        self.assertIsInstance(unknown, UnknownField)
        self.assertTrue(unknown.is_unknown)
        self.assertEqual(unknown.get_value(), self.UNKNOWN_VALUE)
        self.assertEqual(unknown.name, f'unknown_{self.UNKNOWN_ID}')
        # Raw wire slice held for later PRESERVATION rewrite (Stage 3 F).
        self.assertEqual(unknown.raw_bytes, self.UNKNOWN_VALUE.to_bytes(2, 'little'))

    def test_reencode_without_preserve_keeps_unknown_payload(self):
        """Projected re-encode (no wire_document) still emits unknown field bytes."""
        raw = build_record_with_unknown_field(
            unknown_field_id=self.UNKNOWN_ID,
            unknown_value=self.UNKNOWN_VALUE,
            heart_rate=99,
        )
        fit = FitFile.from_bytes(raw)
        fit.mark_dirty()
        rebuilt = fit.to_bytes(preserve=False)
        again = FitFile.from_bytes(rebuilt)
        message = next(r.message for r in again.records if not r.header.is_definition)
        unknown = message.get_field(self.UNKNOWN_ID)
        assert unknown is not None
        self.assertEqual(unknown.get_value(), self.UNKNOWN_VALUE)
        hr = message.get_field(3)
        assert hr is not None
        self.assertEqual(hr.get_value(), 99)


class TestSubfieldBearingMessage(unittest.TestCase):
    """Subfield-relevant workout_step samples (Stage 2 D — golden)."""

    def test_workout_step_with_duration_decodes(self):
        # duration_type DISTANCE = 1; raw duration_value 50000 (wire UINT32)
        raw = build_workout_step_with_duration(
            duration_type=WorkoutStepDuration.DISTANCE.value,
            duration_value_raw=50000,
            name='gap-step',
        )
        fit = FitFile.from_bytes(raw)
        message = next(r.message for r in fit.records if not r.header.is_definition)
        self.assertIsInstance(message, WorkoutStepMessage)
        self.assertEqual(message.workout_step_name, 'gap-step')
        self.assertEqual(message.duration_type, WorkoutStepDuration.DISTANCE.value)
        self.assertAlmostEqual(message.duration_value, 500.0)

    def test_only_matching_subfield_is_valid(self):
        """SubField.is_valid matches permitted ref values (AND semantics)."""
        message = WorkoutStepMessage()
        message.duration_type = WorkoutStepDuration.DISTANCE
        duration_value = message.get_field(2)
        assert duration_value is not None
        valid = [sf for sf in duration_value.sub_fields if sf.is_valid(message.fields)]
        self.assertEqual([sf.name for sf in valid], ['duration_distance'])

    def test_duration_distance_subfield_is_selected(self):
        message = WorkoutStepMessage()
        message.duration_type = WorkoutStepDuration.DISTANCE
        duration_value = message.get_field(2)
        assert duration_value is not None
        selected = duration_value.get_valid_sub_field(message.fields)
        assert selected is not None
        self.assertEqual(selected.name, 'duration_distance')
        self.assertEqual(selected.scale, 100)
        self.assertEqual(selected.units, 'm')

    def test_duration_distance_scale_applied_on_decode(self):
        # Wire raw 50000 with scale 100 → 500 m when duration_type is DISTANCE.
        raw = build_workout_step_with_duration(
            duration_type=WorkoutStepDuration.DISTANCE.value,
            duration_value_raw=50000,
        )
        fit = FitFile.from_bytes(raw)
        message = next(r.message for r in fit.records if not r.header.is_definition)
        self.assertAlmostEqual(message.duration_value, 500.0)

    def test_duration_time_scale_applied_on_decode(self):
        # TIME = 0; wire raw 1500 with scale 1000 → 1.5 s.
        raw = build_workout_step_with_duration(
            duration_type=WorkoutStepDuration.TIME.value,
            duration_value_raw=1500,
        )
        fit = FitFile.from_bytes(raw)
        message = next(r.message for r in fit.records if not r.header.is_definition)
        self.assertAlmostEqual(message.duration_value, 1.5)
        self.assertAlmostEqual(message.duration_time, 1.5)

    def test_duration_time_named_property_gated_by_type(self):
        message = WorkoutStepMessage()
        message.duration_type = WorkoutStepDuration.DISTANCE
        message.duration_value = 100.0  # metres via duration_distance scale
        self.assertIsNone(message.duration_time)
        self.assertAlmostEqual(message.duration_distance, 100.0)


class TestMultiSegmentAndTrailingCorpus(unittest.TestCase):
    """Cross-check multi-segment / trailing cases (already covered; keep corpus link)."""

    def test_three_segment_chain(self):
        one = build_workout_step_with_duration(
            duration_type=WorkoutStepDuration.TIME.value,
            duration_value_raw=1000,
            name='a',
        )
        chained = chain_segments(one, one, one)
        document = decode_bytes(chained)
        self.assertEqual(len(document.segments), 3)
        self.assertTrue(document.is_chained)
        fit = FitFile.from_bytes(chained)
        self.assertEqual(fit.to_bytes(preserve=True), chained)

    def test_trailing_bytes_policy(self):
        one = build_record_with_compressed_speed_distance()
        with self.assertRaises(FitParseError):
            FitFile.from_bytes(one + b'\xff\x00')
        fit = FitFile.from_bytes(one + b'\xff\x00', allow_trailing_bytes=True)
        self.assertGreaterEqual(len(fit.records), 1)


if __name__ == '__main__':
    unittest.main()
