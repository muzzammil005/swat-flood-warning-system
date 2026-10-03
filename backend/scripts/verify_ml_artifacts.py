"""Verification script for Multiclass XGBoost ML Artifacts and Predictor.

Run this inside the backend container to confirm:
  1. feature_columns has all 27 features in exact order.
  2. landcover_encoder.transform(['10', '50', '60', '100']) produces integer codes.
  3. model.predict_proba() runs on dummy feature data matching feature_columns (1, 27)
     and returns 3 class probabilities.
  4. predict_flood_risk_v2() correctly computes predictions and maps via argmax to
     RiskTier.LOW (0), RiskTier.MEDIUM (1), or RiskTier.HIGH (2).

Usage:
    python backend/scripts/verify_ml_artifacts.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT / "backend" / "src"))

from domain.value_objects.risk_tier import RiskTier  # noqa: E402
from infrastructure.ml.artifacts import (  # noqa: E402
    anomaly_median,
    feature_columns,
    landcover_encoder,
    model,
    tier_mapping,
)
from infrastructure.ml.predictor import predict_flood_risk_v2  # noqa: E402

EXPECTED_FEATURES = [
    "elevation",
    "slope",
    "stream_proximity",
    "drainage_density",
    "upstream_area",
    "hand",
    "landcover_encoded",
    "ndvi",
    "rain_jan",
    "rain_feb",
    "rain_mar",
    "rain_apr",
    "rain_may",
    "rain_jun",
    "rain_jul",
    "rain_aug",
    "rain_sep",
    "rain_oct",
    "rain_nov",
    "rain_dec",
    "rain_1day_pre",
    "rain_3day_pre",
    "rain_7day_pre",
    "rain_30day_pre",
    "rainfall_anomaly_ratio",
    "longitude",
    "latitude",
]


def main() -> None:
    print("=" * 65)
    print("Multiclass XGBoost ML Artifact Loading & Predictor Verification")
    print("=" * 65)

    print(f"\n1. Feature columns ({len(feature_columns)}):")
    for i, col in enumerate(feature_columns):
        expected = EXPECTED_FEATURES[i] if i < len(EXPECTED_FEATURES) else "UNKNOWN"
        match = "  OK" if col == expected else "  MISMATCH"
        print(f"   [{i:>2}] {col:<30} expected={expected:<30}{match}")
    assert feature_columns == EXPECTED_FEATURES, "feature_columns mismatch!"
    print("   → Feature column order matches ground truth exactly.")

    print(f"\n2. Anomaly median fallback: {anomaly_median:.6f}")
    assert 0.0 < anomaly_median < 10.0, f"anomaly_median out of range: {anomaly_median}"
    print("   → Anomaly median in expected valid range.")

    print("\n3. Landcover encoder transform on values ['10', '50', '60', '100']:")
    test_values = ["10", "50", "60", "100"]
    encoded = landcover_encoder.transform(test_values)
    for raw, enc in zip(test_values, encoded):
        print(f"   '{raw}' -> {enc} (type={type(enc).__name__})")
    assert len(encoded) == 4
    assert all(isinstance(e, (int, np.integer)) for e in encoded)
    print("   → Encoder produces valid integer codes for test values.")

    print("\n4. model.predict_proba() on dummy feature row (1, 27):")
    n_features = len(feature_columns)
    dummy_row = np.zeros((1, n_features), dtype=np.float32)
    for i, col in enumerate(feature_columns):
        if col == "landcover_encoded":
            dummy_row[0, i] = float(encoded[2])
        elif col == "elevation":
            dummy_row[0, i] = 1500.0
        elif col == "longitude":
            dummy_row[0, i] = 72.5
        elif col == "latitude":
            dummy_row[0, i] = 35.1
        elif col.startswith("rain_"):
            dummy_row[0, i] = 30.0
        elif col == "rainfall_anomaly_ratio":
            dummy_row[0, i] = anomaly_median
        else:
            dummy_row[0, i] = 1.0

    proba = model.predict_proba(dummy_row)
    print(f"   Model type:   {type(model).__name__}")
    print(f"   Input shape:  {dummy_row.shape}")
    print(f"   Output shape: {proba.shape}")
    print(f"   Probabilities (Low, Medium, High): {proba[0].tolist()}")
    assert proba.shape == (1, 3), f"Expected shape (1, 3), got {proba.shape}"
    assert np.isclose(np.sum(proba[0]), 1.0, atol=1e-3), "Probabilities do not sum to 1.0"
    pred_idx = int(np.argmax(proba[0]))
    mapped_tier = tier_mapping[pred_idx]
    print(f"   Argmax: class={pred_idx} -> {mapped_tier.name}")
    print("   → predict_proba() succeeds and returns valid 3-class distribution.")

    print("\n5. Testing predict_flood_risk_v2() function:")
    dummy_terrain = {
        "elevation": 1470.0,
        "slope": 9.8,
        "stream_proximity": 319.0,
        "drainage_density": 51.3,
        "upstream_area": 0.29,
        "hand": 63.9,
        "landcover_encoded": int(encoded[2]),
        "ndvi": 0.19,
        "rain_jan": 46.0, "rain_feb": 50.0, "rain_mar": 102.0, "rain_apr": 99.0,
        "rain_may": 35.0, "rain_jun": 29.0, "rain_jul": 69.0, "rain_aug": 109.0,
        "rain_sep": 116.0, "rain_oct": 16.0, "rain_nov": 28.0, "rain_dec": 13.0,
        "longitude": 72.54,
        "latitude": 35.20,
    }
    # Test with explicit weather metrics
    result = predict_flood_risk_v2(
        dummy_terrain,
        rain_1day_pre=12.5,
        rain_3day_pre=35.0,
        rain_7day_pre=80.0,
        rain_30day_pre=150.0,
        current_month=8,
    )
    print(f"   Result risk tier: {result.risk_level.name}")
    print(f"   Probabilities:    {result.probabilities}")
    print(f"   Anomaly ratio:    {result.rainfall_anomaly_ratio:.3f}")
    assert result.risk_level in {RiskTier.LOW, RiskTier.MEDIUM, RiskTier.HIGH}
    print("   → predict_flood_risk_v2() successfully generated risk assessment.")

    print("\n" + "=" * 65)
    print("ALL CHECKS PASSED — Multiclass XGBoost model & predictor verified!")
    print("=" * 65)


if __name__ == "__main__":
    main()
