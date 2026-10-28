"""PRESERVATION-level validation: post-edit rewrite loss."""

from __future__ import annotations

from fit_tool.data_message import DataMessage
from fit_tool.field import UnknownField
from fit_tool.validation.context import ValidationContext
from fit_tool.validation.report import ConformanceLevel, Severity, ValidationFinding


def collect_preservation_findings(context: ValidationContext) -> None:
    """Report post-edit rewrite risks (opt-in PRESERVATION level).

    Findings fire when an unknown native field lost its captured wire slice
    (``raw_bytes is None``) so a projected re-encode cannot guarantee the same
    bytes. Untouched records that still have ``source_bytes`` are fine.
    """
    for record_index, record in enumerate(context.records):
        if record.is_definition or not isinstance(record.message, DataMessage):
            continue
        message = record.message
        for field in message.fields:
            if not isinstance(field, UnknownField):
                continue
            if not field.is_valid():
                continue
            if field.raw_bytes is None:
                context.findings.append(
                    ValidationFinding(
                        level=ConformanceLevel.PRESERVATION,
                        severity=Severity.ERROR,
                        message=(
                            f'Unknown field id {field.field_id} on message '
                            f'{message.name!r} (global {message.global_id}) lost '
                            f'raw_bytes; post-edit rewrite cannot preserve the '
                            f'original wire slice.'
                        ),
                        record_index=record_index,
                    )
                )
            elif len(field.raw_bytes) != field.size:
                context.findings.append(
                    ValidationFinding(
                        level=ConformanceLevel.PRESERVATION,
                        severity=Severity.ERROR,
                        message=(
                            f'Unknown field id {field.field_id} on message '
                            f'{message.name!r} has raw_bytes length '
                            f'{len(field.raw_bytes)} != field size {field.size}.'
                        ),
                        record_index=record_index,
                    )
                )


__all__ = ['collect_preservation_findings']
