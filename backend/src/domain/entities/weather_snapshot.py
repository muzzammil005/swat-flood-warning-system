from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from domain.exceptions import DomainError

if TYPE_CHECKING:
    from datetime import datetime

    from domain.value_objects import RainfallWindow


@dataclass
class WeatherSnapshot:
    """A weather-provider forecast cached for a zone.

    ``ttl_seconds`` controls how long the infrastructure layer will keep this
    snapshot in Redis before refreshing from the provider (Open-Meteo) again.
    We carry the TTL on the domain entity rather than hiding it purely inside
    the cache adapter so the RiskEngine can distinguish a stale (>24h) forecast
    from a fresh one if it ever needs to.
    """

    zone_id: str
    rainfall: RainfallWindow
    fetched_at: datetime
    ttl_seconds: int

    def __post_init__(self) -> None:
        if self.ttl_seconds < 0:
            raise DomainError(
                f"WeatherSnapshot.ttl_seconds must be >= 0, got {self.ttl_seconds!r}"
            )
