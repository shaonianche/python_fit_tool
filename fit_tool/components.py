"""Component expansion and accumulators for Profile-packed fields.

Decode-time expansion uses the generated Profile main-field registry
(:mod:`fit_tool.profile.component_registry`) plus any
:class:`~fit_tool.field_component.FieldComponent` entries already attached to a
:class:`~fit_tool.field.Field` (for tests and future codegen).

Subfield-gated components are not registered here — they require subfield
selection (Stage 2 D). Nested components (a destination that is itself a
component source) are expanded recursively.
"""

from __future__ import annotations

from collections.abc import Mapping

from fit_tool.field import Field
from fit_tool.field_component import FieldComponent
from fit_tool.message import Message
from fit_tool.profile.component_registry import (
    PROFILE_COMPONENT_SOURCE_COUNT,
    PROFILE_COMPONENTS,
)

# Back-compat alias: historical name used by docs and early tests.
_KNOWN_COMPONENTS = PROFILE_COMPONENTS


def components_for_field(global_id: int, field: Field) -> tuple[FieldComponent, ...]:
    """Return components declared on the field or known for this profile message."""
    if field.components:
        return tuple(field.components)
    return PROFILE_COMPONENTS.get((global_id, field.field_id), ())


def registry_coverage() -> dict[str, object]:
    """Documented coverage of the runtime registry vs Profile main-field sources.

    Returns a dict suitable for tests and capability notes::

        {
            'profile_main_field_sources': 37,
            'registry_entries': 37,
            'coverage_ratio': 1.0,
            'subfield_components': 'deferred (Stage 2 D)',
        }
    """
    registry_entries = len(PROFILE_COMPONENTS)
    profile_sources = PROFILE_COMPONENT_SOURCE_COUNT
    ratio = (
        registry_entries / profile_sources if profile_sources else 1.0
    )
    return {
        'profile_main_field_sources': profile_sources,
        'registry_entries': registry_entries,
        'coverage_ratio': ratio,
        'subfield_components': 'deferred (Stage 2 D)',
    }


def _field_raw_as_int(field: Field) -> int | None:
    """Combine numeric encoded values into a little-endian bit bucket."""
    if not field.is_valid() or not field.encoded_values:
        return None
    if field.base_type.is_string() or field.base_type.is_float():
        return None

    value = 0
    shift = 0
    for encoded in field.encoded_values:
        if encoded is None:
            return None
        width = field.base_type.size * 8
        value |= (int(encoded) & ((1 << width) - 1)) << shift
        shift += width
    return value


def _destination_has_wire_value(field: Field) -> bool:
    """True when the field already holds a non-expanded value from the wire."""
    if field.size == 0 or field.is_expanded_field:
        return False
    if not field.encoded_values:
        return False
    return any(value is not None for value in field.encoded_values)


def _ensure_destination_slot(destination: Field, index: int) -> None:
    """Grow an empty or expanded destination so ``index`` is writable."""
    element_size = max(destination.base_type.size, 1)
    while index >= len(destination.encoded_values):
        destination.encoded_values.append(None)
    needed = (index + 1) * element_size
    if destination.size < needed:
        destination.size = needed


def _apply_component_value(
        destination: Field,
        *,
        index: int,
        raw_part: int,
        component: FieldComponent,
) -> None:
    """Write one expanded component value into *destination* at *index*."""
    _ensure_destination_slot(destination, index)

    scale = component.scale if component.scale else 1.0
    offset = component.offset if component.offset is not None else 0.0
    decoded = (raw_part / scale) - offset
    try:
        destination.set_value(index, decoded)
    except (ValueError, TypeError, OverflowError):
        destination.set_encoded_value(index, int(raw_part), check_validity=False)
    destination.is_expanded_field = True


def expand_message_components(
        message: Message,
        accumulators: dict[tuple[int, int], int] | None = None,
) -> dict[tuple[int, int], int]:
    """Expand packed component source fields into destination fields on ``message``.

    - Components are extracted least-significant bits first.
    - Accumulate components apply unsigned modular rollover state keyed by
      ``(global_id, destination_field_id)``.
    - Wire-present destinations are not overwritten (except accumulate state is
      still updated when the component is marked accumulate).
    - Nested component sources are expanded recursively after a destination is
      written.
    - Multiple components targeting the same field id append as array elements.

    Returns the (possibly updated) accumulator map.
    """
    if accumulators is None:
        accumulators = {}

    global_id = message.global_id
    fields_by_id: Mapping[int, Field] = {
        field.field_id: field for field in getattr(message, 'fields', [])
    }
    expanded_sources: set[int] = set()
    # Next write index for multi-component array destinations within one message.
    dest_write_index: dict[int, int] = {}

    def expand_field(source: Field) -> None:
        if source.field_id in expanded_sources:
            return
        components = components_for_field(global_id, source)
        if not components:
            return
        raw = _field_raw_as_int(source)
        if raw is None:
            return

        expanded_sources.add(source.field_id)
        bit_offset = 0
        # Variable-length packed fields may list more component slots than the
        # actual payload carries (e.g. hr.event_timestamp_12). Stop once the
        # source byte size is exhausted so we do not invent values from zero bits.
        available_bits = max(0, int(source.size) * 8)
        for component in components:
            bits = component.bits or 0
            if bits <= 0:
                continue
            if bit_offset + bits > available_bits:
                break
            mask = (1 << bits) - 1
            part = (raw >> bit_offset) & mask
            bit_offset += bits

            if component.accumulate:
                key = (global_id, component.field_id)
                previous = accumulators.get(key, 0)
                # Rollover: unsigned modular difference in the component bit width.
                max_value = 1 << component.bits if component.bits else 1
                delta = (part - (previous % max_value)) % max_value
                accumulated = previous + delta
                accumulators[key] = accumulated
                raw_part = accumulated
            else:
                raw_part = part

            destination = fields_by_id.get(component.field_id)
            if destination is None:
                continue

            if _destination_has_wire_value(destination):
                # Explicit on-wire value wins; accumulate state already updated.
                continue

            index = dest_write_index.get(component.field_id, 0)
            # If this destination was expanded earlier in the same message and is
            # not an array-style multi-write, keep the first expanded value unless
            # we are appending additional component elements (index advances).
            _apply_component_value(
                destination,
                index=index,
                raw_part=raw_part,
                component=component,
            )
            dest_write_index[component.field_id] = index + 1

            # Nested components: destination may itself be a component source.
            expand_field(destination)

    for source in list(getattr(message, 'fields', [])):
        expand_field(source)

    return accumulators


__all__ = [
    'PROFILE_COMPONENT_SOURCE_COUNT',
    'PROFILE_COMPONENTS',
    '_KNOWN_COMPONENTS',
    'components_for_field',
    'expand_message_components',
    'registry_coverage',
]
