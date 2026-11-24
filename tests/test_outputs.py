import xml.etree.ElementTree as ET
import zipfile

import numpy as np
import pytest

from radiocoverage.coverage import Receiver, Site, compute_coverage
from radiocoverage.coverage_map import build_coverage_map, save_coverage_map
from radiocoverage.coverage_plot import plot_coverage, site_labels
from radiocoverage.geo import GeoPoint
from radiocoverage.kmz import save_kmz
from radiocoverage.rendering import (
    SIGNAL_CLASSES,
    class_ranges_dbm,
    hex_to_rgb,
    mercator_resample,
    server_rgba,
    signal_rgba,
)
from radiocoverage.terrain import FlatTerrain

A = GeoPoint(40.4169, -3.7035)
B = GeoPoint(40.4300, -3.6800)


@pytest.fixture(scope="module")
def network():
    sites = [
        Site("Sol S1", A, 3600.0, 49.0, 17.0, azimuth_deg=0),
        Site("Sol S2", A, 3600.0, 49.0, 17.0, azimuth_deg=120),
        Site("Other", B, 3600.0, 49.0, 17.0),
    ]
    return compute_coverage(sites, Receiver(-95.0, required_margin_db=3), radius_km=1.5,
                            resolution_m=100)  # fmt: skip


def test_signal_classes():
    power = np.array([[-50.0, -75.0, -85.0, -95.0, -105.0]])
    rgba = signal_rgba(power, -100.0)
    assert [tuple(px[:3]) for px in rgba[0][:4]] == [hex_to_rgb(c.colour) for c in SIGNAL_CLASSES]
    assert rgba[0, 4, 3] == 0  # below sensitivity: transparent
    ranges = class_ranges_dbm(-100.0)
    assert ranges[0][1] == "≥ -70 dBm" and ranges[-1][1] == "-100 to -90 dBm"


def test_server_rgba():
    rgba = server_rgba(np.array([[-1, 0, 1]]))
    assert (
        rgba[0, 0, 3] == 0 and rgba[0, 1, 3] > 0 and tuple(rgba[0, 1, :3]) != tuple(rgba[0, 2, :3])
    )


def test_mercator_resample_keeps_shape():
    image = np.zeros((100, 10, 4), np.uint8)
    image[:50] = 255
    out = mercator_resample(image, 40.0, 41.0)
    assert out.shape == image.shape
    assert 45 <= int((out[:, 0, 0] == 255).sum()) <= 55


def test_coverage_map(network, tmp_path):
    html = build_coverage_map(network).get_root().render()
    assert "Network coverage" in html and "Best server" in html and "Sol S2" in html
    saved = save_coverage_map(network, tmp_path / "map.html")
    assert saved.exists()
    with pytest.raises(ValueError):
        save_coverage_map(network, tmp_path / "map.txt")


def test_kmz(network, tmp_path):
    output = save_kmz(network, tmp_path / "net.kmz")
    with zipfile.ZipFile(output) as kmz:
        assert set(kmz.namelist()) == {"doc.kml", "signal.png", "best_server.png"}
        root = ET.fromstring(kmz.read("doc.kml"))
    ns = {"k": "http://www.opengis.net/kml/2.2"}
    assert len(root.findall(".//k:GroundOverlay", ns)) == 2
    assert len(root.findall(".//k:Placemark", ns)) == 3
    north = float(root.find(".//k:north", ns).text)
    assert north == pytest.approx(network.grid.bounds[1][0])
    with pytest.raises(ValueError):
        save_kmz(network, tmp_path / "net.kml")


@pytest.mark.parametrize("layer", ["signal", "server"])
def test_plot(network, tmp_path, layer):
    out = plot_coverage(network, tmp_path / f"{layer}.png", terrain=FlatTerrain(650), layer=layer)
    assert out.read_bytes()[:4] == b"\x89PNG"


def test_site_labels_group_sectors(network):
    labels = site_labels(network.sites)
    assert labels == {A: "Sol", B: "Other"}
