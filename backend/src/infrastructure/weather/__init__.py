"""Weather infrastructure adapters.

Exports the Open-Meteo concrete implementation from Prompt 5.
"""

from infrastructure.weather.open_meteo import OpenMeteoWeatherProvider

__all__ = ["OpenMeteoWeatherProvider"]