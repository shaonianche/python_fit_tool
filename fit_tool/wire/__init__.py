"""Wire layer: binary-authoritative FIT models and decoder.

Semantic (Profile) projection lives in :mod:`fit_tool.compatibility`. The wire
package must not import generated message classes.
"""

from fit_tool.wire.crc import crc16
from fit_tool.wire.decoder import ByteSourceInput, WireDecoder, decode_bytes
from fit_tool.wire.encoder import encode_document, encode_segment
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

__all__ = [
    'ByteSourceInput',
    'FitDocument',
    'FitSegment',
    'RawDataRecord',
    'RawDefinitionRecord',
    'RawDeveloperFieldDefinition',
    'RawFieldDefinition',
    'RawFileHeader',
    'RawRecord',
    'RawRecordHeader',
    'WireDecoder',
    'apply_compressed_time_offset',
    'crc16',
    'decode_bytes',
    'encode_document',
    'encode_segment',
]
