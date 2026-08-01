"""Encode modes and projected-record policies (Stage 3 G / SHA-19).

Two explicit modes:

* :attr:`EncodeMode.PRESERVE` (default) — re-emit wire ``source_bytes`` for
  untouched records; re-project dirty records (post-edit PRESERVATION / F).
* :attr:`EncodeMode.CANONICAL` — full projected re-encode of every record with
  normalized headers, sizes, and CRCs.

``strict=True`` forces the canonical path, runs default conformance levels
before returning bytes, and never silently repairs invalid caller-supplied
field data (no range clamping; wrong overridden CRC raises when ``check_crc``).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from fit_tool.data_message import DataMessage
from fit_tool.definition_message import DefinitionMessage
from fit_tool.exceptions import FitEncodingError
from fit_tool.record import Record, RecordHeader

if TYPE_CHECKING:
    from fit_tool.fit_file import FitFile

_TIMESTAMP_FIELD_ID = 253


class EncodeMode(str, Enum):
    """How :meth:`~fit_tool.fit_file.FitFile.to_bytes` rebuilds the FIT stream."""

    PRESERVE = 'preserve'
    CANONICAL = 'canonical'


@dataclass(frozen=True)
class EncodeOptions:
    """Options for FIT serialization.

    Defaults match historical ``to_bytes()`` behavior: preservation when a wire
    document is available, non-strict (no pre-encode validation).
    """

    mode: EncodeMode = EncodeMode.PRESERVE
    strict: bool = False
    check_crc: bool = True

    def __post_init__(self) -> None:
        if self.strict and self.mode is EncodeMode.PRESERVE:
            # Strict validation applies to the projected/canonical rebuild path.
            # Callers who want preserve + validation should call validate() first.
            object.__setattr__(self, 'mode', EncodeMode.CANONICAL)


def resolve_encode_options(
        *,
        mode: EncodeMode | str | None = None,
        preserve: bool | None = None,
        strict: bool = False,
        check_crc: bool = True,
) -> EncodeOptions:
    """Resolve legacy ``preserve=`` and new ``mode=`` into :class:`EncodeOptions`.

    Precedence:

    1. Explicit ``mode``
    2. Explicit ``preserve`` (``True`` → PRESERVE, ``False`` → CANONICAL)
    3. Default PRESERVE

    ``strict=True`` forces CANONICAL (see :class:`EncodeOptions`).
    """
    if mode is not None:
        resolved = EncodeMode(mode) if not isinstance(mode, EncodeMode) else mode
    elif preserve is not None:
        resolved = EncodeMode.PRESERVE if preserve else EncodeMode.CANONICAL
    else:
        resolved = EncodeMode.PRESERVE

    return EncodeOptions(mode=resolved, strict=strict, check_crc=check_crc)


def definition_includes_field(definition: DefinitionMessage | None, field_id: int) -> bool:
    if definition is None:
        return False
    return any(fd.field_id == field_id for fd in definition.field_definitions)


def expand_compressed_header(record: Record) -> RecordHeader:
    """Return a normal data header for a compressed-timestamp data record."""
    header = record.header
    if not header.is_time_compressed:
        return header
    return RecordHeader(
        is_time_compressed=False,
        is_definition=False,
        has_developer_fields=header.has_developer_fields,
        local_id=header.local_id,
        time_offset_seconds=0,
    )


def can_expand_compressed_to_normal(message: DataMessage) -> bool:
    """True when field 253 is on the definition so a normal header can carry the ts."""
    return definition_includes_field(message.definition_message, _TIMESTAMP_FIELD_ID)


def encode_record_projected(
        record: Record,
        *,
        options: EncodeOptions | None = None,
) -> bytes:
    """Serialize one projected record under encode policies.

    Policies for **data** records:

    * **Compressed timestamp headers** — when the active definition includes
      field 253, expand to a normal header and write the reconstructed
      timestamp. If 253 is absent: keep the compressed header (non-strict) or
      raise in strict mode rather than silently drop the timestamp.
    * **Expanded component destinations** — only fields listed on the active
      definition are written (synthetic destinations stay off-wire unless the
      definition already includes them).
    * **Invalid / cleared values** — integer ``None`` encodes as the protocol
      invalid raw value; floats use the all-ones invalid bit pattern. Out-of-range
      values are rejected at set time, not clamped.
    """
    options = options or EncodeOptions()
    header = record.header
    message = record.message

    if (
        not header.is_definition
        and header.is_time_compressed
        and isinstance(message, DataMessage)
        and (options.mode is EncodeMode.CANONICAL or record.dirty)
    ):
        if can_expand_compressed_to_normal(message):
            header = expand_compressed_header(record)
        elif options.strict:
            raise FitEncodingError(
                'Strict canonical encode cannot expand a compressed-timestamp '
                'header without field 253 on the definition (timestamp would be lost).'
            )
        # else: keep compressed header (timestamp remains in the 5-bit offset).

    try:
        return header.to_bytes() + message.to_bytes()
    except (IndexError, struct.error, UnicodeError, ValueError, TypeError) as exc:
        raise FitEncodingError(f'Could not encode FIT record: {exc}') from exc


def apply_strict_precheck(fit_file: FitFile) -> None:
    """Run default conformance levels and raise on ERROR findings."""
    from fit_tool.validation import DEFAULT_LEVELS, validate_fit_file

    validate_fit_file(fit_file, levels=DEFAULT_LEVELS, raise_on_error=True)
