"""Logic behind the web interface (no Streamlit session needed)."""

import math

import pytest

pytest.importorskip("streamlit")

from radiocoverage.bands import BANDS  # noqa: E402
from radiocoverage.geo import GeoPoint, is_in_spain  # noqa: E402
from radiocoverage.link_budget import compute_link_budget  # noqa: E402
from radiocoverage.path import LinkPath  # noqa: E402
from radiocoverage.profile import terrain_profile  # noqa: E402
from radiocoverage.terrain import SyntheticTerrain  # noqa: E402
from radiocoverage.webapp import charts  # noqa: E402
from radiocoverage.webapp.placement import (  # noqa: E402
    Placement,
    check_point,
    clear,
    place,
    set_point,
    swap,
)
from radiocoverage.webapp.presets import (  # noqa: E402
    BAND_PROFILES,
    EXAMPLE_NETWORKS,
    PLACES,
)
from radiocoverage.webapp.settings import RadioSettings  # noqa: E402
from radiocoverage.webapp.sites_table import (  # noqa: E402
    apply_editor_changes,
    example_rows,
    new_row,
    rows_to_sites,
)
from radiocoverage.webapp.tables import budget_csv, link_budget_rows  # noqa: E402

MADRID = (40.4169, -3.7035)
TOLEDO = (39.8628, -4.0273)


def settings(**overrides) -> RadioSettings:
    values = dict(
        band_key="b20", tx_power_dbm=46.0, tx_gain_dbi=17.0, tx_loss_db=2.0, tx_height_m=30.0,
        rx_height_m=1.5, rx_gain_dbi=0.0, rx_loss_db=3.0, other_losses_db=0.0,
        sensitivity_dbm=-96.0, margin_db=6.0, model="auto", environment="rural", terrain=False,
    )  # fmt: skip
    values.update(overrides)
    return RadioSettings(**values)


# --- Placement by clicks -------------------------------------------------------------


def test_two_clicks_build_a_link():
    state, message = place(Placement(), *MADRID)
    assert message == "planner.msg.tx_placed"
    assert state.tx == GeoPoint(*MADRID) and state.mode == "rx"
    state, message = place(state, *TOLEDO)
    assert message == "planner.msg.rx_placed"
    assert state.complete and state.mode == "rx"
    # Further clicks keep moving the receiver
    state, _ = place(state, 40.0, -3.9)
    assert state.rx == GeoPoint(40.0, -3.9) and state.tx == GeoPoint(*MADRID)


def test_placing_receiver_first_switches_to_transmitter():
    state, message = place(Placement(mode="rx"), *TOLEDO)
    assert message == "planner.msg.rx_placed" and state.mode == "tx"


@pytest.mark.parametrize(
    ("lat", "lon", "message"),
    [(48.85, 2.35, "planner.msg.outside"), (95.0, 0.0, "planner.msg.invalid")],
)
def test_rejected_clicks_keep_the_state(lat, lon, message):
    state = Placement(tx=GeoPoint(*MADRID), mode="rx")
    new, result = place(state, lat, lon)
    assert result == message and new == state


def test_too_close_and_helpers():
    state = Placement(tx=GeoPoint(*MADRID), mode="rx")
    assert place(state, MADRID[0] + 0.00001, MADRID[1])[1] == "planner.msg.too_close"
    full = Placement(GeoPoint(*MADRID), GeoPoint(*TOLEDO), "rx")
    assert swap(full).tx == full.rx and swap(full).rx == full.tx
    assert clear() == Placement() and clear().empty
    moved, error = set_point(full, "rx", 40.1, -3.8)
    assert error is None and moved.rx == GeoPoint(40.1, -3.8)
    assert set_point(full, "rx", 51.5, -0.1)[1] == "planner.msg.outside"
    assert check_point(*MADRID)[1] is None


# --- Presets and settings ------------------------------------------------------------


def test_presets_are_consistent():
    assert set(BAND_PROFILES) == set(BANDS)
    for lat, lon, zoom in PLACES.values():
        assert is_in_spain(GeoPoint(lat, lon)) and 5 <= zoom <= 18
    for network in EXAMPLE_NETWORKS.values():
        assert network.band_key in BANDS
        sites, errors = rows_to_sites(example_rows(network))
        assert not errors and len(sites) == len(network.sites)


def test_settings_build_core_objects():
    s = settings()
    assert s.frequency_mhz == pytest.approx(806.0)
    assert s.eirp_dbm == pytest.approx(61.0)
    params = s.link_parameters(10.0, terrain_loss_db=4.0)
    assert params.terrain_loss_db == 4.0 and params.required_margin_db == 6.0
    assert s.receiver().threshold_dbm == pytest.approx(-90.0)
    site = s.site("A", GeoPoint(*MADRID), azimuth_deg=90.0)
    assert site.is_sector and site.band_name == "LTE B20"
    assert hash(s) == hash(settings())  # usable as a cache key


# --- Sites table ----------------------------------------------------------------------


def test_apply_editor_changes():
    base = [
        new_row("A", 40.0, -3.0, "b20", 46, 17, 30),
        new_row("B", 41.0, -3.5, "n78", 49, 24, 25),
    ]
    defaults = {"name": "New", "band": "b3", "power": 46, "lat": None, "lon": None}
    changes = {
        "edited_rows": {0: {"name": "A2", "azimuth": 120}},
        "deleted_rows": [1],
        "added_rows": [{"lat": 40.5, "lon": -3.2}],
    }
    rows = apply_editor_changes(base, changes, defaults)
    assert [r["name"] for r in rows] == ["A2", "New"]
    assert rows[0]["azimuth"] == 120 and rows[1]["band"] == "b3" and rows[1]["lat"] == 40.5
    assert apply_editor_changes(base, None, defaults) == base
    assert base[0]["name"] == "A"  # input not modified


def test_rows_to_sites_reports_problems():
    rows = [
        new_row("Good", 40.4, -3.7, "b20", 46, 17, 30, azimuth=400),
        {"name": "No coords", "lat": None, "lon": None, "band": "b20"},
        new_row("Paris", 48.85, 2.35, "b20", 46, 17, 30),
        new_row("Bad band", 40.4, -3.7, "x1", 46, 17, 30),
        {"name": "Defaults", "lat": 40.0, "lon": -4.0, "band": "n78", "power": float("nan")},
    ]
    sites, errors = rows_to_sites(rows, tx_loss_db=1.0)
    assert [s.name for s in sites] == ["Good", "Defaults"]
    assert sites[0].azimuth_deg == pytest.approx(40.0)  # wrapped to 0-360
    assert sites[1].tx_power_dbm == BAND_PROFILES["n78"].tx_power_dbm
    assert sites[1].tx_loss_db == 1.0
    assert [(e.row, e.key) for e in errors] == [
        (2, "network.error.coordinates"), (3, "network.error.outside"), (4, "network.error.band"),
    ]  # fmt: skip


# --- Tables and charts ----------------------------------------------------------------


@pytest.fixture
def link():
    path = LinkPath(GeoPoint(40.40, -3.80), GeoPoint(40.40, -3.60), 806.0)
    ridge = SyntheticTerrain(lambda lat, lon: 600 + 150 * (abs(lon + 3.7) < 0.003))
    profile = terrain_profile(path, ridge, 30.0, 1.5)
    budget = compute_link_budget(
        settings().link_parameters(path.distance_km, profile.diffraction_loss_db)
    )
    return path, budget, profile


@pytest.mark.parametrize("lang", ["es", "en"])
def test_link_budget_rows(link, lang):
    path, budget, profile = link
    rows = link_budget_rows(budget, path, profile, lang)
    items = [row["item"] for row in rows]
    assert ("Potencia recibida" if lang == "es" else "Received power") in items
    assert ("Pérdidas por difracción" if lang == "es" else "Diffraction loss") in items
    verdict = rows[-2]["value"]
    assert verdict in ("ENLACE VIABLE", "ENLACE NO VIABLE", "LINK OK", "LINK FAILS")
    csv = budget_csv(rows)
    assert csv.splitlines()[0] == "section;item;value" and len(csv.splitlines()) == len(rows) + 1


def test_rows_without_path_or_terrain(link):
    _, budget, _ = link
    items = [row["item"] for row in link_budget_rows(budget, lang="en")]
    assert "Distance" not in items and "Terrain" not in items


def test_charts(link):
    path, budget, profile = link
    frame = charts.profile_frame(profile)
    assert (frame["fresnel_high_m"] >= frame["los_m"]).all()
    assert charts.profile_chart(profile, "es").to_dict()["layer"]
    power = charts.power_distance_frame(budget, path.distance_km)
    assert power["distance_km"].is_monotonic_increasing
    assert (power["model_dbm"] <= power["free_space_dbm"] + 1e-9).all()
    spec = charts.power_distance_chart(budget, path.distance_km, "en").to_dict()
    assert spec["layer"] and math.isfinite(budget.rx_power_dbm)
