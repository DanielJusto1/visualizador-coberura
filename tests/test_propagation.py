import math

import pytest

from radiocoverage.propagation import free_space_distance_km, free_space_path_loss_db
from radiocoverage.units import wavelength_m


@pytest.mark.parametrize(
    ("distance_km", "frequency_mhz", "expected_db"),
    [
        (1.0, 2400.0, 100.05),  # classic Wi-Fi textbook value
        (1.0, 1.0, 32.45),  # the constant of the formula
        (10.0, 806.0, 110.57),  # LTE B20
        (0.5, 3600.0, 97.55),  # 5G n78
    ],
)
def test_reference_values(distance_km, frequency_mhz, expected_db):
    assert free_space_path_loss_db(distance_km, frequency_mhz) == pytest.approx(
        expected_db, abs=0.01
    )


def test_matches_friis_definition():
    distance_m = 3_000.0
    frequency_mhz = 1842.5
    friis_db = 20 * math.log10(4 * math.pi * distance_m / wavelength_m(frequency_mhz))
    assert free_space_path_loss_db(3.0, frequency_mhz) == pytest.approx(friis_db)


def test_doubling_distance_adds_6_db():
    base = free_space_path_loss_db(2.0, 1800.0)
    assert free_space_path_loss_db(4.0, 1800.0) - base == pytest.approx(6.0206, abs=1e-4)


def test_ten_times_distance_adds_20_db():
    base = free_space_path_loss_db(1.0, 800.0)
    assert free_space_path_loss_db(10.0, 800.0) - base == pytest.approx(20.0)


def test_higher_frequency_loses_more():
    assert free_space_path_loss_db(1.0, 3600.0) > free_space_path_loss_db(1.0, 800.0)


@pytest.mark.parametrize("distance_km", [0.05, 1.0, 12.3, 250.0])
def test_inverse_recovers_distance(distance_km):
    loss = free_space_path_loss_db(distance_km, 942.5)
    assert free_space_distance_km(loss, 942.5) == pytest.approx(distance_km)


@pytest.mark.parametrize(
    ("distance_km", "frequency_mhz"),
    [(0.0, 800.0), (-1.0, 800.0), (1.0, 0.0), (1.0, -5.0), (math.inf, 800.0), (math.nan, 800.0)],
)
def test_invalid_inputs_rejected(distance_km, frequency_mhz):
    with pytest.raises(ValueError):
        free_space_path_loss_db(distance_km, frequency_mhz)
