from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from domain.exceptions import InvalidThresholds

if TYPE_CHECKING:
    from domain.value_objects.water_level import WaterLevel


@dataclass(frozen=True)
class ZoneThresholds:
    """Per-zone tuning knobs consumed by :class:`RiskEngine`.

    Thresholds are *not* hard-coded inside the engine because different
    sub-catchments have very different hydrology: a 120 cm reading in the
    steep upper Swat (Kalam) is far more serious than 120 cm on the wider,
    deeper lower reaches (Mardan). Keeping them as a value object lets us
    load them from the DB and override them for a zone without touching the
    risk code.

    Invariant: ``water_critical_level > water_warning_level``. The critical
    line must sit above the warning line; equal or reversed means someone
    mis-loaded the calibration sheet and we should fail fast rather than
    silently producing nonsense tiers.
    """

    water_warning_level: WaterLevel
    water_critical_level: WaterLevel
    heavy_rain_threshold_mm: float

    def __post_init__(self) -> None:
        if self.heavy_rain_threshold_mm < 0:
            raise InvalidThresholds(
                "ZoneThresholds.heavy_rain_threshold_mm must be >= 0, "
                f"got {self.heavy_rain_threshold_mm!r}"
            )
        if not (self.water_critical_level > self.water_warning_level):
            raise InvalidThresholds(
                "ZoneThresholds invariant: water_critical_level must be strictly "
                f"above water_warning_level. Got warning={self.water_warning_level.centimetres} "
                f"cm, critical={self.water_critical_level.centimetres} cm."
            )
