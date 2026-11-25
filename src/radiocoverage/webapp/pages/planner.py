"""Map planner: place the transmitter and the receiver by clicking on the map."""

import math

import streamlit as st
from streamlit_folium import st_folium

from radiocoverage.geo import bearing_deg
from radiocoverage.rendering import class_ranges_dbm
from radiocoverage.terrain import TerrainError
from radiocoverage.webapp import style
from radiocoverage.webapp.compute import coverage_analysis, link_analysis, relief_url
from radiocoverage.webapp.mapview import base_map, planner_layers
from radiocoverage.webapp.placement import Placement, clear, place, set_point, swap
from radiocoverage.webapp.presets import PLACES, SPAIN_VIEW
from radiocoverage.webapp.results import render_link_results
from radiocoverage.webapp.texts import current_language, labels, t
from radiocoverage.webapp.widgets import init_defaults, radio_settings

P = "pl"
MAP_HEIGHT = 640


# --- State helpers -------------------------------------------------------------------


def _placement() -> Placement:
    return st.session_state.setdefault(f"{P}_placement", Placement())


def _set_placement(placement: Placement) -> None:
    st.session_state[f"{P}_placement"] = placement


def _move_view(lat: float, lon: float, zoom: int) -> None:
    # A tiny offset that changes every time forces the map to move even when the
    # same place is chosen twice (st_folium only reacts to a *different* centre).
    nonce = st.session_state.get(f"{P}_view_nonce", 0) + 1
    st.session_state[f"{P}_view_nonce"] = nonce
    st.session_state[f"{P}_view"] = ((lat + nonce * 1e-9, lon), zoom)


def _zoom_for(distance_km: float, lat: float) -> int:
    metres_per_pixel = distance_km * 1000 * 1.8 / 600  # leave room around the link
    zoom = math.log2(156543.03 * math.cos(math.radians(lat)) / max(metres_per_pixel, 1e-3))
    return int(min(max(zoom, 5), 16))


# --- Callbacks (run before the page is drawn, so they may change any widget) ----------


def _on_mode() -> None:
    mode = st.session_state.get(f"{P}_mode")
    if mode in ("tx", "rx"):
        _set_placement(Placement(_placement().tx, _placement().rx, mode))


def _on_swap() -> None:
    _set_placement(swap(_placement()))
    st.session_state[f"{P}_flash"] = "planner.msg.swapped"


def _on_clear() -> None:
    _set_placement(clear())
    st.session_state.pop(f"{P}_coverage", None)
    st.session_state[f"{P}_flash"] = "planner.msg.cleared"


def _on_goto() -> None:
    name = st.session_state.get(f"{P}_goto")
    if name in PLACES:
        lat, lon, zoom = PLACES[name]
        _move_view(lat, lon, zoom)
    st.session_state[f"{P}_goto"] = None


def _on_fit() -> None:
    placement = _placement()
    if placement.complete:
        lat = (placement.tx.lat + placement.rx.lat) / 2
        lon = (placement.tx.lon + placement.rx.lon) / 2
        from radiocoverage.geo import distance_km

        _move_view(lat, lon, _zoom_for(distance_km(placement.tx, placement.rx), lat))


def _on_coordinates(end: str) -> None:
    lat = st.session_state.get(f"{P}_{end}_lat")
    lon = st.session_state.get(f"{P}_{end}_lon")
    if lat is None or lon is None:
        return
    placement, error = set_point(_placement(), end, lat, lon)
    if error:
        st.session_state[f"{P}_flash"] = error
    else:
        _set_placement(placement)


def _show_flash() -> None:
    message = st.session_state.pop(f"{P}_flash", None)
    if not message:
        return
    good = message.endswith(("placed", "swapped", "cleared"))
    st.toast(t(message), icon="✅" if good else "⚠️")


# --- Page sections -------------------------------------------------------------------


def _toolbar(placement: Placement) -> None:
    st.session_state[f"{P}_mode"] = placement.mode
    c1, c2, c3, c4, c5 = st.columns([2.3, 2.6, 1, 1, 1], vertical_alignment="bottom")
    c1.segmented_control(
        t("planner.place"), ["tx", "rx"], key=f"{P}_mode", on_change=_on_mode,
        format_func=labels("planner.mode."), help=t("help.planner_mode"),
    )  # fmt: skip
    c2.selectbox(
        t("planner.goto"), list(PLACES), index=None, key=f"{P}_goto", on_change=_on_goto,
        placeholder=t("planner.goto_placeholder"),
    )  # fmt: skip
    c3.button(
        t("planner.fit"), icon=":material/fit_screen:", on_click=_on_fit,
        disabled=not placement.complete, width="stretch", help=t("help.fit"),
    )  # fmt: skip
    c4.button(
        t("planner.swap"), icon=":material/swap_horiz:", on_click=_on_swap,
        disabled=not placement.complete, width="stretch", help=t("help.swap"),
    )  # fmt: skip
    c5.button(
        t("planner.clear"), icon=":material/delete:", on_click=_on_clear,
        disabled=placement.empty, width="stretch",
    )  # fmt: skip


def _coverage_signature(placement: Placement, settings, radius, resolution, sector) -> tuple:
    return (placement.tx, placement.rx if sector else None, settings, radius, resolution, sector)


def _current_coverage(placement: Placement, settings):
    stored = st.session_state.get(f"{P}_coverage")
    if not stored or placement.tx is None:
        return None
    signature, result = stored
    radius = st.session_state.get(f"{P}_cov_radius", 5.0)
    resolution = st.session_state.get(f"{P}_cov_res", 100)
    sector = st.session_state.get(f"{P}_cov_sector", False) and placement.rx is not None
    if signature != _coverage_signature(placement, settings, radius, resolution, sector):
        return None
    return result


def _coverage_section(placement: Placement, settings) -> None:
    with st.expander(t("planner.coverage.title"), icon=":material/radar:"):
        st.caption(t("planner.coverage.caption"))
        c1, c2 = st.columns(2)
        c1.slider(t("web.radius"), 0.5, 30.0, 5.0, 0.5, key=f"{P}_cov_radius")
        c2.select_slider(t("web.resolution"), [25, 50, 100, 200, 400], 100, key=f"{P}_cov_res",
                         help=t("help.resolution"))  # fmt: skip
        st.toggle(
            t("planner.coverage.sector"), key=f"{P}_cov_sector",
            disabled=placement.rx is None, help=t("help.sector_to_rx"),
        )  # fmt: skip
        radius = st.session_state[f"{P}_cov_radius"]
        resolution = st.session_state[f"{P}_cov_res"]
        sector = st.session_state[f"{P}_cov_sector"] and placement.rx is not None
        if st.button(t("planner.coverage.compute"), type="primary", icon=":material/radar:",
                     width="stretch"):  # fmt: skip
            azimuth = bearing_deg(placement.tx, placement.rx) if sector else None
            site = settings.site(t("q.transmitter"), placement.tx, azimuth)
            try:
                with st.spinner(t("web.computing")):
                    result = coverage_analysis(
                        (site,), settings.receiver(), radius, resolution, settings.model,
                        settings.environment, settings.terrain,
                    )  # fmt: skip
            except (ValueError, TerrainError) as exc:
                st.error(str(exc))
            else:
                signature = _coverage_signature(placement, settings, radius, resolution, sector)
                st.session_state[f"{P}_coverage"] = (signature, result)
                st.rerun()
        result = _current_coverage(placement, settings)
        if result is not None:
            c1, c2 = st.columns(2)
            c1.metric(t("q.covered_area"), f"{result.covered_area_km2:.1f} km²", border=True)
            c2.metric(t("web.covered_fraction"), f"{result.covered_fraction:.0%}", border=True)
            if st.button(t("planner.coverage.remove"), icon=":material/layers_clear:"):
                st.session_state.pop(f"{P}_coverage", None)
                st.rerun()


def _coordinates_section(placement: Placement) -> None:
    for end in ("tx", "rx"):
        point = getattr(placement, end)
        st.session_state[f"{P}_{end}_lat"] = point.lat if point else None
        st.session_state[f"{P}_{end}_lon"] = point.lon if point else None
    with st.expander(t("planner.coords.title"), icon=":material/my_location:"):
        st.caption(t("planner.coords.caption"))
        for end in ("tx", "rx"):
            c1, c2 = st.columns(2)
            c1.number_input(
                f"{t(f'planner.mode.{end}')} · lat", -90.0, 90.0, format="%.6f", step=0.0001,
                key=f"{P}_{end}_lat", on_change=_on_coordinates, args=(end,),
            )  # fmt: skip
            c2.number_input(
                f"{t(f'planner.mode.{end}')} · lon", -180.0, 180.0, format="%.6f", step=0.0001,
                key=f"{P}_{end}_lon", on_change=_on_coordinates, args=(end,),
            )  # fmt: skip


def _instructions(placement: Placement) -> None:
    tx_state = "done" if placement.tx else "active"
    rx_state = "done" if placement.rx else ("active" if placement.tx else "todo")
    style.steps(
        [
            (tx_state, t("planner.step1.title"), t("planner.step1.text")),
            (rx_state, t("planner.step2.title"), t("planner.step2.text")),
            ("todo", t("planner.step3.title"), t("planner.step3.text")),
        ]
    )


def _relief(result):
    if result is None or not result.terrain:
        return None
    try:
        return relief_url(result.grid.bounds, result.grid.shape, result)
    except TerrainError:
        return None


def render() -> None:
    lang = current_language()
    init_defaults(P, "b20", env="rural")
    _show_flash()
    settings = radio_settings(P)
    placement = _placement()

    style.hero("📡", t("planner.title"), t("planner.subtitle"))
    _toolbar(placement)

    link = None
    link_error = None
    if placement.complete:
        try:
            with st.spinner(t("web.computing")):
                link = link_analysis(placement.tx, placement.rx, settings)
        except TerrainError as exc:
            link_error = str(exc)
        except ValueError as exc:
            link_error = str(exc)
    coverage = _current_coverage(placement, settings)

    left, right = st.columns([3, 2], gap="medium")
    with left:
        center, zoom = st.session_state.get(f"{P}_view", SPAIN_VIEW)
        layers = planner_layers(
            placement.tx, placement.rx, lang,
            link=(link[0], link[1]) if link else None, coverage=coverage,
            relief=_relief(coverage),
        )  # fmt: skip
        output = st_folium(
            base_map(lang),
            key=f"{P}_map_{lang}",
            height=MAP_HEIGHT,
            use_container_width=True,
            returned_objects=["last_clicked"],
            center=center,
            zoom=zoom,
            feature_group_to_add=layers,
        )
        click = (output or {}).get("last_clicked")
        if click:
            signature = (round(click["lat"], 7), round(click["lng"], 7))
            if signature != st.session_state.get(f"{P}_last_click"):
                st.session_state[f"{P}_last_click"] = signature
                new, message = place(placement, click["lat"], click["lng"])
                _set_placement(new)
                st.session_state[f"{P}_flash"] = message
                st.rerun()
        target = t(f"planner.mode.{placement.mode}").lower()
        st.caption(t("planner.map_hint", target=target))
        if coverage is not None:
            style.legend(
                [(c.colour, f"{t(f'class.{c.label.lower()}')} ({text})")
                 for c, text in class_ranges_dbm(coverage.receiver.sensitivity_dbm, t("range.to"))]
            )  # fmt: skip

    with right:
        if link_error:
            st.error(link_error)
        if link is not None:
            path, budget, profile = link
            render_link_results(placement.tx, placement.rx, settings, path, budget, profile, P)
        else:
            _instructions(placement)
        if placement.tx is not None:
            _coverage_section(placement, settings)
        if not placement.empty:
            _coordinates_section(placement)
