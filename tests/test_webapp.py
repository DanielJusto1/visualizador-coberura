"""The pages of the web interface run end to end (headless, with Streamlit's AppTest)."""

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
pytest.importorskip("streamlit_folium")
from streamlit.testing.v1 import AppTest  # noqa: E402

from radiocoverage.geo import GeoPoint  # noqa: E402
from radiocoverage.webapp.placement import Placement  # noqa: E402
from radiocoverage.webapp.presets import EXAMPLE_NETWORKS  # noqa: E402
from radiocoverage.webapp.sites_table import example_rows  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RUNNER = str(ROOT / "tests" / "web_page_runner.py")
APP = str(ROOT / "app" / "streamlit_app.py")


def page(name: str, lang: str = "es", **state) -> AppTest:
    app = AppTest.from_file(RUNNER, default_timeout=120)
    app.session_state["page"] = name
    app.session_state["lang"] = lang
    for key, value in state.items():
        app.session_state[key] = value
    return app.run()


def markdown(app: AppTest) -> str:
    return "\n".join(element.value for element in app.markdown)


def button(app: AppTest, label: str):
    return next(b for b in app.button if b.label == label)


def test_full_app_starts_on_the_planner():
    app = AppTest.from_file(APP, default_timeout=120).run()
    assert not app.exception
    assert "Planificador en mapa" in markdown(app)


@pytest.mark.parametrize("name", ["planner", "network", "link", "about"])
@pytest.mark.parametrize("lang", ["es", "en"])
def test_every_page_renders(name, lang):
    app = page(name, lang)
    assert not app.exception, app.exception
    assert not app.error


def test_planner_shows_steps_until_both_ends_are_placed():
    app = page("planner")
    assert "Coloca el transmisor" in markdown(app)
    assert not app.metric


def test_planner_link_results():
    placement = Placement(GeoPoint(40.7930, -3.9620), GeoPoint(40.9481, -4.1253), "rx")
    app = page("planner", pl_placement=placement)
    assert not app.exception
    assert "ENLACE" in markdown(app)
    labels = [metric.label for metric in app.metric]
    assert labels[:4] == ["Distancia", "Potencia recibida", "Margen", "Pérdidas de propagación"]
    assert app.metric[0].value == "22.04 km"
    assert [tab.label for tab in app.tabs][:4] == [
        "Presupuesto", "Perfil del terreno", "Potencia vs distancia", "Exportar",
    ]  # fmt: skip
    # The coordinate inputs follow the placed points
    assert app.number_input(key="pl_tx_lat").value == pytest.approx(40.7930)


def test_planner_swap_and_clear():
    placement = Placement(GeoPoint(40.7930, -3.9620), GeoPoint(40.9481, -4.1253), "rx")
    app = page("planner", pl_placement=placement)
    button(app, "Invertir").click().run()
    swapped = app.session_state["pl_placement"]
    assert swapped.tx == placement.rx and swapped.rx == placement.tx
    button(app, "Borrar").click().run()
    assert app.session_state["pl_placement"].empty


def test_planner_coverage_of_the_transmitter():
    placement = Placement(GeoPoint(40.4169, -3.7035), None, "rx")
    app = page("planner", pl_placement=placement, pl_cov_radius=2.0, pl_cov_res=200)
    button(app, "Calcular cobertura").click().run()
    assert not app.exception
    assert "Área cubierta" in [metric.label for metric in app.metric]


def test_planner_typed_coordinates_move_the_point():
    placement = Placement(GeoPoint(40.4169, -3.7035), GeoPoint(40.40, -3.60), "rx")
    app = page("planner", pl_placement=placement)
    app.number_input(key="pl_rx_lat").set_value(40.45).run()
    assert app.session_state["pl_placement"].rx.lat == pytest.approx(40.45)


def test_network_example_coverage():
    network = EXAMPLE_NETWORKS["madrid_5g"]
    app = page("network", "en", nw_base=example_rows(network), nw_radius=0.5, nw_res=100)
    assert "Sites (15)" in markdown(app)
    button(app, "Compute coverage").click().run()
    assert not app.exception
    labels = [metric.label for metric in app.metric]
    assert labels == ["Covered area", "Covered fraction", "Sectors"]
    assert app.metric[2].value == "15"
    assert [b.label for b in app.get("download_button")]  # KMZ, map and image


def test_network_reports_bad_rows():
    rows = [{"name": "Paris", "lat": 48.85, "lon": 2.35, "band": "b20"}]
    app = page("network", nw_base=rows)
    assert any("fuera de España" in warning.value for warning in app.warning)


def test_link_page_default_link():
    app = page("link", "en")
    assert "LINK" in markdown(app)
    assert app.metric[0].value == "22.04 km"


def test_link_page_rejects_points_outside_spain():
    app = page("link", lk_tx_place="Madrid · Puerta del Sol")
    app.number_input(key="lk_rx_lon").set_value(2.35).run()
    app.number_input(key="lk_rx_lat").set_value(48.85).run()
    assert any("fuera de España" in error.value for error in app.error)


def test_band_change_loads_typical_values():
    app = page("link")
    app.selectbox(key="lk_band").set_value("n78").run()
    assert app.number_input(key="lk_txp").value == 49.0
    assert app.number_input(key="lk_bw").value == 100.0
