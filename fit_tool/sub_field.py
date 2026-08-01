from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from fit_tool.base_type import BaseType
from fit_tool.field_component import FieldComponent


def _ref_comparable(value):
    """Normalize reference field values for membership checks (enums → raw int)."""
    if isinstance(value, Enum):
        return value.value
    return value


class SubField:

    def __init__(
            self,
            name: str = 'unknown',
            base_type: BaseType = BaseType.ENUM,
            scale: float = 1.0,
            offset: float = 0.0,
            units: str = '',
            reference_map: dict[int, list[int]] = None,
            components=None,
    ):
        if components is None:
            components = []
        self.name = name
        self.base_type = base_type
        self.scale = scale
        # Profile / codegen historically defaulted offset incorrectly to 1.0;
        # missing offset means no offset applied (0.0).
        self.offset = offset
        self.units = units

        self.reference_map = reference_map or {}
        self.components = list(components) if components else []

    def add_component(self, component: FieldComponent) -> None:
        self.components.append(component)

    def is_valid(self, fields: Sequence) -> bool:
        """Return True when every reference field matches a permitted value.

        Garmin Profile subfield refs are conjunctive (AND): each entry in
        ``reference_map`` must be present, valid, and carry a value listed for
        that ref field. An empty map is always valid (no constraints).

        Missing or invalid reference fields fail the match (the subfield is not
        active until its refs are known).
        """
        if not self.reference_map:
            return True

        fields_by_id = {field.field_id: field for field in fields}
        for field_id, permitted in self.reference_map.items():
            field = fields_by_id.get(field_id)
            if field is None or field.is_not_valid():
                return False
            value = _ref_comparable(field.get_value())
            if value is None:
                return False
            permitted_values = {_ref_comparable(item) for item in permitted}
            if value not in permitted_values:
                return False
        return True


@dataclass(frozen=True)
class SubFieldResolution:
    """Result of resolving Profile subfields for a parent field.

    * ``selected`` — first matching subfield in Profile order (deterministic),
      or ``None`` when none match. Decode/encode use this for scale/units.
    * ``matches`` — all matching subfields.
    * ``is_ambiguous`` — more than one match; PROFILE validation reports ERROR.
    """

    selected: SubField | None
    matches: tuple[SubField, ...]

    @property
    def is_ambiguous(self) -> bool:
        return len(self.matches) > 1

    @property
    def has_match(self) -> bool:
        return self.selected is not None
