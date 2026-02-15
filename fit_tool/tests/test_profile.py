# nosetests --nocapture  tests/test_demo.py


import unittest
from pathlib import Path

from fit_tool import SDK_VERSION
from fit_tool.gen import profile as profile_module
from fit_tool.field import ArrayType
from fit_tool.gen.profile import Profile, parse_array_field


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
