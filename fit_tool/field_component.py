from dataclasses import dataclass


@dataclass
class FieldComponent:
    field_id: int
    accumulate: bool
    bits: int
    scale: float
    offset: float
