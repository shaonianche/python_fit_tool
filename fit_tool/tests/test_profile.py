# nosetests --nocapture  tests/test_demo.py


import unittest
from pathlib import Path

from fit_tool import SDK_VERSION
from fit_tool.gen import profile as profile_module
from fit_tool.gen.profile import Profile


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
