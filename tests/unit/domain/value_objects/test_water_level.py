from __future__ import annotations

import pytest

from domain.exceptions import InvalidWaterLevel
from domain.value_objects import WaterLevel


def test_water_level_valid_positive() -> None:
    wl = WaterLevel(150.5)
    assert wl.centimetres == 150.5


def test_water_level_boundary_zero() -> None:
    wl = WaterLevel(0.0)
    assert wl.centimetres == 0.0


def test_water_level_boundary_large_value() -> None:
    wl = WaterLevel(1_000_000.0)
    assert wl.centimetres == 1_000_000.0


def test_water_level_negative_raises() -> None:
    with pytest.raises(InvalidWaterLevel):
        WaterLevel(-0.001)


def test_water_level_very_negative_raises() -> None:
    with pytest.raises(InvalidWaterLevel):
        WaterLevel(-500.0)


def test_water_level_ordering_less_than() -> None:
    assert WaterLevel(50) < WaterLevel(100)
    assert not (WaterLevel(100) < WaterLevel(50))


def test_water_level_ordering_equal() -> None:
    assert WaterLevel(100) <= WaterLevel(100)
    assert WaterLevel(100) >= WaterLevel(100)


def test_water_level_greater_than() -> None:
    assert WaterLevel(200) > WaterLevel(100)
    assert not (WaterLevel(50) > WaterLevel(100))


def test_water_level_immutable_via_frozen() -> None:
    wl = WaterLevel(100)
    with pytest.raises(AttributeError):
        wl.centimetres = 200  # type: ignore[misc]
