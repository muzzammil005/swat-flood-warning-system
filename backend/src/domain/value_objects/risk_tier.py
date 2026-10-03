from __future__ import annotations

from enum import IntEnum


class RiskTier(IntEnum):
    """Ordered flood-risk tiers used by every downstream consumer.

    IntEnum gives us a natural ordering (``RiskTier.HIGH > RiskTier.MEDIUM``)
    *and* lets us serialise the value as a plain integer for storage/API
    purposes without writing a custom codec. The ordering itself encodes the
    single-hop escalation semantics used by :class:`EscalationEngine`:
    incrementing by one level moves to the next tier, and ``DANGER`` is the
    hard cap.
    """

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    DANGER = 4

    def escalate(self) -> RiskTier:
        """Return the tier one step higher, capped at ``DANGER``."""
        if self is RiskTier.DANGER:
            return RiskTier.DANGER
        return RiskTier(self.value + 1)
