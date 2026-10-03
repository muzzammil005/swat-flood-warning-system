"""XGBoost multiclass flood-risk predictor — ``predict_flood_risk_v2()``.

Upgraded from the legacy binary LGBM model to a 3-class XGBoost model
(Low=0, Medium=1, High=2).

Key changes:
    1. Completely removes the old binary 0.557 threshold logic.
    2. Dynamically fetches real-time weather from Open-Meteo for the 5 dynamic metrics:
       ``rain_1day_pre``, ``rain_3day_pre``, ``rain_7day_pre``, ``rain_30day_pre``,
       and ``rainfall_anomaly_ratio``.
    3. Assembles a 27-element feature row matching ``swat_feature_columns_multiclass.joblib``
       order strictly.
    4. Calls ``model.predict_proba()`` to obtain 3-class probabilities.
    5. Uses ``argmax`` to map the prediction directly to:
       - 0 -> RiskTier.LOW
       - 1 -> RiskTier.MEDIUM
       - 2 -> RiskTier.HIGH
       (The model never emits RiskTier.DANGER; that is reserved for escalation).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
from typing import Any

import httpx
import numpy as np

from domain.value_objects.risk_tier import RiskTier
from infrastructure.ml.artifacts import (
    anomaly_median,
    feature_columns,
    model,
    shap_explainer,
    tier_mapping,
)

_MONTH_INDEX_TO_COL: dict[int, str] = {
    1: "rain_jan", 2: "rain_feb", 3: "rain_mar", 4: "rain_apr",
    5: "rain_may", 6: "rain_jun", 7: "rain_jul", 8: "rain_aug",
    9: "rain_sep", 10: "rain_oct", 11: "rain_nov", 12: "rain_dec",
}

_OPEN_METEO_BASE = "https://api.open-meteo.com/v1/forecast"
_OPEN_METEO_TIMEOUT = 10.0


@dataclass
class PredictionResult:
    """Typed prediction output for multiclass flood risk."""

    flood_probability: float
    risk_level: RiskTier
    rainfall_anomaly_ratio: float
    combined_rain_mm: float
    expected_rain_mm: float
    probabilities: list[float] = field(default_factory=list)
    rain_1day_pre: float = 0.0
    rain_3day_pre: float = 0.0
    rain_7day_pre: float = 0.0
    rain_30day_pre: float = 0.0
    top_contributing_features: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "flood_probability": self.flood_probability,
            "risk_level": self.risk_level,
            "rainfall_anomaly_ratio": self.rainfall_anomaly_ratio,
            "combined_rain_mm": self.combined_rain_mm,
            "expected_rain_mm": self.expected_rain_mm,
            "top_contributing_features": list(self.top_contributing_features),
        }


def _monthly_baseline(zone_terrain_features: dict[str, float | int], current_month: int | None) -> float:
    """Return the stored monthly rain baseline (mm) for ``current_month``."""
    if current_month is None or not (1 <= current_month <= 12):
        current_month = datetime.now(timezone.utc).month
    col = _MONTH_INDEX_TO_COL.get(current_month, "rain_jan")
    return float(zone_terrain_features.get(col, 0.0))


def fetch_realtime_weather_sync(latitude: float, longitude: float) -> dict[str, float]:
    """Fetch past 30 days of hourly precipitation from Open-Meteo synchronously.

    Returns a dict with:
        rain_1day_pre: past 24 hours precipitation (mm)
        rain_3day_pre: past 72 hours precipitation (mm)
        rain_7day_pre: past 168 hours precipitation (mm)
        rain_30day_pre: past 720 hours precipitation (mm)
    """
    params: dict[str, Any] = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "precipitation",
        "past_days": 30,
        "forecast_days": 1,
        "timezone": "auto",
    }
    try:
        with httpx.Client(timeout=_OPEN_METEO_TIMEOUT) as client:
            response = client.get(_OPEN_METEO_BASE, params=params)
            response.raise_for_status()
            data = response.json()
            hourly = data.get("hourly", {}).get("precipitation", [])
            # 30 days of past hourly readings = 720 values
            past_len = min(len(hourly), 30 * 24)
            if past_len < 24:
                return {
                    "rain_1day_pre": 0.0,
                    "rain_3day_pre": 0.0,
                    "rain_7day_pre": 0.0,
                    "rain_30day_pre": 0.0,
                }
            past = [float(v or 0.0) for v in hourly[:past_len]]
            past_finite = [v if math.isfinite(v) and v >= 0.0 else 0.0 for v in past]

            rain_1day = sum(past_finite[-24:])
            rain_3day = sum(past_finite[-min(len(past_finite), 72):])
            rain_7day = sum(past_finite[-min(len(past_finite), 168):])
            rain_30day = sum(past_finite)

            return {
                "rain_1day_pre": round(max(rain_1day, 0.0), 3),
                "rain_3day_pre": round(max(rain_3day, 0.0), 3),
                "rain_7day_pre": round(max(rain_7day, 0.0), 3),
                "rain_30day_pre": round(max(rain_30day, 0.0), 3),
            }
    except Exception:
        # Fallback to zero rain on any network or parsing error
        return {
            "rain_1day_pre": 0.0,
            "rain_3day_pre": 0.0,
            "rain_7day_pre": 0.0,
            "rain_30day_pre": 0.0,
        }


def _build_feature_row(full_features: dict[str, float | int]) -> np.ndarray:
    """Assemble the (1, 27) numpy row model.predict_proba() expects.

    Column order strictly follows ``feature_columns`` from
    ``swat_feature_columns_multiclass.joblib``.
    """
    n = len(feature_columns)
    row = np.zeros((1, n), dtype=np.float32)
    for i, col in enumerate(feature_columns):
        row[0, i] = np.float32(full_features.get(col, 0.0))
    return row


def _shap_top_features(row: np.ndarray, *, predicted_class: int, top_k: int = 2) -> list[str]:
    """Return names of top-k SHAP contributing features for the predicted class."""
    if shap_explainer is None:
        return []
    try:
        shap_values = shap_explainer.shap_values(row)
        if isinstance(shap_values, list):
            class_vals = shap_values[predicted_class]
        else:
            arr = np.asarray(shap_values)
            if arr.ndim == 3:
                class_vals = arr[0, :, predicted_class]
            elif arr.ndim == 2:
                class_vals = arr[0, :]
            else:
                class_vals = arr.flatten()
        importance = np.abs(np.asarray(class_vals, dtype=np.float64)).flatten()
        if importance.shape[0] != len(feature_columns):
            return []
        top_idx = np.argsort(importance)[-top_k:][::-1]
        return [feature_columns[i] for i in top_idx]
    except Exception:
        return []


def predict_flood_risk_v2(
    zone_terrain_features: dict[str, float | int],
    *,
    rain_1day_pre: float | None = None,
    rain_3day_pre: float | None = None,
    rain_7day_pre: float | None = None,
    rain_30day_pre: float | None = None,
    rainfall_anomaly_ratio: float | None = None,
    current_month: int | None = None,
    include_shap: bool = False,
) -> PredictionResult:
    """Predict flood risk tier using the 3-class XGBoost model.

    Parameters
    ----------
    zone_terrain_features:
        Dict with static features for the zone (at minimum elevation, slope,
        rain_jan..rain_dec, latitude, longitude, etc.).
    rain_1day_pre:
        1-day antecedent rainfall (mm). If None, fetched via Open-Meteo.
    rain_3day_pre:
        3-day antecedent rainfall (mm). If None, fetched via Open-Meteo.
    rain_7day_pre:
        7-day antecedent rainfall (mm). If None, fetched via Open-Meteo.
    rain_30day_pre:
        30-day antecedent rainfall (mm). If None, fetched via Open-Meteo.
    rainfall_anomaly_ratio:
        Rainfall anomaly ratio (rain_30day / monthly_baseline). If None, calculated.
    current_month:
        Month integer 1..12 to select baseline rainfall.
    include_shap:
        If True and explainer is built, compute top SHAP features.
    """
    lat = float(zone_terrain_features.get("latitude", 35.0))
    lon = float(zone_terrain_features.get("longitude", 72.5))

    # Fetch real-time weather if any metric is missing
    needs_weather = any(
        m is None for m in (rain_1day_pre, rain_3day_pre, rain_7day_pre, rain_30day_pre)
    )
    if needs_weather:
        weather = fetch_realtime_weather_sync(lat, lon)
        r1 = rain_1day_pre if rain_1day_pre is not None else weather["rain_1day_pre"]
        r3 = rain_3day_pre if rain_3day_pre is not None else weather["rain_3day_pre"]
        r7 = rain_7day_pre if rain_7day_pre is not None else weather["rain_7day_pre"]
        r30 = rain_30day_pre if rain_30day_pre is not None else weather["rain_30day_pre"]
    else:
        r1 = float(rain_1day_pre or 0.0)
        r3 = float(rain_3day_pre or 0.0)
        r7 = float(rain_7day_pre or 0.0)
        r30 = float(rain_30day_pre or 0.0)

    # Compute baseline and rainfall_anomaly_ratio if not provided
    monthly_baseline = _monthly_baseline(zone_terrain_features, current_month)
    expected_rain_mm = max(monthly_baseline, 0.0)

    if rainfall_anomaly_ratio is None:
        if expected_rain_mm > 0:
            ratio = r30 / expected_rain_mm
            if not np.isfinite(ratio):
                ratio = anomaly_median
            rainfall_anomaly_ratio = float(np.clip(ratio, 0.05, 20.0))
        else:
            rainfall_anomaly_ratio = anomaly_median
    else:
        rainfall_anomaly_ratio = float(rainfall_anomaly_ratio)

    # Assemble full 27 features dictionary
    full_features: dict[str, float | int] = dict(zone_terrain_features)
    full_features["rain_1day_pre"] = r1
    full_features["rain_3day_pre"] = r3
    full_features["rain_7day_pre"] = r7
    full_features["rain_30day_pre"] = r30
    full_features["rainfall_anomaly_ratio"] = rainfall_anomaly_ratio

    # Build (1, 27) numpy feature row
    row = _build_feature_row(full_features)

    # Run inference: model.predict_proba()
    try:
        proba_raw = model.predict_proba(row)
        proba_arr = np.asarray(proba_raw, dtype=np.float64)
        if proba_arr.ndim == 2:
            probs = [float(p) for p in proba_arr[0]]
        else:
            probs = [float(p) for p in proba_arr.flat]
    except Exception:
        # Safe fallback: Low risk tier
        probs = [1.0, 0.0, 0.0]

    # Map output via argmax -> RiskTier.LOW (0), RiskTier.MEDIUM (1), RiskTier.HIGH (2)
    predicted_idx = int(np.argmax(probs))
    risk_level = tier_mapping.get(predicted_idx, RiskTier.LOW)

    # flood_probability is the probability of the predicted risk tier
    flood_prob = float(probs[predicted_idx])

    # SHAP explanations if requested
    top_features: list[str] = []
    if include_shap:
        top_features = _shap_top_features(row, predicted_class=predicted_idx, top_k=2)

    return PredictionResult(
        flood_probability=flood_prob,
        risk_level=risk_level,
        rainfall_anomaly_ratio=rainfall_anomaly_ratio,
        combined_rain_mm=r7,
        expected_rain_mm=expected_rain_mm,
        probabilities=probs,
        rain_1day_pre=r1,
        rain_3day_pre=r3,
        rain_7day_pre=r7,
        rain_30day_pre=r30,
        top_contributing_features=top_features,
    )


# Backward-compatible wrapper for existing callers
def predict(
    zone_terrain_features: dict[str, float | int],
    past_7day_rain: float | None = None,
    next_72hr_forecast_rain: float | None = None,
    current_month: int | None = None,
    *,
    include_shap: bool = False,
) -> PredictionResult:
    """Backward compatibility wrapper delegating to ``predict_flood_risk_v2``."""
    return predict_flood_risk_v2(
        zone_terrain_features,
        rain_7day_pre=past_7day_rain,
        rain_3day_pre=next_72hr_forecast_rain,
        current_month=current_month,
        include_shap=include_shap,
    )


__all__ = [
    "PredictionResult",
    "fetch_realtime_weather_sync",
    "predict",
    "predict_flood_risk_v2",
]
