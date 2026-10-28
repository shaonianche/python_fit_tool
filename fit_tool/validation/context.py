"""Shared state for one validation run."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from fit_tool.data_message import DataMessage
from fit_tool.record import Record
from fit_tool.validation.report import (
    ConformanceLevel,
    ProfileScope,
    ValidationFinding,
    add_error,
)


@dataclass
class ValidationContext:
    """Records, projected data messages, and collected findings for one run.

    Level collectors take a single context so they do not need to thread the
    same four parallel arguments through every helper.
    """

    records: Sequence[Record]
    findings: list[ValidationFinding]
    data_messages: list[DataMessage]
    data_message_indices: Mapping[int, int]
    profile_scope: ProfileScope
    message_counts: Counter

    def error(
            self,
            level: ConformanceLevel,
            message: str,
            record_index: int | None = None,
    ) -> None:
        add_error(self.findings, level, message, record_index)


def build_context(
        records: Sequence[Record],
        findings: list[ValidationFinding],
        profile_scope: ProfileScope,
) -> ValidationContext:
    """Collect the data messages and indices shared by every level."""
    data_messages: list[DataMessage] = []
    data_message_indices: dict[int, int] = {}
    for record_index, record in enumerate(records):
        if not record.is_definition and isinstance(record.message, DataMessage):
            data_message_indices[len(data_messages)] = record_index
            data_messages.append(record.message)

    return ValidationContext(
        records=records,
        findings=findings,
        data_messages=data_messages,
        data_message_indices=data_message_indices,
        profile_scope=profile_scope,
        message_counts=Counter(message.global_id for message in data_messages),
    )
