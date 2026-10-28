"""PROFILE-level validation: developer fields, catalog rules, and scopes."""

import unittest
from pathlib import Path

from fit_tool.base_type import BaseType
from fit_tool.definition_message import DefinitionMessage
from fit_tool.developer_field import DeveloperField
from fit_tool.exceptions import FitValidationError
from fit_tool.field_definition import FieldDefinition
from fit_tool.fit_file import FitFile
from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.profile.field_catalog import (
    PROFILE_ENUM_FIELD_COUNT,
    PROFILE_ENUM_TYPE_COUNT,
    PROFILE_FIELD_COUNT,
    PROFILE_FIELDS,
    PROFILE_MESSAGE_COUNT,
    PROFILE_SDK_VERSION,
)
from fit_tool.profile.messages.activity_message import ActivityMessage
from fit_tool.profile.messages.developer_data_id_message import DeveloperDataIdMessage
from fit_tool.profile.messages.field_description_message import FieldDescriptionMessage
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.messages.lap_message import LapMessage
from fit_tool.profile.messages.record_message import RecordMessage
from fit_tool.profile.messages.session_message import SessionMessage
from fit_tool.profile.profile_type import FileType, Manufacturer, Sport
from fit_tool.record import Record
from fit_tool.tests.validation_helpers import add_minimal_activity_messages
from fit_tool.validation import (
    DEFAULT_PROFILE_SCOPE,
    DOMAIN_MESSAGE_IDS,
    ConformanceLevel,
    ProfileScope,
    profile_rule_coverage,
    validate_fit_file,
)

DATA_DIR = Path(__file__).resolve().parent / 'data'
SDK_DIR = DATA_DIR / 'sdk'


def _minimal_activity_builder() -> FitFileBuilder:
    builder = FitFileBuilder()
    add_minimal_activity_messages(builder)
    return builder


class TestValidationProfile(unittest.TestCase):

    def test_strict_validation_rejects_undeclared_developer_field(self):
        developer_field = DeveloperField(
            developer_data_index=0,
            field_id=1,
            base_type=BaseType.SINT8,
            size=1,
        )
        developer_field.set_value(0, 5)
        record = RecordMessage(developer_fields=[developer_field])

        builder = FitFileBuilder(strict=True)
        add_minimal_activity_messages(builder, record_message=record)

        with self.assertRaisesRegex(FitValidationError, 'field_description'):
            builder.build_bytes()

    def test_strict_validation_accepts_declared_developer_field(self):
        builder = FitFileBuilder(strict=True)

        file_id = FileIdMessage()
        file_id.type = FileType.ACTIVITY
        file_id.manufacturer = Manufacturer.DEVELOPMENT.value
        file_id.product = 0
        file_id.serial_number = 1234
        file_id.time_created = 1_700_000_000_000
        builder.add(file_id)

        developer_data_id = DeveloperDataIdMessage()
        developer_data_id.developer_data_index = 0
        developer_data_id.application_id = bytes(range(16))
        builder.add(developer_data_id)

        field_description = FieldDescriptionMessage()
        field_description.developer_data_index = 0
        field_description.field_definition_number = 1
        field_description.fit_base_type_id = BaseType.SINT8
        builder.add(field_description)

        developer_field = DeveloperField(
            developer_data_index=0,
            field_id=1,
            base_type=BaseType.SINT8,
            size=1,
        )
        developer_field.set_value(0, 5)
        record = RecordMessage(developer_fields=[developer_field])
        record.timestamp = 1_700_000_000_000
        builder.add(record)

        lap = LapMessage()
        lap.message_index = 0
        lap.timestamp = 1_700_000_001_000
        lap.start_time = 1_700_000_000_000
        lap.total_elapsed_time = 1
        lap.total_timer_time = 1
        builder.add(lap)
        session = SessionMessage()
        session.message_index = 0
        session.timestamp = 1_700_000_001_000
        session.start_time = 1_700_000_000_000
        session.total_elapsed_time = 1
        session.total_timer_time = 1
        session.sport = Sport.CYCLING
        session.first_lap_index = 0
        session.num_laps = 1
        builder.add(session)
        activity = ActivityMessage()
        activity.timestamp = 1_700_000_001_000
        activity.num_sessions = 1
        activity.total_timer_time = 1
        builder.add(activity)

        self.assertGreater(len(builder.build_bytes()), 0)

    def test_profile_developer_field_edge_cases(self):
        from fit_tool.fit_file_builder import FitFileBuilder
        from fit_tool.profile.messages.activity_message import ActivityMessage
        from fit_tool.profile.messages.developer_data_id_message import DeveloperDataIdMessage
        from fit_tool.profile.messages.field_description_message import FieldDescriptionMessage
        from fit_tool.profile.messages.file_id_message import FileIdMessage
        from fit_tool.profile.messages.lap_message import LapMessage
        from fit_tool.profile.messages.record_message import RecordMessage
        from fit_tool.profile.messages.session_message import SessionMessage
        from fit_tool.profile.profile_type import Sport

        def build_with_messages(*extra_before_record, record=None):
            builder = FitFileBuilder()
            file_id = FileIdMessage()
            file_id.type = FileType.ACTIVITY
            file_id.manufacturer = Manufacturer.DEVELOPMENT.value
            file_id.product = 0
            file_id.serial_number = 1234
            file_id.time_created = 1_700_000_000_000
            builder.add(file_id)
            for message in extra_before_record:
                builder.add(message)
            if record is None:
                record = RecordMessage()
                record.timestamp = 1_700_000_000_000
            builder.add(record)
            lap = LapMessage()
            lap.message_index = 0
            lap.timestamp = 1_700_000_001_000
            lap.start_time = 1_700_000_000_000
            lap.total_elapsed_time = 1
            lap.total_timer_time = 1
            builder.add(lap)
            session = SessionMessage()
            session.message_index = 0
            session.timestamp = 1_700_000_001_000
            session.start_time = 1_700_000_000_000
            session.total_elapsed_time = 1
            session.total_timer_time = 1
            session.sport = Sport.CYCLING
            session.first_lap_index = 0
            session.num_laps = 1
            builder.add(session)
            activity = ActivityMessage()
            activity.timestamp = 1_700_000_001_000
            activity.num_sessions = 1
            activity.total_timer_time = 1
            builder.add(activity)
            return builder.build()

        # Missing developer_data_index on developer_data_id
        dev_id = DeveloperDataIdMessage()
        # leave developer_data_index unset
        fit = build_with_messages(dev_id)
        report = validate_fit_file(fit, levels={ConformanceLevel.PROFILE})
        self.assertTrue(any('missing developer_data_index' in f.message for f in report.errors))

        # Bad application_id length
        dev_id2 = DeveloperDataIdMessage()
        dev_id2.developer_data_index = 0
        dev_id2.application_id = bytes(range(8))  # not 16
        fit2 = build_with_messages(dev_id2)
        report2 = validate_fit_file(fit2, levels={ConformanceLevel.PROFILE})
        self.assertTrue(any('16 bytes' in f.message for f in report2.errors))

        # Duplicate developer_data_id
        d1 = DeveloperDataIdMessage()
        d1.developer_data_index = 0
        d1.application_id = bytes(range(16))
        d2 = DeveloperDataIdMessage()
        d2.developer_data_index = 0
        d2.application_id = bytes(range(16))
        fit3 = build_with_messages(d1, d2)
        report3 = validate_fit_file(fit3, levels={ConformanceLevel.PROFILE})
        self.assertTrue(any('Duplicate developer_data_id' in f.message for f in report3.errors))

        # field_description before developer_data_id
        fd = FieldDescriptionMessage()
        fd.developer_data_index = 0
        fd.field_definition_number = 1
        fd.fit_base_type_id = BaseType.SINT8
        fit4 = build_with_messages(fd)
        report4 = validate_fit_file(fit4, levels={ConformanceLevel.PROFILE})
        self.assertTrue(any('before its developer_data_id' in f.message for f in report4.errors))

        # field_description missing field_definition_number
        d_ok = DeveloperDataIdMessage()
        d_ok.developer_data_index = 0
        d_ok.application_id = bytes(range(16))
        fd_missing = FieldDescriptionMessage()
        fd_missing.developer_data_index = 0
        # field_definition_number and fit_base_type_id left unset
        fit5 = build_with_messages(d_ok, fd_missing)
        report5 = validate_fit_file(fit5, levels={ConformanceLevel.PROFILE})
        self.assertTrue(
            any('field_definition_number and fit_base_type_id' in f.message for f in report5.errors)
        )

        # Unknown fit_base_type_id
        fd_bad_type = FieldDescriptionMessage()
        fd_bad_type.developer_data_index = 0
        fd_bad_type.field_definition_number = 1
        fd_bad_type.fit_base_type_id = 250  # not a BaseType
        fit6 = build_with_messages(d_ok, fd_bad_type)
        report6 = validate_fit_file(fit6, levels={ConformanceLevel.PROFILE})
        self.assertTrue(any('unknown fit_base_type_id' in f.message for f in report6.errors))

        # Duplicate field_description
        fd_a = FieldDescriptionMessage()
        fd_a.developer_data_index = 0
        fd_a.field_definition_number = 1
        fd_a.fit_base_type_id = BaseType.SINT8
        fd_b = FieldDescriptionMessage()
        fd_b.developer_data_index = 0
        fd_b.field_definition_number = 1
        fd_b.fit_base_type_id = BaseType.SINT8
        fit7 = build_with_messages(d_ok, fd_a, fd_b)
        report7 = validate_fit_file(fit7, levels={ConformanceLevel.PROFILE})
        self.assertTrue(any('Duplicate field_description' in f.message for f in report7.errors))

        # Base type mismatch vs field_description
        fd_u8 = FieldDescriptionMessage()
        fd_u8.developer_data_index = 0
        fd_u8.field_definition_number = 1
        fd_u8.fit_base_type_id = BaseType.UINT8
        dev_field = DeveloperField(
            developer_data_index=0,
            field_id=1,
            base_type=BaseType.SINT8,
            size=1,
        )
        dev_field.set_value(0, 5)
        record = RecordMessage(developer_fields=[dev_field])
        record.timestamp = 1_700_000_000_000
        fit8 = build_with_messages(d_ok, fd_u8, record=record)
        report8 = validate_fit_file(fit8, levels={ConformanceLevel.PROFILE})
        self.assertTrue(any('uses SINT8' in f.message for f in report8.errors))

    def test_profile_skips_invalid_developer_fields(self):
        from fit_tool.profile.messages.file_id_message import FileIdMessage
        from fit_tool.profile.messages.record_message import RecordMessage
        from fit_tool.record import Record

        invalid_dev = DeveloperField(
            developer_data_index=0,
            field_id=1,
            base_type=BaseType.SINT8,
            size=0,
        )
        record = RecordMessage(developer_fields=[invalid_dev])
        record.timestamp = 1_700_000_000_000
        file_id = FileIdMessage()
        file_id.type = FileType.ACTIVITY
        file_id.manufacturer = Manufacturer.DEVELOPMENT.value
        file_id.product = 0
        file_id.serial_number = 1
        file_id.time_created = 1_700_000_000_000
        report = validate_fit_file(
            [Record.from_message(file_id), Record.from_message(record)],
            levels={ConformanceLevel.PROFILE},
        )
        # size 0 field is skipped (is_valid False), so no undeclared-field error
        self.assertFalse(any('used before' in f.message for f in report.errors))


class TestProfileCatalog(unittest.TestCase):
    def test_catalog_matches_sdk_version_and_counts(self):
        from fit_tool import SDK_VERSION

        self.assertEqual(PROFILE_SDK_VERSION, SDK_VERSION)
        self.assertEqual(PROFILE_MESSAGE_COUNT, 124)
        self.assertEqual(PROFILE_FIELD_COUNT, 1566)
        self.assertEqual(PROFILE_ENUM_TYPE_COUNT, 115)
        self.assertEqual(PROFILE_ENUM_FIELD_COUNT, 164)
        self.assertEqual(len(PROFILE_FIELDS), PROFILE_FIELD_COUNT)

    def test_file_id_type_in_catalog(self):
        entry = PROFILE_FIELDS[(0, 0)]
        name, base_type, type_name, _units, _scale, _offset = entry
        self.assertEqual(name, 'type')
        self.assertEqual(base_type, BaseType.ENUM)
        self.assertEqual(type_name, 'file')


class TestProfileRuleCoverage(unittest.TestCase):
    def test_default_scope_is_core(self):
        self.assertIs(DEFAULT_PROFILE_SCOPE, ProfileScope.CORE)
        core = profile_rule_coverage()
        self.assertEqual(core['scope'], 'core')
        self.assertTrue(core['default_for_strict'])
        self.assertEqual(core['native_fields_in_scope'], 0)
        self.assertEqual(core['field_coverage_pct'], 0.0)
        self.assertIn('developer_fields', core['rule_families'])
        self.assertNotIn('native_base_type', core['rule_families'])

    def test_domain_and_full_coverage(self):
        domain = profile_rule_coverage(ProfileScope.DOMAIN)
        full = profile_rule_coverage(ProfileScope.FULL)

        self.assertEqual(domain['scope'], 'domain')
        self.assertFalse(domain['default_for_strict'])
        self.assertEqual(domain['native_messages_in_scope'], len(DOMAIN_MESSAGE_IDS))
        self.assertGreater(domain['native_fields_in_scope'], 0)
        self.assertLess(domain['field_coverage_pct'], 100.0)
        self.assertIn('native_base_type', domain['rule_families'])
        self.assertIn('closed_enum_values', domain['rule_families'])

        self.assertEqual(full['scope'], 'full')
        self.assertFalse(full['default_for_strict'])
        self.assertEqual(full['native_messages_in_scope'], PROFILE_MESSAGE_COUNT)
        self.assertEqual(full['native_fields_in_scope'], PROFILE_FIELD_COUNT)
        self.assertEqual(full['field_coverage_pct'], 100.0)
        self.assertEqual(full['message_coverage_pct'], 100.0)
        self.assertEqual(full['enum_fields_in_scope'], PROFILE_ENUM_FIELD_COUNT)
        self.assertEqual(full['enum_field_coverage_pct'], 100.0)


class TestProfileScopeValidation(unittest.TestCase):
    def test_core_is_default_and_skips_native_base_type(self):
        # Definition with wrong base type for record.heart_rate (field 3 is UINT8).
        definition = DefinitionMessage(
            local_id=0,
            global_id=20,
            field_definitions=[
                FieldDefinition(field_id=253, size=4, base_type=BaseType.UINT32),
                FieldDefinition(field_id=3, size=2, base_type=BaseType.UINT16),
            ],
        )
        records = [Record.from_message(definition)]

        core = validate_fit_file(records, levels={ConformanceLevel.PROFILE})
        self.assertFalse(core.has_errors)

        domain = validate_fit_file(
            records,
            levels={ConformanceLevel.PROFILE},
            profile_scope=ProfileScope.DOMAIN,
        )
        self.assertTrue(domain.has_errors)
        self.assertTrue(
            any('base type' in finding.message and 'UINT16' in finding.message
                for finding in domain.errors)
        )

    def test_domain_accepts_matching_base_types(self):
        definition = DefinitionMessage(
            local_id=0,
            global_id=20,
            field_definitions=[
                FieldDefinition(field_id=253, size=4, base_type=BaseType.UINT32),
                FieldDefinition(field_id=3, size=1, base_type=BaseType.UINT8),
            ],
        )
        report = validate_fit_file(
            [Record.from_message(definition)],
            levels={ConformanceLevel.PROFILE},
            profile_scope=ProfileScope.DOMAIN,
        )
        self.assertFalse(report.has_errors)

    def test_closed_enum_rejects_unknown_value(self):
        file_id = FileIdMessage()
        file_id.type = 250  # not a Profile file enum value
        file_id.manufacturer = Manufacturer.DEVELOPMENT.value
        file_id.product = 0
        file_id.serial_number = 1
        file_id.time_created = 1_700_000_000_000

        core = validate_fit_file(
            [Record.from_message(file_id)],
            levels={ConformanceLevel.PROFILE},
        )
        self.assertFalse(core.has_errors)

        domain = validate_fit_file(
            [Record.from_message(file_id)],
            levels={ConformanceLevel.PROFILE},
            profile_scope=ProfileScope.DOMAIN,
        )
        self.assertTrue(domain.has_errors)
        self.assertTrue(
            any('outside Profile enum' in finding.message for finding in domain.errors)
        )

    def test_closed_enum_accepts_valid_value(self):
        file_id = FileIdMessage()
        file_id.type = FileType.ACTIVITY
        file_id.manufacturer = Manufacturer.DEVELOPMENT.value
        file_id.product = 0
        file_id.serial_number = 1
        file_id.time_created = 1_700_000_000_000

        report = validate_fit_file(
            [Record.from_message(file_id)],
            levels={ConformanceLevel.PROFILE},
            profile_scope=ProfileScope.DOMAIN,
        )
        self.assertFalse(report.has_errors)

    def test_full_scope_covers_non_domain_message(self):
        # course is not in DOMAIN_MESSAGE_IDS; base-type mismatch only fires under FULL.
        course_global_id = 31
        self.assertNotIn(course_global_id, DOMAIN_MESSAGE_IDS)
        # course.sport is field 4, Profile base type ENUM.
        definition = DefinitionMessage(
            local_id=0,
            global_id=course_global_id,
            field_definitions=[
                FieldDefinition(field_id=4, size=1, base_type=BaseType.UINT8),  # wrong: Profile is ENUM
            ],
        )
        records = [Record.from_message(definition)]

        domain = validate_fit_file(
            records,
            levels={ConformanceLevel.PROFILE},
            profile_scope=ProfileScope.DOMAIN,
        )
        self.assertFalse(domain.has_errors)

        full = validate_fit_file(
            records,
            levels={ConformanceLevel.PROFILE},
            profile_scope=ProfileScope.FULL,
        )
        self.assertTrue(full.has_errors)
        self.assertTrue(any('base type' in f.message for f in full.errors))

    def test_minimal_activity_passes_domain_and_full(self):
        fit_file = _minimal_activity_builder().build()
        for scope in (ProfileScope.CORE, ProfileScope.DOMAIN, ProfileScope.FULL):
            report = validate_fit_file(
                fit_file,
                levels={ConformanceLevel.PROFILE},
                profile_scope=scope,
            )
            self.assertFalse(report.has_errors, msg=f'scope={scope}: {report.findings}')

    def test_sdk_activity_passes_full_profile_scope(self):
        path = SDK_DIR / 'Activity.fit'
        if not path.is_file():
            self.skipTest('SDK Activity.fit fixture missing')
        fit_file = FitFile.from_file(str(path))
        report = validate_fit_file(
            fit_file,
            levels={ConformanceLevel.PROFILE},
            profile_scope=ProfileScope.FULL,
        )
        self.assertFalse(report.has_errors, msg=report.findings)

    def test_fit_file_validate_forwards_profile_scope(self):
        fit_file = _minimal_activity_builder().build()
        report = fit_file.validate(
            levels={ConformanceLevel.PROFILE},
            profile_scope=ProfileScope.DOMAIN,
        )
        self.assertFalse(report.has_errors)

    def test_invalid_profile_scope_type_raises(self):
        with self.assertRaisesRegex(Exception, 'ProfileScope'):
            validate_fit_file(
                [],
                levels={ConformanceLevel.PROFILE},
                profile_scope='full',  # type: ignore[arg-type]
            )

    def test_public_exports(self):
        from fit_tool import ProfileScope as RootScope
        from fit_tool import profile_rule_coverage as root_coverage

        self.assertIs(RootScope, ProfileScope)
        self.assertIs(root_coverage, profile_rule_coverage)
        self.assertEqual(RootScope.FULL.value, 'full')
