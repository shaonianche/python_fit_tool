"""PROFILE scope selection (CORE / DOMAIN / FULL) and catalog-backed rules."""

from __future__ import annotations

import unittest
from pathlib import Path

from fit_tool.base_type import BaseType
from fit_tool.definition_message import DefinitionMessage
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
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.messages.lap_message import LapMessage
from fit_tool.profile.messages.record_message import RecordMessage
from fit_tool.profile.messages.session_message import SessionMessage
from fit_tool.profile.profile_type import FileType, Manufacturer, Sport
from fit_tool.record import Record
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
    file_id = FileIdMessage()
    file_id.type = FileType.ACTIVITY
    file_id.manufacturer = Manufacturer.DEVELOPMENT.value
    file_id.product = 0
    file_id.serial_number = 1234
    file_id.time_created = 1_700_000_000_000
    builder.add(file_id)

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
    return builder


class TestProfileCatalog(unittest.TestCase):
    def test_catalog_matches_sdk_version_and_counts(self):
        from fit_tool import SDK_VERSION

        self.assertEqual(PROFILE_SDK_VERSION, SDK_VERSION)
        self.assertEqual(PROFILE_MESSAGE_COUNT, 123)
        self.assertEqual(PROFILE_FIELD_COUNT, 1406)
        self.assertEqual(PROFILE_ENUM_TYPE_COUNT, 100)
        self.assertEqual(PROFILE_ENUM_FIELD_COUNT, 153)
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


if __name__ == '__main__':
    unittest.main()
