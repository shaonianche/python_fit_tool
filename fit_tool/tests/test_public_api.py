"""Tests for the stable package-level public API."""

from __future__ import annotations

import unittest


class TestPublicApi(unittest.TestCase):
    def test_core_symbols_importable_from_package_root(self) -> None:
        from fit_tool import (  # noqa: PLC0415
            FIT_DATA_TYPE,
            PROTOCOL_VERSION,
            SDK_VERSION,
            ConformanceLevel,
            FitCRCError,
            FitEncodingError,
            FitError,
            FitFile,
            FitFileBuilder,
            FitHeaderError,
            FitParseError,
            FitRecordError,
            FitValidationError,
            Severity,
            ValidationFinding,
            ValidationReport,
            validate_fit_file,
        )

        self.assertEqual(SDK_VERSION, '21.205.0')
        self.assertEqual(PROTOCOL_VERSION, '2.4')
        self.assertEqual(FIT_DATA_TYPE, b'.FIT')
        self.assertTrue(issubclass(FitCRCError, FitParseError))
        self.assertTrue(issubclass(FitParseError, FitError))
        self.assertTrue(issubclass(FitValidationError, FitEncodingError))
        self.assertTrue(issubclass(FitEncodingError, FitError))
        self.assertTrue(issubclass(FitHeaderError, FitParseError))
        self.assertTrue(issubclass(FitRecordError, FitParseError))
        self.assertTrue(callable(FitFile.from_file))
        self.assertTrue(callable(FitFileBuilder))
        self.assertTrue(callable(validate_fit_file))
        self.assertTrue(callable(FitFile.validate))
        self.assertEqual(ConformanceLevel.WIRE.value, 'wire')
        self.assertEqual(Severity.ERROR.value, 'error')
        self.assertTrue(issubclass(ValidationFinding, object))
        self.assertTrue(callable(ValidationReport))

    def test_package_all_matches_api_surface(self) -> None:
        import fit_tool
        from fit_tool import api

        for name in api.__all__:
            self.assertIn(name, fit_tool.__all__)
            self.assertIs(getattr(fit_tool, name), getattr(api, name))

        for name in ('PROTOCOL_VERSION', 'SDK_VERSION', 'FIT_DATA_TYPE'):
            self.assertIn(name, fit_tool.__all__)
            self.assertTrue(hasattr(fit_tool, name))

    def test_deep_imports_remain_supported(self) -> None:
        from fit_tool import FitCRCError, FitFile, FitFileBuilder
        from fit_tool.exceptions import FitCRCError as DeepFitCRCError
        from fit_tool.fit_file import FitFile as DeepFitFile
        from fit_tool.fit_file_builder import FitFileBuilder as DeepFitFileBuilder

        self.assertIs(FitFile, DeepFitFile)
        self.assertIs(FitFileBuilder, DeepFitFileBuilder)
        self.assertIs(FitCRCError, DeepFitCRCError)

    def test_message_import_convention(self) -> None:
        from fit_tool.profile.messages.file_id_message import FileIdMessage
        from fit_tool.profile.messages.record_message import RecordMessage
        from fit_tool.profile.profile_type import FileType, Sport

        self.assertEqual(FileIdMessage.__name__, 'FileIdMessage')
        self.assertEqual(RecordMessage.__name__, 'RecordMessage')
        self.assertIsNotNone(FileType)
        self.assertIsNotNone(Sport)
