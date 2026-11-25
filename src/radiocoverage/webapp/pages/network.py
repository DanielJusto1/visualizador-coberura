"""Network page: an editable table of sites, click-to-add on the map and coverage."""

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from radiocoverage.coverage import KM_PER_DEG_LAT
from radiocoverage.rendering import class_ranges_dbm, server_colour
from radiocoverage.terrain import TerrainError
from radiocoverage.webapp import style
from radiocoverage.webapp.compute import coverage_analysis, coverage_files_cached, relief_url
from radiocoverage.webapp.mapview import base_map, network_layers
from radiocoverage.webapp.placement import check_point
from radiocoverage.webapp.presets import BAND_KEYS, EXAMPLE_NETWORKS, SPAIN_VIEW
from radiocoverage.webapp.sites_table import (
    COLUMNS,
    apply_editor_changes,
    example_rows,
    new_row,
    rows_to_sites,
)
from radiocoverage.webapp.texts import current_language, labels, t
from radiocoverage.webapp.widgets import band_label, init_defaults, radio_settings

P = "nw"
MAP_HEIGHT = 520


def _editor_key() -> str:
    return f"{P}_editor_{st.session_state.get(f'{P}_version', 0)}"


def _base_rows() -> list[dict]:
    return st.session_state.setdefault(f"{P}_base", [])


def _replace_rows(rows: list[dict]) -> None:
    """Give the table new content (starts a fresh editor so old edits are not replayed)."""
    st.session_state[f"{P}_base"] = rows
    st.session_state[f"{P}_version"] = st.session_state.get(f"{P}_version", 0) + 1


def _default_row(settings, number: int) -> dict:
    return {
        "name": t("network.site_name", number=number), "lat": None, "lon": None,
        "band": settings.band_key, "power": settings.tx_power_dbm,
        "gain": settings.tx_gain_dbi, "height": settings.tx_height_m, "azimuth": None,
        "beamwidth": 65.0,
    }  # fmt: skip


def _current_rows(settings) -> list[dict]:
    changes = st.session_state.get(_editor_key())
    return apply_editor_changes(
        _base_rows(), changes, _default_row(settings, len(_base_rows()) + 1)
    )


def _on_load_example() -> None:
    key = st.session_state.get(f"{P}_example")
    if key not in EXAMPLE_NETWORKS:
        return
    network = EXAMPLE_NETWORKS[key]
    _replace_rows(example_rows(network))
    st.session_state[f"{P}_band"] = network.band_key
    from radiocoverage.webapp.widgets import apply_band_profile

    apply_band_profile(P)
    st.session_state[f"{P}_env"] = network.environment
    st.session_state[f"{P}_terrain"] = network.terrain
    st.session_state[f"{P}_radius"] = network.radius_km
    st.session_state[f"{P}_res"] = network.resolution_m
    st.session_state.pop(f"{P}_result", None)
    lats = [site[1] for site in network.sites]
    lons = [site[2] for site in network.sites]
    zoom = 15 if network.radius_km <= 2 else 11
    st.session_state[f"{P}_view"] = ((sum(lats) / len(lats), sum(lons) / len(lons)), zoom)
    st.session_state[f"{P}_flash"] = "network.msg.loaded"


def _on_clear() -> None:
    _replace_rows([])
    st.session_state.pop(f"{P}_result", None)


def _area_controls() -> None:
    st.session_state.setdefault(f"{P}_radius", 3.0)
    st.session_state.setdefault(f"{P}_res", 100)
    with st.sidebar.expander(t("web.params.area"), icon=":material/grid_on:", expanded=True):
        st.slider(t("web.radius"), 0.5, 30.0, step=0.5, key=f"{P}_radius",
                  help=t("help.radius"))  # fmt: skip
        st.select_slider(t("web.resolution"), [25, 50, 100, 150, 200, 400], key=f"{P}_res",
                         help=t("help.resolution"))  # fmt: skip


def _signature(rows, settings) -> tuple:
    frozen = tuple(tuple((k, row.get(k)) for k in COLUMNS) for row in rows)
    return (frozen, settings, st.session_state[f"{P}_radius"], st.session_state[f"{P}_res"])


def _table(rows: list[dict]) -> None:
    frame = pd.DataFrame(_base_rows(), columns=list(COLUMNS))
    st.data_editor(
        frame,
        key=_editor_key(),
        num_rows="dynamic",
        hide_index=True,
        width="stretch",
        column_config={
            "name": st.column_config.TextColumn(t("network.col.name"), required=True),
            "lat": st.column_config.NumberColumn("Lat", format="%.5f", min_value=27.0,
                                                 max_value=44.0),
            "lon": st.column_config.NumberColumn("Lon", format="%.5f", min_value=-19.0,
                                                 max_value=5.0),
            "band": st.column_config.SelectboxColumn(
                t("q.band"), options=BAND_KEYS, required=True, format_func=band_label,
                width="medium",
            ),
            "power": st.column_config.NumberColumn(t("network.col.power"), format="%.1f"),
            "gain": st.column_config.NumberColumn(t("network.col.gain"), format="%.1f"),
            "height": st.column_config.NumberColumn(t("network.col.height"), format="%.0f",
                                                    min_value=1.0),
            "azimuth": st.column_config.NumberColumn(
                t("network.col.azimuth"), format="%.0f", min_value=0.0, max_value=360.0,
                help=t("help.azimuth_column"),
            ),
            "beamwidth": st.column_config.NumberColumn(t("network.col.beamwidth"),
                                                       format="%.0f", min_value=1.0,
                                                       max_value=360.0),
        },
    )  # fmt: skip
    st.caption(t("network.table_caption"))


def _results(settings, rows, lang: str) -> None:
    sites, errors = rows_to_sites(rows, settings.tx_loss_db)
    for error in errors:
        st.warning(t("network.row_problem", row=error.row, problem=t(error.key)))
    compute = st.button(
        t("network.compute"), type="primary", icon=":material/radar:",
        width="stretch", disabled=not sites,
    )  # fmt: skip
    if compute:
        try:
            with st.spinner(t("web.computing")):
                result = coverage_analysis(
                    tuple(sites), settings.receiver(), st.session_state[f"{P}_radius"],
                    st.session_state[f"{P}_res"], settings.model, settings.environment,
                    settings.terrain,
                )  # fmt: skip
        except (ValueError, TerrainError) as exc:
            st.error(str(exc))
        else:
            st.session_state[f"{P}_result"] = (_signature(rows, settings), result)
            st.rerun()

    stored = st.session_state.get(f"{P}_result")
    if stored is None:
        st.info(t("network.no_result"), icon=":material/info:")
        return
    signature, result = stored
    if signature != _signature(rows, settings):
        st.warning(t("network.stale"), icon=":material/update:")

    c1, c2, c3 = st.columns(3)
    c1.metric(t("q.covered_area"), f"{result.covered_area_km2:.1f} km²", border=True)
    c2.metric(t("web.covered_fraction"), f"{result.covered_fraction:.0%}", border=True)
    c3.metric(t("network.sites"), len(result.sites), border=True)
    st.caption(
        t("network.result_caption", model=", ".join(sorted({result.model_label(s)
                                                             for s in result.sites})),
          area=result.area_km2, threshold=result.receiver.threshold_dbm)
    )  # fmt: skip
    served = result.served_area_km2()
    table = pd.DataFrame(
        {
            t("q.site"): [site.name for site in result.sites],
            t("q.band"): [site.band_name for site in result.sites],
            t("network.col.served"): served,
            t("network.col.share"): [area / max(result.covered_area_km2, 1e-9) * 100
                                     for area in served],
        }
    )  # fmt: skip
    st.dataframe(
        table, hide_index=True, width="stretch",
        column_config={
            t("network.col.served"): st.column_config.NumberColumn(format="%.2f km²"),
            t("network.col.share"): st.column_config.ProgressColumn(
                format="%.0f %%", min_value=0, max_value=100),
        },
    )  # fmt: skip
    files = coverage_files_cached(signature, result, lang)
    d1, d2, d3 = st.columns(3)
    d1.download_button("KMZ (Google Earth)", files["kmz"], "coverage.kmz",
                       "application/vnd.google-earth.kmz", icon=":material/public:",
                       width="stretch")  # fmt: skip
    d2.download_button(t("web.download.map"), files["html"], "coverage.html", "text/html",
                       icon=":material/map:", width="stretch")  # fmt: skip
    d3.download_button(t("web.download.image"), files["png"], "coverage.png", "image/png",
                       icon=":material/image:", width="stretch")  # fmt: skip


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
    message = st.session_state.pop(f"{P}_flash", None)
    if message:
        st.toast(t(message), icon="⚠️" if message.startswith("planner.msg") else "✅")
    settings = radio_settings(P)
    _area_controls()
    rows = _current_rows(settings)

    style.hero("🗼", t("network.title"), t("network.subtitle"))

    c1, c2, c3, c4 = st.columns([2.4, 1.2, 1.6, 1.2], vertical_alignment="bottom")
    c1.selectbox(t("network.example"), list(EXAMPLE_NETWORKS), key=f"{P}_example",
                 format_func=labels("network.example."))  # fmt: skip
    c2.button(t("network.load"), on_click=_on_load_example, icon=":material/download:",
              width="stretch")  # fmt: skip
    c3.toggle(t("network.click_to_add"), value=True, key=f"{P}_click_add",
              help=t("help.click_to_add"))  # fmt: skip
    c4.button(t("network.clear"), on_click=_on_clear, icon=":material/delete:",
              disabled=not rows, width="stretch")  # fmt: skip

    stored = st.session_state.get(f"{P}_result")
    coverage = stored[1] if stored else None
    layer = "signal"
    if coverage is not None and len(coverage.sites) > 1:
        layer = st.segmented_control(
            t("network.layer"), ["signal", "server"], default="signal", key=f"{P}_layer",
            format_func=labels("map.layer."),
        ) or "signal"  # fmt: skip

    sites_for_map, _ = rows_to_sites(rows, settings.tx_loss_db)
    if coverage is not None:
        (south, west), (north, east) = coverage.grid.bounds
        arrow_km = max(0.15, 0.08 * min(north - south, east - west) * KM_PER_DEG_LAT)
    else:
        arrow_km = 0.3 * st.session_state[f"{P}_radius"]
    center, zoom = st.session_state.get(f"{P}_view", SPAIN_VIEW)
    output = st_folium(
        base_map(lang),
        key=f"{P}_map_{lang}",
        height=MAP_HEIGHT,
        use_container_width=True,
        returned_objects=["last_clicked"],
        center=center,
        zoom=zoom,
        feature_group_to_add=network_layers(
            [(s.name, s.location, s.azimuth_deg) for s in sites_for_map], lang,
            coverage=coverage, show_server=layer == "server", arrow_km=arrow_km,
            relief=_relief(coverage),
        ),
    )  # fmt: skip
    click = (output or {}).get("last_clicked")
    if click:
        signature = (round(click["lat"], 7), round(click["lng"], 7))
        if signature != st.session_state.get(f"{P}_last_click"):
            st.session_state[f"{P}_last_click"] = signature
            if st.session_state.get(f"{P}_click_add", True):
                _, problem = check_point(click["lat"], click["lng"])
                if problem is None:
                    row = new_row(
                        t("network.site_name", number=len(rows) + 1), click["lat"],
                        click["lng"], settings.band_key, settings.tx_power_dbm,
                        settings.tx_gain_dbi, settings.tx_height_m,
                    )  # fmt: skip
                    _replace_rows([*rows, row])
                    st.session_state[f"{P}_flash"] = "network.msg.added"
                else:
                    st.session_state[f"{P}_flash"] = problem
                st.rerun()
    if coverage is not None:
        if layer == "server":
            style.legend([(server_colour(i), s.name) for i, s in enumerate(coverage.sites)])
        else:
            style.legend(
                [(c.colour, f"{t(f'class.{c.label.lower()}')} ({text})")
                 for c, text in class_ranges_dbm(coverage.receiver.sensitivity_dbm, t("range.to"))]
            )  # fmt: skip
    else:
        st.caption(t("network.map_hint"))

    left, right = st.columns([3, 2], gap="medium")
    with left:
        st.markdown(f"##### {t('network.table_title', count=len(rows))}")
        _table(rows)
    with right:
        st.markdown(f"##### {t('network.results_title')}")
        _results(settings, rows, lang)
