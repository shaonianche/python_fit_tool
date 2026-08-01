from __future__ import annotations

import csv
import shutil
import struct
import tempfile
from typing import BinaryIO, Iterator

from fit_tool.decoder import FitDecoder
from fit_tool.exceptions import FitCRCError, FitEncodingError
from fit_tool.fit_file_header import FitFileHeader
from fit_tool.record import Record
from fit_tool.utils.crc import crc16
from fit_tool.utils.logging import logger


class FitFile:
    """Public FIT file facade.

    Decode uses the unified :class:`~fit_tool.decoder.FitDecoder` state machine
    (wire layer + projection) shared with streaming APIs. Encode still
    serializes the projected :class:`~fit_tool.record.Record` list (lossless
    unknown-field rewrite is deferred).
    """

    def __init__(self, header: FitFileHeader, records: list[Record], crc: int | None = None):
        self.header = header
        self.records = records
        self._crc = crc  # crc16 of header and records
        self._crc_overridden = False

    @property
    def crc(self) -> int | None:
        return self._crc

    @crc.setter
    def crc(self, value: int | None) -> None:
        self._crc = value
        self._crc_overridden = value is not None

    def mark_dirty(self) -> None:
        """Mark the current checksum as stale after an in-memory edit."""
        self._crc = None
        self._crc_overridden = False

    def add_record(self, record: Record) -> None:
        self.records.append(record)
        self.mark_dirty()

    def remove_record(self, record: Record) -> None:
        self.records.remove(record)
        self.mark_dirty()

    @classmethod
    def from_file(cls, path: str) -> FitFile:
        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            return fit_file

    @classmethod
    def iter_file(cls, path: str, check_crc: bool = True) -> Iterator[Record]:
        from fit_tool.fit_file_stream import iter_fit_file
        return iter_fit_file(path, check_crc=check_crc)

    @classmethod
    def iter_stream(cls, file_object: BinaryIO, check_crc: bool = True) -> Iterator[Record]:
        from fit_tool.fit_file_stream import iter_fit_stream
        return iter_fit_stream(file_object, check_crc=check_crc)

    @classmethod
    def from_bytes(cls, bytes_buffer: bytes, check_crc: bool = True) -> FitFile:
        """Parse FIT bytes via the shared FitDecoder state machine.

        Collects the same projected records that :meth:`iter_stream` would yield
        from an equivalent stream, so CRC handling and developer-field
        registration stay aligned between full-load and streaming paths.
        """
        decoder = FitDecoder(check_crc=check_crc)
        header, records, calculated_crc = decoder.decode(bytes_buffer)
        return cls(header, records, calculated_crc)

    def to_bytes(self, check_crc: bool = True) -> bytes:
        try:
            record_buffers = [record.to_bytes() for record in self.records]
        except (IndexError, struct.error, UnicodeError, ValueError) as exc:
            raise FitEncodingError(f'Could not encode FIT records: {exc}') from exc

        records_size = sum(len(buffer) for buffer in record_buffers)
        if self.header.records_size != records_size:
            self.header.records_size = records_size

        if self.header.crc is not None:
            self.header.crc = FitFileHeader.generate_crc(
                self.header.protocol_version, self.header.profile_version, records_size
            )

        calculated_crc = 0
        bytes_buffer = bytearray()
        buffer = self.header.to_bytes()
        calculated_crc = crc16(buffer, crc=calculated_crc)
        bytes_buffer.extend(buffer)

        for buffer in record_buffers:
            calculated_crc = crc16(buffer, crc=calculated_crc)
            bytes_buffer.extend(buffer)

        if self._crc is None:
            self._crc = calculated_crc
        elif self._crc != calculated_crc:
            if self._crc_overridden:
                message = f'Calculated crc ({calculated_crc}) != defined crc ({self._crc})'
                if check_crc:
                    raise FitCRCError(message)
                logger.warning(message)
            else:
                self._crc = calculated_crc

        buffer = struct.pack('<H', self._crc)
        bytes_buffer.extend(buffer)

        return bytes(bytes_buffer)

    def to_rows(self) -> list[list]:
        rows = [record.to_row() for record in self.records]
        max_columns = max((len(row) for row in rows), default=0)
        rows.insert(0, self._create_csv_header(max_columns))
        return rows

    @staticmethod
    def _create_csv_header(max_columns: int) -> list:
        header_row = ['Type', 'Local ID', 'Message']
        max_fields = (max_columns - 3) // 3

        for i in range(max_fields):
            header_row.extend([f'Field {i}', f'Value {i}', f'Units {i}'])

        return header_row

    def to_csv(self, path: str) -> None:
        with tempfile.SpooledTemporaryFile(
                max_size=1024 * 1024, mode='w+', newline='', encoding='utf-8') as rows_file:
            rows_writer = csv.writer(rows_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            max_columns = 0
            for record in self.records:
                row = record.to_row()
                max_columns = max(max_columns, len(row))
                rows_writer.writerow(row)

            rows_file.seek(0)
            with open(path, 'w', newline='') as csv_file:
                csv_writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                csv_writer.writerow(self._create_csv_header(max_columns))
                shutil.copyfileobj(rows_file, csv_file)

    def to_file(self, path: str) -> None:
        with open(path, 'wb') as file_object:
            file_object.write(self.to_bytes())
