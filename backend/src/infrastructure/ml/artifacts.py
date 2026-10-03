"""ML artifact loader — XGBoost multiclass model, encoders, and feature_columns.

All artifacts are loaded **once at module import time** (not per-request). Importing
this module triggers the load; subsequent imports hit Python's module cache and
return the already-loaded singletons.

Artifact resolution
-------------------
The multiclass artifacts live in ``backend/models/`` relative to the project root.
We resolve the directory via ``pathlib`` walking up from ``__file__`` so the path is
correct both locally (editable install) and inside the Docker image (``/app/backend/models``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.preprocessing import LabelEncoder

from domain.value_objects.risk_tier import RiskTier

_MODELS_DIR = Path(__file__).resolve().parents[3] / "models"

_MODEL_PATH = _MODELS_DIR / "swat_flood_multiclass_model.joblib"
_ENCODER_PATH = _MODELS_DIR / "swat_landcover_encoder_multiclass.joblib"
_FEATURE_COLS_PATH = _MODELS_DIR / "swat_feature_columns_multiclass.joblib"
_ANOMALY_MEDIAN_PATH = _MODELS_DIR / "swat_anomaly_median_multiclass.joblib"


def _load_joblib(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(
            f"ML artifact not found at {path}. "
            "Confirm the model files are in backend/models/ before starting the backend."
        )
    return joblib.load(path)


model = _load_joblib(_MODEL_PATH)
landcover_encoder = _load_joblib(_ENCODER_PATH)
feature_columns: list[str] = list(_load_joblib(_FEATURE_COLS_PATH))
anomaly_median: float = float(_load_joblib(_ANOMALY_MEDIAN_PATH))

# 3-class label encoder and mapping for multiclass output:
# Index 0 -> LOW, Index 1 -> MEDIUM, Index 2 -> HIGH
tier_mapping: dict[int, RiskTier] = {
    0: RiskTier.LOW,
    1: RiskTier.MEDIUM,
    2: RiskTier.HIGH,
}

label_encoder = LabelEncoder()
label_encoder.classes_ = np.array(["Low", "Medium", "High"])

shap_explainer: Any | None = None


def build_shap_explainer() -> None:
    """Build a SHAP TreeExplainer for the loaded XGBoost model."""
    global shap_explainer
    import shap  # noqa: F401

    background = np.zeros((1, len(feature_columns)), dtype=np.float32)
    shap_explainer = shap.TreeExplainer(model, background)


__all__ = [
    "anomaly_median",
    "build_shap_explainer",
    "feature_columns",
    "label_encoder",
    "landcover_encoder",
    "model",
    "shap_explainer",
    "tier_mapping",
]
