import pytest
from fit_tool.field_component import FieldComponent


class TestFieldComponent:
    @pytest.mark.parametrize("field_id, accumulate, bits, scale, offset", [
        (1, True, 8, 1.0, 0.0),
        (255, False, 16, 100.0, 500.0),
        (0, False, 0, 0.0, 0.0),
        (10, True, 32, 0.001, -500.0),
    ])
    def test_init(self, field_id, accumulate, bits, scale, offset):
        component = FieldComponent(
            field_id=field_id,
            accumulate=accumulate,
            bits=bits,
            scale=scale,
            offset=offset,
        )
        assert component.field_id == field_id
        assert component.accumulate is accumulate
        assert component.bits == bits
        assert component.scale == scale
        assert component.offset == offset
