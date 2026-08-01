"""Encode wire models back to bytes (preservation path).

When a :class:`~fit_tool.wire.model.FitDocument` is untouched, each segment is
re-emitted from stored ``source_bytes`` and CRC fields so the output matches the
input byte-for-byte (header, records, file CRC).
"""

from __future__ import annotations

import struct

from fit_tool.wire.crc import crc16
from fit_tool.wire.model import FitDocument, FitSegment


def encode_segment(segment: FitSegment, *, recompute_crc: bool = False) -> bytes:
    """Serialize one segment from preserved source bytes."""
    if not segment.header.source_bytes:
        raise ValueError('Cannot encode segment without header source_bytes.')

    parts = [segment.header.source_bytes]
    for record in segment.records:
        if not record.source_bytes:
            raise ValueError(
                f'Cannot encode record at offset {record.source_offset} without source_bytes.'
            )
        parts.append(record.source_bytes)

    body = b''.join(parts)
    if recompute_crc:
        file_crc = crc16(body)
    else:
        file_crc = segment.stored_crc
    return body + struct.pack('<H', file_crc)


def encode_document(document: FitDocument, *, recompute_crc: bool = False) -> bytes:
    """Serialize all segments of a wire document (chained FIT)."""
    if not document.segments:
        raise ValueError('Cannot encode an empty FitDocument.')
    return b''.join(
        encode_segment(segment, recompute_crc=recompute_crc)
        for segment in document.segments
    )
