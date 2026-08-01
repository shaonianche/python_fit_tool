"""CRC helpers for the wire layer.

Reuses the FIT CRC-16 implementation from :mod:`fit_tool.utils.crc` so the
wire package does not duplicate the table or algorithm.
"""

from __future__ import annotations

from fit_tool.utils.crc import CRC_TABLE, crc16

__all__ = ['CRC_TABLE', 'crc16']
