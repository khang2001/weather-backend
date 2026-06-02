"""Unit tests for wind-speed parsing. Pure, no I/O."""
import pytest

from src.utils.parsing import parse_wind_speed


@pytest.mark.parametrize("raw,expected", [
    ("5 mph",      5.0),
    ("10 mph",     10.0),
    ("10-15 mph",  12.5),   # range → average
    ("5 to 10",    0.0),    # "to" form not supported → 0.0 (documents current behaviour)
    ("calm",       0.0),
    ("",           0.0),
    (None,         0.0),
    ("garbage",    0.0),
])
def test_parse_wind_speed(raw, expected):
    assert parse_wind_speed(raw) == pytest.approx(expected, abs=0.01)
