"""Streaming FIT record parser.

Both :func:`iter_fit_stream` and :meth:`~fit_tool.fit_file.FitFile.from_bytes`
delegate to :class:`~fit_tool.decoder.FitDecoder` so stream and in-memory paths
share one decode state machine (definitions, developer registry, CRC,
compressed timestamps, component expansion).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import BinaryIO

from fit_tool.decoder import FitDecoder
from fit_tool.record import Record


def iter_fit_stream(
        file_object: BinaryIO,
        check_crc: bool = True,
        *,
        allow_trailing_bytes: bool = False,
) -> Iterator[Record]:
    """Yield records from a binary FIT stream; CRC validation completes when iteration is exhausted.

    Only the first segment is read from a stream. Use
    :meth:`~fit_tool.fit_file.FitFile.from_bytes` for chained multi-segment files.
    """
    yield from FitDecoder(
        check_crc=check_crc,
        allow_trailing_bytes=allow_trailing_bytes,
    ).iter_records(file_object)


def iter_fit_file(
        path: str,
        check_crc: bool = True,
        *,
        allow_trailing_bytes: bool = False,
) -> Iterator[Record]:
    """Yield records from a FIT file path.

    For chained multi-segment files, prefer :meth:`~fit_tool.fit_file.FitFile.from_file`
    / ``from_bytes`` so every segment is decoded. Streaming opens the path and
    yields only the first segment.
    """
    with open(path, 'rb') as file_object:
        # Load fully so chained segments are handled consistently with from_bytes.
        data = file_object.read()
    yield from FitDecoder(
        check_crc=check_crc,
        allow_trailing_bytes=allow_trailing_bytes,
    ).iter_records(data)
