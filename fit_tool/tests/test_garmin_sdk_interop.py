import base64
import datetime
import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path

from fit_tool import SDK_VERSION
from fit_tool.data_message import DataMessage
from fit_tool.fit_file import FitFile
from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.profile.messages.activity_message import ActivityMessage
from fit_tool.profile.messages.event_message import EventMessage
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.messages.lap_message import LapMessage
from fit_tool.profile.messages.record_message import RecordMessage
from fit_tool.profile.messages.session_message import SessionMessage
from fit_tool.profile.profile_type import Event, EventType, FileType, Manufacturer, Sport, SubSport

TEST_DIR = Path(__file__).parent
ACTIVITY_FIXTURE_PATH = TEST_DIR / 'data' / 'interop' / 'activity.json'
GARMIN_BRIDGE_PATH = TEST_DIR / 'interop' / 'garmin_fit_bridge.mjs'

# Produced by Garmin's official fit-javascript-sdk 21.205.0 Encoder for the
# equivalent file_id values used below.
GARMIN_JS_21_205_FILE_ID = bytes.fromhex(
    '0e02d552230000002e4649548f2a'
    '40000000000500010201028402028403048c040486'
    '0004ff000000d204000080b4f43ffbfe'
)


def _timestamp_millis(value):
    return round(datetime.datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp() * 1000)


def _timestamp_iso(value):
    return (
        datetime.datetime.fromtimestamp(value / 1000, tz=datetime.timezone.utc)
        .isoformat(timespec='milliseconds')
        .replace('+00:00', 'Z')
    )


def _enum_name(enum_type, value):
    enum_value = value if isinstance(value, enum_type) else enum_type(value)
    parts = enum_value.name.lower().split('_')
    return parts[0] + ''.join(part.title() for part in parts[1:])


def _build_python_activity(fixture):
    builder = FitFileBuilder(strict=True)

    file_id = FileIdMessage()
    file_id.type = FileType[fixture['fileId']['type'].upper()]
    file_id.manufacturer = Manufacturer[fixture['fileId']['manufacturer'].upper()].value
    file_id.product = fixture['fileId']['product']
    file_id.serial_number = fixture['fileId']['serialNumber']
    file_id.time_created = _timestamp_millis(fixture['fileId']['timeCreated'])
    builder.add(file_id)

    start_event = EventMessage()
    start_event.timestamp = _timestamp_millis(fixture['events'][0]['timestamp'])
    start_event.event = Event[fixture['events'][0]['event'].upper()]
    start_event.event_type = EventType[fixture['events'][0]['eventType'].upper()]
    builder.add(start_event)

    for values in fixture['records']:
        message = RecordMessage()
        message.timestamp = _timestamp_millis(values['timestamp'])
        message.distance = values['distance']
        message.heart_rate = values['heartRate']
        message.cadence = values['cadence']
        message.power = values['power']
        builder.add(message)

    stop_event = EventMessage()
    stop_event.timestamp = _timestamp_millis(fixture['events'][1]['timestamp'])
    stop_event.event = Event[fixture['events'][1]['event'].upper()]
    stop_event.event_type = EventType[fixture['events'][1]['eventType'].upper()]
    builder.add(stop_event)

    for values in fixture['laps']:
        message = LapMessage()
        message.message_index = values['messageIndex']
        message.timestamp = _timestamp_millis(values['timestamp'])
        message.start_time = _timestamp_millis(values['startTime'])
        message.total_elapsed_time = values['totalElapsedTime']
        message.total_timer_time = values['totalTimerTime']
        builder.add(message)

    for values in fixture['sessions']:
        message = SessionMessage()
        message.message_index = values['messageIndex']
        message.timestamp = _timestamp_millis(values['timestamp'])
        message.start_time = _timestamp_millis(values['startTime'])
        message.total_elapsed_time = values['totalElapsedTime']
        message.total_timer_time = values['totalTimerTime']
        message.sport = Sport[values['sport'].upper()]
        message.sub_sport = SubSport[values['subSport'].upper()]
        message.first_lap_index = values['firstLapIndex']
        message.num_laps = values['numLaps']
        builder.add(message)

    values = fixture['activity']
    activity = ActivityMessage()
    activity.timestamp = _timestamp_millis(values['timestamp'])
    activity.num_sessions = values['numSessions']
    activity.total_timer_time = values['totalTimerTime']
    builder.add(activity)

    return builder.build_bytes()


def _normalize_python_activity(fit_bytes):
    fit_file = FitFile.from_bytes(fit_bytes)
    messages = [
        record.message for record in fit_file.records
        if not record.is_definition and isinstance(record.message, DataMessage)
    ]

    file_id = next(message for message in messages if isinstance(message, FileIdMessage))
    events = [message for message in messages if isinstance(message, EventMessage)]
    records = [message for message in messages if isinstance(message, RecordMessage)]
    laps = [message for message in messages if isinstance(message, LapMessage)]
    sessions = [message for message in messages if isinstance(message, SessionMessage)]
    activity = next(message for message in messages if isinstance(message, ActivityMessage))

    return {
        'fileId': {
            'type': _enum_name(FileType, file_id.type),
            'manufacturer': _enum_name(Manufacturer, file_id.manufacturer),
            'product': file_id.product,
            'serialNumber': file_id.serial_number,
            'timeCreated': _timestamp_iso(file_id.time_created),
        },
        'events': [
            {
                'timestamp': _timestamp_iso(message.timestamp),
                'event': _enum_name(Event, message.event),
                'eventType': _enum_name(EventType, message.event_type),
            }
            for message in events
        ],
        'records': [
            {
                'timestamp': _timestamp_iso(message.timestamp),
                'distance': message.distance,
                'heartRate': message.heart_rate,
                'cadence': message.cadence,
                'power': message.power,
            }
            for message in records
        ],
        'laps': [
            {
                'messageIndex': message.message_index,
                'timestamp': _timestamp_iso(message.timestamp),
                'startTime': _timestamp_iso(message.start_time),
                'totalElapsedTime': message.total_elapsed_time,
                'totalTimerTime': message.total_timer_time,
            }
            for message in laps
        ],
        'sessions': [
            {
                'messageIndex': message.message_index,
                'timestamp': _timestamp_iso(message.timestamp),
                'startTime': _timestamp_iso(message.start_time),
                'totalElapsedTime': message.total_elapsed_time,
                'totalTimerTime': message.total_timer_time,
                'sport': _enum_name(Sport, message.sport),
                'subSport': _enum_name(SubSport, message.sub_sport),
                'firstLapIndex': message.first_lap_index,
                'numLaps': message.num_laps,
            }
            for message in sessions
        ],
        'activity': {
            'timestamp': _timestamp_iso(activity.timestamp),
            'numSessions': activity.num_sessions,
            'totalTimerTime': activity.total_timer_time,
        },
    }


def _run_garmin_bridge(request):
    result = subprocess.run(
        ['node', str(GARMIN_BRIDGE_PATH)],
        input=json.dumps(request),
        text=True,
        capture_output=True,
        check=True,
        env=os.environ.copy(),
    )
    return json.loads(result.stdout)


class TestGarminSdkInterop(unittest.TestCase):

    def test_decodes_official_javascript_sdk_file_and_profile_version(self):
        fit_file = FitFile.from_bytes(GARMIN_JS_21_205_FILE_ID)
        message = fit_file.records[-1].message

        self.assertEqual('21.205', str(fit_file.header.profile_version))
        self.assertEqual(FileType.ACTIVITY.value, message.type)
        self.assertEqual(1234, message.serial_number)

    def test_builder_declares_the_generated_profile_version(self):
        message = FileIdMessage()
        message.type = FileType.ACTIVITY
        message.manufacturer = Manufacturer.DEVELOPMENT.value
        message.product = 0
        message.serial_number = 1234
        message.time_created = 1_704_067_200_000

        builder = FitFileBuilder()
        builder.add(message)
        fit_file = FitFile.from_bytes(builder.build_bytes())

        self.assertEqual('21.205', str(fit_file.header.profile_version))


@unittest.skipUnless(
    os.environ.get('FIT_JS_SDK_PATH') and shutil.which('node'),
    'FIT_JS_SDK_PATH and Node.js are required for live Garmin SDK interoperability tests.',
)
class TestGarminSdkCrossInterop(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(ACTIVITY_FIXTURE_PATH) as fixture_file:
            cls.fixture = json.load(fixture_file)

        sdk_package_path = Path(os.environ['FIT_JS_SDK_PATH']) / 'package.json'
        with open(sdk_package_path) as package_file:
            cls.sdk_package = json.load(package_file)

    def test_same_activity_cross_decodes_to_identical_semantics(self):
        self.assertEqual(SDK_VERSION, self.sdk_package['version'])

        python_fit = _build_python_activity(self.fixture)
        garmin_result = _run_garmin_bridge({
            'operation': 'generate',
            'fixture': self.fixture,
        })
        garmin_fit = base64.b64decode(garmin_result['fitBase64'])

        garmin_decodes_python = _run_garmin_bridge({
            'operation': 'decode',
            'fitBase64': base64.b64encode(python_fit).decode(),
        })
        garmin_decodes_garmin = _run_garmin_bridge({
            'operation': 'decode',
            'fitBase64': base64.b64encode(garmin_fit).decode(),
        })

        self.assertTrue(garmin_decodes_python['integrity'])
        self.assertTrue(garmin_decodes_garmin['integrity'])
        self.assertEqual(self.fixture, _normalize_python_activity(python_fit))
        self.assertEqual(self.fixture, _normalize_python_activity(garmin_fit))
        self.assertEqual(self.fixture, garmin_decodes_python['messages'])
        self.assertEqual(self.fixture, garmin_decodes_garmin['messages'])
