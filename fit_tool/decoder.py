"""Unified FIT decoder state machine for stream and in-memory paths.

Built on the Stage 2 wire layer. One control loop owns:

- local definition snapshots (via :class:`~fit_tool.wire.decoder.WireDecoder`)
- developer field registry
- CRC accumulation
- ``last_timestamp`` hook (for compressed timestamps later)

:meth:`FitFile.from_bytes` collects records from this machine;
:func:`~fit_tool.fit_file_stream.iter_fit_stream` yields them.
"""

from __future__ import annotations

from typing import BinaryIO, Iterator, Union

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
from fit_tool.wire.model import RawDataRecord, RawDefinitionRecord, RawRecord

Source = Union[bytes, bytearray, memoryview, BinaryIO]


class FitDecoder:
    """Stateful decoder shared by full-load and streaming public APIs.

    After :meth:`iter_records` completes (or is exhausted), session fields are
    available: :attr:`header`, :attr:`calculated_crc`, :attr:`stored_crc`,
    :attr:`last_timestamp`, and :attr:`developer_fields_by_data_index`.
    """

    def __init__(self, check_crc: bool = True) -> None:
        self.check_crc = check_crc
        self._wire = WireDecoder(check_crc=check_crc)
        self._reset_session()

    def _reset_session(self) -> None:
        self.header: FitFileHeader | None = None
        self.calculated_crc: int = 0
        self.stored_crc: int = 0
        self.last_timestamp: int | None = None
        self.developer_fields_by_data_index: dict[int, dict[int, DeveloperField]] = {}

    def iter_records(self, source: Source) -> Iterator[Record]:
        """Yield projected records from bytes or a binary stream.

        CRC is validated when iteration is exhausted (same as historical
        ``iter_fit_stream`` behaviour). Developer-field registration runs as
        Field Description data messages are projected, so later data messages
        see the same registry on both stream and full-load paths.
        """
        self._reset_session()
        developer_registry = self.developer_fields_by_data_index

        for raw in self._wire.iter_raw_records(source):
            record = self._project_raw(raw, developer_registry)
            register_developer_field(record, developer_registry)
            # Propagate wire timestamp hook for future compressed-timestamp work.
            self.last_timestamp = self._wire.last_timestamp
            yield record

        assert self._wire.header is not None
        self.header = project_header(self._wire.header)
        self.calculated_crc = self._wire.calculated_crc
        self.stored_crc = self._wire.stored_crc
        self.last_timestamp = self._wire.last_timestamp

        if self.calculated_crc != self.stored_crc and not self.check_crc:
            logger.warning(
                f'Calculated crc ({hex(self.calculated_crc)}) does not match '
                f'crc in file ({hex(self.stored_crc)}).'
            )

    def decode(self, source: Source) -> tuple[FitFileHeader, list[Record], int]:
        """Decode a full segment into header, records, and calculated CRC."""
        records = list(self.iter_records(source))
        if self.header is None:
            raise FitEncodingError('Decoder finished without a FIT header.')
        return self.header, records, self.calculated_crc

    @staticmethod
    def _project_raw(
            raw: RawRecord,
            developer_fields_by_data_index: dict[int, dict[int, DeveloperField]],
    ) -> Record:
        if isinstance(raw, RawDefinitionRecord):
            return project_definition_record(raw)
        if isinstance(raw, RawDataRecord):
            return project_data_record(raw, developer_fields_by_data_index)
        raise FitEncodingError(f'Unsupported wire record type: {type(raw)!r}')


def iter_fit_records(source: Source, check_crc: bool = True) -> Iterator[Record]:
    """Yield projected FIT records from bytes or a stream (shared decode path)."""
    yield from FitDecoder(check_crc=check_crc).iter_records(source)


# Re-export for type checkers / callers that need the wire source alias.
__all__ = [
    'ByteSourceInput',
    'FitDecoder',
    'Source',
    'iter_fit_records',
]
