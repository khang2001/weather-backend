"""
Phase 3 — comfort score (SC1 verified, SC2 fixed). Pure unit, no I/O.

Refactored to pytest + parametrize per the wiki "avoid logic in tests" rule
(was a manual for-loop runner). See unit-testing-best-practices.
"""
import pytest

from src.services.scoring.weather_scoring import score_temperature, wind_multiplier, score_weather
from tests.conftest import FakeWeather


# --- score_temperature -----------------------------------------------------

@pytest.mark.parametrize("temp,comfort,expected", [
    (70.0, 70.0,  10.0),   # at comfort
    (80.0, 70.0,   5.0),   # +10°F
    (60.0, 70.0,   5.0),   # -10°F
    (90.0, 70.0,   0.0),   # +20°F
    (30.0, 70.0, -10.0),   # extreme cold
])
def test_score_temperature(temp, comfort, expected):
    assert score_temperature(temp, comfort) == expected


# --- wind_multiplier (SC1: never exceeds 1.0) ------------------------------

@pytest.mark.parametrize("wind,expected", [
    (0.0,  1.0),    # SC1: below threshold stays at 1.0
    (3.0,  1.0),
    (5.0,  1.0),    # at threshold
    (10.0, 0.5),    # 5 above
    (15.0, 0.0),    # 10 above
    (100.0, 0.0),   # floor, never negative
])
def test_wind_multiplier_bounds(wind, expected):
    assert wind_multiplier(wind) == pytest.approx(expected, abs=0.01)


# --- score_weather (SC2: no phantom +5 floor) ------------------------------

@pytest.mark.parametrize("temp,wind,forecast,expected", [
    (70.0, 0.0,  "sunny",         10.0),   # perfect day
    (70.0, 20.0, "sunny",          9.0),   # perfect temp, windy: 10 -0 -1.5 +0.5
    (43.0, 20.0, "",               0.0),   # SC2: was phantom 5.0
    (5.0,  30.0, "partly cloudy",  0.0),   # cold + very windy
    (60.0, 5.0,  "overcast",       4.75),  # 10 -5 -0 -0.25
])
def test_score_weather_cases(temp, wind, forecast, expected):
    w = FakeWeather(temp, wind, forecast)
    assert score_weather(w, comfort_temperature=70.0) == pytest.approx(expected, abs=0.01)


def test_score_weather_no_phantom_floor():
    """Good-temp + wind must outscore bad-temp + same wind (old model tied them at 5.0)."""
    good = FakeWeather(70.0, 20.0, "")
    bad = FakeWeather(43.0, 20.0, "")
    assert score_weather(good, 70.0) > score_weather(bad, 70.0)


@pytest.mark.parametrize("temp,wind,forecast", [
    (-50.0, 100.0, "blizzard"),
    (150.0, 0.0,   "sunny"),
    (70.0,  0.0,   "sunny"),
])
def test_score_weather_always_in_range(temp, wind, forecast):
    s = score_weather(FakeWeather(temp, wind, forecast), 70.0)
    assert 0.0 <= s <= 10.0


# --- SC3: asymmetric comfort (directional temperature penalties) -----------

def test_default_penalties_are_symmetric():
    # SC3 backward-compat: equal hot/cold deviations score the same by default.
    ct = 70.0
    hot = FakeWeather(80.0, 0.0, "")   # +10°F
    cold = FakeWeather(60.0, 0.0, "")  # -10°F
    assert score_weather(hot, ct) == pytest.approx(score_weather(cold, ct), abs=0.01)


def test_heat_sensitive_user_scores_hot_lower():
    # Someone who tolerates cold but not heat: a hot deviation should hurt more
    # than an equal cold deviation.
    ct = 70.0
    hot = FakeWeather(80.0, 0.0, "")
    cold = FakeWeather(60.0, 0.0, "")
    kwargs = dict(comfort_temperature=ct, cold_penalty_per_degree=0.25, heat_penalty_per_degree=0.75)
    assert score_weather(hot, **kwargs) < score_weather(cold, **kwargs)


def test_cold_sensitive_user_scores_cold_lower():
    ct = 70.0
    hot = FakeWeather(80.0, 0.0, "")
    cold = FakeWeather(60.0, 0.0, "")
    kwargs = dict(comfort_temperature=ct, cold_penalty_per_degree=0.75, heat_penalty_per_degree=0.25)
    assert score_weather(cold, **kwargs) < score_weather(hot, **kwargs)


def test_asymmetric_penalty_exact_value():
    # comfort 70, temp 80 (+10), heat slope 0.75 → penalty 7.5 → 10 - 7.5 = 2.5
    w = FakeWeather(80.0, 0.0, "")
    s = score_weather(w, comfort_temperature=70.0,
                      cold_penalty_per_degree=0.5, heat_penalty_per_degree=0.75)
    assert s == pytest.approx(2.5, abs=0.01)


def test_at_comfort_temp_tolerances_dont_matter():
    # No temperature deviation → no temp penalty regardless of slopes.
    w = FakeWeather(70.0, 0.0, "")
    a = score_weather(w, comfort_temperature=70.0, cold_penalty_per_degree=0.9, heat_penalty_per_degree=0.1)
    b = score_weather(w, comfort_temperature=70.0, cold_penalty_per_degree=0.1, heat_penalty_per_degree=0.9)
    assert a == pytest.approx(b, abs=0.01)


def test_forecast_modifier_ordering():
    ct = 70.0
    base   = FakeWeather(60.0, 0.0, "")
    sunny  = FakeWeather(60.0, 0.0, "sunny")
    cloudy = FakeWeather(60.0, 0.0, "overcast")
    rainy  = FakeWeather(60.0, 0.0, "rain")
    assert score_weather(sunny, ct)  > score_weather(base, ct)
    assert score_weather(cloudy, ct) < score_weather(base, ct)
    assert score_weather(rainy, ct)  < score_weather(cloudy, ct)
