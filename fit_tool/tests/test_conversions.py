import pytest
from fit_tool.utils.conversions import (
    MILLISECONDS_EPOCH_1989_DELTA,
    to_seconds_since_1989_epoch,
    to_milliseconds_since_epoch,
    to_semicircles,
    to_degrees,
)


class TestEpochConversions:
    def test_to_seconds_since_1989_epoch(self):
        ms_epoch = MILLISECONDS_EPOCH_1989_DELTA
        assert to_seconds_since_1989_epoch(ms_epoch) == 0

        ms_epoch = MILLISECONDS_EPOCH_1989_DELTA + 1000
        assert to_seconds_since_1989_epoch(ms_epoch) == 1

        ms_epoch = MILLISECONDS_EPOCH_1989_DELTA + 60000
        assert to_seconds_since_1989_epoch(ms_epoch) == 60

    def test_to_milliseconds_since_epoch(self):
        assert to_milliseconds_since_epoch(0) == MILLISECONDS_EPOCH_1989_DELTA

        assert to_milliseconds_since_epoch(1) == MILLISECONDS_EPOCH_1989_DELTA + 1000

        assert to_milliseconds_since_epoch(60) == MILLISECONDS_EPOCH_1989_DELTA + 60000

    def test_round_trip_conversion(self):
        original_ms = 1700000000000
        seconds = to_seconds_since_1989_epoch(original_ms)
        result_ms = to_milliseconds_since_epoch(seconds)
        assert result_ms == (original_ms // 1000) * 1000


class TestCoordinateConversions:
    def test_to_semicircles(self):
        assert to_semicircles(0) == 0

        assert to_semicircles(180) == 2147483648

        assert to_semicircles(-180) == -2147483648

        assert to_semicircles(90) == 1073741824

    def test_to_degrees(self):
        assert to_degrees(0) == 0.0

        assert to_degrees(2147483648) == 180.0

        assert to_degrees(-2147483648) == -180.0

        assert to_degrees(1073741824) == 90.0

    def test_round_trip_conversion(self):
        for degrees in [0, 45, 90, -90, 180, -180, 37.7749, -122.4194]:
            semicircles = to_semicircles(degrees)
            result = to_degrees(semicircles)
            assert abs(result - degrees) < 0.0001
