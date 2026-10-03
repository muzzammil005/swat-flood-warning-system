from __future__ import annotations

import pytest

from domain.exceptions import InvalidRainfallWindow
from domain.value_objects import RainfallWindow


def test_rainfall_window_valid_typical() -> None:
    rw = RainfallWindow(millimetres=18.5, duration_hours=24)
    assert rw.millimetres == pytest.approx(18.5)
    assert rw.duration_hours == 24


def test_rainfall_window_boundary_zeros() -> None:
    rw = RainfallWindow(millimetres=0.0, duration_hours=0.0)
    assert rw.millimetres == 0.0
    assert rw.duration_hours == 0.0


def test_rainfall_window_short_intense_window() -> None:
    rw = RainfallWindow(millimetres=60.0, duration_hours=1.0)
    assert rw.millimetres == 60.0
    assert rw.duration_hours == 1.0


def test_rainfall_window_negative_mm_raises() -> None:
    with pytest.raises(InvalidRainfallWindow):
        RainfallWindow(millimetres=-0.001, duration_hours=24)


def test_rainfall_window_negative_hours_raises() -> None:
    with pytest.raises(InvalidRainfallWindow):
        RainfallWindow(millimetres=10.0, duration_hours=-1.0)


def test_rainfall_window_both_negative() -> None:
    with pytest.raises(InvalidRainfallWindow):
        RainfallWindow(millimetres=-5.0, duration_hours=-2.0)


def test_rainfall_window_immutable() -> None:
    rw = RainfallWindow(10.0, 24.0)
    with pytest.raises(AttributeError):
        rw.millimetres = 20.0  # type: ignore[misc]
