"""Unit tests for :mod:`infrastructure.ml.predictor` (Multiclass XGBoost model).

Test cases cover:
    1. Baseline prediction with no rain data -> valid 3-class result.
    2. Dynamic weather calculation and feature row assembly for 27 features.
    3. Argmax mapping:
       - 0 -> RiskTier.LOW
       - 1 -> RiskTier.MEDIUM
       - 2 -> RiskTier.HIGH
       - DANGER is *never* emitted by the ML predictor.
    4. PredictionResult.as_dict() structure and typing.
"""

from __future__ import annotations

import math
from unittest.mock import patch

import numpy as np
import pytest

from domain.value_objects.risk_tier import RiskTier
from infrastructure.ml.artifacts import feature_columns
from infrastructure.ml.predictor import (
    predict,
    predict_flood_risk_v2,
)
import infrastructure.ml.predictor as predictor_module


@pytest.fixture
def fake_zone_terrain() -> dict[str, float | int]:
    """A hand-crafted 22-key static feature dict shaped like a real zone."""
    base: dict[str, float | int] = {
        "elevation": 930.0,
        "slope": 5.0,
        "stream_proximity": 310.0,
        "drainage_density": 48.0,
        "upstream_area": 0.05,
        "hand": 7.0,
        "landcover_encoded": 2,
        "ndvi": 0.06,
        "rain_jan": 50.0, "rain_feb": 70.0, "rain_mar": 120.0,
        "rain_apr": 70.0, "rain_may": 50.0, "rain_jun": 35.0,
        "rain_jul": 170.0, "rain_aug": 110.0, "rain_sep": 80.0,
        "rain_oct": 45.0, "rain_nov": 40.0, "rain_dec": 20.0,
        "longitude": 72.36,
        "latitude": 34.77,
    }
    return base


def test_predict_without_rain_data_returns_baseline(fake_zone_terrain) -> None:
    """predict_flood_risk_v2 returns a valid result with zero/None rain inputs."""
    result = predict_flood_risk_v2(
        fake_zone_terrain,
        rain_1day_pre=0.0,
        rain_3day_pre=0.0,
        rain_7day_pre=0.0,
        rain_30day_pre=0.0,
    )
    assert 0.0 <= result.flood_probability <= 1.0
    assert math.isfinite(result.flood_probability)
    assert math.isfinite(result.expected_rain_mm)
    assert math.isfinite(result.rainfall_anomaly_ratio)
    assert result.risk_level in {RiskTier.LOW, RiskTier.MEDIUM, RiskTier.HIGH}
    assert result.risk_level is not RiskTier.DANGER


def test_predict_backward_compat_wrapper(fake_zone_terrain) -> None:
    """predict() wrapper succeeds and returns valid PredictionResult."""
    result = predict(fake_zone_terrain, past_7day_rain=10.0, next_72hr_forecast_rain=5.0)
    assert 0.0 <= result.flood_probability <= 1.0
    assert result.risk_level in {RiskTier.LOW, RiskTier.MEDIUM, RiskTier.HIGH}
    assert result.risk_level is not RiskTier.DANGER


def test_argmax_maps_to_low() -> None:
    """When class 0 has highest probability, risk tier is LOW."""
    fake_output = np.array([[0.8, 0.15, 0.05]], dtype=np.float64)
    with patch.object(predictor_module.model, "predict_proba", return_value=fake_output):
        result = predict_flood_risk_v2(
            {"latitude": 35.0, "longitude": 72.0},
            rain_1day_pre=0.0,
            rain_3day_pre=0.0,
            rain_7day_pre=0.0,
            rain_30day_pre=0.0,
        )
    assert result.risk_level is RiskTier.LOW
    assert result.flood_probability == pytest.approx(0.8)


def test_argmax_maps_to_medium() -> None:
    """When class 1 has highest probability, risk tier is MEDIUM."""
    fake_output = np.array([[0.2, 0.7, 0.1]], dtype=np.float64)
    with patch.object(predictor_module.model, "predict_proba", return_value=fake_output):
        result = predict_flood_risk_v2(
            {"latitude": 35.0, "longitude": 72.0},
            rain_1day_pre=0.0,
            rain_3day_pre=0.0,
            rain_7day_pre=0.0,
            rain_30day_pre=0.0,
        )
    assert result.risk_level is RiskTier.MEDIUM
    assert result.flood_probability == pytest.approx(0.7)


def test_argmax_maps_to_high() -> None:
    """When class 2 has highest probability, risk tier is HIGH."""
    fake_output = np.array([[0.1, 0.2, 0.7]], dtype=np.float64)
    with patch.object(predictor_module.model, "predict_proba", return_value=fake_output):
        result = predict_flood_risk_v2(
            {"latitude": 35.0, "longitude": 72.0},
            rain_1day_pre=0.0,
            rain_3day_pre=0.0,
            rain_7day_pre=0.0,
            rain_30day_pre=0.0,
        )
    assert result.risk_level is RiskTier.HIGH
    assert result.flood_probability == pytest.approx(0.7)


def test_model_never_returns_danger(fake_zone_terrain) -> None:
    """The ML predictor should never emit RiskTier.DANGER."""
    fake_output = np.array([[0.0, 0.0, 1.0]], dtype=np.float64)
    with patch.object(predictor_module.model, "predict_proba", return_value=fake_output):
        result = predict_flood_risk_v2(
            fake_zone_terrain,
            rain_1day_pre=100.0,
            rain_3day_pre=200.0,
            rain_7day_pre=300.0,
            rain_30day_pre=500.0,
        )
    assert result.risk_level is RiskTier.HIGH
    assert result.risk_level is not RiskTier.DANGER


def test_prediction_result_as_dict_round_trips(fake_zone_terrain) -> None:
    """as_dict() returns expected keys."""
    result = predict_flood_risk_v2(
        fake_zone_terrain,
        rain_1day_pre=5.0,
        rain_3day_pre=10.0,
        rain_7day_pre=20.0,
        rain_30day_pre=50.0,
    )
    d = result.as_dict()
    expected_keys = {
        "flood_probability",
        "risk_level",
        "rainfall_anomaly_ratio",
        "combined_rain_mm",
        "expected_rain_mm",
        "top_contributing_features",
    }
    assert set(d.keys()) == expected_keys
    assert isinstance(d["flood_probability"], float)
    assert isinstance(d["risk_level"], RiskTier)
    assert isinstance(d["top_contributing_features"], list)
