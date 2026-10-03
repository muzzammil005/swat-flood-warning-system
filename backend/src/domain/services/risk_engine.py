"""RiskEngine — threshold-based local risk computation.

Design rationale (for the viva / supervisor read-through):

The engine takes three *local* inputs (zone state, current water-level reading,
24-hour rainfall forecast) plus a per-zone :class:`ZoneThresholds` bundle and
returns a single :class:`RiskAssessment`. We intentionally do NOT do the
upstream-escalation pass here — that's the job of :class:`EscalationEngine`,
which runs *after* this engine has produced per-zone base tiers.

Splitting the two concerns keeps both pieces trivially testable: RiskEngine has
zero knowledge of river topology, and EscalationEngine has zero knowledge of
what a "water level" actually means. That separation is exactly what makes the
logic defensible under audit instead of one monolithic ``compute_everything``
function.

Tiering rules (standard flood-forecast semantics, mirrored in the code below):

    water_level < warning                       → LOW  (base)
    warning ≤ water_level < critical            → MEDIUM
    water_level ≥ critical                      → HIGH
    rainfall  ≥ heavy_rain_threshold:
        MEDIUM  → HIGH                       (rain upgrade)
        LOW     → MEDIUM                     (rain upgrade)
        HIGH    → DANGER                     (rain upgrade when combined with high water)

The "combined" branch (high water + heavy rain) is the only path that reaches
DANGER from inside this engine; DANGER can also be injected later by a
ManualOverride, or via EscalationEngine propagation from an upstream DANGER.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from domain.entities import RiskAssessment, Zone
from domain.value_objects import (
    RainfallWindow,
    RiskTier,
    WaterLevel,
    ZoneThresholds,
)


@dataclass
class RiskEngine:
    """Computes a *local* (pre-escalation) :class:`RiskAssessment` for a zone."""

    def assess(
        self,
        zone: Zone,
        current_water_level: WaterLevel,
        forecast_rain_24h: RainfallWindow,
        thresholds: ZoneThresholds,
        *,
        now: datetime | None = None,
    ) -> RiskAssessment:
        ts = now if now is not None else datetime.now(UTC)
        reasons: list[str] = []

        water_tier, water_reason = self._water_tier(
            current_water_level, thresholds
        )
        if water_reason:
            reasons.append(water_reason)

        rain_hit = forecast_rain_24h.millimetres >= thresholds.heavy_rain_threshold_mm
        if rain_hit:
            reasons.append(
                f"Heavy rainfall ({forecast_rain_24h.millimetres:.1f}mm) "
                f"forecasted in next {int(forecast_rain_24h.duration_hours)} hours."
            )

        tier = water_tier
        tier, upgrade_reason = self._apply_rain_upgrade(tier, rain_hit, water_tier)
        if upgrade_reason:
            reasons.append(upgrade_reason)

        if not reasons:
            reasons.append(
                f"Water level is low ({current_water_level.centimetres:.1f}cm) and no "
                "heavy rainfall forecasted."
            )
        explanation = " ".join(reasons)

        probability = self._probability(tier, current_water_level, thresholds, rain_hit)

        return RiskAssessment(
            zone_id=zone.id,
            tier=tier,
            probability=probability,
            explanation=explanation,
            computed_at=ts,
        )

    # ------------------------------------------------------------------
    # Internal helpers (pure functions, kept tiny for branch coverage)
    # ------------------------------------------------------------------

    @staticmethod
    def _water_tier(
        wl: WaterLevel, th: ZoneThresholds
    ) -> tuple[RiskTier, str]:
        if wl >= th.water_critical_level:
            return (
                RiskTier.HIGH,
                f"Water level is CRITICAL ({wl.centimetres:.1f}cm) — above critical threshold "
                f"({th.water_critical_level.centimetres:.1f}cm).",
            )
        if wl >= th.water_warning_level:
            return (
                RiskTier.MEDIUM,
                f"Water level is elevated ({wl.centimetres:.1f}cm) — above warning threshold "
                f"({th.water_warning_level.centimetres:.1f}cm).",
            )
        return RiskTier.LOW, ""

    @staticmethod
    def _apply_rain_upgrade(
        current: RiskTier, rain_hit: bool, water_tier: RiskTier
    ) -> tuple[RiskTier, str]:
        if not rain_hit:
            return current, ""
        # Heavy rain alone upgrades LOW→MEDIUM or MEDIUM→HIGH.
        # If water already pushed us HIGH, the combination is DANGER.
        if current is RiskTier.HIGH:
            return RiskTier.DANGER, "Combined high water level + heavy rain: danger tier."
        if current is RiskTier.DANGER:
            return RiskTier.DANGER, ""
        return current.escalate(), (
            f"Heavy rainfall upgraded risk from {water_tier.name} to {current.escalate().name}."
        )

    @staticmethod
    def _probability(
        tier: RiskTier,
        wl: WaterLevel,
        th: ZoneThresholds,
        rain_hit: bool,
    ) -> float:
        """Deterministic 0–1 confidence score used by the SHAP panel.

        Not a calibrated statistical probability — think of it as a "severity
        score" normalised to [0, 1]. The SHAP panel in Stage 6 decomposes
        *why* this number came out as it did (water contribution vs rain
        contribution vs upstream contribution).
        """
        warn_cm = th.water_warning_level.centimetres
        crit_cm = th.water_critical_level.centimetres
        spread = max(crit_cm - warn_cm, 1.0)

        water_contrib = 0.0
        if wl.centimetres >= warn_cm:
            # 0.4 at warning line → 0.7 at critical line, clamp to 0.7 max from water
            water_contrib = min(
                0.4 + 0.3 * (wl.centimetres - warn_cm) / spread, 0.7
            )
        else:
            water_contrib = 0.25 * (wl.centimetres / max(warn_cm, 1.0))

        rain_contrib = 0.15 if rain_hit else 0.0
        tier_bonus = {RiskTier.LOW: 0.0, RiskTier.MEDIUM: 0.05, RiskTier.HIGH: 0.1, RiskTier.DANGER: 0.15}[tier]
        raw = water_contrib + rain_contrib + tier_bonus
        if tier is RiskTier.DANGER:
            return max(0.85, min(raw, 0.995))
        return max(0.01, min(raw, 0.99))
