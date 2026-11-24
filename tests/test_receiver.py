import pytest

from radiocoverage.receiver import (
    THERMAL_NOISE_DENSITY_DBM_HZ,
    sensitivity_dbm,
    thermal_noise_dbm,
)


def test_thermal_noise_density_is_minus_174():
    assert THERMAL_NOISE_DENSITY_DBM_HZ == pytest.approx(-173.98, abs=0.01)


def test_thermal_noise_in_lte_channels():
    assert thermal_noise_dbm(10.0) == pytest.approx(-103.98, abs=0.01)
    assert thermal_noise_dbm(20.0) == pytest.approx(-100.97, abs=0.01)


def test_sensitivity_formula():
    # 10 MHz, NF 9 dB, SNR -1 dB -> -103.98 + 9 - 1
    assert sensitivity_dbm(10.0, 9.0, -1.0) == pytest.approx(-95.98, abs=0.01)


def test_wider_bandwidth_means_worse_sensitivity():
    assert sensitivity_dbm(100.0, 7.0, 0.0) > sensitivity_dbm(10.0, 7.0, 0.0)


@pytest.mark.parametrize("bandwidth", [0.0, -10.0])
def test_invalid_bandwidth(bandwidth):
    with pytest.raises(ValueError):
        thermal_noise_dbm(bandwidth)


def test_negative_noise_figure_rejected():
    with pytest.raises(ValueError):
        sensitivity_dbm(10.0, -1.0, 0.0)
