from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from domain.exceptions import InvalidRiskAssessment

if TYPE_CHECKING:
    from datetime import datetime

    from domain.value_objects import RiskTier


@dataclass(frozen=True)
class RiskAssessment:
    """Immutable output of :class:`RiskEngine` (and escalation).

    This is intentionally a *frozen* dataclass — once an assessment has been
    signed off by the engine for a given cycle, nothing should mutate it in
    place. A new cycle produces a brand-new instance. This append-only
    semantics is what makes the assessments table auditable later: every
    change is a new row, never an UPDATE.

    ``probability`` is a [0, 1] float that captures how confident the engine
    is in the tier assignment; it's surfaced to the SHAP explainability panel
    in the web UI (Stage 6).
    """

    zone_id: str
    tier: RiskTier
    probability: float
    explanation: str
    computed_at: datetime
    combined_rain_mm: float | None = None
    expected_rain_mm: float | None = None
    rainfall_anomaly_ratio: float | None = None
    top_contributing_features: list[str] | None = None

    def __post_init__(self) -> None:
        if not (0.0 <= self.probability <= 1.0):
            raise InvalidRiskAssessment(
                f"RiskAssessment.probability must be in [0, 1], got {self.probability!r}"
            )
        if not self.explanation:
            raise InvalidRiskAssessment("RiskAssessment.explanation must be non-empty")
        if not self.zone_id:
            raise InvalidRiskAssessment("RiskAssessment.zone_id must be non-empty")
