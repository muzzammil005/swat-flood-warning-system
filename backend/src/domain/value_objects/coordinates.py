from __future__ import annotations

from dataclasses import dataclass

from domain.exceptions import InvalidCoordinates


@dataclass(frozen=True)
class Coordinates:
    """A WGS-84 latitude/longitude pair for a sensor or zone centroid.

    Validation uses the classic EPSG:4326 bounds: lat ∈ [-90, 90] and
    lon ∈ [-180, 180]. Swat's zones all sit roughly at (34–36°N, 72–73°E)
    so these bounds are comfortably wide without accepting the kind of
    nonsense values that come from swapping lat/lon order.
    """

    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not (-90.0 <= self.latitude <= 90.0):
            raise InvalidCoordinates(
                f"Latitude must be in [-90, 90], got {self.latitude!r}"
            )
        if not (-180.0 <= self.longitude <= 180.0):
            raise InvalidCoordinates(
                f"Longitude must be in [-180, 180], got {self.longitude!r}"
            )
