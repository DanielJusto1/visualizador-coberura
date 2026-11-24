import numpy as np
import pytest

from radiocoverage.coverage import (
    MAX_GRID_POINTS,
    Receiver,
    Site,
    compute_coverage,
    grid_around,
    make_grid,
)
from radiocoverage.geo import GeoPoint, distance_km_array
from radiocoverage.terrain import SyntheticTerrain

CENTRE = GeoPoint(40.4169, -3.7035)


def site(**overrides):
    values = dict(name="A", location=CENTRE, frequency_mhz=806.0, tx_power_dbm=46.0,
                  tx_gain_dbi=17.0, tx_loss_db=2.0, height_m=30.0)  # fmt: skip
    values.update(overrides)
    return Site(**values)


RECEIVER = Receiver(sensitivity_dbm=-100.0, required_margin_db=5.0)


def test_grid_geometry():
    grid = grid_around([CENTRE], radius_km=5.0, resolution_m=100.0)
    (south, west), (north, east) = grid.bounds
    assert south < CENTRE.lat < north and west < CENTRE.lon < east
    assert grid.shape[0] == pytest.approx(100, abs=2)
    assert grid.pixel_area_km2().sum() == pytest.approx(100.0, rel=0.03)  # 10 x 10 km
    assert np.all(np.diff(grid.lats) < 0)  # north to south


def test_grid_limits():
    with pytest.raises(ValueError, match="limit"):
        make_grid(36, -9, 43, 3, 10.0)
    assert MAX_GRID_POINTS >= 1_000_000
    with pytest.raises(ValueError):
        grid_around([CENTRE], radius_km=0, resolution_m=100)


def test_omni_site_depends_only_on_distance():
    result = compute_coverage([site()], RECEIVER, radius_km=5, resolution_m=200)
    lats, lons = result.grid.mesh()
    distance = distance_km_array(CENTRE, lats, lons).ravel()
    power = result.best_power_dbm.ravel()
    order = np.argsort(distance)
    assert np.all(np.diff(power[order]) <= 1e-9)  # strictly weaker further away


def test_sector_points_where_azimuth_says():
    result = compute_coverage([site(azimuth_deg=90.0)], RECEIVER, radius_km=5, resolution_m=200)
    power = result.best_power_dbm
    row = power.shape[0] // 2
    east, west = power[row, -5], power[row, 4]
    assert east - west == pytest.approx(25.0, abs=1.0)  # front-to-back ratio


def test_best_server_and_areas():
    sites = [site(name="West", location=GeoPoint(40.4169, -3.76)),
             site(name="East", location=GeoPoint(40.4169, -3.64))]  # fmt: skip
    result = compute_coverage(sites, RECEIVER, radius_km=3, resolution_m=200, model="auto")
    server = result.best_server
    row = server.shape[0] // 2
    assert server[row, 2] == 0 and server[row, -3] == 1
    assert sum(result.served_area_km2()) == pytest.approx(result.covered_area_km2)
    assert 0 < result.covered_fraction <= 1


def test_better_receiver_covers_more():
    small = compute_coverage([site()], Receiver(-90.0), radius_km=30, resolution_m=500)
    large = compute_coverage([site()], Receiver(-105.0), radius_km=30, resolution_m=500)
    assert large.covered_area_km2 > small.covered_area_km2


def test_terrain_shadow_reduces_coverage():
    flat = compute_coverage([site()], RECEIVER, radius_km=15, resolution_m=500,
                            environment="rural")  # fmt: skip
    wall = SyntheticTerrain(
        lambda lat, lon: 600.0 + 400.0 * np.exp(-(((lon - (CENTRE.lon + 0.03)) / 0.01) ** 2))
    )
    shadowed = compute_coverage([site()], RECEIVER, radius_km=15, resolution_m=500,
                                environment="rural", terrain=wall)  # fmt: skip
    assert shadowed.terrain
    assert shadowed.covered_area_km2 < flat.covered_area_km2
    row = flat.grid.shape[0] // 2
    # Behind the ridge (east) the signal drops a lot more than in front of it (west).
    east_drop = flat.best_power_dbm[row, -3] - shadowed.best_power_dbm[row, -3]
    west_drop = flat.best_power_dbm[row, 2] - shadowed.best_power_dbm[row, 2]
    assert east_drop > west_drop + 10


@pytest.mark.parametrize(
    "overrides",
    [{"frequency_mhz": 0}, {"height_m": 0}, {"tx_loss_db": -1}, {"azimuth_deg": 400},
     {"beamwidth_deg": 0}],
)  # fmt: skip
def test_invalid_sites(overrides):
    with pytest.raises(ValueError):
        site(**overrides)


def test_invalid_receiver_and_inputs():
    with pytest.raises(ValueError):
        Receiver(-100, height_m=0)
    with pytest.raises(ValueError):
        Receiver(-100, loss_db=-1)
    with pytest.raises(ValueError):
        compute_coverage([], RECEIVER)
    with pytest.raises(ValueError, match="only valid"):
        compute_coverage([site(frequency_mhz=3600.0)], RECEIVER, model="okumura-hata")


def test_site_description():
    assert "sector 120°" in site(azimuth_deg=120).description
    assert "omni" in site().description
    assert site().eirp_dbm == pytest.approx(61.0)
