"""Unit tests for OpenMeteoWeatherProvider using respx mock transport."""

from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest
import respx
from domain.exceptions.base import DomainError
from domain.value_objects.coordinates import Coordinates
from infrastructure.weather import OpenMeteoWeatherProvider


@pytest.fixture
def weather_provider() -> OpenMeteoWeatherProvider:
    """Return a weather provider with short timeouts for testing."""
    return OpenMeteoWeatherProvider(
        base_url="https://api.open-meteo.com",
        timeout_seconds=1.0,
        max_retries=1,
    )


@pytest.mark.asyncio
async def test_fetch_forecast_success(weather_provider: OpenMeteoWeatherProvider) -> None:
    """Test successful forecast fetch with realistic Open-Meteo response."""
    # Mock response data: 24 hours of precipitation values
    mock_response = {
        "latitude": 34.8,
        "longitude": 72.4,
        "generationtime_ms": 0.123,
        "utc_offset_seconds": 0,
        "timezone": "GMT",
        "timezone_abbreviation": "GMT",
        "elevation": 100.0,
        "hourly_units": {
            "time": "iso8601",
            "precipitation (mm)": "mm",
        },
        "hourly": {
            "time": [
                "2024-01-01T00:00", "2024-01-01T01:00", "2024-01-01T02:00",
                "2024-01-01T03:00", "2024-01-01T04:00", "2024-01-01T05:00",
                "2024-01-01T06:00", "2024-01-01T07:00", "2024-01-01T08:00",
                "2024-01-01T09:00", "2024-01-01T10:00", "2024-01-01T11:00",
                "2024-01-01T12:00", "2024-01-01T13:00", "2024-01-01T14:00",
                "2024-01-01T15:00", "2024-01-01T16:00", "2024-01-01T17:00",
                "2024-01-01T18:00", "2024-01-01T19:00", "2024-01-01T20:00",
                "2024-01-01T21:00", "2024-01-01T22:00", "2024-01-01T23:00",
            ],
            "precipitation (mm)": [
                0.0, 0.0, 0.1, 0.2, 0.5, 1.0,  # 0-5h
                2.0, 3.0, 2.5, 1.5, 1.0, 0.5,  # 6-11h  
                0.2, 0.1, 0.0, 0.0, 0.0, 0.0,  # 12-17h
                0.0, 0.0, 0.1, 0.2, 0.3, 0.1,  # 18-23h
            ],
        },
    }
    
    coordinates = Coordinates(latitude=34.8, longitude=72.4)
    
    with respx.mock:
        route = respx.get("https://api.open-meteo.com/v1/forecast").mock(
            return_value=httpx.Response(200, json=mock_response)
        )
        
        rainfall_window = await weather_provider.fetch_forecast(coordinates)
        
        # Verify request was made with correct parameters
        assert route.called
        request = route.calls[0].request
        assert "latitude=34.8" in str(request.url)
        assert "longitude=72.4" in str(request.url)
        assert "hourly=precipitation" in str(request.url)
        assert "forecast_days=1" in str(request.url)
        
        # Verify RainfallWindow calculation
        # Sum of all precipitation values: 0.0+0.0+0.1+0.2+0.5+1.0+2.0+3.0+2.5+1.5+1.0+0.5+0.2+0.1+0.0+0.0+0.0+0.0+0.0+0.0+0.1+0.2+0.3+0.1 = 13.3 mm
        assert rainfall_window.millimetres == pytest.approx(13.3, rel=1e-3)
        assert rainfall_window.duration_hours == 24


@pytest.mark.asyncio
async def test_fetch_forecast_zero_rainfall(weather_provider: OpenMeteoWeatherProvider) -> None:
    """Test forecast with zero precipitation (dry weather)."""
    mock_response = {
        "hourly": {
            "precipitation (mm)": [0.0] * 24,
        },
    }
    
    coordinates = Coordinates(latitude=0.0, longitude=0.0)
    
    with respx.mock:
        respx.get("https://api.open-meteo.com/v1/forecast").mock(
            return_value=httpx.Response(200, json=mock_response)
        )
        
        rainfall_window = await weather_provider.fetch_forecast(coordinates)
        
        assert rainfall_window.millimetres == 0.0
        assert rainfall_window.duration_hours == 24


@pytest.mark.asyncio
async def test_fetch_forecast_http_error(weather_provider: OpenMeteoWeatherProvider) -> None:
    """Test that HTTP errors raise DomainError after retries exhausted."""
    coordinates = Coordinates(latitude=34.8, longitude=72.4)
    
    with respx.mock:
        # Mock a 500 server error
        respx.get("https://api.open-meteo.com/v1/forecast").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        
        with pytest.raises(DomainError, match="Open-Meteo forecast unavailable"):
            await weather_provider.fetch_forecast(coordinates)


@pytest.mark.asyncio
async def test_fetch_forecast_timeout(weather_provider: OpenMeteoWeatherProvider) -> None:
    """Test that timeouts raise DomainError."""
    coordinates = Coordinates(latitude=34.8, longitude=72.4)
    
    with respx.mock:
        # Mock a timeout
        respx.get("https://api.open-meteo.com/v1/forecast").mock(
            side_effect=httpx.TimeoutException("Request timed out")
        )
        
        with pytest.raises(DomainError, match="Open-Meteo forecast unavailable"):
            await weather_provider.fetch_forecast(coordinates)


@pytest.mark.asyncio
async def test_fetch_forecast_invalid_json(weather_provider: OpenMeteoWeatherProvider) -> None:
    """Test that invalid JSON responses raise DomainError."""
    coordinates = Coordinates(latitude=34.8, longitude=72.4)
    
    with respx.mock:
        respx.get("https://api.open-meteo.com/v1/forecast").mock(
            return_value=httpx.Response(200, text="Not JSON")
        )
        
        with pytest.raises(DomainError, match="Open-Meteo forecast unavailable"):
            await weather_provider.fetch_forecast(coordinates)


@pytest.mark.asyncio
async def test_fetch_forecast_missing_precipitation_field(weather_provider: OpenMeteoWeatherProvider) -> None:
    """Test that missing precipitation field raises DomainError."""
    mock_response = {
        "hourly": {
            # Missing "precipitation (mm)" field
            "temperature_2m": [20.0] * 24,
        },
    }
    
    coordinates = Coordinates(latitude=34.8, longitude=72.4)
    
    with respx.mock:
        respx.get("https://api.open-meteo.com/v1/forecast").mock(
            return_value=httpx.Response(200, json=mock_response)
        )
        
        with pytest.raises(DomainError, match="Open-Meteo forecast unavailable"):
            await weather_provider.fetch_forecast(coordinates)


@pytest.mark.asyncio
async def test_fetch_forecast_client_error_no_retry(weather_provider: OpenMeteoWeatherProvider) -> None:
    """Test that client errors (4xx) don't trigger retries."""
    coordinates = Coordinates(latitude=34.8, longitude=72.4)
    
    with respx.mock:
        # Mock a 400 Bad Request (client error)
        respx.get("https://api.open-meteo.com/v1/forecast").mock(
            return_value=httpx.Response(400, text="Bad Request")
        )
        
        with pytest.raises(DomainError, match="Open-Meteo forecast unavailable"):
            await weather_provider.fetch_forecast(coordinates)
        
        # Should only be called once (no retry for client errors)
        assert len(respx.calls) == 1


@pytest.mark.asyncio
async def test_fetch_forecast_server_error_with_retry(weather_provider: OpenMeteoWeatherProvider) -> None:
    """Test that server errors (5xx) trigger retries."""
    coordinates = Coordinates(latitude=34.8, longitude=72.4)
    
    with respx.mock:
        # Mock a 503 Service Unavailable (server error)
        respx.get("https://api.open-meteo.com/v1/forecast").mock(
            return_value=httpx.Response(503, text="Service Unavailable")
        )
        
        with pytest.raises(DomainError, match="Open-Meteo forecast unavailable"):
            await weather_provider.fetch_forecast(coordinates)
        
        # Should be called max_retries + 1 times = 2 times
        assert len(respx.calls) == 2