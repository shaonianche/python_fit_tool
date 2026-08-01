"""CRC helpers for the wire layer.

Thin re-export of :mod:`fit_tool.utils.crc` — the **single** FIT CRC-16
implementation in this package. Prefer importing ``crc16`` from
``fit_tool.utils.crc`` or this module; never copy the table/algorithm.
"""

from __future__ import annotations

from fit_tool.utils.crc import CRC_TABLE, crc16

__all__ = ['CRC_TABLE', 'crc16']
