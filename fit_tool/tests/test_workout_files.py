# nosetests --nocapture  tests/test_field.py
import logging
import os
import sys
import unittest
from pathlib import Path

from fit_tool.fit_file import FitFile
from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.messages.workout_message import WorkoutMessage
from fit_tool.profile.messages.workout_step_message import WorkoutStepMessage
from fit_tool.profile.profile_type import (
    FileType,
    Manufacturer,
    Sport,
    WorkoutStepDuration,
    WorkoutStepTarget,
)
from fit_tool.utils.logging import formatter, logger
from fit_tool.validation import ConformanceLevel, validate_fit_file

SDK_DIR = Path(__file__).resolve().parent / 'data' / 'sdk'
WORKOUT_SDK_FILES = sorted(SDK_DIR.glob('Workout*.fit'))


class TestCourseFiles(unittest.TestCase):

    def setUp(self):
        super().setUp()
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    def shortDescription(self):
        return None

    def test_decode_trainer_road(self):
        """Test decoding workout repeat greater than step file
        """
        path = os.path.join(os.path.dirname(__file__), 'data/trainerroad_744490.fit')

        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            print(f'Profile version: {fit_file.header.profile_version}')
            fit_file.to_rows()


class TestWorkoutFileTypeValidation(unittest.TestCase):
    """FILE_TYPE rules for Workout (SHA-21 / design Phase 4 §7)."""

    def test_sdk_workout_fixtures_pass_file_type(self):
        self.assertTrue(WORKOUT_SDK_FILES, 'expected committed SDK Workout*.fit fixtures')
        for path in WORKOUT_SDK_FILES:
            with self.subTest(path=path.name):
                fit_file = FitFile.from_file(str(path))
                report = validate_fit_file(fit_file, levels={ConformanceLevel.FILE_TYPE})
                self.assertFalse(
                    report.has_errors,
                    f'{path.name} FILE_TYPE errors: {[f.message for f in report.errors]}',
                )

    def test_trainerroad_workout_passes_file_type(self):
        path = Path(__file__).resolve().parent / 'data' / 'trainerroad_744490.fit'
        fit_file = FitFile.from_file(str(path))
        report = validate_fit_file(fit_file, levels={ConformanceLevel.FILE_TYPE})
        self.assertFalse(
            report.has_errors,
            f'FILE_TYPE errors: {[f.message for f in report.errors]}',
        )

    def test_strict_builder_builds_minimal_workout(self):
        builder = FitFileBuilder(strict=True, auto_define=True, min_string_size=50)
        file_id = FileIdMessage()
        file_id.type = FileType.WORKOUT
        file_id.manufacturer = Manufacturer.DEVELOPMENT.value
        file_id.product = 0
        file_id.serial_number = 0x12345678
        file_id.time_created = 1_700_000_000_000
        builder.add(file_id)

        step = WorkoutStepMessage()
        step.message_index = 0
        step.workout_step_name = 'Warm up'
        step.duration_type = WorkoutStepDuration.TIME
        step.duration_time = 600.0
        step.target_type = WorkoutStepTarget.OPEN
        step.target_value = 0

        workout = WorkoutMessage()
        workout.workout_name = 'Tempo'
        workout.sport = Sport.CYCLING
        workout.num_valid_steps = 1

        builder.add(workout)
        builder.add(step)
        encoded = builder.build_bytes()
        self.assertGreater(len(encoded), 0)

        report = validate_fit_file(
            FitFile.from_bytes(encoded),
            levels={ConformanceLevel.FILE_TYPE},
        )
        self.assertFalse(report.has_errors)

    def _minimal_workout_builder(self):
        builder = FitFileBuilder(auto_define=True, min_string_size=50)
        file_id = FileIdMessage()
        file_id.type = FileType.WORKOUT
        file_id.manufacturer = Manufacturer.DEVELOPMENT.value
        file_id.product = 0
        file_id.serial_number = 0x12345678
        file_id.time_created = 1_700_000_000_000
        builder.add(file_id)
        return builder

    def test_num_valid_steps_mismatch_errors(self):
        """Codex P2: num_valid_steps must match non-repeat step count."""
        builder = self._minimal_workout_builder()
        workout = WorkoutMessage()
        workout.workout_name = 'Bad count'
        workout.sport = Sport.CYCLING
        workout.num_valid_steps = 0  # wrong — one ordinary step present
        builder.add(workout)
        step = WorkoutStepMessage()
        step.message_index = 0
        step.duration_type = WorkoutStepDuration.TIME
        step.duration_time = 60.0
        step.target_type = WorkoutStepTarget.OPEN
        builder.add(step)
        report = validate_fit_file(builder.build(), levels={ConformanceLevel.FILE_TYPE})
        self.assertTrue(report.has_errors)
        self.assertTrue(
            any('num_valid_steps' in f.message for f in report.errors),
            [f.message for f in report.errors],
        )

    def test_value_duration_without_duration_value_errors(self):
        """Codex P2: TIME (and other non-OPEN) requires duration_value."""
        builder = self._minimal_workout_builder()
        workout = WorkoutMessage()
        workout.workout_name = 'No duration'
        workout.sport = Sport.CYCLING
        workout.num_valid_steps = 1
        builder.add(workout)
        step = WorkoutStepMessage()
        step.message_index = 0
        step.duration_type = WorkoutStepDuration.TIME
        # intentionally no duration_time / duration_value
        step.target_type = WorkoutStepTarget.OPEN
        builder.add(step)
        report = validate_fit_file(builder.build(), levels={ConformanceLevel.FILE_TYPE})
        self.assertTrue(report.has_errors)
        self.assertTrue(
            any('duration_value' in f.message for f in report.errors),
            [f.message for f in report.errors],
        )
