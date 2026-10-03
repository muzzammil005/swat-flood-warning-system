from __future__ import annotations

import pytest

from domain.value_objects import RiskTier


def test_risk_tier_values_are_ordered() -> None:
    assert RiskTier.LOW < RiskTier.MEDIUM < RiskTier.HIGH < RiskTier.DANGER


def test_risk_tier_intenum_numeric_values() -> None:
    assert int(RiskTier.LOW) == 1
    assert int(RiskTier.MEDIUM) == 2
    assert int(RiskTier.HIGH) == 3
    assert int(RiskTier.DANGER) == 4


def test_risk_tier_comparison_high_vs_medium() -> None:
    assert RiskTier.HIGH > RiskTier.MEDIUM
    assert RiskTier.MEDIUM < RiskTier.HIGH
    assert RiskTier.MEDIUM <= RiskTier.MEDIUM
    assert RiskTier.HIGH >= RiskTier.HIGH


def test_risk_tier_escalate_one_level() -> None:
    assert RiskTier.LOW.escalate() is RiskTier.MEDIUM
    assert RiskTier.MEDIUM.escalate() is RiskTier.HIGH
    assert RiskTier.HIGH.escalate() is RiskTier.DANGER


def test_risk_tier_escalate_danger_is_capped() -> None:
    assert RiskTier.DANGER.escalate() is RiskTier.DANGER


def test_risk_tier_iteration_order() -> None:
    assert list(RiskTier) == [RiskTier.LOW, RiskTier.MEDIUM, RiskTier.HIGH, RiskTier.DANGER]


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        (RiskTier.LOW, RiskTier.MEDIUM, True),
        (RiskTier.MEDIUM, RiskTier.HIGH, True),
        (RiskTier.HIGH, RiskTier.DANGER, True),
        (RiskTier.MEDIUM, RiskTier.LOW, False),
        (RiskTier.HIGH, RiskTier.HIGH, False),
    ],
)
def test_risk_tier_lt_table(left: RiskTier, right: RiskTier, expected: bool) -> None:
    assert (left < right) is expected
