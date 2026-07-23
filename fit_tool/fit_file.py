from __future__ import annotations

import csv
import shutil
import struct
import tempfile
from typing import BinaryIO, Iterator

from fit_tool.base_type import BaseType
from fit_tool.definition_message import DefinitionMessage
from fit_tool.developer_field import DeveloperField
from fit_tool.exceptions import FitCRCError, FitEncodingError, FitHeaderError, FitRecordError
from fit_tool.fit_file_header import FitFileHeader
from fit_tool.profile.messages.field_description_message import FieldDescriptionMessage
from fit_tool.record import Record
from fit_tool.utils.crc import crc16
from fit_tool.utils.logging import logger


class FitFile:
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

    @staticmethod
    def _parse_record(
            definition_messages: dict[int, DefinitionMessage],
            bytes_buffer: bytes | memoryview,
            offset: int,
            developer_fields_by_data_index: dict[int, dict[int, DeveloperField]],
            record_index: int) -> Record:
        try:
            return Record.from_bytes(
                definition_messages=definition_messages,
                bytes_buffer=bytes_buffer,
                offset=offset,
                developer_fields_by_data_index=developer_fields_by_data_index,
            )
        except FitRecordError:
            raise
        except (IndexError, struct.error, UnicodeError, ValueError) as exc:
            raise FitRecordError(
                f'Could not parse record {record_index} at byte offset {offset}: {exc}'
            ) from exc

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
        if len(bytes_buffer) < 1:
            raise FitHeaderError('FIT data is empty; expected at least a header-size byte.')

        crc = 0
        buffer_view = memoryview(bytes_buffer)
        offset = 0

        header_size = bytes_buffer[0]
        if header_size < 12:
            raise FitHeaderError(f'FIT header size must be at least 12 bytes, got {header_size}.')
        if len(bytes_buffer) < header_size:
            raise FitHeaderError(f'FIT header declares {header_size} bytes but only {len(bytes_buffer)} are available.')

        try:
            header_bytes = buffer_view[:header_size]
            header = FitFileHeader.from_bytes(header_bytes)
        except (IndexError, struct.error, ValueError) as exc:
            raise FitHeaderError(f'Invalid FIT header: {exc}') from exc
        crc = crc16(header_bytes, crc=crc)
        offset += header_size
        records_end = offset + header.records_size
        if records_end + 2 > len(bytes_buffer):
            raise FitHeaderError('FIT data is truncated before the declared records and file CRC.')
        records_view = buffer_view[:records_end]

        records = []
        definition_messages: dict[int, DefinitionMessage] = {}
        developer_fields_by_data_index: dict[int, dict[int, DeveloperField]] = {}

        record_index = 0
        record_bytes_remaining_count = header.records_size
        while record_bytes_remaining_count > 0:
            record = cls._parse_record(
                definition_messages,
                records_view,
                offset,
                developer_fields_by_data_index,
                record_index,
            )

            if record.is_definition:
                definition_messages[record.local_id] = record.message
            elif isinstance(record.message, FieldDescriptionMessage):
                message = record.message
                developer_field = DeveloperField(developer_data_index=message.developer_data_index,
                                                 field_id=message.field_definition_number,
                                                 base_type=BaseType(message.fit_base_type_id),
                                                 name=message.field_name,
                                                 scale=message.scale,
                                                 offset=message.offset,
                                                 units=message.units)
                if developer_field.developer_data_index not in developer_fields_by_data_index:
                    developer_fields_by_data_index[developer_field.developer_data_index] = {}

                developer_fields_by_data_index[developer_field.developer_data_index][
                    developer_field.field_id] = developer_field

            records.append(record)
            definition_message = definition_messages[record.local_id]
            record_size = record.size
            defined_size = record.defined_size(definition_message)
            if defined_size <= 0 or defined_size > record_bytes_remaining_count:
                raise FitRecordError(
                    f'Record {record_index} at byte offset {offset} exceeds the declared records section.'
                )
            crc = crc16(records_view[offset:offset + defined_size], crc=crc)

            if record_size != defined_size:
                logger.warning(
                    f'Record {record_index}, {record.message}: size ({record_size}) != defined size ({defined_size}). Some fields were not read correctly.')

            record_bytes_remaining_count -= defined_size
            offset += defined_size
            record_index += 1

        file_crc, = struct.unpack_from('<H', buffer_view, offset)

        if crc != file_crc:
            message = f'Calculated crc ({hex(crc)}) does not match crc in file ({hex(file_crc)}).'

            if check_crc:
                raise FitCRCError(message)
            else:
                logger.warning(message)

        return cls(header, records, crc)

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
