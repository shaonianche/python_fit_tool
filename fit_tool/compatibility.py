"""Compatibility bridge from wire models to the existing public FitFile types.

The wire package stays free of generated Profile message classes. This module
projects raw records into :class:`~fit_tool.record.Record`,
:class:`~fit_tool.definition_message.DefinitionMessage`, and
:class:`~fit_tool.data_message.DataMessage` for the FitFile facade.
"""

from __future__ import annotations

import struct

from fit_tool.base_type import BaseType
from fit_tool.components import expand_message_components
from fit_tool.data_message import DataMessage
from fit_tool.definition_message import DefinitionMessage
from fit_tool.developer_field import DeveloperField
from fit_tool.developer_field_definition import DeveloperFieldDefinition
from fit_tool.endian import Endian
from fit_tool.exceptions import FitRecordError
from fit_tool.field_definition import FieldDefinition
from fit_tool.fit_file_header import FitFileHeader, ProfileVersion, ProtocolVersion
from fit_tool.profile.messages.field_description_message import FieldDescriptionMessage
from fit_tool.record import Record, RecordHeader
from fit_tool.wire.model import (
    FitDocument,
    FitSegment,
    RawDataRecord,
    RawDefinitionRecord,
    RawFileHeader,
    RawRecord,
)

_TIMESTAMP_FIELD_ID = 253


def project_header(raw: RawFileHeader) -> FitFileHeader:
    """Project a wire header into the existing FitFileHeader type."""
    protocol = ProtocolVersion(raw.protocol_version >> 4, raw.protocol_version & 0x0F)
    scale = (
        ProfileVersion.CURRENT_MAJOR_SCALE
        if raw.profile_version > ProfileVersion.SCALE_CHANGE_VALUE
        else ProfileVersion.LEGACY_MAJOR_SCALE
    )
    profile = ProfileVersion(raw.profile_version // scale, raw.profile_version % scale)
    return FitFileHeader(
        records_size=raw.records_size,
        protocol_version=protocol,
        profile_version=profile,
        crc=raw.crc,
    )


def definition_from_raw(raw: RawDefinitionRecord) -> DefinitionMessage:
    """Build a DefinitionMessage from an immutable wire definition snapshot."""
    field_definitions = [
        FieldDefinition(
            field_id=field_def.field_id,
            size=field_def.size,
            base_type=BaseType(field_def.base_type),
        )
        for field_def in raw.field_definitions
    ]
    developer_field_definitions = [
        DeveloperFieldDefinition(
            field_id=field_def.field_id,
            size=field_def.size,
            developer_data_index=field_def.developer_data_index,
        )
        for field_def in raw.developer_field_definitions
    ]
    return DefinitionMessage(
        local_id=raw.local_id,
        global_id=raw.global_id,
        endian=Endian(raw.architecture),
        field_definitions=field_definitions,
        developer_field_definitions=developer_field_definitions,
    )


def record_header_from_raw(raw_header) -> RecordHeader:
    """Project a wire record header into RecordHeader."""
    return RecordHeader(
        is_time_compressed=raw_header.is_time_compressed,
        is_definition=raw_header.is_definition,
        has_developer_fields=raw_header.has_developer_fields,
        local_id=raw_header.local_id,
        time_offset_seconds=raw_header.time_offset_seconds,
    )


def project_definition_record(raw: RawDefinitionRecord) -> Record:
    """Project a wire definition record to a compatibility Record."""
    header = record_header_from_raw(raw.header)
    message = definition_from_raw(raw)
    return Record(header, message)


def project_data_record(
        raw: RawDataRecord,
        developer_fields_by_data_index: dict[int, dict[int, DeveloperField]],
        *,
        accumulators: dict[tuple[int, int], int] | None = None,
) -> Record:
    """Project a wire data record to a typed DataMessage wrapped in a Record."""
    header = record_header_from_raw(raw.header)
    # Always build DefinitionMessage from the snapshot attached to this record so
    # redefinition of the same local_id cannot mutate earlier projections.
    definition_message = definition_from_raw(raw.definition)

    try:
        # Always resolve developer fields when the definition declares them so
        # missing Field Description registration fails the same way on stream
        # and full-load paths (empty registry is not treated as "no fields").
        if definition_message.developer_field_definitions:
            developer_fields = definition_message.get_developer_fields(
                developer_fields_by_data_index
            )
        else:
            developer_fields = []

        message = DataMessage.from_bytes(
            definition_message,
            developer_fields,
            raw.payload,
            offset=0,
        )
    except FitRecordError:
        raise
    except (IndexError, struct.error, UnicodeError, ValueError) as exc:
        raise FitRecordError(
            f'Could not project data record at byte offset {raw.source_offset}: {exc}'
        ) from exc

    message.local_id = raw.local_id

    if raw.resolved_timestamp is not None:
        _apply_resolved_timestamp(message, raw.resolved_timestamp)

    if accumulators is not None:
        expand_message_components(message, accumulators)
    else:
        expand_message_components(message)

    return Record(header, message)


def _apply_resolved_timestamp(message: DataMessage, timestamp: int) -> None:
    """Inject a reconstructed FIT date_time into field 253 when present."""
    field = message.get_field(_TIMESTAMP_FIELD_ID)
    if field is None:
        return
    if field.size == 0:
        field.size = field.base_type.size
        field.encoded_values = [None]
    field.set_encoded_value(0, timestamp, check_validity=False)


def register_developer_field(
        record: Record,
        developer_fields_by_data_index: dict[int, dict[int, DeveloperField]],
) -> None:
    """Register Field Description metadata into the developer-field registry.

    Stream and full-load paths share this registration so validation strictness
    stays aligned (missing required metadata raises :class:`FitRecordError`).
    """
    if not isinstance(record.message, FieldDescriptionMessage):
        return

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


# Backward-compatible private alias used by earlier Stage 2 code / tests.
_register_developer_field = register_developer_field


def project_segment(
        segment: FitSegment,
        *,
        accumulators: dict[tuple[int, int], int] | None = None,
) -> list[Record]:
    """Project all wire records in a segment to compatibility Records."""
    records: list[Record] = []
    developer_fields_by_data_index: dict[int, dict[int, DeveloperField]] = {}
    if accumulators is None:
        accumulators = {}

    for raw in segment.records:
        if isinstance(raw, RawDefinitionRecord):
            record = project_definition_record(raw)
        elif isinstance(raw, RawDataRecord):
            record = project_data_record(
                raw,
                developer_fields_by_data_index,
                accumulators=accumulators,
            )
            register_developer_field(record, developer_fields_by_data_index)
        else:
            raise FitRecordError(f'Unsupported wire record type: {type(raw)!r}')
        records.append(record)

    return records


def project_document(document: FitDocument) -> list[Record]:
    """Project every segment of a (possibly chained) document into one record list."""
    records: list[Record] = []
    accumulators: dict[tuple[int, int], int] = {}
    for segment in document.segments:
        records.extend(project_segment(segment, accumulators=accumulators))
    return records


def project_records(records: list[RawRecord]) -> list[Record]:
    """Project a sequence of raw records (used by unit tests)."""
    segment = FitSegment(
        header=RawFileHeader(
            header_size=14,
            protocol_version=0x20,
            profile_version=0,
            records_size=0,
            data_type=b'.FIT',
            crc=None,
            source_offset=0,
            source_bytes=b'',
        ),
        records=list(records),
    )
    return project_segment(segment)
