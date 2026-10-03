"""Open-Meteo HTTP adapter for the WeatherProvider port.

Fetches 24‑hour precipitation forecast for a given Coordinates via the
Open-Meteo free public API (https://open-meteo.com). The API returns hourly
forecast data; we sum the precipitation values over the next 24 hours and
wrap them in a domain RainfallWindow.

If the HTTP call fails after retries, we raise a domain-friendly exception
instead of leaking httpx errors up to the use case.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from application.ports.weather import WeatherProvider
from domain.exceptions.base import DomainError
from domain.value_objects.rainfall_window import RainfallWindow

if TYPE_CHECKING:
    from domain.value_objects.coordinates import Coordinates


class _OpenMeteoHourlyResponse(BaseModel):
    """Hourly forecast fields we care about from Open-Meteo JSON."""

    precipitation: list[float] = Field(alias="precipitation (mm)")


class _OpenMeteoForecastResponse(BaseModel):
    """Top‑level Open-Meteo forecast response."""

    hourly: _OpenMeteoHourlyResponse
    model_config = ConfigDict(extra="ignore")


class OpenMeteoWeatherProvider(WeatherProvider):
    """Concrete WeatherProvider that talks to the Open-Meteo HTTP API."""

    def __init__(
        self,
        *,
        base_url: str = "https://api.open-meteo.com",
        timeout_seconds: float = 10.0,
        max_retries: int = 2,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._max_retries = max_retries

        # Use a single client instance for connection pooling
        self._client = httpx.AsyncClient(
            timeout=timeout_seconds,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )

    async def fetch_forecast(self, coordinates: Coordinates, /) -> RainfallWindow:
        """Return accumulated rainfall forecast over the next 24 hours.

        Raises:
            DomainError: If the API call fails after retries, or the response
                schema doesn't match what we expect.
        """
        # Open-Meteo expects latitude first, longitude second (standard "lat, lon")
        params: dict[str, Any] = {
            "latitude": coordinates.latitude,
            "longitude": coordinates.longitude,
            "hourly": "precipitation",
            "forecast_days": 1,  # We only need 24h ahead
            "timezone": "auto",
        }

        last_exception: Exception | None = None

        for _attempt in range(self._max_retries + 1):
            try:
                response = await self._client.get(
                    f"{self._base_url}/v1/forecast",
                    params=params,
                )
                response.raise_for_status()

                data = response.json()
                validated = _OpenMeteoForecastResponse.model_validate(data)

                # Sum precipitation over the next 24 hours
                # Open-Meteo returns hourly values; we sum the first 24 entries
                hourly_mm = validated.hourly.precipitation[:24]  # safety slice
                total_mm = sum(hourly_mm)

                return RainfallWindow(
                    millimetres=total_mm,
                    duration_hours=24,
                )

            except httpx.HTTPError as exc:
                last_exception = exc
                # Don't retry on client errors (4xx), only on server errors (5xx) or network
                if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code < 500:
                    break
                # Continue to next retry attempt

            except (ValidationError, json.JSONDecodeError, KeyError, IndexError) as exc:
                # Schema mismatch or malformed response – unlikely to succeed on retry
                last_exception = exc
                break

            except Exception as exc:
                # Network timeout, connection reset, etc.
                last_exception = exc
                # Continue to next retry attempt

        # All retries exhausted
        raise DomainError(
            f"Open-Meteo forecast unavailable for {coordinates}: {last_exception!s}"
        )

    async def close(self) -> None:
        """Close the underlying HTTP client (call this on shutdown)."""
        await self._client.aclose()

    async def __aenter__(self) -> OpenMeteoWeatherProvider:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()


# Export only the concrete implementation; the abstract WeatherProvider
# is already exported by application.ports.weather
__all__ = ["OpenMeteoWeatherProvider"]