from __future__ import annotations

import struct

from fit_tool import SDK_VERSION
from fit_tool.utils.crc import crc16


class ProtocolVersion:
    def __init__(self, major: int, minor: int) -> None:
        self.major = major
        self.minor = minor

    def to_bytes(self) -> bytes:
        return struct.pack('B', (self.major << 4) | self.minor)

    @classmethod
    def from_bytes(cls, bytes_buffer: bytes) -> ProtocolVersion:
        value = bytes_buffer[0]
        major = value >> 4
        minor = value & 0x0f
        return ProtocolVersion(major, minor)

    def __str__(self) -> str:
        return f'{self.major}.{self.minor}'


class ProfileVersion:
    LEGACY_MAJOR_SCALE = 100
    CURRENT_MAJOR_SCALE = 1000
    SCALE_CHANGE_VALUE = 2199

    def __init__(self, major: int, minor: int) -> None:
        self.major = major
        self.minor = minor

    def to_bytes(self) -> bytes:
        return struct.pack('<H', self.version_code)

    @property
    def version_code(self) -> int:
        legacy_code = self.major * self.LEGACY_MAJOR_SCALE + self.minor
        scale = self.CURRENT_MAJOR_SCALE if legacy_code > self.SCALE_CHANGE_VALUE else self.LEGACY_MAJOR_SCALE
        return self.major * scale + self.minor

    @classmethod
    def from_bytes(cls, bytes_buffer: bytes) -> ProfileVersion:
        value, = struct.unpack('<H', bytes_buffer[0:2])
        scale = cls.CURRENT_MAJOR_SCALE if value > cls.SCALE_CHANGE_VALUE else cls.LEGACY_MAJOR_SCALE
        major = value // scale
        minor = value % scale
        return ProfileVersion(major, minor)

    @classmethod
    def from_sdk_version(cls, sdk_version: str) -> ProfileVersion:
        major, minor, *_ = (int(part) for part in sdk_version.split('.'))
        return cls(major, minor)

    def __str__(self) -> str:
        return f'{self.major}.{self.minor}'


DEFAULT_PROTOCOL_VERSION = ProtocolVersion(2, 3)
DEFAULT_PROFILE_VERSION = ProfileVersion.from_sdk_version(SDK_VERSION)


class FitFileHeader:
    def __init__(self, records_size: int, protocol_version: ProtocolVersion | None = None,
                 profile_version: ProfileVersion | None = None, crc: int | None = None,
                 gen_crc: bool = False) -> None:
        self.records_size = records_size
        self.protocol_version = protocol_version if protocol_version else DEFAULT_PROTOCOL_VERSION
        self.profile_version = profile_version if profile_version else DEFAULT_PROFILE_VERSION

        # crc16 of header bytes 0-11
        #
        # By including the CRC in the header you effectively reset the CRC for the
        # file, (when you CRC-16 a value with itself the CRC returned is 0)
        self.crc: int | None
        if crc is not None:
            self.crc = crc
        elif gen_crc:
            self.crc = FitFileHeader.generate_crc(self.protocol_version, self.profile_version, self.records_size)
        else:
            self.crc = None

    @classmethod
    def generate_crc(
        cls,
        protocol_version: ProtocolVersion,
        profile_version: ProfileVersion,
        records_size: int,
    ) -> int:
        bytes_buffer = struct.pack('B', 14)
        bytes_buffer += protocol_version.to_bytes()
        bytes_buffer += profile_version.to_bytes()
        bytes_buffer += struct.pack('<I', records_size)
        bytes_buffer += b'.FIT'

        return crc16(bytes_buffer)

    @property
    def size(self) -> int:
        if self.crc is not None:
            return 14
        else:
            return 12

    def to_bytes(self) -> bytes:

        bytes_buffer = struct.pack('B', self.size)
        bytes_buffer += self.protocol_version.to_bytes()
        bytes_buffer += self.profile_version.to_bytes()
        bytes_buffer += struct.pack('<I', self.records_size)
        bytes_buffer += b'.FIT'

        if self.crc is not None:
            bytes_buffer += struct.pack('<H', self.crc)

        return bytes_buffer

    @classmethod
    def from_bytes(cls, bytes_buffer: bytes) -> FitFileHeader:
        offset = 0
        size, = struct.unpack('B', bytes_buffer[0:1])
        if size != len(bytes_buffer):
            raise ValueError(f'Size {size} does not match bytes length: {len(bytes_buffer)}')
        offset += 1

        protocol_version = ProtocolVersion.from_bytes(bytes_buffer[offset: offset + 1])
        offset += 1

        profile_version = ProfileVersion.from_bytes(bytes_buffer[offset: offset + 2])
        offset += 2

        records_size, = struct.unpack('<I', bytes_buffer[offset:offset + 4])
        offset += 4

        # .FIT
        tag_value, = struct.unpack('4s', bytes_buffer[offset:offset + 4])
        offset += 4
        if tag_value != b'.FIT':
            raise ValueError('".FIT" not in header.')

        crc = None
        if len(bytes_buffer) == 14:
            crc, = struct.unpack('<H', bytes_buffer[offset:offset + 2])

        return cls(protocol_version=protocol_version,
                   profile_version=profile_version,
                   records_size=records_size,
                   crc=crc)
