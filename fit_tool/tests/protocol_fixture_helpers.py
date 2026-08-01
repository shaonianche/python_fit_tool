"""Constructive FIT byte builders for protocol gap / golden tests.

Prefer these helpers over committing large binary dumps. All builders produce
CRC-valid 12-byte-header files unless noted.
"""

from __future__ import annotations

import struct
from collections.abc import Sequence

from fit_tool.base_type import BaseType
from fit_tool.definition_message import DefinitionMessage
from fit_tool.endian import Endian
from fit_tool.field_definition import FieldDefinition
from fit_tool.fit_file_header import FitFileHeader
from fit_tool.record import Record
from fit_tool.utils.crc import crc16


def wrap_records(records: bytes, *, with_header_crc: bool = False) -> bytes:
    """Prefix *records* with a FIT header and append file CRC.

    *with_header_crc* requests a classic 14-byte header (header CRC present).
    """
    if with_header_crc:
        header = FitFileHeader(records_size=len(records), gen_crc=True)
    else:
        header = FitFileHeader(records_size=len(records))
    body = header.to_bytes() + records
    return body + struct.pack('<H', crc16(body))


def definition_and_data(
        *,
        global_id: int,
        field_definitions: Sequence[FieldDefinition],
        payload: bytes,
        local_id: int = 0,
        endian: Endian = Endian.LITTLE,
) -> bytes:
    """Serialize one definition record + one data record (no header/CRC)."""
    definition = DefinitionMessage(
        local_id=local_id,
        global_id=global_id,
        endian=endian,
        field_definitions=list(field_definitions),
    )
    definition_bytes = Record.from_message(definition).to_bytes()
    data_header = bytes([local_id & 0x0F])
    expected = sum(fd.size for fd in field_definitions)
    if len(payload) != expected:
        raise ValueError(f'payload length {len(payload)} != defined size {expected}')
    return definition_bytes + data_header + payload


def build_record_with_unknown_field(
        *,
        timestamp_raw: int = 1000,
        heart_rate: int = 120,
        unknown_field_id: int = 250,
        unknown_value: int = 0xABCD,
) -> bytes:
    """Record (global 20) with known fields plus an unknown native field id.

    Layout: timestamp (253), unknown UINT16, heart_rate (3).
    """
    payload = (
        struct.pack('<I', timestamp_raw)
        + struct.pack('<H', unknown_value)
        + struct.pack('<B', heart_rate)
    )
    records = definition_and_data(
        global_id=20,
        field_definitions=[
            FieldDefinition(field_id=253, size=4, base_type=BaseType.UINT32),
            FieldDefinition(field_id=unknown_field_id, size=2, base_type=BaseType.UINT16),
            FieldDefinition(field_id=3, size=1, base_type=BaseType.UINT8),
        ],
        payload=payload,
    )
    return wrap_records(records)


def build_record_with_compressed_speed_distance(
        *,
        timestamp_raw: int = 1000,
        speed_encoded_12bit: int = 1000,
        distance_encoded_12bit: int = 32,
) -> bytes:
    """Record message with packed field 8 only (component expansion target)."""
    packed = (speed_encoded_12bit & 0xFFF) | ((distance_encoded_12bit & 0xFFF) << 12)
    payload = struct.pack('<I', timestamp_raw) + bytes(
        [packed & 0xFF, (packed >> 8) & 0xFF, (packed >> 16) & 0xFF]
    )
    records = definition_and_data(
        global_id=20,
        field_definitions=[
            FieldDefinition(field_id=253, size=4, base_type=BaseType.UINT32),
            FieldDefinition(field_id=8, size=3, base_type=BaseType.BYTE),
        ],
        payload=payload,
    )
    return wrap_records(records)


def build_workout_step_with_duration(
        *,
        duration_type: int,
        duration_value_raw: int,
        name: str = 'step',
) -> bytes:
    """Minimal workout_step (global 27) carrying duration_type + duration_value.

    *duration_value_raw* is the on-wire UINT32 (before subfield scale).
    """
    name_bytes = name.encode('utf-8') + b'\x00'
    # Fields: name (0 string), duration_type (1 enum), duration_value (2 uint32)
    payload = name_bytes + struct.pack('<B', duration_type & 0xFF) + struct.pack(
        '<I', duration_value_raw & 0xFFFFFFFF
    )
    records = definition_and_data(
        global_id=27,
        field_definitions=[
            FieldDefinition(field_id=0, size=len(name_bytes), base_type=BaseType.STRING),
            FieldDefinition(field_id=1, size=1, base_type=BaseType.ENUM),
            FieldDefinition(field_id=2, size=4, base_type=BaseType.UINT32),
        ],
        payload=payload,
    )
    return wrap_records(records)


def chain_segments(*segment_bodies: bytes) -> bytes:
    """Concatenate complete FIT files (each already includes its file CRC)."""
    if not segment_bodies:
        raise ValueError('At least one segment body is required.')
    return b''.join(segment_bodies)
