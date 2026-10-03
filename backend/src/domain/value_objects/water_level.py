from __future__ import annotations

from dataclasses import dataclass

from domain.exceptions import InvalidWaterLevel


@dataclass(frozen=True)
class WaterLevel:
    """River water level in centimetres above the reference gauge zero.

    Immutable; any negative reading is treated as a sensor error (or a
    malformed import) and rejected, because a gauge cannot physically read
    below its own zero datum.
    """

    centimetres: float

    def __post_init__(self) -> None:
        if self.centimetres < 0:
            raise InvalidWaterLevel(
                f"WaterLevel must be >= 0 cm, got {self.centimetres!r}"
            )

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, WaterLevel):
            return NotImplemented
        return self.centimetres < other.centimetres

    def __le__(self, other: object) -> bool:
        if not isinstance(other, WaterLevel):
            return NotImplemented
        return self.centimetres <= other.centimetres

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, WaterLevel):
            return NotImplemented
        return self.centimetres > other.centimetres

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, WaterLevel):
            return NotImplemented
        return self.centimetres >= other.centimetres
