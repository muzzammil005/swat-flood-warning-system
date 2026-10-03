from __future__ import annotations

from datetime import UTC, datetime

import pytest

from domain.entities import (
    Alert,
    CommunityReport,
    ManualOverride,
    RiskAssessment,
    SensorReading,
    WeatherSnapshot,
    Zone,
)
from domain.exceptions import (
    DomainError,
    InvalidRiskAssessment,
)
from domain.value_objects import (
    Coordinates,
    RainfallWindow,
    RiskTier,
    WaterLevel,
)

# ---------------------------------------------------------------------------
# Zone
# ---------------------------------------------------------------------------


def test_zone_valid_headwater() -> None:
    zone = Zone(
        id="kalam",
        name="Kalam Bazaar",
        coordinates=Coordinates(35.479, 72.596),
        upstream_zone_id=None,
    )
    assert zone.id == "kalam"
    assert zone.upstream_zone_id is None


def test_zone_valid_with_upstream() -> None:
    zone = Zone(
        id="mingora",
        name="Mingora",
        coordinates=Coordinates(34.774, 72.361),
        upstream_zone_id="kalam",
    )
    assert zone.upstream_zone_id == "kalam"


# ---------------------------------------------------------------------------
# SensorReading
# ---------------------------------------------------------------------------


def test_sensor_reading_valid_real() -> None:
    ts = datetime.now(UTC)
    sr = SensorReading(
        id="sr-1",
        zone_id="mingora",
        water_level=WaterLevel(165.2),
        timestamp=ts,
        source="real",
    )
    assert sr.water_level == WaterLevel(165.2)
    assert sr.source == "real"


def test_sensor_reading_valid_test_source() -> None:
    sr = SensorReading(
        id="sr-t1",
        zone_id="mingora",
        water_level=WaterLevel(0.0),
        timestamp=datetime.now(UTC),
        source="test",
    )
    assert sr.source == "test"


def test_sensor_reading_bad_source_raises() -> None:
    with pytest.raises(DomainError):
        SensorReading(
            id="sr-bad",
            zone_id="mingora",
            water_level=WaterLevel(100),
            timestamp=datetime.now(UTC),
            source="synthetic",  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# WeatherSnapshot
# ---------------------------------------------------------------------------


def test_weather_snapshot_valid() -> None:
    ts = datetime.now(UTC)
    ws = WeatherSnapshot(
        zone_id="mingora",
        rainfall=RainfallWindow(18.5, 24),
        fetched_at=ts,
        ttl_seconds=900,
    )
    assert ws.ttl_seconds == 900


def test_weather_snapshot_zero_ttl_is_valid() -> None:
    ws = WeatherSnapshot(
        zone_id="mingora",
        rainfall=RainfallWindow(0, 24),
        fetched_at=datetime.now(UTC),
        ttl_seconds=0,
    )
    assert ws.ttl_seconds == 0


def test_weather_snapshot_negative_ttl_raises() -> None:
    with pytest.raises(DomainError):
        WeatherSnapshot(
            zone_id="mingora",
            rainfall=RainfallWindow(10, 24),
            fetched_at=datetime.now(UTC),
            ttl_seconds=-1,
        )


# ---------------------------------------------------------------------------
# RiskAssessment (immutable, probability 0-1, non-empty explanation/zone)
# ---------------------------------------------------------------------------


def test_risk_assessment_valid_boundary_probabilities() -> None:
    base = dict(
        zone_id="mingora",
        tier=RiskTier.MEDIUM,
        explanation="All good.",
        computed_at=datetime.now(UTC),
    )
    a = RiskAssessment(probability=0.0, **base)  # type: ignore[arg-type]
    b = RiskAssessment(probability=1.0, **base)  # type: ignore[arg-type]
    assert a.probability == 0.0
    assert b.probability == 1.0


def test_risk_assessment_probability_above_1_raises() -> None:
    with pytest.raises(InvalidRiskAssessment):
        RiskAssessment(
            zone_id="mingora",
            tier=RiskTier.HIGH,
            probability=1.0001,
            explanation="oops",
            computed_at=datetime.now(UTC),
        )


def test_risk_assessment_negative_probability_raises() -> None:
    with pytest.raises(InvalidRiskAssessment):
        RiskAssessment(
            zone_id="mingora",
            tier=RiskTier.LOW,
            probability=-0.0001,
            explanation="oops",
            computed_at=datetime.now(UTC),
        )


def test_risk_assessment_empty_explanation_raises() -> None:
    with pytest.raises(InvalidRiskAssessment):
        RiskAssessment(
            zone_id="mingora",
            tier=RiskTier.LOW,
            probability=0.5,
            explanation="",
            computed_at=datetime.now(UTC),
        )


def test_risk_assessment_empty_zone_id_raises() -> None:
    with pytest.raises(InvalidRiskAssessment):
        RiskAssessment(
            zone_id="",
            tier=RiskTier.LOW,
            probability=0.5,
            explanation="OK",
            computed_at=datetime.now(UTC),
        )


def test_risk_assessment_is_immutable() -> None:
    ra = RiskAssessment(
        zone_id="mingora",
        tier=RiskTier.MEDIUM,
        probability=0.5,
        explanation="OK",
        computed_at=datetime.now(UTC),
    )
    with pytest.raises(AttributeError):
        ra.tier = RiskTier.HIGH  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Alert (CAP inspired)
# ---------------------------------------------------------------------------


def test_alert_valid_cap_fields() -> None:
    alert = Alert(
        zone_id="mingora",
        severity=RiskTier.HIGH,
        certainty="Likely",
        urgency="Expected",
        headline="River levels rising in Mingora",
        description="Swat river at Mingora gauge crossed warning threshold at 14:00.",
        sent_at=datetime.now(UTC),
    )
    assert alert.severity is RiskTier.HIGH
    assert alert.certainty == "Likely"


def test_alert_bad_certainty_raises() -> None:
    with pytest.raises(DomainError):
        Alert(
            zone_id="mingora",
            severity=RiskTier.HIGH,
            certainty="VeryPossible",
            urgency="Expected",
            headline="x",
            description="y",
            sent_at=datetime.now(UTC),
        )


def test_alert_bad_urgency_raises() -> None:
    with pytest.raises(DomainError):
        Alert(
            zone_id="mingora",
            severity=RiskTier.HIGH,
            certainty="Likely",
            urgency="SometimeSoon",
            headline="x",
            description="y",
            sent_at=datetime.now(UTC),
        )


def test_alert_empty_headline_raises() -> None:
    with pytest.raises(DomainError):
        Alert(
            zone_id="mingora",
            severity=RiskTier.HIGH,
            certainty="Likely",
            urgency="Expected",
            headline="",
            description="y",
            sent_at=datetime.now(UTC),
        )


def test_alert_empty_description_raises() -> None:
    with pytest.raises(DomainError):
        Alert(
            zone_id="mingora",
            severity=RiskTier.HIGH,
            certainty="Likely",
            urgency="Expected",
            headline="x",
            description="",
            sent_at=datetime.now(UTC),
        )


# ---------------------------------------------------------------------------
# CommunityReport
# ---------------------------------------------------------------------------


def test_community_report_valid_pending() -> None:
    cr = CommunityReport(
        id="cr-1",
        zone_id="mingora",
        observation="Water entering houses on Riverside Rd.",
        status="Pending",
        submitted_at=datetime.now(UTC),
    )
    assert cr.status == "Pending"


@pytest.mark.parametrize("status", ["Approved", "Rejected"])
def test_community_report_valid_statuses(status: str) -> None:
    cr = CommunityReport(
        id="cr-1",
        zone_id="mingora",
        observation="Road near bridge submerged.",
        status=status,  # type: ignore[arg-type]
        submitted_at=datetime.now(UTC),
    )
    assert cr.status == status


def test_community_report_bad_status_raises() -> None:
    with pytest.raises(DomainError):
        CommunityReport(
            id="cr-bad",
            zone_id="mingora",
            observation="x",
            status="Published",  # type: ignore[arg-type]
            submitted_at=datetime.now(UTC),
        )


def test_community_report_empty_observation_raises() -> None:
    with pytest.raises(DomainError):
        CommunityReport(
            id="cr-bad",
            zone_id="mingora",
            observation="",
            status="Pending",
            submitted_at=datetime.now(UTC),
        )


# ---------------------------------------------------------------------------
# ManualOverride
# ---------------------------------------------------------------------------


def test_manual_override_valid() -> None:
    mo = ManualOverride(
        id="mo-1",
        zone_id="mingora",
        threat_level=RiskTier.DANGER,
        reason="Visual confirmation of flash flood from community reports + webcam.",
        admin_username="admin_hayat",
        timestamp=datetime.now(UTC),
    )
    assert mo.admin_username == "admin_hayat"
    assert mo.threat_level is RiskTier.DANGER


def test_manual_override_empty_reason_raises() -> None:
    with pytest.raises(DomainError):
        ManualOverride(
            id="mo-bad",
            zone_id="mingora",
            threat_level=RiskTier.HIGH,
            reason="",
            admin_username="x",
            timestamp=datetime.now(UTC),
        )


def test_manual_override_empty_admin_raises() -> None:
    with pytest.raises(DomainError):
        ManualOverride(
            id="mo-bad",
            zone_id="mingora",
            threat_level=RiskTier.HIGH,
            reason="Just because.",
            admin_username="",
            timestamp=datetime.now(UTC),
        )
