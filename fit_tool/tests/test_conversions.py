import pytest
from fit_tool.utils.conversions import (
    MILLISECONDS_EPOCH_1989_DELTA,
    to_seconds_since_1989_epoch,
    to_milliseconds_since_epoch,
    to_semicircles,
    to_degrees,
)


class TestEpochConversions:
    @pytest.mark.parametrize("ms_epoch, expected_seconds", [
        (MILLISECONDS_EPOCH_1989_DELTA, 0),
        (MILLISECONDS_EPOCH_1989_DELTA + 1000, 1),
        (MILLISECONDS_EPOCH_1989_DELTA + 60000, 60),
    ])
    def test_to_seconds_since_1989_epoch(self, ms_epoch, expected_seconds):
        assert to_seconds_since_1989_epoch(ms_epoch) == expected_seconds

    @pytest.mark.parametrize("seconds, ms_offset", [
        (0, 0),
        (1, 1000),
        (60, 60000),
    ])
    def test_to_milliseconds_since_epoch(self, seconds, ms_offset):
        expected_ms = MILLISECONDS_EPOCH_1989_DELTA + ms_offset
        assert to_milliseconds_since_epoch(seconds) == expected_ms

    @pytest.mark.parametrize("original_ms", [
        1700000000000,
        MILLISECONDS_EPOCH_1989_DELTA,
        MILLISECONDS_EPOCH_1989_DELTA + 1234,
    ])
    def test_round_trip_conversion(self, original_ms):
        seconds = to_seconds_since_1989_epoch(original_ms)
        result_ms = to_milliseconds_since_epoch(seconds)
        assert result_ms == (original_ms // 1000) * 1000


class TestCoordinateConversions:
    @pytest.mark.parametrize("degrees, expected_semicircles", [
        (0, 0),
        (180, 2147483648),
        (-180, -2147483648),
        (90, 1073741824),
    ])
    def test_to_semicircles(self, degrees, expected_semicircles):
        assert to_semicircles(degrees) == expected_semicircles

    @pytest.mark.parametrize("semicircles, expected_degrees", [
        (0, 0.0),
        (2147483648, 180.0),
        (-2147483648, -180.0),
        (1073741824, 90.0),
    ])
    def test_to_degrees(self, semicircles, expected_degrees):
        assert to_degrees(semicircles) == pytest.approx(expected_degrees)

    @pytest.mark.parametrize("degrees", [0, 45, 90, -90, 180, -180, 37.7749, -122.4194])
    def test_round_trip_conversion(self, degrees):
        semicircles = to_semicircles(degrees)
        result = to_degrees(semicircles)
        assert result == pytest.approx(degrees, abs=1e-4)
