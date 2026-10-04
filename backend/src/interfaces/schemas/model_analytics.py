"""Pydantic schemas for ML model analytics and performance metrics."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, RootModel


class ClassMetrics(BaseModel):
    """Evaluation metrics for a single risk tier class."""

    precision: float
    recall: float
    f1_score: float

    model_config = ConfigDict(from_attributes=True)

    def __getitem__(self, item: str) -> float:
        return getattr(self, item)


class ModelMetricsResponse(RootModel[dict[str, ClassMetrics]]):
    """Model evaluation metrics mapping class names to precision, recall, and f1_score."""

    root: dict[str, ClassMetrics]

    def __getattr__(self, name: str) -> ClassMetrics:
        if name in self.root:
            return self.root[name]
        raise AttributeError(f"'ModelMetricsResponse' object has no attribute '{name}'")

    def __getitem__(self, item: str) -> ClassMetrics:
        return self.root[item]

    @property
    def metrics(self) -> dict[str, ClassMetrics]:
        return self.root

    @property
    def classes(self) -> dict[str, ClassMetrics]:
        return self.root


class FeatureImportanceItem(BaseModel):
    """Single feature importance score."""

    feature_name: str
    importance_score: float

    model_config = ConfigDict(from_attributes=True)

    def __getitem__(self, item: str) -> str | float:
        return getattr(self, item)


class FeatureImportanceResponse(RootModel[list[FeatureImportanceItem]]):
    """Top feature importances for the flood risk prediction model."""

    root: list[FeatureImportanceItem]

    def __init__(self, *args, **kwargs):
        if "features" in kwargs and "root" not in kwargs:
            kwargs["root"] = kwargs.pop("features")
        super().__init__(*args, **kwargs)

    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]

    def __len__(self) -> int:
        return len(self.root)

    @property
    def features(self) -> list[FeatureImportanceItem]:
        return self.root
