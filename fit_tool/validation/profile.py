"""PROFILE-level validation: developer fields, subfields, catalog rules."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from fit_tool.base_type import BaseType
from fit_tool.data_message import DataMessage
from fit_tool.definition_message import DefinitionMessage
from fit_tool.profile.field_catalog import (
    PROFILE_ENUM_FIELD_COUNT,
    PROFILE_ENUM_TYPE_COUNT,
    PROFILE_ENUM_VALUES,
    PROFILE_FIELD_COUNT,
    PROFILE_FIELDS,
    PROFILE_MESSAGE_COUNT,
    PROFILE_SDK_VERSION,
)
from fit_tool.profile.profile_type import MesgNum
from fit_tool.record import Record
from fit_tool.validation.context import ValidationContext
from fit_tool.validation.report import (
    DEFAULT_PROFILE_SCOPE,
    ConformanceLevel,
    ProfileScope,
    add_error,
    enum_value,
    normalize_profile_scope,
)

# High-frequency Activity / Workout messages for PROFILE DOMAIN scope (§3.1 M4).
DOMAIN_MESSAGE_IDS: frozenset[int] = frozenset({
    MesgNum.FILE_ID.value,       # 0
    MesgNum.SESSION.value,       # 18
    MesgNum.LAP.value,           # 19
    MesgNum.RECORD.value,        # 20
    MesgNum.EVENT.value,         # 21
    MesgNum.DEVICE_INFO.value,   # 23
    MesgNum.WORKOUT.value,       # 26
    MesgNum.WORKOUT_STEP.value,  # 27
    MesgNum.ACTIVITY.value,      # 34
})


def message_ids_for_scope(scope: ProfileScope) -> frozenset[int] | None:
    """Return global message ids in scope, or ``None`` when scope is CORE (no native catalog)."""
    if scope is ProfileScope.CORE:
        return None
    if scope is ProfileScope.DOMAIN:
        return DOMAIN_MESSAGE_IDS
    # FULL: every message that appears in the catalog.
    return frozenset(global_id for global_id, _field_id in PROFILE_FIELDS)


def profile_rule_coverage(scope: ProfileScope | None = None) -> dict[str, Any]:
    """Publish PROFILE validation coverage metrics for *scope*.

    Used by docs/tests and release notes. Percentages are relative to the full
    bundled Profile field catalog (``PROFILE_*`` constants from gen export).
    """
    selected = normalize_profile_scope(scope)
    message_ids = message_ids_for_scope(selected)

    rule_families: tuple[str, ...]
    if message_ids is None:
        native_messages = 0
        native_fields = 0
        enum_fields = 0
        rule_families = (
            'developer_fields',
            'subfield_ambiguity',
        )
    else:
        native_messages = len({gid for gid in message_ids if any(
            key[0] == gid for key in PROFILE_FIELDS
        )})
        native_fields = sum(1 for key in PROFILE_FIELDS if key[0] in message_ids)
        enum_fields = sum(
            1
            for key, meta in PROFILE_FIELDS.items()
            if key[0] in message_ids and meta[2] in PROFILE_ENUM_VALUES
        )
        rule_families = (
            'developer_fields',
            'subfield_ambiguity',
            'native_base_type',
            'closed_enum_values',
        )

    def _pct(part: int, whole: int) -> float:
        if whole <= 0:
            return 0.0
        return round(100.0 * part / whole, 2)

    return {
        'scope': selected.value,
        'profile_sdk_version': PROFILE_SDK_VERSION,
        'rule_families': list(rule_families),
        'full_messages': PROFILE_MESSAGE_COUNT,
        'full_fields': PROFILE_FIELD_COUNT,
        'full_enum_types': PROFILE_ENUM_TYPE_COUNT,
        'full_enum_fields': PROFILE_ENUM_FIELD_COUNT,
        'native_messages_in_scope': native_messages,
        'native_fields_in_scope': native_fields,
        'enum_fields_in_scope': enum_fields,
        'message_coverage_pct': _pct(native_messages, PROFILE_MESSAGE_COUNT),
        'field_coverage_pct': _pct(native_fields, PROFILE_FIELD_COUNT),
        'enum_field_coverage_pct': _pct(enum_fields, PROFILE_ENUM_FIELD_COUNT),
        'default_for_strict': selected is DEFAULT_PROFILE_SCOPE,
    }


def collect_profile_findings(context: ValidationContext) -> None:
    """Run PROFILE checks at the scope selected for this run."""
    data_messages = context.data_messages
    findings = context.findings
    indices = context.data_message_indices

    # CORE (always when PROFILE is selected).
    _collect_developer_field_findings(data_messages, findings, indices)
    for message_pos, message in enumerate(data_messages):
        _collect_subfield_ambiguity_findings(
            message,
            findings,
            indices.get(message_pos),
        )

    message_ids = message_ids_for_scope(context.profile_scope)
    if message_ids is None:
        return

    # DOMAIN / FULL: data-driven native rules from gen-exported field catalog.
    _collect_native_base_type_findings(context.records, findings, message_ids)
    _collect_closed_enum_findings(data_messages, findings, indices, message_ids)


def _collect_developer_field_findings(
        data_messages: Sequence[DataMessage],
        findings: list,
        data_message_indices: Mapping[int, int],
) -> None:
    developer_data_indices = set()
    descriptions = {}

    for message_pos, message in enumerate(data_messages):
        record_index = data_message_indices.get(message_pos)
        if message.global_id == MesgNum.DEVELOPER_DATA_ID.value:
            developer_data_index = enum_value(getattr(message, 'developer_data_index', None))
            if developer_data_index is None:
                add_error(
                    findings,
                    ConformanceLevel.PROFILE,
                    'developer_data_id is missing developer_data_index.',
                    record_index,
                )
            else:
                application_id = getattr(message, 'application_id', None)
                if application_id is None or len(application_id) != 16:
                    add_error(
                        findings,
                        ConformanceLevel.PROFILE,
                        'developer_data_id.application_id must contain exactly 16 bytes.',
                        record_index,
                    )
                if developer_data_index in developer_data_indices:
                    add_error(
                        findings,
                        ConformanceLevel.PROFILE,
                        f'Duplicate developer_data_id for developer_data_index {developer_data_index}.',
                        record_index,
                    )
                else:
                    developer_data_indices.add(developer_data_index)

        elif message.global_id == MesgNum.FIELD_DESCRIPTION.value:
            developer_data_index = enum_value(getattr(message, 'developer_data_index', None))
            field_number = enum_value(getattr(message, 'field_definition_number', None))
            fit_base_type_id = enum_value(getattr(message, 'fit_base_type_id', None))
            if developer_data_index not in developer_data_indices:
                add_error(
                    findings,
                    ConformanceLevel.PROFILE,
                    f'field_description references developer_data_index {developer_data_index} '
                    f'before its developer_data_id message.',
                    record_index,
                )
            if field_number is None or fit_base_type_id is None:
                add_error(
                    findings,
                    ConformanceLevel.PROFILE,
                    'field_description requires field_definition_number and fit_base_type_id.',
                    record_index,
                )
            else:
                try:
                    base_type = BaseType(fit_base_type_id)
                except ValueError:
                    add_error(
                        findings,
                        ConformanceLevel.PROFILE,
                        f'field_description contains unknown fit_base_type_id {fit_base_type_id}.',
                        record_index,
                    )
                    base_type = None
                if base_type is not None:
                    key = (developer_data_index, field_number)
                    if key in descriptions:
                        add_error(
                            findings,
                            ConformanceLevel.PROFILE,
                            f'Duplicate field_description for developer field {key}.',
                            record_index,
                        )
                    else:
                        descriptions[key] = base_type

        for developer_field in message.developer_fields:
            if not developer_field.is_valid():
                continue
            key = (developer_field.developer_data_index, developer_field.field_id)
            described_base_type = descriptions.get(key)
            if described_base_type is None:
                add_error(
                    findings,
                    ConformanceLevel.PROFILE,
                    f'Developer field {key} is used before a matching field_description message.',
                    record_index,
                )
            elif described_base_type != developer_field.base_type:
                add_error(
                    findings,
                    ConformanceLevel.PROFILE,
                    f'Developer field {key} uses {developer_field.base_type.name}, but its '
                    f'field_description declares {described_base_type.name}.',
                    record_index,
                )


def _collect_subfield_ambiguity_findings(
        message: DataMessage,
        findings: list,
        record_index: int | None,
) -> None:
    """PROFILE ERROR when more than one subfield matches the same ref values.

    Decode still picks the first match (see :meth:`Field.resolve_sub_field`);
    ambiguity is reported only at the PROFILE level.
    """
    fields = getattr(message, 'fields', None) or []
    if not fields:
        return
    for field in fields:
        if not getattr(field, 'sub_fields', None):
            continue
        if not field.is_valid():
            continue
        resolution = field.resolve_sub_field(fields)
        if not resolution.is_ambiguous:
            continue
        names = ', '.join(sub.name for sub in resolution.matches)
        add_error(
            findings,
            ConformanceLevel.PROFILE,
            f'Ambiguous subfields for {message.name}.{field.name}: {names}.',
            record_index,
        )


def _collect_native_base_type_findings(
        records: Sequence[Record],
        findings: list,
        message_ids: frozenset[int],
) -> None:
    """ERROR when a definition declares a base type that differs from Profile.

    Only main fields present in the gen-exported catalog are checked. Unknown
    field ids (not in Profile for that message) are ignored here — they belong
    to unknown-field / PRESERVATION work.
    """
    for record_index, record in enumerate(records):
        message = record.message
        if not isinstance(message, DefinitionMessage):
            continue
        if message.global_id not in message_ids:
            continue
        for field_def in message.field_definitions:
            key = (message.global_id, field_def.field_id)
            catalog_entry = PROFILE_FIELDS.get(key)
            if catalog_entry is None:
                continue
            field_name, expected_base_type, _type_name, _units, _scale, _offset = catalog_entry
            if field_def.base_type is expected_base_type:
                continue
            add_error(
                findings,
                ConformanceLevel.PROFILE,
                (
                    f'Native field {field_name!r} (id {field_def.field_id}) on global '
                    f'message {message.global_id} declares base type '
                    f'{field_def.base_type.name}, but Profile requires '
                    f'{expected_base_type.name}.'
                ),
                record_index,
            )


def _collect_closed_enum_findings(
        data_messages: Sequence[DataMessage],
        findings: list,
        data_message_indices: Mapping[int, int],
        message_ids: frozenset[int],
) -> None:
    """ERROR when a closed Profile enum field holds an unknown value.

    Only Types-sheet entries with base type ``enum`` are checked (closed sets).
    Open lists (manufacturer, garmin_product, …) and bitfields are excluded from
    the catalog. Invalid FIT sentinels are skipped.
    """
    for message_pos, message in enumerate(data_messages):
        if message.global_id not in message_ids:
            continue
        record_index = data_message_indices.get(message_pos)
        for field in getattr(message, 'fields', None) or []:
            if not field.is_valid():
                continue
            key = (message.global_id, field.field_id)
            catalog_entry = PROFILE_FIELDS.get(key)
            if catalog_entry is None:
                continue
            field_name, _base_type, type_name, _units, _scale, _offset = catalog_entry
            if not type_name:
                continue
            allowed = PROFILE_ENUM_VALUES.get(type_name)
            if allowed is None:
                continue
            invalid_raw = field.base_type.invalid_raw_value()
            for encoded in field.encoded_values:
                if encoded is None or encoded == invalid_raw:
                    continue
                if encoded in allowed:
                    continue
                add_error(
                    findings,
                    ConformanceLevel.PROFILE,
                    (
                        f'Native field {message.name}.{field_name} has value '
                        f'{encoded!r} outside Profile enum {type_name!r}.'
                    ),
                    record_index,
                )


__all__ = [
    'DOMAIN_MESSAGE_IDS',
    'collect_profile_findings',
    'message_ids_for_scope',
    'profile_rule_coverage',
]
