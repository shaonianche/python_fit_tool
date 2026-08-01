"""Encode wire models back to bytes (preservation path).

When a :class:`~fit_tool.wire.model.FitDocument` is untouched, each segment is
re-emitted from stored ``source_bytes`` and CRC fields so the output matches the
input byte-for-byte (header, records, file CRC).

Post-edit PRESERVATION mixes per-record ``source_bytes`` for untouched records
with caller-supplied replacement bytes for dirty records
(:func:`encode_segment_mixed` / :func:`encode_document_mixed`).
"""

from __future__ import annotations

import struct
from collections.abc import Sequence

from fit_tool.exceptions import FitEncodingError
from fit_tool.wire.crc import crc16
from fit_tool.wire.model import FitDocument, FitSegment, RawFileHeader


def encode_segment(segment: FitSegment, *, recompute_crc: bool = False) -> bytes:
    """Serialize one segment from preserved source bytes."""
    if not segment.header.source_bytes:
        raise FitEncodingError('Cannot encode segment without header source_bytes.')

    parts = [segment.header.source_bytes]
    for record in segment.records:
        if not record.source_bytes:
            raise FitEncodingError(
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
        raise FitEncodingError('Cannot encode an empty FitDocument.')
    return b''.join(
        encode_segment(segment, recompute_crc=recompute_crc)
        for segment in document.segments
    )


def rewrite_header_source_bytes(header: RawFileHeader, records_size: int) -> bytes:
    """Rebuild header bytes with an updated ``records_size`` (and header CRC).

    Keeps the original header length (12 or 14+). For headers larger than 14
    bytes, intermediate extension bytes between the classic 12-byte prefix and
    the trailing CRC are preserved.
    """
    source = header.source_bytes
    if not source:
        raise FitEncodingError('Cannot rewrite header without source_bytes.')

    header_size = header.header_size
    if len(source) < header_size:
        raise FitEncodingError(
            f'Header source_bytes length {len(source)} < declared size {header_size}.'
        )

    # Classic layout: size(1) + protocol(1) + profile(2) + records_size(4) + .FIT(4) [+ crc(2)]
    prefix = bytearray(source[:header_size])
    prefix[0] = header_size
    prefix[1] = header.protocol_version & 0xFF
    struct.pack_into('<H', prefix, 2, header.profile_version & 0xFFFF)
    struct.pack_into('<I', prefix, 4, records_size & 0xFFFFFFFF)
    prefix[8:12] = b'.FIT'

    if header_size >= 14:
        # Last two bytes = CRC of all preceding header bytes.
        header_crc = crc16(bytes(prefix[: header_size - 2]))
        struct.pack_into('<H', prefix, header_size - 2, header_crc)

    return bytes(prefix)


def encode_segment_mixed(
        segment: FitSegment,
        record_bytes: Sequence[bytes],
        *,
        recompute: bool = False,
) -> bytes:
    """Serialize a segment using per-record byte buffers.

    *record_bytes* must align 1:1 with ``segment.records``. When *recompute* is
    true (any record in the segment was edited), the header ``records_size`` and
    file CRC are recalculated. Untouched segments keep the original header and
    stored file CRC when *recompute* is false.
    """
    if len(record_bytes) != len(segment.records):
        raise FitEncodingError(
            f'Segment has {len(segment.records)} records but {len(record_bytes)} '
            f'replacement buffers were supplied.'
        )

    records_blob = b''.join(record_bytes)

    if recompute:
        header_bytes = rewrite_header_source_bytes(segment.header, len(records_blob))
        body = header_bytes + records_blob
        file_crc = crc16(body)
    else:
        if not segment.header.source_bytes:
            raise FitEncodingError('Cannot encode segment without header source_bytes.')
        body = segment.header.source_bytes + records_blob
        file_crc = segment.stored_crc

    return body + struct.pack('<H', file_crc)


def encode_document_mixed(
        document: FitDocument,
        segment_record_bytes: Sequence[Sequence[bytes]],
        segment_recompute: Sequence[bool],
) -> bytes:
    """Serialize a document with per-segment / per-record replacement bytes."""
    if not document.segments:
        raise FitEncodingError('Cannot encode an empty FitDocument.')
    if len(segment_record_bytes) != len(document.segments):
        raise FitEncodingError(
            f'Document has {len(document.segments)} segments but '
            f'{len(segment_record_bytes)} segment buffers were supplied.'
        )
    if len(segment_recompute) != len(document.segments):
        raise FitEncodingError(
            f'Document has {len(document.segments)} segments but '
            f'{len(segment_recompute)} recompute flags were supplied.'
        )

    parts = []
    for segment, rec_bytes, recompute in zip(
            document.segments,
            segment_record_bytes,
            segment_recompute,
    ):
        parts.append(encode_segment_mixed(segment, rec_bytes, recompute=recompute))
    return b''.join(parts)
