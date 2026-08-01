"""FIT CRC-16 — single algorithm implementation for the package.

**Canonical module.** All other packages should import ``crc16`` / ``CRC_TABLE``
from here (or the thin re-export in :mod:`fit_tool.wire.crc`). Do not
re-implement the FIT CRC polynomial elsewhere.
"""

from __future__ import annotations

CRC_TABLE = (
    0x0000, 0xCC01, 0xD801, 0x1400, 0xF001, 0x3C00, 0x2800, 0xE401,
    0xA001, 0x6C00, 0x7800, 0xB401, 0x5000, 0x9C01, 0x8801, 0x4400,
)


def crc16(buffer, crc=0):
    """CRC-16 as specified by the Garmin FIT SDK (nibble table).

    Used for 14-byte **header** CRC (first 12 header bytes) and the trailing
    **file** CRC (header + records section).
    """
    if not buffer:
        return crc

    for byte in buffer:
        byte_char = byte
        # Taken verbatim from FIT SDK docs
        tmp = CRC_TABLE[crc & 0xF]
        crc = (crc >> 4) & 0x0FFF
        crc = crc ^ tmp ^ CRC_TABLE[byte_char & 0xF]
        # now compute checksum of upper four bits of byte
        tmp = CRC_TABLE[crc & 0xF]
        crc = (crc >> 4) & 0x0FFF
        crc = crc ^ tmp ^ CRC_TABLE[(byte_char >> 4) & 0xF]
    return crc
