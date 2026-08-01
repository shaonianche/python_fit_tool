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

from fit_tool.compatibility import (
    project_data_record,
    project_definition_record,
    project_header,
    register_developer_field,
)
from fit_tool.developer_field import DeveloperField
from fit_tool.exceptions import FitEncodingError
from fit_tool.fit_file_header import FitFileHeader
from fit_tool.record import Record
from fit_tool.utils.logging import logger
from fit_tool.wire.decoder import ByteSourceInput, WireDecoder
from fit_tool.wire.model import FitDocument, RawDataRecord, RawDefinitionRecord, RawRecord

Source = Union[bytes, bytearray, memoryview, BinaryIO]


class FitDecoder:
    """Stateful decoder shared by full-load and streaming public APIs.

    After :meth:`iter_records` / :meth:`decode` / :meth:`decode_document`
    completes, session fields are available: :attr:`header`,
    :attr:`calculated_crc`, :attr:`stored_crc`, :attr:`last_timestamp`,
    :attr:`developer_fields_by_data_index`, and :attr:`wire_document` (buffer path).
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
        self.header: FitFileHeader | None = None
        self.calculated_crc: int = 0
        self.stored_crc: int = 0
        self.last_timestamp: int | None = None
        self.developer_fields_by_data_index: dict[int, dict[int, DeveloperField]] = {}
        self.wire_document: FitDocument | None = None
        self._accumulators: dict[tuple[int, int], int] = {}

    def iter_records(self, source: Source) -> Iterator[Record]:
        """Yield projected records from bytes or a binary stream.

        For in-memory buffers, chained multi-segment FIT files yield records
        from every segment. Streaming inputs decode a single segment (the
        stream position ends after the first file CRC).

        CRC is validated when each segment is exhausted. Developer-field
        registration and component expansion run during projection.
        """
        self._reset_session()
        developer_registry = self.developer_fields_by_data_index

        if isinstance(source, (bytes, bytearray, memoryview)):
            document = self._wire.decode(
                bytes(source),
                allow_trailing_bytes=self.allow_trailing_bytes,
            )
            self.wire_document = document
            for segment in document.segments:
                if self.header is None:
                    self.header = project_header(segment.header)
                self.calculated_crc = segment.calculated_crc
                self.stored_crc = segment.stored_crc
                for raw in segment.records:
                    record = self._project_raw(raw, developer_registry)
                    register_developer_field(record, developer_registry)
                    yield record
            self.last_timestamp = self._wire.last_timestamp
            if (
                self.calculated_crc != self.stored_crc
                and not self.check_crc
                and document.segments
            ):
                logger.warning(
                    f'Calculated crc ({hex(self.calculated_crc)}) does not match '
                    f'crc in file ({hex(self.stored_crc)}).'
                )
            return

        for raw in self._wire.iter_raw_records(source):
            record = self._project_raw(raw, developer_registry)
            register_developer_field(record, developer_registry)
            self.last_timestamp = self._wire.last_timestamp
            yield record

        assert self._wire.header is not None
        self.header = project_header(self._wire.header)
        self.calculated_crc = self._wire.calculated_crc
        self.stored_crc = self._wire.stored_crc
        self.last_timestamp = self._wire.last_timestamp
        # Stream path does not retain raw records for preservation encode.
        self.wire_document = None

        if self.calculated_crc != self.stored_crc and not self.check_crc:
            logger.warning(
                f'Calculated crc ({hex(self.calculated_crc)}) does not match '
                f'crc in file ({hex(self.stored_crc)}).'
            )

    def decode(self, source: Source) -> tuple[FitFileHeader, list[Record], int]:
        """Decode into header, projected records, and calculated CRC of the last segment."""
        records = list(self.iter_records(source))
        if self.header is None:
            raise FitEncodingError('Decoder finished without a FIT header.')
        return self.header, records, self.calculated_crc

    def decode_document(self, bytes_buffer: bytes) -> FitDocument:
        """Decode a buffer to a wire :class:`~fit_tool.wire.model.FitDocument`."""
        self._reset_session()
        document = self._wire.decode(
            bytes_buffer,
            allow_trailing_bytes=self.allow_trailing_bytes,
        )
        self.wire_document = document
        if document.segments:
            last = document.segments[-1]
            self.header = project_header(document.segments[0].header)
            self.calculated_crc = last.calculated_crc
            self.stored_crc = last.stored_crc
        self.last_timestamp = self._wire.last_timestamp
        return document

    def _project_raw(
            self,
            raw: RawRecord,
            developer_fields_by_data_index: dict[int, dict[int, DeveloperField]],
    ) -> Record:
        if isinstance(raw, RawDefinitionRecord):
            return project_definition_record(raw)
        if isinstance(raw, RawDataRecord):
            return project_data_record(
                raw,
                developer_fields_by_data_index,
                accumulators=self._accumulators,
            )
        raise FitEncodingError(f'Unsupported wire record type: {type(raw)!r}')


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
