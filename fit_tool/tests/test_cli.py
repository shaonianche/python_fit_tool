"""Tests for the command line interface."""

import os
import tempfile
import unittest
from unittest.mock import patch

from fit_tool.cli import main, parse_args


class TestParseArgs(unittest.TestCase):

    def test_parse_args_minimal(self):
        with patch('sys.argv', ['fit-tool', 'test.fit']):
            args = parse_args()
            self.assertEqual(args.fitfile, 'test.fit')
            self.assertFalse(args.verbose)
            self.assertIsNone(args.output)
            self.assertIsNone(args.log)
            self.assertIsNone(args.type)

    def test_parse_args_with_options(self):
        with patch('sys.argv', ['fit-tool', 'test.fit', '-v', '-o', 'out.csv', '-l', 'log.txt', '-t', 'csv']):
            args = parse_args()
            self.assertEqual(args.fitfile, 'test.fit')
            self.assertTrue(args.verbose)
            self.assertEqual(args.output, 'out.csv')
            self.assertEqual(args.log, 'log.txt')
            self.assertEqual(args.type, 'csv')

    def test_parse_args_rejects_unknown_type(self):
        with patch('sys.argv', ['fit-tool', 'test.fit', '-t', 'bad']):
            with self.assertRaises(SystemExit):
                parse_args()


class TestMain(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_fit_file = os.path.join(
            os.path.dirname(__file__),
            'data',
            'sdk',
            'Activity.fit'
        )

    def tearDown(self):
        for f in os.listdir(self.test_dir):
            os.remove(os.path.join(self.test_dir, f))
        os.rmdir(self.test_dir)

    def test_main_convert_to_csv(self):
        output_file = os.path.join(self.test_dir, 'output.csv')
        with patch('sys.argv', ['fit-tool', self.test_fit_file, '-o', output_file]):
            main()
        self.assertTrue(os.path.exists(output_file))

    def test_main_convert_to_fit(self):
        output_file = os.path.join(self.test_dir, 'output.fit')
        with patch('sys.argv', ['fit-tool', self.test_fit_file, '-o', output_file, '-t', 'fit']):
            main()
        self.assertTrue(os.path.exists(output_file))

    def test_main_with_verbose(self):
        output_file = os.path.join(self.test_dir, 'output.csv')
        with patch('sys.argv', ['fit-tool', self.test_fit_file, '-v', '-o', output_file]):
            main()
        self.assertTrue(os.path.exists(output_file))

    def test_main_with_log_file(self):
        output_file = os.path.join(self.test_dir, 'output.csv')
        log_file = os.path.join(self.test_dir, 'test.log')
        with patch('sys.argv', ['fit-tool', self.test_fit_file, '-o', output_file, '-l', log_file]):
            main()
        self.assertTrue(os.path.exists(output_file))
        self.assertTrue(os.path.exists(log_file))

    def test_main_default_output_filename(self):
        original_cwd = os.getcwd()
        try:
            os.chdir(self.test_dir)
            with patch('sys.argv', ['fit-tool', self.test_fit_file]):
                main()
            self.assertTrue(os.path.exists('Activity.csv'))
        finally:
            os.chdir(original_cwd)

    def test_main_infer_format_from_output(self):
        output_file = os.path.join(self.test_dir, 'output.fit')
        with patch('sys.argv', ['fit-tool', self.test_fit_file, '-o', output_file]):
            main()
        self.assertTrue(os.path.exists(output_file))

    def test_main_rejects_unsupported_output_extension(self):
        output_file = os.path.join(self.test_dir, 'output.bad')
        with patch('sys.argv', ['fit-tool', self.test_fit_file, '-o', output_file]):
            with self.assertRaises(ValueError):
                main()


if __name__ == '__main__':
    unittest.main()
