import pytest
from fit_tool.field_component import FieldComponent


class TestFieldComponent:
    def test_init(self):
        component = FieldComponent(
            field_id=1,
            accumulate=True,
            bits=8,
            scale=1.0,
            offset=0.0,
        )
        assert component.field_id == 1
        assert component.accumulate is True
        assert component.bits == 8
        assert component.scale == 1.0
        assert component.offset == 0.0

    def test_init_with_different_values(self):
        component = FieldComponent(
            field_id=255,
            accumulate=False,
            bits=16,
            scale=100.0,
            offset=500.0,
        )
        assert component.field_id == 255
        assert component.accumulate is False
        assert component.bits == 16
        assert component.scale == 100.0
        assert component.offset == 500.0

    def test_init_with_zero_values(self):
        component = FieldComponent(
            field_id=0,
            accumulate=False,
            bits=0,
            scale=0.0,
            offset=0.0,
        )
        assert component.field_id == 0
        assert component.accumulate is False
        assert component.bits == 0
        assert component.scale == 0.0
        assert component.offset == 0.0

    def test_init_with_negative_offset(self):
        component = FieldComponent(
            field_id=10,
            accumulate=True,
            bits=32,
            scale=0.001,
            offset=-500.0,
        )
        assert component.field_id == 10
        assert component.offset == -500.0
