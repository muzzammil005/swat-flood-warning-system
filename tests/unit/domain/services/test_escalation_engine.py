from __future__ import annotations

from datetime import UTC, datetime

import pytest

from domain.entities import RiskAssessment, Zone
from domain.exceptions import CycleInUpstreamGraph
from domain.services import EscalationEngine
from domain.value_objects import Coordinates, RiskTier

FIXED_TS = datetime(2026, 8, 9, 12, 0, 0, tzinfo=UTC)


def _zone(zid: str, name: str, upstream: str | None = None) -> Zone:
    # We don't use Coordinates in the engine; any valid pair is fine.
    return Zone(id=zid, name=name, coordinates=Coordinates(34.0, 72.0), upstream_zone_id=upstream)


def _assessment(zid: str, tier: RiskTier, explanation: str = "local tier") -> RiskAssessment:
    return RiskAssessment(
        zone_id=zid,
        tier=tier,
        probability=0.5,
        explanation=explanation,
        computed_at=FIXED_TS,
    )


# ---------------------------------------------------------------------------
# No escalation needed
# ---------------------------------------------------------------------------


def test_no_escalation_all_low_tiers() -> None:
    zones = [
        _zone("kalam", "Kalam"),
        _zone("mingora", "Mingora", upstream="kalam"),
    ]
    engine = EscalationEngine()
    engine.build_graph(zones)
    base = {
        "kalam": _assessment("kalam", RiskTier.LOW),
        "mingora": _assessment("mingora", RiskTier.LOW),
    }
    out = engine.propagate(base)
    assert out["kalam"].tier is RiskTier.LOW
    assert out["mingora"].tier is RiskTier.LOW
    assert "Escalated" not in out["mingora"].explanation


def test_no_escalation_medium_upstream_does_not_propagate() -> None:
    zones = [
        _zone("kalam", "Kalam"),
        _zone("mingora", "Mingora", upstream="kalam"),
    ]
    engine = EscalationEngine()
    engine.build_graph(zones)
    base = {
        "kalam": _assessment("kalam", RiskTier.MEDIUM),
        "mingora": _assessment("mingora", RiskTier.LOW),
    }
    out = engine.propagate(base)
    assert out["mingora"].tier is RiskTier.LOW


# ---------------------------------------------------------------------------
# Single-hop escalation
# ---------------------------------------------------------------------------


def test_single_kalam_high_escalates_mingora() -> None:
    zones = [
        _zone("kalam", "Kalam"),
        _zone("mingora", "Mingora", upstream="kalam"),
    ]
    engine = EscalationEngine()
    engine.build_graph(zones)
    base = {
        "kalam": _assessment("kalam", RiskTier.HIGH),
        "mingora": _assessment("mingora", RiskTier.LOW),
    }
    out = engine.propagate(base)
    assert out["kalam"].tier is RiskTier.HIGH
    assert out["mingora"].tier is RiskTier.MEDIUM
    assert "Escalated due to heavy rain/high risk in Kalam (HIGH)" in out["mingora"].explanation


def test_single_kalam_danger_escalates_mingora_medium_to_high() -> None:
    zones = [
        _zone("kalam", "Kalam"),
        _zone("mingora", "Mingora", upstream="kalam"),
    ]
    engine = EscalationEngine()
    engine.build_graph(zones)
    base = {
        "kalam": _assessment("kalam", RiskTier.DANGER),
        "mingora": _assessment("mingora", RiskTier.MEDIUM),
    }
    out = engine.propagate(base)
    assert out["mingora"].tier is RiskTier.HIGH


# ---------------------------------------------------------------------------
# Multi-hop chain escalation (A -> B -> C)
# ---------------------------------------------------------------------------


def test_multihop_chain_danger_propagates_through_chain() -> None:
    # Kabal <- Mingora <- Kalam (headwater)
    zones = [
        _zone("kalam", "Kalam"),
        _zone("mingora", "Mingora", upstream="kalam"),
        _zone("kabal",  "Kabal",  upstream="mingora"),
    ]
    engine = EscalationEngine()
    engine.build_graph(zones)
    base = {
        "kalam":   _assessment("kalam",   RiskTier.HIGH),
        "mingora": _assessment("mingora", RiskTier.LOW),
        "kabal":   _assessment("kabal",   RiskTier.LOW),
    }
    out = engine.propagate(base)
    # Kalam (HIGH) → Mingora LOW → MEDIUM
    assert out["mingora"].tier is RiskTier.MEDIUM
    # Now Mingora is MEDIUM after escalation. MEDIUM is not in {HIGH,DANGER}
    # so Kabal stays LOW. Only HIGH/DANGER propagates.
    assert out["kabal"].tier is RiskTier.LOW


def test_multihop_chain_danger_kabal_gets_hit_when_mingora_was_high() -> None:
    zones = [
        _zone("kalam", "Kalam"),
        _zone("mingora", "Mingora", upstream="kalam"),
        _zone("kabal",  "Kabal",  upstream="mingora"),
    ]
    engine = EscalationEngine()
    engine.build_graph(zones)
    base = {
        "kalam":   _assessment("kalam",   RiskTier.DANGER),
        "mingora": _assessment("mingora", RiskTier.HIGH),  # already HIGH locally
        "kabal":   _assessment("kabal",   RiskTier.MEDIUM),
    }
    out = engine.propagate(base)
    # kalam DANGER escalates mingora HIGH → DANGER
    assert out["mingora"].tier is RiskTier.DANGER
    # mingora is now DANGER after first hop (topo order ensures this is
    # committed before kabal is processed), so kabal MEDIUM→HIGH.
    assert out["kabal"].tier is RiskTier.HIGH


# ---------------------------------------------------------------------------
# DANGER cap — don't escalate past DANGER
# ---------------------------------------------------------------------------


def test_already_at_danger_does_not_infinite_escalate() -> None:
    zones = [
        _zone("kalam", "Kalam"),
        _zone("mingora", "Mingora", upstream="kalam"),
    ]
    engine = EscalationEngine()
    engine.build_graph(zones)
    base = {
        "kalam":   _assessment("kalam",   RiskTier.DANGER),
        "mingora": _assessment("mingora", RiskTier.DANGER),
    }
    out = engine.propagate(base)
    assert out["kalam"].tier is RiskTier.DANGER
    assert out["mingora"].tier is RiskTier.DANGER
    # No escalation suffix should be appended since nothing changed.
    assert "Escalated" not in out["mingora"].explanation


# ---------------------------------------------------------------------------
# Cycle detection
# ---------------------------------------------------------------------------


def test_cycle_a_to_b_to_a_raises() -> None:
    zones = [
        _zone("a", "Zone A", upstream="b"),
        _zone("b", "Zone B", upstream="a"),
    ]
    engine = EscalationEngine()
    with pytest.raises(CycleInUpstreamGraph):
        engine.build_graph(zones)


def test_cycle_self_loop_raises() -> None:
    zones = [
        _zone("a", "Zone A", upstream="a"),
    ]
    engine = EscalationEngine()
    with pytest.raises(CycleInUpstreamGraph):
        engine.build_graph(zones)


def test_cycle_three_node_chain_with_backedge_raises() -> None:
    zones = [
        _zone("a", "A"),
        _zone("b", "B", upstream="a"),
        _zone("c", "C", upstream="b"),
        _zone("a", "A-still", upstream="c"),  # zid reused — makes a cycle in the graph
    ]
    engine = EscalationEngine()
    # build_graph iterates zones sequentially; last Zone object for a given
    # zid wins the upstream_zone_id field in the adjacency because we update
    # per-zone and append edges. Reuse zid "a" with upstream="c" creates the
    # cycle a→b→c→a.
    with pytest.raises(CycleInUpstreamGraph):
        engine.build_graph(zones)
