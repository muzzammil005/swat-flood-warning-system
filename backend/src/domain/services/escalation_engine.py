"""EscalationEngine — propagate HIGH/DANGER risk from upstream zones downstream.

Design rationale (for the viva):

Flood propagation across a river basin is inherently a directed-graph problem.
Zones are nodes; ``Zone.upstream_zone_id`` defines a directed edge from
**upstream → downstream** (the direction water actually flows). Treating this
as a flat loop-over-zones-with-upstream check works for 2–3 zones but breaks
the second you have a chain A→B→C and need A's DANGER tier to reach C in one
pass. EscalationEngine solves this properly:

1. Build an upstream→downstreams adjacency list from a list of :class:`Zone`.
2. Compute a topological order via Kahn's algorithm so we always finish an
   upstream node *before* any of its downstream children (correct propagation
   in one pass, no re-scan required). The order and adjacency are cached on
   the engine so `propagate` stays O(V + E) per cycle.
3. During topo construction, if the queue drains before every node has been
   visited, the graph contains a cycle (a zone being its own ancestor —
   physically impossible in a river) and we raise :class:`CycleInUpstreamGraph`
   instead of silently producing an infinite loop.

This generalises cleanly to arbitrary topologies: a zone can be upstream of
several siblings (e.g. main river → two flood-plain sub-zones), and chains of
any length still propagate correctly.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from domain.entities import RiskAssessment, Zone
from domain.exceptions import CycleInUpstreamGraph
from domain.value_objects import RiskTier


@dataclass
class EscalationEngine:
    """Propagates upstream HIGH/DANGER tiers to downstream zones.

    Usage::

        engine = EscalationEngine()
        engine.build_graph(all_zones)             # raises CycleInUpstreamGraph if cyclic
        final = engine.propagate(base_tiers_dict) # O(V+E), one pass
    """

    _adjacency: dict[str, list[str]] = field(default_factory=dict)
    _zone_name: dict[str, str] = field(default_factory=dict)
    _topo_order: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def build_graph(self, zones: list[Zone]) -> None:
        """Build adjacency + topological order.

        Raises :class:`CycleInUpstreamGraph` immediately if the upstream
        relationships contain a directed cycle.
        """
        self._adjacency = {}
        self._zone_name = {}
        in_degree: dict[str, int] = {}
        all_ids: set[str] = set()

        for z in zones:
            zid = z.id
            self._zone_name[zid] = z.name
            self._adjacency.setdefault(zid, [])
            in_degree.setdefault(zid, 0)
            all_ids.add(zid)
            upstream = z.upstream_zone_id
            if upstream is None:
                continue
            # Register the upstream node even if no Zone obj was passed for it
            # (tolerant lookup; topo-sort will still handle it).
            self._adjacency.setdefault(upstream, [])
            self._adjacency[upstream].append(zid)
            in_degree[zid] += 1
            in_degree.setdefault(upstream, 0)
            all_ids.add(upstream)

        self._topo_order = self._topo_sort(in_degree, all_ids)

    # ------------------------------------------------------------------
    # Propagation
    # ------------------------------------------------------------------

    def propagate(
        self,
        base_assessments: dict[str, RiskAssessment],
    ) -> dict[str, RiskAssessment]:
        """Propagate HIGH/DANGER upstream tiers downstream in topological order.

        A single pass is sufficient because upstream nodes are always visited
        before their downstreams. DANGER is the hard ceiling (never escalated
        further). The downstream assessment's ``explanation`` is appended with
        the source zone name so the SHAP panel can show the chain of causes.
        """
        if not self._topo_order:
            return dict(base_assessments)

        escalated: dict[str, RiskAssessment] = dict(base_assessments)

        for zid in self._topo_order:
            upstream_assessment = escalated.get(zid)
            if upstream_assessment is None:
                continue
            if upstream_assessment.tier not in {RiskTier.HIGH, RiskTier.DANGER}:
                continue
            for downstream_id in self._adjacency.get(zid, []):
                down = escalated.get(downstream_id)
                if down is None:
                    continue
                if down.tier is RiskTier.DANGER:
                    continue
                new_tier = down.tier.escalate()
                source_name = self._zone_name.get(zid, zid)
                suffix = (
                    f" Escalated due to heavy rain/high risk in {source_name} "
                    f"({upstream_assessment.tier.name})."
                )
                new_probability = min(down.probability + 0.08, 0.995)
                escalated[downstream_id] = RiskAssessment(
                    zone_id=down.zone_id,
                    tier=new_tier,
                    probability=new_probability,
                    explanation=down.explanation.rstrip() + suffix,
                    computed_at=down.computed_at,
                )

        return escalated

    # ------------------------------------------------------------------
    # Internal: Kahn's topological sort + cycle detection
    # ------------------------------------------------------------------

    def _topo_sort(self, in_degree: dict[str, int], all_ids: set[str]) -> list[str]:
        q: deque[str] = deque(zid for zid in all_ids if in_degree.get(zid, 0) == 0)
        seen: list[str] = []
        while q:
            nid = q.popleft()
            seen.append(nid)
            for nbr in self._adjacency.get(nid, []):
                in_degree[nbr] -= 1
                if in_degree[nbr] == 0:
                    q.append(nbr)
        if len(seen) != len(all_ids):
            raise CycleInUpstreamGraph(
                "Upstream zone graph contains a cycle; a zone cannot be its own ancestor."
            )
        return seen
