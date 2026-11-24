import pytest

from radiocoverage.bands import get_band
from radiocoverage.geo import GeoPoint
from radiocoverage.link_budget import LinkParameters, compute_link_budget
from radiocoverage.link_map import FAIL_COLOUR, OK_COLOUR, build_link_map, save_link_map
from radiocoverage.path import LinkPath

TX = GeoPoint(40.4233, -3.6714)
RX = GeoPoint(40.4169, -3.7035)


def make(other_losses_db=0.0):
    band = get_band("n78")
    path = LinkPath(TX, RX, band.centre_mhz)
    params = LinkParameters(
        frequency_mhz=band.centre_mhz,
        distance_km=path.distance_km,
        tx_power_dbm=43.0,
        rx_sensitivity_dbm=-95.0,
        other_losses_db=other_losses_db,
    )
    return path, compute_link_budget(params), band


def render(path, result, band):
    return build_link_map(path, result, band).get_root().render()


def test_map_contents_for_a_working_link():
    html = render(*make())
    assert "5G NR n78" in html
    assert "LINK OK" in html
    assert OK_COLOUR in html
    assert "40.4233" in html and "-3.6714" in html
    assert "First Fresnel zone" in html
    assert "IGN aerial imagery (PNOA)" in html


def test_map_shows_failing_link_in_red():
    html = render(*make(other_losses_db=80.0))
    assert "LINK FAILS" in html
    assert FAIL_COLOUR in html


def test_save_map(tmp_path):
    path, result, band = make()
    output = save_link_map(path, result, tmp_path / "sub" / "link.html", band)
    assert output.exists()
    assert output.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")


def test_save_map_requires_html_extension(tmp_path):
    with pytest.raises(ValueError, match=".html"):
        save_link_map(*make()[:2], tmp_path / "link.png")
