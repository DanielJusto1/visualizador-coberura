import pytest

from radiocoverage.geo import GeoPoint, distance_km
from radiocoverage.path import LinkPath

TX = GeoPoint(40.7853, -4.0127)  # Bola del Mundo
RX = GeoPoint(40.9481, -4.1253)  # Segovia


@pytest.fixture
def path():
    return LinkPath(TX, RX, 806.0)


def test_geometry(path):
    assert path.distance_km == pytest.approx(20.43, abs=0.01)
    assert path.bearing_deg == pytest.approx(332.4, abs=0.1)
    assert path.reverse_bearing_deg == pytest.approx((path.bearing_deg + 180) % 360, abs=0.2)
    assert distance_km(TX, path.midpoint) == pytest.approx(path.distance_km / 2)


def test_fresnel_and_bulge(path):
    assert path.fresnel_radius_midpoint_m == pytest.approx(43.6, abs=0.1)
    assert path.clearance_midpoint_m == pytest.approx(0.6 * path.fresnel_radius_midpoint_m)
    assert path.earth_bulge_midpoint_m() == pytest.approx(6.14, abs=0.01)


def test_fresnel_outline(path):
    outline = path.fresnel_outline(samples=40)
    assert len(outline) == 2 * 41 + 1
    assert outline[0] == outline[-1]  # closed polygon
    assert distance_km(outline[0], TX) < 1e-9  # zero width at the transmitter
    assert distance_km(outline[40], RX) < 1e-9  # and at the receiver
    widest_km = distance_km(outline[20], outline[-21 - 1])
    assert widest_km * 1000 == pytest.approx(2 * path.fresnel_radius_midpoint_m, rel=1e-3)


def test_same_location_rejected():
    with pytest.raises(ValueError, match="different locations"):
        LinkPath(TX, TX, 806.0)


def test_outline_needs_samples(path):
    with pytest.raises(ValueError):
        path.fresnel_outline(samples=1)
