# Taken verbatim from FIT SDK docs
_CRC_TABLE_NIBBLE = (
    0x0000, 0xCC01, 0xD801, 0x1400, 0xF001, 0x3C00, 0x2800, 0xE401,
    0xA001, 0x6C00, 0x7800, 0xB401, 0x5000, 0x9C01, 0x8801, 0x4400,
)


def _generate_crc_table():
    """
    Generates a 256-entry CRC table from the 16-entry nibble table.
    This allows for a faster byte-wise lookup during CRC calculation.
    """
    table = []
    for i in range(256):
        crc = 0
        byte_char = i

        # Process lower nibble
        tmp = _CRC_TABLE_NIBBLE[crc & 0xF]
        crc = (crc >> 4) & 0x0FFF
        crc = crc ^ tmp ^ _CRC_TABLE_NIBBLE[byte_char & 0xF]

        # Process upper nibble
        tmp = _CRC_TABLE_NIBBLE[crc & 0xF]
        crc = (crc >> 4) & 0x0FFF
        crc = crc ^ tmp ^ _CRC_TABLE_NIBBLE[(byte_char >> 4) & 0xF]

        table.append(crc)
    return tuple(table)


CRC_TABLE = _generate_crc_table()


def crc16(buffer, crc=0):
    if not buffer:
        return crc

    for byte in buffer:
        crc = (crc >> 8) ^ CRC_TABLE[(crc ^ byte) & 0xFF]
    return crc
