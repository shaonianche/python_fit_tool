import unittest

from fit_tool.utils.crc import crc16


class TestCRC(unittest.TestCase):
    def test_crc16(self):
        data = b'123456789'
        result = crc16(data)
        self.assertEqual(result, 0xBB3D)
