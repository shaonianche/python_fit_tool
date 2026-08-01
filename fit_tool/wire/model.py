"""Authoritative binary (wire) models for FIT files.

These types describe structure and source byte ranges. They must not depend on
generated Profile message classes. Semantic projection happens outside this
package (see :mod:`fit_tool.compatibility`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union


@dataclass(frozen=True)
class RawRecordHeader:
    """One-byte FIT record header with structural flags."""

    is_time_compressed: bool
    is_definition: bool
    has_developer_fields: bool
    local_id: int
    time_offset_seconds: int
    source_offset: int
    source_bytes: bytes

    @property
    def size(self) -> int:
        return len(self.source_bytes)


@dataclass(frozen=True)
class RawFieldDefinition:
    """Native field definition entry (3 bytes on the wire)."""

    field_id: int
    size: int
    base_type: int


@dataclass(frozen=True)
class RawDeveloperFieldDefinition:
    """Developer field definition entry (3 bytes on the wire)."""

    field_id: int
    size: int
    developer_data_index: int


@dataclass(frozen=True)
class RawDefinitionRecord:
    """Immutable definition-message snapshot.

    When a local message ID is redefined, a *new* snapshot is stored for later
    data records. Earlier data records keep the snapshot they were decoded with.
    """

    header: RawRecordHeader
    reserved: int
    architecture: int  # 0 = little-endian, 1 = big-endian
    global_id: int
    field_definitions: tuple[RawFieldDefinition, ...]
    developer_field_definitions: tuple[RawDeveloperFieldDefinition, ...]
    source_offset: int
    source_bytes: bytes
    dirty: bool = False

    @property
    def local_id(self) -> int:
        return self.header.local_id

    @property
    def defined_data_size(self) -> int:
        size = 0
        for field_def in self.field_definitions:
            size += field_def.size
        for field_def in self.developer_field_definitions:
            size += field_def.size
        return size

    @property
    def size(self) -> int:
        return len(self.source_bytes)


@dataclass(frozen=True)
class RawDataRecord:
    """Data-message record with payload bytes and the definition snapshot used."""

    header: RawRecordHeader
    definition: RawDefinitionRecord
    payload: bytes
    source_offset: int
    source_bytes: bytes
    dirty: bool = False

    @property
    def local_id(self) -> int:
        return self.header.local_id

    @property
    def size(self) -> int:
        return len(self.source_bytes)


RawRecord = Union[RawDefinitionRecord, RawDataRecord]


@dataclass
class RawFileHeader:
    """Parsed FIT file header (12- or 14-byte form)."""

    header_size: int
    protocol_version: int  # raw packed byte (major << 4 | minor)
    profile_version: int  # raw u16 version code
    records_size: int
    data_type: bytes
    crc: int | None
    source_offset: int
    source_bytes: bytes

    @property
    def size(self) -> int:
        return len(self.source_bytes)


@dataclass
class FitSegment:
    """One FIT file segment (header + records + trailing file CRC)."""

    header: RawFileHeader
    records: list[RawRecord] = field(default_factory=list)
    stored_crc: int = 0
    calculated_crc: int = 0
    crc_offset: int = 0


@dataclass
class FitDocument:
    """Top-level wire document.

    MVP decoder produces a single segment. Multi-segment (chained) documents
    are deferred.
    """

    segments: list[FitSegment] = field(default_factory=list)

    @property
    def first_segment(self) -> FitSegment | None:
        return self.segments[0] if self.segments else None
