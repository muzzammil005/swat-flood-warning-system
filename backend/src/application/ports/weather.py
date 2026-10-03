"""Weather forecast provider port.

The application layer (Stage 3 :class:`AssessZoneRisk` use case) calls
:meth:`WeatherProvider.fetch_forecast` to get the 24h rainfall outlook for a
zone before handing it to the domain :class:`RiskEngine`. Implementations live
in :mod:`infrastructure.weather` (Open-Meteo adapter in Prompt 5).

Keeping the provider behind an abstract port means:
- We can swap Open-Meteo for a paid provider later without touching the risk engine.
- Unit tests can inject a deterministic fake (deterministic RainfallWindow) and
  get reproducible RiskEngine output regardless of the weather outside.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.value_objects.coordinates import Coordinates
    from domain.value_objects.rainfall_window import RainfallWindow


class WeatherProvider(ABC):
    """Fetch precipitation forecast for a given geographic point."""

    @abstractmethod
    async def fetch_forecast(self, coordinates: Coordinates, /) -> RainfallWindow:
        """Return accumulated rainfall forecast over the next 24 hours.

        Raises an application-layer exception (never a raw HTTP/transport
        exception) if the provider call fails after retries are exhausted.
        """
        ...
