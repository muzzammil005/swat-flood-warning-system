from __future__ import annotations

import pytest

from domain.exceptions import InvalidCoordinates
from domain.value_objects import Coordinates


@pytest.mark.parametrize(
    ("lat", "lon"),
    [
        (34.8, 72.4),          # Swat typical
        (0.0, 0.0),            # Null island
        (90.0, 180.0),         # Top-right corner
        (-90.0, -180.0),       # Bottom-left corner
        (90.0, -180.0),
        (-90.0, 180.0),
        (0.0, 179.999),
        (-0.0000001, 0.0),     # Float negative zero edge
    ],
)
def test_coordinates_valid(lat: float, lon: float) -> None:
    coords = Coordinates(lat, lon)
    assert coords.latitude == pytest.approx(lat)
    assert coords.longitude == pytest.approx(lon)


def test_coordinates_latitude_too_high_raises() -> None:
    with pytest.raises(InvalidCoordinates):
        Coordinates(90.0001, 0.0)


def test_coordinates_latitude_too_low_raises() -> None:
    with pytest.raises(InvalidCoordinates):
        Coordinates(-90.0001, 0.0)


def test_coordinates_longitude_too_high_raises() -> None:
    with pytest.raises(InvalidCoordinates):
        Coordinates(0.0, 180.0001)


def test_coordinates_longitude_too_low_raises() -> None:
    with pytest.raises(InvalidCoordinates):
        Coordinates(0.0, -180.0001)


def test_coordinates_both_invalid_reports_latitude_first() -> None:
    with pytest.raises(InvalidCoordinates):
        Coordinates(999.0, 999.0)


def test_coordinates_immutable() -> None:
    coords = Coordinates(35.0, 72.0)
    with pytest.raises(AttributeError):
        coords.latitude = 36.0  # type: ignore[misc]
