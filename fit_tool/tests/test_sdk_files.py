# nosetests --nocapture  tests/test_field.py
import csv
import os
import unittest

from fit_tool.fit_file import FitFile

TEST_DIR = os.path.dirname(__file__)
OUT_DIR = os.path.join(TEST_DIR, 'out')
os.makedirs(OUT_DIR, exist_ok=True)


class TestSdkFiles(unittest.TestCase):

    def setUp(self):
        super().setUp()
        # stream_handler = logging.StreamHandler(sys.stdout)
        # stream_handler.setFormatter(formatter)
        # logger.addHandler(stream_handler)

    def shortDescription(self):
        return None

    def test_developer_data(self):
        """Test decoding activity file with developer fields.
        """
        path = os.path.join(os.path.dirname(__file__), 'data/sdk/DeveloperData.fit')

        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            # print(f'Profile version: {fit_file.header.profile_version}')
            fit_file.to_rows()

    def test_activity(self):
        """Test decoding activity file.
        """
        path = os.path.join(os.path.dirname(__file__), 'data/sdk/Activity.fit')

        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            # print(f'Profile version: {fit_file.header.profile_version}')
            rows = fit_file.to_rows()

        out_path = os.path.join(os.path.dirname(__file__), 'out/Activity.csv')
        with open(out_path, 'w', newline='') as csv_file:
            csv_writer = csv.writer(csv_file, delimiter=',',
                                    quotechar='|', quoting=csv.QUOTE_MINIMAL)
            for row in rows:
                csv_writer.writerow(row)

    def test_activity_developer_data(self):
        """Test decoding activity file.
        """
        path = os.path.join(os.path.dirname(__file__), 'data/sdk/activity_developerdata.fit')

        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            # print(f'Profile version: {fit_file.header.profile_version}')
            rows = fit_file.to_rows()

        out_path = os.path.join(os.path.dirname(__file__), 'out/activity_developerdata.csv')
        with open(out_path, 'w', newline='') as csv_file:
            csv_writer = csv.writer(csv_file, delimiter=',',
                                    quotechar='|', quoting=csv.QUOTE_MINIMAL)
            for row in rows:
                csv_writer.writerow(row)

    def test_activity_low_battery(self):
        """Test decoding activity low battery file.
        """
        path = os.path.join(os.path.dirname(__file__), 'data/sdk/activity_lowbattery.fit')

        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            # print(f'Profile version: {fit_file.header.profile_version}')
            fit_file.to_rows()

    def test_activity_multi_sport(self):
        """Test decoding activity multisport file.
        """
        path = os.path.join(os.path.dirname(__file__), 'data/sdk/activity_multisport.fit')

        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            # print(f'Profile version: {fit_file.header.profile_version}')
            fit_file.to_rows()

    def test_activity_poolswim_with_hr(self):
        """Test decoding
        """
        path = os.path.join(os.path.dirname(__file__), 'data/sdk/activity_poolswim_with_hr.fit')

        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            # print(f'Profile version: {fit_file.header.profile_version}')
            fit_file.to_rows()

    def test_activity_poolswim(self):
        """Test decoding
        """
        path = os.path.join(os.path.dirname(__file__), 'data/sdk/activity_poolswim.fit')

        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            # print(f'Profile version: {fit_file.header.profile_version}')
            fit_file.to_rows()

    def test_activity_truncated(self):
        """Test decoding
        """
        path = os.path.join(os.path.dirname(__file__), 'data/sdk/activity_truncated.fit')

        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            # print(f'Profile version: {fit_file.header.profile_version}')
            fit_file.to_rows()

    def test_monitoring_file(self):
        """Test decoding
        """
        path = os.path.join(os.path.dirname(__file__), 'data/sdk/MonitoringFile.fit')

        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            # print(f'Profile version: {fit_file.header.profile_version}')
            fit_file.to_rows()

    def test_weight_scale_multi_user(self):
        """Test decoding
        """
        path = os.path.join(os.path.dirname(__file__), 'data/sdk/WeightScaleMultiUser.fit')

        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            # print(f'Profile version: {fit_file.header.profile_version}')
            fit_file.to_rows()

    def test_weight_scale_single_user(self):
        """Test decoding
        """
        path = os.path.join(os.path.dirname(__file__), 'data/sdk/WeightScaleSingleUser.fit')

        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            # print(f'Profile version: {fit_file.header.profile_version}')
            fit_file.to_rows()

    def test_workout_individual_steps(self):
        """Test decoding
        """
        path = os.path.join(os.path.dirname(__file__), 'data/sdk/WorkoutIndividualSteps.fit')

        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            # print(f'Profile version: {fit_file.header.profile_version}')
            fit_file.to_rows()

    def test_workout_custom_target_values(self):
        """Test decoding
        """
        path = os.path.join(os.path.dirname(__file__), 'data/sdk/WorkoutCustomTargetValues.fit')

        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            # print(f'Profile version: {fit_file.header.profile_version}')
            fit_file.to_rows()

    def test_workout_repeat_greater_than_step(self):
        """Test decoding
        """
        path = os.path.join(os.path.dirname(__file__), 'data/sdk/WorkoutRepeatGreaterThanStep.fit')

        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            # print(f'Profile version: {fit_file.header.profile_version}')
            fit_file.to_rows()

    def test_workout_repeat_steps(self):
        """Test decoding workout repeat steps file.
        """
        path = os.path.join(os.path.dirname(__file__), 'data/sdk/WorkoutRepeatSteps.fit')

        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            # print(f'Profile version: {fit_file.header.profile_version}')
            fit_file.to_rows()


class TestInvalidValueDecoding(unittest.TestCase):
    """FIT sentinels read as no value while their raw bytes still round-trip."""

    @staticmethod
    def _load(name):
        path = os.path.join(os.path.dirname(__file__), 'data', 'sdk', name)
        with open(path, 'rb') as file_object:
            return FitFile.from_bytes(file_object.read())

    @staticmethod
    def _records(fit_file, message_name):
        from fit_tool.data_message import DataMessage

        for record in fit_file.records:
            message = record.message
            if isinstance(message, DataMessage) and message.name == message_name:
                yield message

    def test_activity_scalar_sentinels_decode_as_none(self):
        sentinels = {'cadence': 0xff, 'speed': 0xffff, 'left_pco': 0x7f}
        seen = {}
        for message in self._records(self._load('Activity.fit'), 'record'):
            for name, sentinel in sentinels.items():
                field = message.get_field_by_name(name)
                if field is not None and field.size and sentinel in field.encoded_values:
                    seen.setdefault(name, (message, field))

        self.assertEqual(set(seen), set(sentinels))
        for name, (message, field) in seen.items():
            self.assertIsNone(getattr(message, name))
            self.assertFalse(field.has_value())
            self.assertIn(sentinels[name], field.encoded_values)

    def test_activity_power_phase_sentinels_decode_as_none(self):
        for message in self._records(self._load('Activity.fit'), 'record'):
            field = message.get_field_by_name('left_power_phase')
            if field is not None and field.size and 0xff in field.encoded_values:
                self.assertEqual(message.left_power_phase, [None, None])
                self.assertEqual(field.to_bytes(), b'\xff\xff')
                return
        self.fail('no record with an invalid left_power_phase')

    def test_lap_unset_power_zones_decode_as_none(self):
        for message in self._records(self._load('activity_poolswim_with_hr.fit'), 'lap'):
            field = message.get_field_by_name('time_in_power_zone')
            if field is not None and field.size and all(
                value == 0xffffffff for value in field.encoded_values
            ):
                self.assertEqual(message.time_in_power_zone, [None] * len(field.encoded_values))
                self.assertEqual(field.to_bytes(), b'\xff' * field.size)
                return
        self.fail('no lap with an unset time_in_power_zone')

    def test_edited_record_keeps_invalid_sentinel_bytes(self):
        fit_file = self._load('Activity.fit')
        target = None
        for message in self._records(fit_file, 'record'):
            cadence = message.get_field_by_name('cadence')
            heart_rate = message.get_field_by_name('heart_rate')
            if (
                cadence is not None
                and cadence.size
                and cadence.get_value() is None
                and heart_rate is not None
                and heart_rate.size
                and message.timestamp is not None
            ):
                target = message
                break
        self.assertIsNotNone(target)
        timestamp = target.timestamp
        target.heart_rate = 123

        for message in self._records(FitFile.from_bytes(fit_file.to_bytes()), 'record'):
            if message.timestamp == timestamp:
                cadence = message.get_field_by_name('cadence')
                self.assertIsNone(cadence.get_value())
                self.assertEqual(cadence.encoded_values, [0xff])
                self.assertEqual(message.heart_rate, 123)
                return
        self.fail('edited record not found after re-encode')

    def test_all_fixtures_round_trip_byte_identical(self):
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        paths = []
        for root, _, files in os.walk(data_dir):
            paths.extend(
                os.path.join(root, filename)
                for filename in files
                if filename.endswith('.fit')
            )
        self.assertGreaterEqual(len(paths), 20)
        for path in sorted(paths):
            with open(path, 'rb') as file_object:
                raw = file_object.read()
            self.assertEqual(
                FitFile.from_bytes(raw).to_bytes(),
                raw,
                os.path.basename(path),
            )
