"""Compressed-timestamp helpers (FIT protocol 5-bit offset / 32 s rollover)."""

from __future__ import annotations

from fit_tool.exceptions import FitRecordError

TIME_OFFSET_MASK = 0x1F
TIME_OFFSET_ROLLOVER = 0x20


def apply_compressed_time_offset(previous_timestamp: int, time_offset: int) -> int:
    """Return the absolute FIT datetime from a prior timestamp and 5-bit offset.

    ``previous_timestamp`` and the result are FIT ``date_time`` values (seconds
    since 1989-12-31 00:00:00 UTC). ``time_offset`` is in ``[0, 31]``.
    """
    if not 0 <= time_offset <= TIME_OFFSET_MASK:
        raise FitRecordError(f'time_offset must be 0..{TIME_OFFSET_MASK}, got {time_offset!r}')

    base = previous_timestamp & ~TIME_OFFSET_MASK
    if time_offset >= (previous_timestamp & TIME_OFFSET_MASK):
        return base + time_offset
    return base + time_offset + TIME_OFFSET_ROLLOVER
