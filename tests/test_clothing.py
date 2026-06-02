"""Unit tests for clothing recommendation logic. Pure, no I/O."""
import pytest

from src.services.scoring.clothing_scoring import recommend_clothing


def test_warm_calm_day_returns_single_base_layer():
    recs = recommend_clothing(comfort_temperature=70.0, temperature=70.0, wind_speed=0.0)
    assert len(recs) == 1
    assert recs[0]["category"] == "base"


def test_always_returns_at_least_one_layer():
    recs = recommend_clothing(70.0, 90.0, 0.0)  # hotter than comfort, no wind
    assert len(recs) >= 1


def test_layers_capped_at_max():
    # Extreme cold + high wind would exceed the cap; must clamp to 5
    recs = recommend_clothing(70.0, -20.0, 60.0)
    assert len(recs) <= 5


def test_high_wind_selects_windproof_outer():
    recs = recommend_clothing(70.0, 40.0, 20.0)  # wind > 15 → windproof required
    assert any(item.get("windproof") for item in recs)


@pytest.mark.parametrize("expected_accessory", ["hat", "gloves"])
def test_freezing_adds_hat_and_gloves(expected_accessory):
    # 30°F: 3 base layers (tee/sweater/outer) + hat + gloves = exactly the 5-layer cap
    recs = recommend_clothing(70.0, 30.0, 0.0)
    names = {item["name"] for item in recs}
    assert expected_accessory in names


def test_max_layer_cap_can_truncate_extreme_cold_accessories():
    """
    Documents a real wart: scarf/thermal_leggings for sub-20°F are appended
    AFTER layers, so the 5-layer cap can truncate them. See weather-app open questions.
    """
    recs = recommend_clothing(70.0, 18.0, 0.0)
    assert len(recs) == 5  # capped; not all accessories survive


def test_no_none_values_in_output():
    recs = recommend_clothing(70.0, 10.0, 10.0)
    assert all(item is not None for item in recs)
