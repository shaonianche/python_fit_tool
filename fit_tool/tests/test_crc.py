from fit_tool.utils.crc import crc16


def test_crc16():
    data = b"123456789"
    result = crc16(data)
    assert result == 0xBB3D
