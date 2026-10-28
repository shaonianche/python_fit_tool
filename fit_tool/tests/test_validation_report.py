"""Validation report, level selection, and legacy facade."""

import unittest

from fit_tool.exceptions import FitValidationError
from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.profile_type import FileType, Manufacturer
from fit_tool.tests.validation_helpers import (
    add_minimal_activity_messages,
)
from fit_tool.validation import (
    ConformanceLevel,
    FitFileValidator,
    Severity,
    validate_fit_file,
)


class TestValidationReport(unittest.TestCase):

    def test_validate_fit_file_report_mode_on_fit_file(self):
        builder = FitFileBuilder()
        add_minimal_activity_messages(builder)
        fit_file = builder.build()

        report = validate_fit_file(fit_file)

        self.assertTrue(report)
        self.assertFalse(report.has_errors)
        self.assertEqual(report.findings, [])

    def test_validate_fit_file_raise_mode_matches_strict_builder(self):
        builder = FitFileBuilder()
        file_id = FileIdMessage()
        file_id.type = FileType.ACTIVITY
        file_id.manufacturer = Manufacturer.DEVELOPMENT.value
        file_id.product = 0
        file_id.serial_number = 1234
        file_id.time_created = 1_700_000_000_000
        builder.add(file_id)
        fit_file = builder.build()

        with self.assertRaisesRegex(FitValidationError, 'record'):
            validate_fit_file(fit_file, raise_on_error=True)

        report = fit_file.validate()
        self.assertTrue(report.has_errors)
        self.assertEqual(report.errors[0].level, ConformanceLevel.FILE_TYPE)
        self.assertEqual(report.errors[0].severity, Severity.ERROR)
        self.assertIn('record', report.errors[0].message)

    def test_validate_wire_only_skips_file_type_rules(self):
        builder = FitFileBuilder()
        file_id = FileIdMessage()
        file_id.type = FileType.SETTINGS
        file_id.manufacturer = Manufacturer.DEVELOPMENT.value
        file_id.product = 0
        file_id.serial_number = 1234
        file_id.time_created = 1_700_000_000_000
        builder.add(file_id)
        fit_file = builder.build()

        wire_report = validate_fit_file(fit_file, levels={ConformanceLevel.WIRE})
        self.assertFalse(wire_report.has_errors)

        full_report = fit_file.validate()
        self.assertTrue(full_report.has_errors)
        self.assertTrue(
            any('not implemented' in finding.message for finding in full_report.errors)
        )

    def test_fit_file_validator_legacy_facade(self):
        builder = FitFileBuilder()
        add_minimal_activity_messages(builder)
        FitFileValidator(builder.records).validate()

        incomplete = FitFileBuilder()
        file_id = FileIdMessage()
        file_id.type = FileType.ACTIVITY
        file_id.manufacturer = Manufacturer.DEVELOPMENT.value
        file_id.product = 0
        file_id.serial_number = 1234
        file_id.time_created = 1_700_000_000_000
        incomplete.add(file_id)

        with self.assertRaisesRegex(FitValidationError, 'record'):
            FitFileValidator(incomplete.records).validate()

    def test_public_api_exports_validation_symbols(self):
        from fit_tool import (
            ConformanceLevel as RootLevel,
        )
        from fit_tool import (
            ValidationReport,
        )
        from fit_tool import (
            validate_fit_file as root_validate,
        )

        self.assertIs(RootLevel, ConformanceLevel)
        self.assertIs(root_validate, validate_fit_file)
        self.assertTrue(callable(ValidationReport))

    def test_finding_str_and_report_warnings(self):
        from fit_tool.validation import ValidationFinding, ValidationReport

        finding = ValidationFinding(
            level=ConformanceLevel.WIRE,
            severity=Severity.WARNING,
            message='soft issue',
            record_index=3,
        )
        self.assertIn('record 3', str(finding))
        self.assertIn('wire', str(finding))
        self.assertIn('soft issue', str(finding))

        report = ValidationReport([finding])
        self.assertEqual(len(report.warnings), 1)
        self.assertFalse(report.has_errors)
        self.assertTrue(bool(report))
        report.raise_for_errors()

    def test_normalize_levels_rejects_empty_and_unknown(self):
        with self.assertRaisesRegex(ValueError, 'at least one'):
            validate_fit_file([], levels=set())

        class FakeLevel:
            value = 'preservation'

        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            validate_fit_file([], levels={FakeLevel()})

    def test_legacy_validator_helpers(self):
        builder = FitFileBuilder()
        add_minimal_activity_messages(builder)
        validator = FitFileValidator(builder.records)
        validator._validate_definitions_and_data()
        validator._validate_developer_fields()
        validator._validate_file_type()

        incomplete = FitFileBuilder()
        file_id = FileIdMessage()
        file_id.type = FileType.ACTIVITY
        file_id.manufacturer = Manufacturer.DEVELOPMENT.value
        file_id.product = 0
        file_id.serial_number = 1234
        file_id.time_created = 1_700_000_000_000
        incomplete.add(file_id)
        with self.assertRaises(FitValidationError):
            FitFileValidator(incomplete.records)._validate_file_type()
