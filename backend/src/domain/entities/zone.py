from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.value_objects import Coordinates


@dataclass
class Zone:
    """A geographic flood-monitoring zone (e.g. a river-basin sub-catchment).

    ``upstream_zone_id`` is the self-referential edge that lets
    :class:`EscalationEngine` model the river as a directed graph: zone A
    (upstream) can propagate risk downstream to zone B. A zone with no
    upstream neighbour is a river headwater (``upstream_zone_id = None``).
    """

    id: str
    name: str
    coordinates: Coordinates
    upstream_zone_id: str | None = None
