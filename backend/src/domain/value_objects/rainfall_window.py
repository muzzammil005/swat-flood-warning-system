from __future__ import annotations

from dataclasses import dataclass

from domain.exceptions import InvalidRainfallWindow


@dataclass(frozen=True)
class RainfallWindow:
    """Accumulated precipitation (mm) observed or forecast over ``duration_hours``.

    Both fields are non-negative: a negative accumulation is nonsensical, and
    a negative window duration would invert the meaning of "forecast" vs
    "historical". The default use case in :class:`RiskEngine` is a 24-hour
    forecast window, but the VO itself makes no assumption about length so
    shorter (1 h flash-flood) or longer (72 h) windows can be modelled with
    the same type.
    """

    millimetres: float
    duration_hours: float

    def __post_init__(self) -> None:
        if self.millimetres < 0:
            raise InvalidRainfallWindow(
                f"Rainfall mm must be >= 0, got {self.millimetres!r}"
            )
        if self.duration_hours < 0:
            raise InvalidRainfallWindow(
                f"Rainfall window hours must be >= 0, got {self.duration_hours!r}"
            )
