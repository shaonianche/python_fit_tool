"""Streaming FIT record parser.

Both :func:`iter_fit_stream` and :meth:`~fit_tool.fit_file.FitFile.from_bytes`
delegate to :class:`~fit_tool.decoder.FitDecoder` so stream and in-memory paths
share one decode state machine (definitions, developer registry, CRC).
"""

from __future__ import annotations

from typing import BinaryIO, Iterator

from fit_tool.decoder import FitDecoder
from fit_tool.record import Record


def iter_fit_stream(file_object: BinaryIO, check_crc: bool = True) -> Iterator[Record]:
    """Yield records from a binary FIT stream; CRC validation completes when iteration is exhausted."""
    yield from FitDecoder(check_crc=check_crc).iter_records(file_object)


def iter_fit_file(path: str, check_crc: bool = True) -> Iterator[Record]:
    """Yield records from a FIT file without loading the complete file into memory."""
    with open(path, 'rb') as file_object:
        yield from iter_fit_stream(file_object, check_crc=check_crc)
