from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from domain.exceptions import DomainError

if TYPE_CHECKING:
    from datetime import datetime

    from domain.value_objects import WaterLevel


@dataclass
class SensorReading:
    """A single water-level observation from a gauge inside a :class:`Zone`.

    ``source`` distinguishes real gauges from synthetic/seeded test data so we
    never accidentally plot a QA fixture against a live dashboard. This is a
    thin marker on the domain entity — enforcement of "don't use test data in
    production" lives in the application layer.
    """

    id: str
    zone_id: str
    water_level: WaterLevel
    timestamp: datetime
    source: Literal["real", "test"]

    def __post_init__(self) -> None:
        if self.source not in {"real", "test"}:
            raise DomainError(
                f"SensorReading.source must be 'real' or 'test', got {self.source!r}"
            )
