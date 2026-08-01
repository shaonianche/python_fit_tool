from __future__ import annotations

import csv
import shutil
import struct
import tempfile
from collections.abc import Iterable, Iterator
from typing import TYPE_CHECKING, BinaryIO

from fit_tool.decoder import FitDecoder
from fit_tool.encode import (
    EncodeMode,
    EncodeOptions,
    apply_strict_precheck,
    encode_record_projected,
    resolve_encode_options,
)
from fit_tool.exceptions import FitCRCError, FitEncodingError
from fit_tool.fit_file_header import FitFileHeader
from fit_tool.record import Record
from fit_tool.utils.crc import crc16
from fit_tool.utils.logging import logger
from fit_tool.wire.encoder import encode_document, encode_document_mixed
from fit_tool.wire.model import FitDocument

if TYPE_CHECKING:
    from fit_tool.validation import ConformanceLevel, ValidationReport


class FitFile:
    """Public FIT file facade.

    Decode uses the unified :class:`~fit_tool.decoder.FitDecoder` state machine
    (wire layer + projection) shared with streaming APIs. When the source is an
    in-memory buffer, the raw :class:`~fit_tool.wire.model.FitDocument` is retained
    so :meth:`to_bytes` can re-emit the original bytes for **unedited** records
    (preservation mode).

    **Encode modes** (Stage 3 G):

    * :attr:`~fit_tool.encode.EncodeMode.PRESERVE` (default) — unedited
      ``source_bytes`` + dirty re-project (post-edit PRESERVATION / F).
    * :attr:`~fit_tool.encode.EncodeMode.CANONICAL` — full projected re-encode
      with normalized sizes/CRCs; compressed dirty headers may expand to normal.

    Pass ``mode=`` / ``strict=`` to :meth:`to_bytes`, or the legacy
    ``preserve=True|False`` alias (``False`` maps to CANONICAL).

    **Post-edit PRESERVATION:** mutating fields on projected messages marks the
    owning :class:`~fit_tool.record.Record` dirty (via field mutation hooks).
    Preserve mode then re-encodes only dirty records and copies ``source_bytes``
    for the rest. Structural edits (:meth:`add_record`, :meth:`remove_record`,
    :meth:`mark_dirty`, CRC override) drop the wire document and fully re-project.
    """

    def __init__(
            self,
            header: FitFileHeader,
            records: list[Record],
            crc: int | None = None,
            *,
            wire_document: FitDocument | None = None,
    ):
        self.header = header
        self.records = records
        self._crc = crc  # crc16 of header and records (last segment when chained)
        self._crc_overridden = False
        self._wire_document = wire_document

    @property
    def wire_document(self) -> FitDocument | None:
        """Raw multi-segment wire model when decoded from a buffer.

        Present after buffer decode until a **structural** edit clears it
        (:meth:`mark_dirty`, add/remove record, CRC override). Per-record field
        edits keep this document so untouched records can be re-emitted from
        ``source_bytes``.
        """
        return self._wire_document

    @property
    def crc(self) -> int | None:
        return self._crc

    @crc.setter
    def crc(self, value: int | None) -> None:
        self._crc = value
        self._crc_overridden = value is not None
        self._wire_document = None

    def mark_dirty(self) -> None:
        """Mark the file structurally dirty (full re-encode on next ``to_bytes``).

        Clears the retained wire document. Prefer editing fields in place so
        only the affected :class:`~fit_tool.record.Record` is marked dirty and
        post-edit PRESERVATION can keep other records' ``source_bytes``.
        """
        self._crc = None
        self._crc_overridden = False
        self._wire_document = None

    def add_record(self, record: Record) -> None:
        self.records.append(record)
        self.mark_dirty()

    def remove_record(self, record: Record) -> None:
        self.records.remove(record)
        self.mark_dirty()

    def has_dirty_records(self) -> bool:
        """Return True when any projected record was edited in place."""
        return any(record.dirty for record in self.records)

    @classmethod
    def from_file(cls, path: str, *, allow_trailing_bytes: bool = False) -> FitFile:
        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            return FitFile.from_bytes(
                bytes_buffer,
                allow_trailing_bytes=allow_trailing_bytes,
            )

    @classmethod
    def iter_file(
            cls,
            path: str,
            check_crc: bool = True,
            *,
            allow_trailing_bytes: bool = False,
    ) -> Iterator[Record]:
        from fit_tool.fit_file_stream import iter_fit_file
        return iter_fit_file(
            path,
            check_crc=check_crc,
            allow_trailing_bytes=allow_trailing_bytes,
        )

    @classmethod
    def iter_stream(
            cls,
            file_object: BinaryIO,
            check_crc: bool = True,
            *,
            allow_trailing_bytes: bool = False,
    ) -> Iterator[Record]:
        from fit_tool.fit_file_stream import iter_fit_stream
        return iter_fit_stream(
            file_object,
            check_crc=check_crc,
            allow_trailing_bytes=allow_trailing_bytes,
        )

    @classmethod
    def from_bytes(
            cls,
            bytes_buffer: bytes,
            check_crc: bool = True,
            *,
            allow_trailing_bytes: bool = False,
    ) -> FitFile:
        """Parse FIT bytes via the shared FitDecoder state machine.

        Chained multi-segment files yield the concatenation of all segments'
        projected records. Trailing non-header bytes raise
        :class:`~fit_tool.exceptions.FitParseError` unless
        ``allow_trailing_bytes`` is true.
        """
        decoder = FitDecoder(
            check_crc=check_crc,
            allow_trailing_bytes=allow_trailing_bytes,
        )
        header, records, calculated_crc = decoder.decode(bytes_buffer)
        return cls(
            header,
            records,
            calculated_crc,
            wire_document=decoder.wire_document,
        )

    def to_bytes(
            self,
            check_crc: bool = True,
            *,
            preserve: bool | None = None,
            mode: EncodeMode | str | None = None,
            strict: bool = False,
            options: EncodeOptions | None = None,
    ) -> bytes:
        """Serialize this file.

        **Modes** (see :class:`~fit_tool.encode.EncodeMode`):

        * **PRESERVE** (default; ``preserve=True``) when a wire document is
          available:

          - **No dirty records** — re-emit original segment bytes bit-identically
            (chained files, unknown layouts, compressed headers).
          - **Some dirty records** — copy ``source_bytes`` for untouched records
            and re-project dirty ones; recompute header size and file CRC only for
            segments that contain edits (post-edit PRESERVATION).

        * **CANONICAL** (``mode=EncodeMode.CANONICAL`` or ``preserve=False``) —
          full projected re-encode of every record; normalized sizes and CRCs.

        ``strict=True`` forces CANONICAL, runs WIRE+PROFILE+FILE_TYPE validation
        before encode, and raises rather than silently repairing invalid field
        data or mismatched overridden CRCs (when ``check_crc`` is true).

        Prefer ``mode=`` / ``strict=`` for new code; ``preserve=`` remains the
        boolean compatibility alias.
        """
        if options is None:
            options = resolve_encode_options(
                mode=mode,
                preserve=preserve,
                strict=strict,
                check_crc=check_crc,
            )
        elif preserve is not None or mode is not None or strict or check_crc is not True:
            # Explicit kwargs win over a partial options object when both given.
            options = resolve_encode_options(
                mode=mode if mode is not None else options.mode,
                preserve=preserve,
                strict=strict or options.strict,
                check_crc=check_crc if check_crc is not True else options.check_crc,
            )

        if options.strict:
            apply_strict_precheck(self)

        if options.mode is EncodeMode.PRESERVE and self._wire_document is not None:
            if self.has_dirty_records():
                return self._to_bytes_preserve_edits(options=options)
            return encode_document(self._wire_document, recompute_crc=False)

        return self._to_bytes_projected(options=options)

    def _to_bytes_preserve_edits(self, *, options: EncodeOptions) -> bytes:
        """Mixed preserve: untouched wire bytes + re-encoded dirty records."""
        document = self._wire_document
        assert document is not None

        wire_count = sum(len(segment.records) for segment in document.segments)
        if wire_count != len(self.records):
            # Structural mismatch — fall back to full projected encode.
            logger.warning(
                'Record count (%s) does not match wire document (%s); '
                'falling back to full re-encode.',
                len(self.records),
                wire_count,
            )
            self.mark_dirty()
            return self._to_bytes_projected(
                options=EncodeOptions(
                    mode=EncodeMode.CANONICAL,
                    strict=options.strict,
                    check_crc=options.check_crc,
                )
            )

        projected_iter = iter(self.records)
        segment_record_bytes: list[list[bytes]] = []
        segment_recompute: list[bool] = []

        try:
            for segment in document.segments:
                rec_bytes: list[bytes] = []
                dirty_in_segment = False
                for raw in segment.records:
                    projected = next(projected_iter)
                    if projected.dirty:
                        dirty_in_segment = True
                        rec_bytes.append(
                            encode_record_projected(projected, options=options)
                        )
                    elif projected.source_bytes is not None:
                        rec_bytes.append(projected.source_bytes)
                    elif raw.source_bytes:
                        rec_bytes.append(raw.source_bytes)
                    else:
                        rec_bytes.append(
                            encode_record_projected(projected, options=options)
                        )
                        dirty_in_segment = True
                segment_record_bytes.append(rec_bytes)
                segment_recompute.append(dirty_in_segment)
        except FitEncodingError:
            raise
        except (IndexError, struct.error, UnicodeError, ValueError) as exc:
            raise FitEncodingError(f'Could not encode FIT records: {exc}') from exc

        result = encode_document_mixed(document, segment_record_bytes, segment_recompute)
        # Stale file CRC after mixed encode; leave override semantics to caller.
        self._crc = None
        self._crc_overridden = False
        return result

    def _to_bytes_projected(self, *, options: EncodeOptions) -> bytes:
        """Full projected re-encode (canonical path, or no wire document)."""
        try:
            record_buffers = [
                encode_record_projected(record, options=options)
                for record in self.records
            ]
        except FitEncodingError:
            raise
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
                if options.check_crc:
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

    def to_file(
            self,
            path: str,
            *,
            preserve: bool | None = None,
            mode: EncodeMode | str | None = None,
            strict: bool = False,
    ) -> None:
        with open(path, 'wb') as file_object:
            file_object.write(
                self.to_bytes(preserve=preserve, mode=mode, strict=strict)
            )

    def validate(
        self,
        levels: Iterable[ConformanceLevel] | None = None,
        *,
        raise_on_error: bool = False,
    ) -> ValidationReport:
        """Validate this file at selected conformance levels.

        Independent of :class:`~fit_tool.fit_file_builder.FitFileBuilder`.
        Defaults to WIRE + PROFILE + FILE_TYPE. Use
        ``levels={ConformanceLevel.WIRE}`` for structure-only checks after decode,
        or include :attr:`~fit_tool.validation.ConformanceLevel.PRESERVATION`
        for opt-in post-edit rewrite-loss findings.

        See :func:`~fit_tool.validation.validate_fit_file` for details.
        """
        from fit_tool.validation import validate_fit_file

        return validate_fit_file(self, levels=levels, raise_on_error=raise_on_error)
