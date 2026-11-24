import math

import pytest

from radiocoverage.fresnel import earth_bulge_m, fresnel_radius_m


def test_midpoint_radius_rule_of_thumb():
    # Textbook formula at mid-path: r = 8.656 * sqrt(D_km / f_GHz) metres.
    for distance, freq_mhz in [(10.0, 1000.0), (20.43, 806.0), (2.0, 3600.0)]:
        expected = 8.656 * math.sqrt(distance / (freq_mhz / 1000.0))
        assert fresnel_radius_m(distance / 2, distance / 2, freq_mhz) == pytest.approx(
            expected, rel=1e-3
        )


def test_radius_is_zero_at_the_ends_and_widest_in_the_middle():
    assert fresnel_radius_m(0.0, 10.0, 1800.0) == 0.0
    assert fresnel_radius_m(10.0, 0.0, 1800.0) == 0.0
    assert fresnel_radius_m(5.0, 5.0, 1800.0) > fresnel_radius_m(2.0, 8.0, 1800.0)


def test_higher_zones_and_frequencies():
    first = fresnel_radius_m(5.0, 5.0, 1800.0)
    assert fresnel_radius_m(5.0, 5.0, 1800.0, zone=2) == pytest.approx(first * math.sqrt(2))
    assert fresnel_radius_m(5.0, 5.0, 3600.0) < first


def test_earth_bulge():
    # Classic formula h = d1 * d2 / (12.74 * k) metres, with d1 and d2 in km.
    assert earth_bulge_m(5.0, 5.0) == pytest.approx(25 / (12.742 * 4 / 3), rel=1e-3)
    assert earth_bulge_m(10.0, 10.0, k_factor=1.0) == pytest.approx(7.85, abs=0.01)
    assert earth_bulge_m(0.0, 10.0) == 0.0


@pytest.mark.parametrize(
    ("args", "kwargs"),
    [((-1.0, 5.0, 900.0), {}), ((0.0, 0.0, 900.0), {}), ((5.0, 5.0, 900.0), {"zone": 0})],
)
def test_invalid_fresnel_inputs(args, kwargs):
    with pytest.raises(ValueError):
        fresnel_radius_m(*args, **kwargs)


def test_invalid_bulge_inputs():
    with pytest.raises(ValueError):
        earth_bulge_m(-1.0, 5.0)
    with pytest.raises(ValueError):
        earth_bulge_m(5.0, 5.0, k_factor=0.0)
