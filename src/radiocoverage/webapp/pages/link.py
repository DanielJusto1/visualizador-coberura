"""Link page: a point-to-point link from typed coordinates or well-known places."""

import streamlit as st

from radiocoverage.terrain import TerrainError
from radiocoverage.webapp import style
from radiocoverage.webapp.compute import link_analysis
from radiocoverage.webapp.placement import check_point
from radiocoverage.webapp.presets import PLACES
from radiocoverage.webapp.results import render_link_results
from radiocoverage.webapp.texts import t
from radiocoverage.webapp.widgets import init_defaults, radio_settings

P = "lk"
DEFAULTS = {"tx": "Sierra de Guadarrama · Bola del Mundo", "rx": "Segovia · Plaza Mayor"}


def _on_place(end: str) -> None:
    name = st.session_state.get(f"{P}_{end}_place")
    if name in PLACES:
        lat, lon, _ = PLACES[name]
        st.session_state[f"{P}_{end}_lat"] = lat
        st.session_state[f"{P}_{end}_lon"] = lon


def _end_inputs(end: str) -> None:
    if f"{P}_{end}_place" not in st.session_state:
        st.session_state[f"{P}_{end}_place"] = DEFAULTS[end]
        _on_place(end)
    with st.container(border=True):
        st.markdown(f"**{t(f'planner.mode.{end}')}**")
        st.selectbox(
            t("link.place"), list(PLACES), key=f"{P}_{end}_place", on_change=_on_place,
            args=(end,), help=t("help.link_place"),
        )  # fmt: skip
        c1, c2 = st.columns(2)
        c1.number_input(t("link.lat"), -90.0, 90.0, format="%.6f", step=0.0001,
                        key=f"{P}_{end}_lat")  # fmt: skip
        c2.number_input(t("link.lon"), -180.0, 180.0, format="%.6f", step=0.0001,
                        key=f"{P}_{end}_lon")  # fmt: skip


def render() -> None:
    init_defaults(P, "b20", env="rural")
    settings = radio_settings(P)
    style.hero("🛰️", t("link.title"), t("link.subtitle"))

    c1, c2 = st.columns(2)
    with c1:
        _end_inputs("tx")
    with c2:
        _end_inputs("rx")

    tx, tx_problem = check_point(st.session_state[f"{P}_tx_lat"], st.session_state[f"{P}_tx_lon"])
    rx, rx_problem = check_point(st.session_state[f"{P}_rx_lat"], st.session_state[f"{P}_rx_lon"])
    if tx_problem or rx_problem:
        st.error(f"{t('planner.mode.tx' if tx_problem else 'planner.mode.rx')}: "
                 f"{t(tx_problem or rx_problem)}")  # fmt: skip
        return
    if tx == rx:
        st.error(t("planner.msg.too_close"))
        return
    try:
        with st.spinner(t("web.computing")):
            path, budget, profile = link_analysis(tx, rx, settings)
    except (TerrainError, ValueError) as exc:
        st.error(str(exc))
        return
    render_link_results(tx, rx, settings, path, budget, profile, P, show_map=True)
