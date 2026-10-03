from __future__ import annotations

from datetime import UTC, datetime

import pytest

from domain.entities import Zone
from domain.exceptions import InvalidThresholds
from domain.services import RiskEngine
from domain.value_objects import (
    Coordinates,
    RainfallWindow,
    RiskTier,
    WaterLevel,
    ZoneThresholds,
)


@pytest.fixture()
def mingora_zone() -> Zone:
    return Zone(
        id="mingora",
        name="Mingora",
        coordinates=Coordinates(34.774, 72.361),
        upstream_zone_id="kalam",
    )


@pytest.fixture()
def mingora_thresholds() -> ZoneThresholds:
    """Calibrated for Mingora: warning at 150 cm, critical at 200 cm,
    heavy rain = ≥15 mm in 24 h."""
    return ZoneThresholds(
        water_warning_level=WaterLevel(150),
        water_critical_level=WaterLevel(200),
        heavy_rain_threshold_mm=15.0,
    )


@pytest.fixture()
def engine() -> RiskEngine:
    return RiskEngine()


# ---------------------------------------------------------------------------
# ZoneThresholds invariants (Prompt 7 gap)
# ---------------------------------------------------------------------------


class TestZoneThresholds:
    def test_valid_thresholds(self) -> None:
        th = ZoneThresholds(
            water_warning_level=WaterLevel(100),
            water_critical_level=WaterLevel(180),
            heavy_rain_threshold_mm=12.0,
        )
        assert th.water_warning_level == WaterLevel(100)
        assert th.water_critical_level == WaterLevel(180)
        assert th.heavy_rain_threshold_mm == 12.0

    def test_boundary_zero_rain_threshold(self) -> None:
        th = ZoneThresholds(
            water_warning_level=WaterLevel(100),
            water_critical_level=WaterLevel(180),
            heavy_rain_threshold_mm=0.0,
        )
        assert th.heavy_rain_threshold_mm == 0.0

    def test_negative_rain_threshold_raises(self) -> None:
        with pytest.raises(InvalidThresholds):
            ZoneThresholds(
                water_warning_level=WaterLevel(100),
                water_critical_level=WaterLevel(180),
                heavy_rain_threshold_mm=-0.001,
            )

    def test_critical_equal_warning_raises(self) -> None:
        with pytest.raises(InvalidThresholds):
            ZoneThresholds(
                water_warning_level=WaterLevel(150),
                water_critical_level=WaterLevel(150),
                heavy_rain_threshold_mm=10.0,
            )

    def test_critical_below_warning_raises(self) -> None:
        with pytest.raises(InvalidThresholds):
            ZoneThresholds(
                water_warning_level=WaterLevel(200),
                water_critical_level=WaterLevel(150),
                heavy_rain_threshold_mm=10.0,
            )

    def test_immutable(self) -> None:
        th = ZoneThresholds(
            water_warning_level=WaterLevel(100),
            water_critical_level=WaterLevel(180),
            heavy_rain_threshold_mm=10.0,
        )
        with pytest.raises(AttributeError):
            th.heavy_rain_threshold_mm = 20.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# RiskEngine — table-driven cases
# ---------------------------------------------------------------------------


FIXED_TS = datetime(2026, 8, 9, 12, 0, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    (
        "water_cm",
        "rain_mm_24h",
        "expected_tier",
        "tier_reason_excerpt",
    ),
    [
        # --- Normal / low risk ------------------------------------------------
        (50.0,  0.0,   RiskTier.LOW,     "low"),
        (149.9, 14.9,  RiskTier.LOW,     "low"),

        # --- Water-only escalation ------------------------------------------
        (150.0, 0.0,   RiskTier.MEDIUM,  "elevated"),            # exactly at warning
        (175.0, 0.0,   RiskTier.MEDIUM,  "elevated"),            # between warn & crit
        (199.9, 0.0,   RiskTier.MEDIUM,  "elevated"),
        (200.0, 0.0,   RiskTier.HIGH,    "CRITICAL"),            # exactly at critical
        (250.0, 0.0,   RiskTier.HIGH,    "CRITICAL"),            # well above critical

        # --- Rain-only escalation -------------------------------------------
        (50.0,  15.0,  RiskTier.MEDIUM,  "Heavy rainfall upgraded"),  # LOW→MEDIUM via rain
        (149.9, 20.0,  RiskTier.MEDIUM,  "Heavy rainfall upgraded"),
        (175.0, 15.0,  RiskTier.HIGH,    "Heavy rainfall upgraded"),  # MEDIUM→HIGH via rain

        # --- Combined (water + rain → DANGER) -------------------------------
        (200.0, 15.0,  RiskTier.DANGER,  "Combined high water level + heavy rain"),
        (250.0, 50.0,  RiskTier.DANGER,  "Combined high water level + heavy rain"),
    ],
    ids=[
        "low_ok", "low_boundary_below_both",
        "water_at_warning_medium", "water_between_wc_medium",
        "water_just_below_critical_medium",
        "water_exactly_critical_high", "water_above_critical_high",
        "rain_only_low_to_medium", "rain_only_below_warn_to_medium",
        "rain_medium_to_high",
        "combined_water_crit_plus_rain_danger",
        "combined_deep_danger",
    ],
)
def test_risk_engine_table(
    engine: RiskEngine,
    mingora_zone: Zone,
    mingora_thresholds: ZoneThresholds,
    water_cm: float,
    rain_mm_24h: float,
    expected_tier: RiskTier,
    tier_reason_excerpt: str,
) -> None:
    assessment = engine.assess(
        zone=mingora_zone,
        current_water_level=WaterLevel(water_cm),
        forecast_rain_24h=RainfallWindow(rain_mm_24h, 24),
        thresholds=mingora_thresholds,
        now=FIXED_TS,
    )
    assert assessment.zone_id == mingora_zone.id
    assert assessment.tier is expected_tier
    assert assessment.computed_at == FIXED_TS
    assert 0.0 <= assessment.probability <= 1.0
    assert tier_reason_excerpt.lower() in assessment.explanation.lower()
    # No empty explanations ever.
    assert assessment.explanation.strip()


def test_risk_engine_probability_monotonic_increasing_along_tiers(
    engine: RiskEngine,
    mingora_zone: Zone,
    mingora_thresholds: ZoneThresholds,
) -> None:
    """The SHAP panel expects higher tiers to have (on average) higher confidence."""
    scenarios = [
        (50.0, 0.0),    # LOW
        (175.0, 0.0),   # MEDIUM (water only)
        (210.0, 0.0),   # HIGH (water only)
        (210.0, 20.0),  # DANGER (combined)
    ]
    probs: list[float] = []
    for water_cm, rain_mm in scenarios:
        a = engine.assess(
            zone=mingora_zone,
            current_water_level=WaterLevel(water_cm),
            forecast_rain_24h=RainfallWindow(rain_mm, 24),
            thresholds=mingora_thresholds,
            now=FIXED_TS,
        )
        probs.append(a.probability)
    for prev, nxt in zip(probs, probs[1:], strict=False):
        assert prev <= nxt, (
            f"Expected probabilities monotonic {probs}, but drop seen between adjacent tiers"
        )
    # DANGER scenario must explicitly be ≥ 0.85 per engine contract.
    assert probs[-1] >= 0.85
