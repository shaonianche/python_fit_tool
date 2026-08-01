"""Stateful FIT wire decoder.

Produces :class:`~fit_tool.wire.model.FitDocument` / raw records without
constructing Profile-generated message classes.
"""

from __future__ import annotations

import struct

from fit_tool.exceptions import FitCRCError, FitHeaderError, FitRecordError
from fit_tool.wire.crc import crc16
from fit_tool.wire.model import (
    FitDocument,
    FitSegment,
    RawDataRecord,
    RawDefinitionRecord,
    RawDeveloperFieldDefinition,
    RawFieldDefinition,
    RawFileHeader,
    RawRecordHeader,
)

_IS_TIME_COMPRESSED = 0x80
_IS_DEFINITION = 0x40
_HAS_DEVELOPER_FIELDS = 0x20
_NORMAL_LOCAL_ID = 0x0F
_TIME_COMPRESSED_LOCAL_ID = 0x60
_TIME_OFFSET = 0x1F

_FIT_TAG = b'.FIT'
_MIN_HEADER_SIZE = 12
_FILE_CRC_SIZE = 2
_FIELD_DEFINITION_SIZE = 3
_DEFINITION_PREFIX_SIZE = 5  # reserved + architecture + global_id + field_count


class WireDecoder:
    """Decode FIT binary into raw wire models.

    Definition table entries are immutable snapshots. Redefining a local message
    ID replaces the table entry for *subsequent* records only.
    """

    def __init__(self, check_crc: bool = True) -> None:
        self.check_crc = check_crc

    def decode(self, bytes_buffer: bytes) -> FitDocument:
        """Decode a buffer into a document (single segment for MVP)."""
        if len(bytes_buffer) < 1:
            raise FitHeaderError('FIT data is empty; expected at least a header-size byte.')

        segment, _consumed = self._decode_segment(bytes_buffer, offset=0)
        return FitDocument(segments=[segment])

    def decode_segment(self, bytes_buffer: bytes, offset: int = 0) -> FitSegment:
        """Decode a single segment starting at ``offset``."""
        segment, _ = self._decode_segment(bytes_buffer, offset=offset)
        return segment

    def _decode_segment(self, bytes_buffer: bytes, offset: int) -> tuple:
        buffer_view = memoryview(bytes_buffer)
        start = offset

        header, offset = self._decode_header(buffer_view, offset)
        calculated_crc = crc16(header.source_bytes)

        records_end = offset + header.records_size
        file_crc_end = records_end + _FILE_CRC_SIZE
        if file_crc_end > len(bytes_buffer):
            raise FitHeaderError('FIT data is truncated before the declared records and file CRC.')

        definitions: dict[int, RawDefinitionRecord] = {}
        records = []
        record_index = 0
        remaining = header.records_size

        while remaining > 0:
            try:
                raw_record, record_size = self._decode_record(
                    buffer_view, offset, definitions, record_index
                )
            except FitRecordError:
                raise
            except (IndexError, struct.error, ValueError) as exc:
                raise FitRecordError(
                    f'Could not parse record {record_index} at byte offset {offset}: {exc}'
                ) from exc

            if record_size <= 0 or record_size > remaining:
                raise FitRecordError(
                    f'Record {record_index} at byte offset {offset} exceeds the declared records section.'
                )

            if isinstance(raw_record, RawDefinitionRecord):
                # Store immutable snapshot; redefinition does not mutate prior snapshots.
                definitions[raw_record.local_id] = raw_record

            calculated_crc = crc16(buffer_view[offset:offset + record_size], crc=calculated_crc)
            records.append(raw_record)
            remaining -= record_size
            offset += record_size
            record_index += 1

        stored_crc, = struct.unpack_from('<H', buffer_view, offset)
        if calculated_crc != stored_crc:
            message = (
                f'Calculated crc ({hex(calculated_crc)}) does not match crc in file ({hex(stored_crc)}).'
            )
            if self.check_crc:
                raise FitCRCError(message)

        segment = FitSegment(
            header=header,
            records=records,
            stored_crc=stored_crc,
            calculated_crc=calculated_crc,
            crc_offset=offset,
        )
        return segment, offset + _FILE_CRC_SIZE - start

    def _decode_header(self, buffer_view: memoryview, offset: int) -> tuple:
        if offset >= len(buffer_view):
            raise FitHeaderError('FIT data is empty; expected at least a header-size byte.')

        header_size = buffer_view[offset]
        if header_size < _MIN_HEADER_SIZE:
            raise FitHeaderError(
                f'FIT header size must be at least {_MIN_HEADER_SIZE} bytes, got {header_size}.'
            )
        if offset + header_size > len(buffer_view):
            raise FitHeaderError(
                f'FIT header declares {header_size} bytes but only '
                f'{len(buffer_view) - offset} are available.'
            )

        source_bytes = bytes(buffer_view[offset:offset + header_size])
        try:
            protocol_version = source_bytes[1]
            profile_version, = struct.unpack_from('<H', source_bytes, 2)
            records_size, = struct.unpack_from('<I', source_bytes, 4)
            data_type = source_bytes[8:12]
            if data_type != _FIT_TAG:
                raise ValueError('".FIT" not in header.')
            crc: int | None = None
            if header_size >= 14:
                crc, = struct.unpack_from('<H', source_bytes, 12)
        except (IndexError, struct.error, ValueError) as exc:
            raise FitHeaderError(f'Invalid FIT header: {exc}') from exc

        header = RawFileHeader(
            header_size=header_size,
            protocol_version=protocol_version,
            profile_version=profile_version,
            records_size=records_size,
            data_type=data_type,
            crc=crc,
            source_offset=offset,
            source_bytes=source_bytes,
        )
        return header, offset + header_size

    def _decode_record_header(self, buffer_view: memoryview, offset: int) -> RawRecordHeader:
        if offset >= len(buffer_view):
            raise FitRecordError(f'Truncated FIT input while reading record header at offset {offset}.')

        byte = buffer_view[offset]
        source_bytes = bytes(buffer_view[offset:offset + 1])

        is_time_compressed = (byte & _IS_TIME_COMPRESSED) == _IS_TIME_COMPRESSED
        if is_time_compressed:
            # Compressed timestamp headers are always data-message headers.
            local_id = (byte & _TIME_COMPRESSED_LOCAL_ID) >> 5
            time_offset_seconds = byte & _TIME_OFFSET
            return RawRecordHeader(
                is_time_compressed=True,
                is_definition=False,
                has_developer_fields=False,
                local_id=local_id,
                time_offset_seconds=time_offset_seconds,
                source_offset=offset,
                source_bytes=source_bytes,
            )

        is_definition = (byte & _IS_DEFINITION) == _IS_DEFINITION
        has_developer_fields = (byte & _HAS_DEVELOPER_FIELDS) == _HAS_DEVELOPER_FIELDS
        local_id = byte & _NORMAL_LOCAL_ID
        return RawRecordHeader(
            is_time_compressed=False,
            is_definition=is_definition,
            has_developer_fields=has_developer_fields,
            local_id=local_id,
            time_offset_seconds=0,
            source_offset=offset,
            source_bytes=source_bytes,
        )

    def _decode_record(
            self,
            buffer_view: memoryview,
            offset: int,
            definitions: dict[int, RawDefinitionRecord],
            record_index: int,
    ) -> tuple:
        header = self._decode_record_header(buffer_view, offset)
        body_offset = offset + header.size

        if header.is_definition:
            return self._decode_definition(buffer_view, offset, body_offset, header)
        return self._decode_data(buffer_view, offset, body_offset, header, definitions, record_index)

    def _decode_definition(
            self,
            buffer_view: memoryview,
            record_offset: int,
            body_offset: int,
            header: RawRecordHeader,
    ) -> tuple:
        if body_offset + _DEFINITION_PREFIX_SIZE > len(buffer_view):
            raise FitRecordError(
                f'Truncated definition message at offset {record_offset}.'
            )

        reserved = buffer_view[body_offset]
        architecture = buffer_view[body_offset + 1]
        if architecture not in (0, 1):
            raise FitRecordError(
                f'Invalid definition architecture {architecture} at offset {record_offset}.'
            )

        endian_symbol = '<' if architecture == 0 else '>'
        global_id, = struct.unpack_from(f'{endian_symbol}H', buffer_view, body_offset + 2)
        field_count = buffer_view[body_offset + 4]
        cursor = body_offset + _DEFINITION_PREFIX_SIZE

        field_definitions = []
        for _ in range(field_count):
            if cursor + _FIELD_DEFINITION_SIZE > len(buffer_view):
                raise FitRecordError(f'Truncated field definitions at offset {record_offset}.')
            field_id = buffer_view[cursor]
            size = buffer_view[cursor + 1]
            base_type = buffer_view[cursor + 2]
            field_definitions.append(RawFieldDefinition(field_id, size, base_type))
            cursor += _FIELD_DEFINITION_SIZE

        developer_field_definitions = []
        if header.has_developer_fields:
            if cursor >= len(buffer_view):
                raise FitRecordError(f'Truncated developer field count at offset {record_offset}.')
            developer_count = buffer_view[cursor]
            cursor += 1
            for _ in range(developer_count):
                if cursor + _FIELD_DEFINITION_SIZE > len(buffer_view):
                    raise FitRecordError(
                        f'Truncated developer field definitions at offset {record_offset}.'
                    )
                field_id = buffer_view[cursor]
                size = buffer_view[cursor + 1]
                developer_data_index = buffer_view[cursor + 2]
                developer_field_definitions.append(
                    RawDeveloperFieldDefinition(field_id, size, developer_data_index)
                )
                cursor += _FIELD_DEFINITION_SIZE

        source_bytes = bytes(buffer_view[record_offset:cursor])
        raw = RawDefinitionRecord(
            header=header,
            reserved=reserved,
            architecture=architecture,
            global_id=global_id,
            field_definitions=tuple(field_definitions),
            developer_field_definitions=tuple(developer_field_definitions),
            source_offset=record_offset,
            source_bytes=source_bytes,
        )
        return raw, len(source_bytes)

    def _decode_data(
            self,
            buffer_view: memoryview,
            record_offset: int,
            body_offset: int,
            header: RawRecordHeader,
            definitions: dict[int, RawDefinitionRecord],
            record_index: int,
    ) -> tuple:
        definition = definitions.get(header.local_id)
        if definition is None:
            raise FitRecordError(
                f'DefinitionMessage not defined for local_id: {header.local_id}'
            )

        payload_size = definition.defined_data_size
        end = body_offset + payload_size
        if end > len(buffer_view):
            raise FitRecordError(
                f'Truncated data record {record_index} at offset {record_offset}: '
                f'need {payload_size} payload bytes.'
            )

        payload = bytes(buffer_view[body_offset:end])
        source_bytes = bytes(buffer_view[record_offset:end])
        raw = RawDataRecord(
            header=header,
            definition=definition,
            payload=payload,
            source_offset=record_offset,
            source_bytes=source_bytes,
        )
        return raw, len(source_bytes)


def decode_bytes(bytes_buffer: bytes, check_crc: bool = True) -> FitDocument:
    """Decode FIT bytes into a wire document."""
    return WireDecoder(check_crc=check_crc).decode(bytes_buffer)
