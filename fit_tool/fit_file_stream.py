"""Streaming FIT record parser."""

from __future__ import annotations

import struct
from typing import BinaryIO, Iterator, cast

from fit_tool.base_type import BaseType
from fit_tool.definition_message import DefinitionMessage
from fit_tool.developer_field import DeveloperField
from fit_tool.exceptions import FitCRCError, FitHeaderError, FitRecordError
from fit_tool.fit_file_header import FitFileHeader
from fit_tool.profile.messages.field_description_message import FieldDescriptionMessage
from fit_tool.record import Record, RecordHeader
from fit_tool.utils.crc import crc16
from fit_tool.utils.logging import logger


def _read_exact(file_object: BinaryIO, size: int, context: str, header: bool = False) -> bytes:
    data = bytearray()
    while len(data) < size:
        chunk = file_object.read(size - len(data))
        if not chunk:
            break
        data.extend(chunk)

    if len(data) != size:
        error_type = FitHeaderError if header else FitRecordError
        raise error_type(f'Truncated FIT input while reading {context}: expected {size} bytes, got {len(data)}.')
    return bytes(data)


def _register_record(
        record: Record,
        definition_messages: dict[int, DefinitionMessage],
        developer_fields_by_data_index: dict[int, dict[int, DeveloperField]]) -> None:
    if record.is_definition:
        definition_messages[record.local_id] = cast(DefinitionMessage, record.message)
        return

    if isinstance(record.message, FieldDescriptionMessage):
        message = record.message
        if (
            message.developer_data_index is None
            or message.field_definition_number is None
            or message.fit_base_type_id is None
        ):
            raise FitRecordError('Field description is missing required developer-field metadata.')
        developer_field = DeveloperField(
            developer_data_index=message.developer_data_index,
            field_id=message.field_definition_number,
            base_type=BaseType(message.fit_base_type_id),
            name=message.field_name,
            scale=message.scale,
            offset=message.offset,
            units=message.units,
        )
        fields_by_id = developer_fields_by_data_index.setdefault(developer_field.developer_data_index, {})
        fields_by_id[developer_field.field_id] = developer_field


def iter_fit_stream(file_object: BinaryIO, check_crc: bool = True) -> Iterator[Record]:
    """Yield records from a binary FIT stream; CRC validation completes when iteration is exhausted."""
    header_size_bytes = _read_exact(file_object, 1, 'header size', header=True)
    header_size = header_size_bytes[0]
    if header_size < 12:
        raise FitHeaderError(f'FIT header size must be at least 12 bytes, got {header_size}.')

    header_bytes = header_size_bytes + _read_exact(
        file_object, header_size - 1, 'remaining header', header=True
    )
    try:
        header = FitFileHeader.from_bytes(header_bytes)
    except (IndexError, struct.error, ValueError) as exc:
        raise FitHeaderError(f'Invalid FIT header: {exc}') from exc

    crc = crc16(header_bytes)
    remaining = header.records_size
    definition_messages: dict[int, DefinitionMessage] = {}
    developer_fields_by_data_index: dict[int, dict[int, DeveloperField]] = {}
    record_index = 0

    while remaining > 0:
        record_header_bytes = _read_exact(file_object, 1, f'record {record_index} header')
        try:
            record_header = RecordHeader.from_bytes(record_header_bytes)
        except (IndexError, ValueError) as exc:
            raise FitRecordError(f'Invalid record {record_index} header: {exc}') from exc

        if record_header.is_definition:
            body = bytearray(_read_exact(file_object, 5, f'record {record_index} definition prefix'))
            body.extend(_read_exact(file_object, body[4] * 3, f'record {record_index} field definitions'))
            if record_header.has_developer_fields:
                developer_count = _read_exact(file_object, 1, f'record {record_index} developer count')
                body.extend(developer_count)
                body.extend(_read_exact(
                    file_object, developer_count[0] * 3, f'record {record_index} developer definitions'
                ))
        else:
            definition_message = definition_messages.get(record_header.local_id)
            if definition_message is None:
                raise FitRecordError(
                    f'DefinitionMessage not defined for local_id {record_header.local_id} at record {record_index}.'
                )
            body = bytearray(_read_exact(
                file_object, definition_message.defined_data_size, f'record {record_index} data'
            ))

        record_bytes = record_header_bytes + bytes(body)
        if len(record_bytes) > remaining:
            raise FitRecordError(f'Record {record_index} exceeds the declared records section.')

        try:
            record = Record.from_bytes(
                definition_messages,
                record_bytes,
                developer_fields_by_data_index=developer_fields_by_data_index,
            )
            _register_record(record, definition_messages, developer_fields_by_data_index)
        except FitRecordError:
            raise
        except (IndexError, struct.error, UnicodeError, ValueError) as exc:
            raise FitRecordError(f'Could not parse record {record_index}: {exc}') from exc

        crc = crc16(record_bytes, crc=crc)
        remaining -= len(record_bytes)
        record_index += 1
        yield record

    file_crc_bytes = _read_exact(file_object, 2, 'file CRC', header=True)
    file_crc, = struct.unpack('<H', file_crc_bytes)
    if crc != file_crc:
        message = f'Calculated crc ({hex(crc)}) does not match crc in file ({hex(file_crc)}).'
        if check_crc:
            raise FitCRCError(message)
        logger.warning(message)


def iter_fit_file(path: str, check_crc: bool = True) -> Iterator[Record]:
    """Yield records from a FIT file without loading the complete file into memory."""
    with open(path, 'rb') as file_object:
        yield from iter_fit_stream(file_object, check_crc=check_crc)
