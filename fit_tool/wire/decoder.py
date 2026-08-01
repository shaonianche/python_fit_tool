"""Stateful FIT wire decoder.

Produces :class:`~fit_tool.wire.model.FitDocument` / raw records without
constructing Profile-generated message classes.

Streaming and in-memory paths share one control loop via a byte-source
abstraction. Session state (definition snapshots, CRC, last_timestamp hook)
lives on the decoder instance for the duration of a segment decode.
"""

from __future__ import annotations

import struct
from typing import BinaryIO, Iterator, Protocol, Union

from fit_tool.exceptions import FitCRCError, FitHeaderError, FitParseError, FitRecordError
from fit_tool.wire.crc import crc16
from fit_tool.wire.model import (
    FitDocument,
    FitSegment,
    RawDataRecord,
    RawDefinitionRecord,
    RawDeveloperFieldDefinition,
    RawFieldDefinition,
    RawFileHeader,
    RawRecord,
    RawRecordHeader,
)
from fit_tool.wire.timestamp import apply_compressed_time_offset

# Native FIT date_time field number (seconds since 1989-12-31).
_TIMESTAMP_FIELD_ID = 253

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

ByteSourceInput = Union[bytes, bytearray, memoryview, BinaryIO]


class _ByteSource(Protocol):
    """Sequential reader used by the shared decode loop."""

    @property
    def position(self) -> int:
        ...

    def read_exact(self, size: int, context: str, *, header: bool = False) -> bytes:
        ...


class _BufferSource:
    """Read from an in-memory buffer starting at ``offset``."""

    def __init__(self, data: bytes, offset: int = 0) -> None:
        self._view = memoryview(data)
        self._offset = offset

    @property
    def position(self) -> int:
        return self._offset

    def read_exact(self, size: int, context: str, *, header: bool = False) -> bytes:
        available = len(self._view) - self._offset
        if size > available:
            error_type = FitHeaderError if header else FitRecordError
            raise error_type(
                f'Truncated FIT input while reading {context}: expected {size} bytes, got {available}.'
            )
        data = bytes(self._view[self._offset:self._offset + size])
        self._offset += size
        return data


class _StreamSource:
    """Read from a binary stream, handling short reads."""

    def __init__(self, file_object: BinaryIO, position: int = 0) -> None:
        self._file = file_object
        self._position = position

    @property
    def position(self) -> int:
        return self._position

    def read_exact(self, size: int, context: str, *, header: bool = False) -> bytes:
        data = bytearray()
        while len(data) < size:
            chunk = self._file.read(size - len(data))
            if not chunk:
                break
            data.extend(chunk)

        if len(data) != size:
            error_type = FitHeaderError if header else FitRecordError
            raise error_type(
                f'Truncated FIT input while reading {context}: expected {size} bytes, got {len(data)}.'
            )
        self._position += size
        return bytes(data)


def _as_byte_source(source: ByteSourceInput, offset: int = 0) -> _ByteSource:
    if isinstance(source, (bytes, bytearray, memoryview)):
        return _BufferSource(bytes(source), offset=offset)
    return _StreamSource(source, position=offset)


class WireDecoder:
    """Decode FIT binary into raw wire models.

    Definition table entries are immutable snapshots. Redefining a local message
    ID replaces the table entry for *subsequent* records only.

    Session state after a successful :meth:`iter_raw_records` / :meth:`decode_segment`
    call:

    - :attr:`header` — parsed file header
    - :attr:`definitions` — final local-id → definition snapshot map
    - :attr:`calculated_crc` / :attr:`stored_crc`
    - :attr:`last_timestamp` — reserved for compressed-timestamp reconstruction
    """

    def __init__(self, check_crc: bool = True, allow_trailing_bytes: bool = False) -> None:
        self.check_crc = check_crc
        self.allow_trailing_bytes = allow_trailing_bytes
        self._reset_session()

    def _reset_session(self) -> None:
        self.header: RawFileHeader | None = None
        self.definitions: dict[int, RawDefinitionRecord] = {}
        self.calculated_crc: int = 0
        self.stored_crc: int = 0
        self.crc_offset: int = 0
        self.last_timestamp: int | None = None

    def decode(
            self,
            bytes_buffer: bytes,
            *,
            allow_trailing_bytes: bool | None = None,
    ) -> FitDocument:
        """Decode a buffer into a document (supports chained multi-segment FIT).

        After each segment's file CRC, if more bytes remain and look like another
        FIT header, a further segment is decoded. Non-header trailing bytes raise
        :class:`FitParseError` unless ``allow_trailing_bytes`` is true.
        """
        if len(bytes_buffer) < 1:
            raise FitHeaderError('FIT data is empty; expected at least a header-size byte.')

        allow_trailing = (
            self.allow_trailing_bytes if allow_trailing_bytes is None else allow_trailing_bytes
        )
        segments: list[FitSegment] = []
        offset = 0
        while offset < len(bytes_buffer):
            segment = self.decode_segment(bytes_buffer, offset=offset)
            segments.append(segment)
            offset = segment.crc_offset + _FILE_CRC_SIZE
            if offset >= len(bytes_buffer):
                break
            if self._looks_like_header(bytes_buffer, offset):
                continue
            if allow_trailing:
                break
            raise FitParseError(
                f'Trailing {len(bytes_buffer) - offset} byte(s) after FIT segment at '
                f'offset {offset} are not a chained FIT header. '
                f'Pass allow_trailing_bytes=True to ignore them.'
            )

        return FitDocument(segments=segments)

    @staticmethod
    def _looks_like_header(buffer: bytes, offset: int) -> bool:
        if offset + _MIN_HEADER_SIZE > len(buffer):
            return False
        header_size = buffer[offset]
        if header_size < _MIN_HEADER_SIZE or offset + header_size > len(buffer):
            return False
        return buffer[offset + 8:offset + 12] == _FIT_TAG

    def decode_segment(self, source: ByteSourceInput, offset: int = 0) -> FitSegment:
        """Decode a single segment from bytes or a binary stream."""
        records = list(self.iter_raw_records(source, offset=offset))
        assert self.header is not None
        return FitSegment(
            header=self.header,
            records=records,
            stored_crc=self.stored_crc,
            calculated_crc=self.calculated_crc,
            crc_offset=self.crc_offset,
        )

    def iter_raw_records(
            self,
            source: ByteSourceInput,
            offset: int = 0,
    ) -> Iterator[RawRecord]:
        """Yield raw records for one segment; validates file CRC when exhausted.

        Both streaming and in-memory callers use this same control loop.
        """
        self._reset_session()
        byte_source = _as_byte_source(source, offset=offset)

        header = self._read_header(byte_source)
        self.header = header
        self.calculated_crc = crc16(header.source_bytes)
        remaining = header.records_size
        record_index = 0

        # Buffer sources know their total length: reject undersized payloads
        # early with FitHeaderError (matches historical from_bytes behaviour).
        # Streams discover truncation while reading and raise FitRecordError /
        # FitHeaderError from read_exact instead.
        if isinstance(byte_source, _BufferSource):
            available = len(byte_source._view) - byte_source.position
            needed = remaining + _FILE_CRC_SIZE
            if available < needed:
                raise FitHeaderError(
                    'FIT data is truncated before the declared records and file CRC.'
                )

        while remaining > 0:
            try:
                raw_record = self._read_record(byte_source, record_index)
            except FitRecordError:
                raise
            except (IndexError, struct.error, ValueError) as exc:
                raise FitRecordError(
                    f'Could not parse record {record_index} at byte offset '
                    f'{byte_source.position}: {exc}'
                ) from exc

            record_size = raw_record.size
            if record_size <= 0 or record_size > remaining:
                raise FitRecordError(
                    f'Record {record_index} at byte offset {raw_record.source_offset} '
                    f'exceeds the declared records section.'
                )

            if isinstance(raw_record, RawDefinitionRecord):
                # Store immutable snapshot; redefinition does not mutate prior snapshots.
                self.definitions[raw_record.local_id] = raw_record
            elif isinstance(raw_record, RawDataRecord):
                raw_record = self._apply_timestamp_state(raw_record, record_index)

            self.calculated_crc = crc16(raw_record.source_bytes, crc=self.calculated_crc)
            remaining -= record_size
            record_index += 1
            yield raw_record

        self.crc_offset = byte_source.position
        file_crc_bytes = byte_source.read_exact(_FILE_CRC_SIZE, 'file CRC', header=True)
        self.stored_crc, = struct.unpack('<H', file_crc_bytes)
        if self.calculated_crc != self.stored_crc:
            message = (
                f'Calculated crc ({hex(self.calculated_crc)}) does not match '
                f'crc in file ({hex(self.stored_crc)}).'
            )
            if self.check_crc:
                raise FitCRCError(message)

    def _apply_timestamp_state(
            self,
            raw_record: RawDataRecord,
            record_index: int,
    ) -> RawDataRecord:
        """Update ``last_timestamp`` and attach resolved compressed timestamps."""
        resolved: int | None = None
        header = raw_record.header

        if header.is_time_compressed:
            if self.last_timestamp is None:
                raise FitRecordError(
                    f'Compressed timestamp at record {record_index} requires a prior '
                    f'full timestamp field (253).'
                )
            resolved = apply_compressed_time_offset(
                self.last_timestamp, header.time_offset_seconds
            )
            self.last_timestamp = resolved
            return RawDataRecord(
                header=raw_record.header,
                definition=raw_record.definition,
                payload=raw_record.payload,
                source_offset=raw_record.source_offset,
                source_bytes=raw_record.source_bytes,
                dirty=raw_record.dirty,
                resolved_timestamp=resolved,
            )

        native_ts = self._extract_timestamp_from_payload(raw_record)
        if native_ts is not None:
            self.last_timestamp = native_ts
        return raw_record

    @staticmethod
    def _extract_timestamp_from_payload(raw_record: RawDataRecord) -> int | None:
        """Read native field 253 (date_time) from a data payload when present."""
        definition = raw_record.definition
        endian_symbol = '<' if definition.architecture == 0 else '>'
        offset = 0
        for field_def in definition.field_definitions:
            if field_def.field_id == _TIMESTAMP_FIELD_ID and field_def.size >= 4:
                # date_time is uint32; take the first 4 bytes of the field slot.
                value, = struct.unpack_from(f'{endian_symbol}I', raw_record.payload, offset)
                # Invalid FIT date_time is 0xFFFFFFFF.
                if value == 0xFFFFFFFF:
                    return None
                return value
            offset += field_def.size
        return None

    def _read_header(self, source: _ByteSource) -> RawFileHeader:
        offset = source.position
        header_size_bytes = source.read_exact(1, 'header size', header=True)
        header_size = header_size_bytes[0]
        if header_size < _MIN_HEADER_SIZE:
            raise FitHeaderError(
                f'FIT header size must be at least {_MIN_HEADER_SIZE} bytes, got {header_size}.'
            )

        source_bytes = header_size_bytes + source.read_exact(
            header_size - 1, 'remaining header', header=True
        )
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

        # 14-byte headers store CRC-16 of the first 12 header bytes at offset 12.
        # Same check_crc gate as the trailing file CRC.
        if header_size >= 14 and crc is not None:
            calculated_header_crc = crc16(source_bytes[:12])
            if calculated_header_crc != crc:
                message = (
                    f'Calculated header crc ({hex(calculated_header_crc)}) does not match '
                    f'crc in header ({hex(crc)}).'
                )
                if self.check_crc:
                    raise FitCRCError(message)

        return RawFileHeader(
            header_size=header_size,
            protocol_version=protocol_version,
            profile_version=profile_version,
            records_size=records_size,
            data_type=data_type,
            crc=crc,
            source_offset=offset,
            source_bytes=source_bytes,
        )

    def _decode_record_header(self, source_bytes: bytes, offset: int) -> RawRecordHeader:
        if not source_bytes:
            raise FitRecordError(f'Truncated FIT input while reading record header at offset {offset}.')

        byte = source_bytes[0]
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

    def _read_record(self, source: _ByteSource, record_index: int) -> RawRecord:
        record_offset = source.position
        header_bytes = source.read_exact(1, f'record {record_index} header')
        header = self._decode_record_header(header_bytes, record_offset)

        if header.is_definition:
            return self._read_definition(source, header, record_offset, header_bytes)
        return self._read_data(source, header, record_offset, header_bytes, record_index)

    def _read_definition(
            self,
            source: _ByteSource,
            header: RawRecordHeader,
            record_offset: int,
            header_bytes: bytes,
    ) -> RawDefinitionRecord:
        prefix = source.read_exact(
            _DEFINITION_PREFIX_SIZE, f'definition prefix at offset {record_offset}'
        )
        reserved = prefix[0]
        architecture = prefix[1]
        if architecture not in (0, 1):
            raise FitRecordError(
                f'Invalid definition architecture {architecture} at offset {record_offset}.'
            )

        endian_symbol = '<' if architecture == 0 else '>'
        global_id, = struct.unpack(f'{endian_symbol}H', prefix[2:4])
        field_count = prefix[4]

        field_definitions = []
        field_bytes = bytearray()
        for _ in range(field_count):
            entry = source.read_exact(
                _FIELD_DEFINITION_SIZE, f'field definitions at offset {record_offset}'
            )
            field_bytes.extend(entry)
            field_definitions.append(RawFieldDefinition(entry[0], entry[1], entry[2]))

        developer_field_definitions = []
        developer_bytes = bytearray()
        if header.has_developer_fields:
            developer_count_bytes = source.read_exact(
                1, f'developer field count at offset {record_offset}'
            )
            developer_bytes.extend(developer_count_bytes)
            developer_count = developer_count_bytes[0]
            for _ in range(developer_count):
                entry = source.read_exact(
                    _FIELD_DEFINITION_SIZE,
                    f'developer field definitions at offset {record_offset}',
                )
                developer_bytes.extend(entry)
                developer_field_definitions.append(
                    RawDeveloperFieldDefinition(entry[0], entry[1], entry[2])
                )

        source_bytes = header_bytes + prefix + bytes(field_bytes) + bytes(developer_bytes)
        return RawDefinitionRecord(
            header=header,
            reserved=reserved,
            architecture=architecture,
            global_id=global_id,
            field_definitions=tuple(field_definitions),
            developer_field_definitions=tuple(developer_field_definitions),
            source_offset=record_offset,
            source_bytes=source_bytes,
        )

    def _read_data(
            self,
            source: _ByteSource,
            header: RawRecordHeader,
            record_offset: int,
            header_bytes: bytes,
            record_index: int,
    ) -> RawDataRecord:
        definition = self.definitions.get(header.local_id)
        if definition is None:
            raise FitRecordError(
                f'DefinitionMessage not defined for local_id: {header.local_id}'
            )

        payload_size = definition.defined_data_size
        payload = source.read_exact(
            payload_size,
            f'data record {record_index} payload at offset {record_offset}',
        )
        source_bytes = header_bytes + payload
        return RawDataRecord(
            header=header,
            definition=definition,
            payload=payload,
            source_offset=record_offset,
            source_bytes=source_bytes,
        )


def decode_bytes(
        bytes_buffer: bytes,
        check_crc: bool = True,
        *,
        allow_trailing_bytes: bool = False,
) -> FitDocument:
    """Decode FIT bytes into a wire document (chained segments supported)."""
    return WireDecoder(
        check_crc=check_crc,
        allow_trailing_bytes=allow_trailing_bytes,
    ).decode(bytes_buffer, allow_trailing_bytes=allow_trailing_bytes)
