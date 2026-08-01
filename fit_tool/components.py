"""Component expansion and accumulators for Profile-packed fields.

Generated message classes historically omit component metadata (codegen path
commented out). A small registry covers common packed fields; expansion also
honours any :class:`~fit_tool.field_component.FieldComponent` entries already
attached to a :class:`~fit_tool.field.Field`.
"""

from __future__ import annotations

from collections.abc import Mapping

from fit_tool.field import Field
from fit_tool.field_component import FieldComponent
from fit_tool.message import Message

# (global_message_number, containing_field_id) -> components (LSB first)
# Scales/offsets match Garmin Profile 21.x for record message packing.
_KNOWN_COMPONENTS: dict[tuple[int, int], tuple[FieldComponent, ...]] = {
    # record.compressed_speed_distance (field 8) → speed (6), distance (5)
    (20, 8): (
        FieldComponent(field_id=6, accumulate=False, bits=12, scale=100.0, offset=0.0),
        FieldComponent(field_id=5, accumulate=False, bits=12, scale=16.0, offset=0.0),
    ),
    # record.compressed_accumulated_power (field 28) → accumulated_power (29)
    (20, 28): (
        FieldComponent(field_id=29, accumulate=True, bits=16, scale=1.0, offset=0.0),
    ),
}


def components_for_field(global_id: int, field: Field) -> tuple[FieldComponent, ...]:
    """Return components declared on the field or known for this profile message."""
    if field.components:
        return tuple(field.components)
    return _KNOWN_COMPONENTS.get((global_id, field.field_id), ())


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


def expand_message_components(
        message: Message,
        accumulators: dict[tuple[int, int], int] | None = None,
) -> dict[tuple[int, int], int]:
    """Expand packed component source fields into destination fields on ``message``.

    Returns the (possibly updated) accumulator map keyed by
    ``(global_id, destination_field_id)``.
    """
    if accumulators is None:
        accumulators = {}

    global_id = message.global_id
    fields_by_id: Mapping[int, Field] = {
        field.field_id: field for field in getattr(message, 'fields', [])
    }

    for source in list(getattr(message, 'fields', [])):
        components = components_for_field(global_id, source)
        if not components:
            continue
        raw = _field_raw_as_int(source)
        if raw is None:
            continue

        bit_offset = 0
        for component in components:
            mask = (1 << component.bits) - 1 if component.bits else 0
            part = (raw >> bit_offset) & mask
            bit_offset += component.bits

            if component.accumulate:
                key = (global_id, component.field_id)
                previous = accumulators.get(key, 0)
                # Rollover: unsigned modular difference in the component bit width.
                max_value = 1 << component.bits
                delta = (part - (previous % max_value)) % max_value
                accumulated = previous + delta
                accumulators[key] = accumulated
                raw_part = accumulated
            else:
                raw_part = part

            destination = fields_by_id.get(component.field_id)
            if destination is None:
                continue
            if destination.size == 0:
                destination.size = max(destination.base_type.size, 1)
                destination.encoded_values = [None]

            # Component scale/offset yield the destination field's *decoded* value;
            # set_value re-encodes with the destination field's own scale/offset.
            scale = component.scale if component.scale else 1.0
            offset = component.offset if component.offset is not None else 0.0
            decoded = (raw_part / scale) - offset
            try:
                destination.set_value(0, decoded)
            except (ValueError, TypeError):
                destination.set_encoded_value(0, int(raw_part), check_validity=False)
            destination.is_expanded_field = True

    return accumulators
