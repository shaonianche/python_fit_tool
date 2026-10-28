"""Unified FIT decoder state machine for stream and in-memory paths.

Built on the wire layer. One control loop owns:

- local definition snapshots (via :class:`~fit_tool.wire.decoder.WireDecoder`)
- developer field registry
- CRC accumulation
- compressed-timestamp reconstruction (``last_timestamp``)
- component accumulators across records

:meth:`FitFile.from_bytes` collects records from this machine;
:func:`~fit_tool.fit_file_stream.iter_fit_stream` yields them.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import BinaryIO, Union

from fit_tool.compatibility import project_header, project_raw_record
from fit_tool.developer_field import DeveloperField
from fit_tool.exceptions import FitEncodingError
from fit_tool.fit_file_header import FitFileHeader
from fit_tool.record import Record
from fit_tool.utils.logging import logger
from fit_tool.wire.decoder import ByteSourceInput, WireDecoder
from fit_tool.wire.model import FitDocument, RawFileHeader, RawRecord

Source = Union[bytes, bytearray, memoryview, BinaryIO]


class FitDecoder:
    """Stateful decoder shared by full-load and streaming public APIs.

    Session state lives on the underlying :class:`WireDecoder` and is exposed
    here as read-only properties; only the developer-field registry, the
    retained wire document, and component accumulators are owned by this class.
    """

    def __init__(
            self,
            check_crc: bool = True,
            *,
            allow_trailing_bytes: bool = False,
    ) -> None:
        self.check_crc = check_crc
        self.allow_trailing_bytes = allow_trailing_bytes
        self._wire = WireDecoder(
            check_crc=check_crc,
            allow_trailing_bytes=allow_trailing_bytes,
        )
        self._reset_session()

    def _reset_session(self) -> None:
        self.developer_fields_by_data_index: dict[int, dict[int, DeveloperField]] = {}
        self.wire_document: FitDocument | None = None
        self._accumulators: dict[tuple[int, int], int] = {}

    @property
    def header(self) -> FitFileHeader | None:
        """Projected file header; chained files report the first segment's."""
        document = self.wire_document
        raw_header: RawFileHeader | None
        if document is not None and document.segments:
            raw_header = document.segments[0].header
        else:
            raw_header = self._wire.header
        return project_header(raw_header) if raw_header is not None else None

    @property
    def calculated_crc(self) -> int:
        return self._wire.calculated_crc

    @property
    def stored_crc(self) -> int:
        return self._wire.stored_crc

    @property
    def last_timestamp(self) -> int | None:
        return self._wire.last_timestamp

    def iter_records(self, source: Source) -> Iterator[Record]:
        """Yield projected records from bytes or a binary stream.

        For in-memory buffers, chained multi-segment FIT files yield records
        from every segment. Streaming inputs decode a single segment (the
        stream position ends after the first file CRC).

        CRC is validated when each segment is exhausted. Developer-field
        registration and component expansion run during projection.
        """
        self._reset_session()
        registry = self.developer_fields_by_data_index

        raw_records: Iterator[RawRecord]
        if isinstance(source, (bytes, bytearray, memoryview)):
            document = self._wire.decode(
                bytes(source),
                allow_trailing_bytes=self.allow_trailing_bytes,
            )
            self.wire_document = document
            raw_records = (
                raw for segment in document.segments for raw in segment.records
            )
        else:
            raw_records = self._wire.iter_raw_records(source)

        for raw in raw_records:
            yield project_raw_record(raw, registry, accumulators=self._accumulators)

        self._warn_crc_mismatch()

    def _warn_crc_mismatch(self) -> None:
        if self.check_crc or self.calculated_crc == self.stored_crc:
            return
        logger.warning(
            f'Calculated crc ({hex(self.calculated_crc)}) does not match '
            f'crc in file ({hex(self.stored_crc)}).'
        )

    def decode(self, source: Source) -> tuple[FitFileHeader, list[Record], int]:
        """Decode into header, projected records, and calculated CRC of the last segment."""
        records = list(self.iter_records(source))
        header = self.header
        if header is None:
            raise FitEncodingError('Decoder finished without a FIT header.')
        return header, records, self.calculated_crc

    def decode_document(self, bytes_buffer: bytes) -> FitDocument:
        """Decode a buffer to a wire :class:`~fit_tool.wire.model.FitDocument`."""
        self._reset_session()
        self.wire_document = self._wire.decode(
            bytes_buffer,
            allow_trailing_bytes=self.allow_trailing_bytes,
        )
        return self.wire_document


def iter_fit_records(
        source: Source,
        check_crc: bool = True,
        *,
        allow_trailing_bytes: bool = False,
) -> Iterator[Record]:
    """Yield projected FIT records from bytes or a stream (shared decode path)."""
    yield from FitDecoder(
        check_crc=check_crc,
        allow_trailing_bytes=allow_trailing_bytes,
    ).iter_records(source)


# Re-export for type checkers / callers that need the wire source alias.
__all__ = [
    'ByteSourceInput',
    'FitDecoder',
    'Source',
    'iter_fit_records',
]
