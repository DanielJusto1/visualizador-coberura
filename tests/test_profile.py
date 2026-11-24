import math

import numpy as np
import pytest

from radiocoverage.geo import GeoPoint, distance_km_array
from radiocoverage.path import LinkPath
from radiocoverage.profile import (
    bullington_edge,
    fresnel_nu,
    knife_edge_loss_db,
    plot_profile,
    radial_diffraction_db,
    terrain_profile,
)
from radiocoverage.terrain import FlatTerrain, SyntheticTerrain
from radiocoverage.units import wavelength_m

TX = GeoPoint(40.40, -3.80)
RX = GeoPoint(40.40, -3.60)  # ~17 km east
FREQ = 806.0


def ridge(height_m, centre_lon=-3.70, width_deg=0.004):
    """A north-south ridge across the middle of the link."""
    return SyntheticTerrain(
        lambda lat, lon: 600.0 + height_m * np.exp(-(((lon - centre_lon) / width_deg) ** 2))
    )


def test_knife_edge_reference_values():
    # ITU-R P.526: J(0) = 6.0 dB, and J(v) ~ 6.9 + 20 log10(sqrt((v-0.1)^2+1) + v - 0.1)
    assert knife_edge_loss_db(0.0) == pytest.approx(6.03, abs=0.01)
    assert knife_edge_loss_db(1.0) == pytest.approx(13.9, abs=0.1)
    assert knife_edge_loss_db(-0.78) == 0.0
    assert knife_edge_loss_db(-2.0) == 0.0
    losses = knife_edge_loss_db(np.linspace(-0.7, 5, 50))
    assert np.all(np.diff(losses) > 0)


def test_fresnel_nu():
    lam = wavelength_m(FREQ)
    # v = h * sqrt(2 (d1 + d2) / (lambda d1 d2))
    assert fresnel_nu(10.0, 5000.0, 5000.0, lam) == pytest.approx(
        10.0 * math.sqrt(2 * 10000 / (lam * 5000 * 5000))
    )


def test_flat_terrain_is_clear():
    profile = terrain_profile(LinkPath(TX, RX, FREQ), FlatTerrain(600), 30.0, 30.0)
    assert profile.has_line_of_sight
    assert profile.fresnel_clear
    assert profile.diffraction_loss_db == 0.0
    assert profile.status.startswith("clear")
    assert profile.length_km == pytest.approx(LinkPath(TX, RX, FREQ).distance_km)


def test_ridge_blocks_the_link():
    path = LinkPath(TX, RX, FREQ)
    profile = terrain_profile(path, ridge(200.0), 30.0, 1.5)
    assert not profile.has_line_of_sight
    assert profile.status.startswith("obstructed")
    assert profile.diffraction_loss_db > 15.0
    # The equivalent edge sits on the ridge, about halfway along the path.
    assert profile.edge.distance_m / 1000 == pytest.approx(path.distance_km / 2, rel=0.05)


def test_single_knife_edge_matches_textbook():
    # One sharp obstacle on a short flat path: Bullington = single knife edge.
    d = np.linspace(0.0, 10_000.0, 1001)
    ground = np.zeros_like(d)
    ground[500] = 40.0
    lam = wavelength_m(FREQ)
    edge = bullington_edge(d, d[-1], ground, 30.0, 30.0, lam)
    expected_nu = fresnel_nu(10.0, 5000.0, 5000.0, lam)
    assert bool(edge.line_of_sight) is False
    assert edge.nu == pytest.approx(expected_nu, rel=1e-3)
    assert edge.loss_db == pytest.approx(knife_edge_loss_db(expected_nu), rel=1e-3)


def test_higher_ridge_more_loss():
    path = LinkPath(TX, RX, FREQ)
    losses = [
        terrain_profile(path, ridge(h), 30.0, 1.5).diffraction_loss_db for h in (0, 50, 150, 300)
    ]
    assert losses == sorted(losses)
    assert losses[0] < losses[-1]


def test_radial_matches_profile():
    terrain = ridge(150.0)
    path = LinkPath(TX, RX, FREQ)
    profile = terrain_profile(path, terrain, 30.0, 1.5)
    lats, lons = np.array([RX.lat]), np.array([RX.lon])
    radial = radial_diffraction_db(
        TX, 30.0, lats, lons, distance_km_array(TX, lats, lons), 1.5, FREQ, terrain, samples=400
    )
    assert radial[0] == pytest.approx(profile.diffraction_loss_db, abs=1.0)


def test_plot_profile(tmp_path):
    profile = terrain_profile(LinkPath(TX, RX, FREQ), ridge(150.0), 30.0, 1.5)
    output = plot_profile(profile, tmp_path / "profile.png", "Test")
    assert output.read_bytes()[:4] == b"\x89PNG"
    with pytest.raises(ValueError, match=".png"):
        plot_profile(profile, tmp_path / "profile.jpg")
