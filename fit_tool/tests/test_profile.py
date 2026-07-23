# nosetests --nocapture  tests/test_demo.py


import sys
import unittest
from pathlib import Path

from fit_tool import SDK_VERSION
from fit_tool.field import ArrayType
from fit_tool.gen import profile as profile_module
from fit_tool.gen.profile import Profile, parse_array_field, parse_profile_number
from fit_tool.profile.messages.lap_message import LapMessage
from fit_tool.profile.messages.record_message import RecordMessage


class TestFitFile(unittest.TestCase):

    def test_profile(self):
        gen_dir = Path(profile_module.__file__).resolve().parent
        expected = gen_dir / f'Profile_{SDK_VERSION}.xlsx'
        self.assertTrue(
            expected.exists(),
            f'Expected profile file not found: {expected}'
        )

        profile = Profile.get_default_profile()

        for type_name in profile.types_by_name:
            profile_type = profile.types_by_name[type_name]
            print(f'{type_name}', profile_type)


class TestParseArrayField(unittest.TestCase):

    def test_empty_values_are_not_arrays(self):
        self.assertEqual((None, None), parse_array_field(None))
        self.assertEqual((None, None), parse_array_field(''))
        self.assertEqual((None, None), parse_array_field('   '))

    def test_parses_variable_array(self):
        self.assertEqual((ArrayType.VARIABLE, None), parse_array_field('[N]'))

    def test_parses_fixed_array(self):
        self.assertEqual((ArrayType.FIXED, 3), parse_array_field('[3]'))
        self.assertEqual((ArrayType.FIXED, 12), parse_array_field(' [12] '))

    def test_rejects_invalid_array_formats(self):
        invalid_values = ('[]', '[ ]', '[abc]', 'abc', 'N', '[3a]')
        for value in invalid_values:
            with self.assertRaisesRegex(ValueError, 'Invalid array field value'):
                parse_array_field(value)


class TestProfileTypes(unittest.TestCase):

    def test_get_type_by_name_raises_key_error_for_missing_type(self):
        profile = Profile()
        with self.assertRaises(KeyError):
            profile.get_type_by_name('missing_type')

    def test_generated_fields_preserve_numeric_profile_scales(self):
        self.assertEqual(100, RecordMessage().get_field(5).scale)
        self.assertEqual(1000, LapMessage().get_field(7).scale)


class TestParseProfileNumber(unittest.TestCase):

    def test_parses_numeric_strings_without_discarding_scale(self):
        self.assertEqual(100, parse_profile_number('100', 1))
        self.assertEqual(0.7111111, parse_profile_number('0.7111111', 1))
        self.assertEqual(-110, parse_profile_number('-110', 0))

    def test_uses_default_for_blank_cells(self):
        self.assertEqual(1, parse_profile_number(None, 1))
        self.assertEqual(0, parse_profile_number(' ', 0))

    def test_rejects_component_lists(self):
        with self.assertRaises(ValueError):
            parse_profile_number('100,16', 1)


class TestMessageFactory(unittest.TestCase):

    def test_message_modules_are_imported_lazily(self):
        from fit_tool.profile.messages import message_factory

        module_name = 'fit_tool.profile.messages.lap_message'
        sys.modules.pop(module_name, None)
        message_factory._get_message_class.cache_clear()

        self.assertNotIn(module_name, sys.modules)
        message_class = message_factory._get_message_class(19)
        self.assertEqual('LapMessage', message_class.__name__)
        self.assertIn(module_name, sys.modules)
