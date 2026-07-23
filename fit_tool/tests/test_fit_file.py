# nosetests --nocapture  tests/test_fit_file.py


import csv
import io
import struct
import tempfile
import unittest
from unittest import mock

from fit_tool.definition_message import DefinitionMessage
from fit_tool.exceptions import FitCRCError, FitHeaderError
from fit_tool.fit_file import FitFile
from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.profile.messages.workout_step_message import WorkoutStepMessage
from fit_tool.profile.profile_type import WorkoutStepDuration


class TestFitFile(unittest.TestCase):

    def test_conversion_simple(self):
        mesg = WorkoutStepMessage(local_id=0)
        mesg.workout_step_name = '1st step'
        mesg.duration_type = WorkoutStepDuration.DISTANCE

        def_mesg = DefinitionMessage.from_data_message(mesg)

        builder = FitFileBuilder(auto_define=False)
        builder.add(def_mesg)
        builder.add(mesg)

        fit_file = builder.build()

        bytes1 = fit_file.to_bytes()

        fite_file2 = FitFile.from_bytes(bytes1)
        bytes2 = fite_file2.to_bytes()

        print(f'{bytes1}')
        print(f'{bytes2}')
        self.assertEqual(bytes2, bytes1)

    def test_builder_with_auto_define(self):
        mesg1 = WorkoutStepMessage(local_id=0)
        mesg1.workout_step_name = '1st step'
        mesg1.duration_type = WorkoutStepDuration.DISTANCE

        mesg2 = WorkoutStepMessage(local_id=0)
        mesg2.workout_step_name = '2nd step'
        mesg2.duration_type = WorkoutStepDuration.DISTANCE

        builder = FitFileBuilder(auto_define=True, min_string_size=50)
        builder.add(mesg1)
        builder.add(mesg2)

        fit_file = builder.build()

        self.assertEqual(len(fit_file.records), 3)

    def test_from_bytes_invalid_crc_raises_value_error(self):
        mesg = WorkoutStepMessage(local_id=0)
        mesg.workout_step_name = '1st step'
        mesg.duration_type = WorkoutStepDuration.DISTANCE

        builder = FitFileBuilder(auto_define=True)
        builder.add(mesg)
        fit_file = builder.build()
        valid_bytes = fit_file.to_bytes()

        stored_crc, = struct.unpack('<H', valid_bytes[-2:])
        tampered_crc = (stored_crc + 1) % 65536
        tampered_bytes = valid_bytes[:-2] + struct.pack('<H', tampered_crc)

        with self.assertRaises(ValueError):
            FitFile.from_bytes(tampered_bytes)

    def test_to_bytes_mismatched_crc_raises_value_error(self):
        mesg = WorkoutStepMessage(local_id=0)
        mesg.workout_step_name = '1st step'
        mesg.duration_type = WorkoutStepDuration.DISTANCE

        builder = FitFileBuilder(auto_define=True)
        builder.add(mesg)
        fit_file = builder.build()

        fit_file.crc = (fit_file.crc + 1) % 65536
        with self.assertRaises(ValueError):
            fit_file.to_bytes()

    def test_to_bytes_mismatched_crc_logs_warning_when_check_disabled(self):
        mesg = WorkoutStepMessage(local_id=0)
        mesg.workout_step_name = '1st step'
        mesg.duration_type = WorkoutStepDuration.DISTANCE

        builder = FitFileBuilder(auto_define=True)
        builder.add(mesg)
        fit_file = builder.build()

        fit_file.crc = (fit_file.crc + 1) % 65536
        bytes_buffer = fit_file.to_bytes(check_crc=False)
        self.assertIsInstance(bytes_buffer, bytes)

    def test_builder_requires_definition_when_auto_define_is_false(self):
        mesg = WorkoutStepMessage(local_id=0)
        mesg.workout_step_name = '1st step'
        mesg.duration_type = WorkoutStepDuration.DISTANCE

        builder = FitFileBuilder(auto_define=False)
        with self.assertRaises(ValueError):
            builder.add(mesg)

    def test_builder_rejects_unsupported_definition_when_auto_define_is_false(self):
        first = WorkoutStepMessage(local_id=0)
        first.workout_step_name = 'a'
        first.duration_type = WorkoutStepDuration.DISTANCE

        second = WorkoutStepMessage(local_id=0)
        second.workout_step_name = 'this-name-is-longer'
        second.duration_type = WorkoutStepDuration.DISTANCE

        builder = FitFileBuilder(auto_define=False)
        builder.add(DefinitionMessage.from_data_message(first))
        builder.add(first)
        with self.assertRaises(ValueError):
            builder.add(second)

    def test_to_csv_does_not_materialize_all_rows(self):
        message = WorkoutStepMessage(local_id=0)
        message.workout_step_name = 'step'
        message.duration_type = WorkoutStepDuration.DISTANCE

        builder = FitFileBuilder(auto_define=True)
        builder.add(message)
        fit_file = builder.build()

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = f'{temp_dir}/output.csv'
            with mock.patch.object(fit_file, 'to_rows', side_effect=AssertionError('to_rows must not be called')):
                fit_file.to_csv(output_path)

            with open(output_path, newline='') as csv_file:
                rows = list(csv.reader(csv_file))
        self.assertEqual(rows[0][:3], ['Type', 'Local ID', 'Message'])
        self.assertEqual(rows[1][0], 'Definition')
        self.assertEqual(rows[2][0], 'Data')

    def test_builder_build_bytes_matches_built_file(self):
        message = WorkoutStepMessage(local_id=0)
        message.workout_step_name = 'step'
        message.duration_type = WorkoutStepDuration.DISTANCE

        direct_builder = FitFileBuilder(auto_define=True)
        direct_builder.add(message)
        direct_bytes = direct_builder.build_bytes()

        regular_builder = FitFileBuilder(auto_define=True)
        regular_builder.add(message)
        regular_bytes = regular_builder.build().to_bytes()

        self.assertEqual(direct_bytes, regular_bytes)

    def test_from_bytes_raises_fit_header_error_for_empty_or_truncated_input(self):
        with self.assertRaises(FitHeaderError):
            FitFile.from_bytes(b'')

        message = WorkoutStepMessage(local_id=0)
        message.duration_type = WorkoutStepDuration.DISTANCE
        builder = FitFileBuilder(auto_define=True)
        builder.add(message)
        valid_bytes = builder.build_bytes()

        with self.assertRaises(FitHeaderError):
            FitFile.from_bytes(valid_bytes[:-3])

    def test_iter_stream_matches_regular_parser(self):
        message = WorkoutStepMessage(local_id=0)
        message.workout_step_name = 'step'
        message.duration_type = WorkoutStepDuration.DISTANCE
        builder = FitFileBuilder(auto_define=True)
        builder.add(message)
        fit_bytes = builder.build_bytes()

        streamed_records = list(FitFile.iter_stream(io.BytesIO(fit_bytes)))
        regular_records = FitFile.from_bytes(fit_bytes).records

        self.assertEqual(
            [record.to_bytes() for record in streamed_records],
            [record.to_bytes() for record in regular_records],
        )

    def test_iter_stream_handles_partial_reads(self):
        class PartialReadStream(io.BytesIO):
            def read(self, size=-1):
                return super().read(min(size, 2) if size >= 0 else 2)

        message = WorkoutStepMessage(local_id=0)
        message.duration_type = WorkoutStepDuration.DISTANCE
        builder = FitFileBuilder(auto_define=True)
        builder.add(message)

        records = list(FitFile.iter_stream(PartialReadStream(builder.build_bytes())))

        self.assertEqual(2, len(records))

    def test_iter_stream_validates_crc_when_exhausted(self):
        message = WorkoutStepMessage(local_id=0)
        message.duration_type = WorkoutStepDuration.DISTANCE
        builder = FitFileBuilder(auto_define=True)
        builder.add(message)
        fit_bytes = bytearray(builder.build_bytes())
        fit_bytes[-1] ^= 0xff

        with self.assertRaises(FitCRCError):
            list(FitFile.iter_stream(io.BytesIO(fit_bytes)))

    def test_message_edit_refreshes_crc_without_explicit_override(self):
        message = WorkoutStepMessage(local_id=0)
        message.duration_type = WorkoutStepDuration.DISTANCE
        builder = FitFileBuilder(auto_define=True)
        builder.add(message)
        fit_file = builder.build()
        original_crc = fit_file.crc

        message.duration_type = WorkoutStepDuration.TIME
        encoded = fit_file.to_bytes()

        self.assertNotEqual(fit_file.crc, original_crc)
        self.assertEqual(FitFile.from_bytes(encoded).to_bytes(), encoded)
