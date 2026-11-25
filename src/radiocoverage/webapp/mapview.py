"""Clickable maps for the web interface (rendered with streamlit-folium)."""

import folium

from radiocoverage.coverage import CoverageResult
from radiocoverage.coverage_map import add_coverage_layers, relief_layer
from radiocoverage.geo import GeoPoint
from radiocoverage.i18n import tr
from radiocoverage.link_budget import LinkBudgetResult
from radiocoverage.link_map import TX_ICON, add_link_layers
from radiocoverage.mapstyle import add_base_layers, add_controls
from radiocoverage.path import LinkPath
from radiocoverage.webapp.presets import SPAIN_VIEW


def base_map(lang: str) -> folium.Map:
    """The static part of a clickable map.

    It is always built with the same view, so streamlit-folium keeps the map (and the
    user's zoom) between interactions; markers and overlays go in a feature group that
    is updated on its own, and the view is moved with st_folium's center/zoom.
    """
    (lat, lon), zoom = SPAIN_VIEW
    m = folium.Map(location=(lat, lon), zoom_start=zoom, tiles=None, control_scale=True)
    add_base_layers(m, lang)
    add_controls(m, lang)
    folium.LayerControl(collapsed=True).add_to(m)
    return m


def point_marker(point: GeoPoint, kind: str, lang: str) -> folium.Marker:
    if kind == "tx":
        return folium.Marker(
            (point.lat, point.lon), tooltip=tr("map.tx", lang), icon=folium.Icon(**TX_ICON)
        )
    return folium.Marker(
        (point.lat, point.lon),
        tooltip=tr("map.rx", lang),
        icon=folium.Icon(color="cadetblue", icon="mobile-screen", prefix="fa"),
    )


def planner_layers(
    tx: GeoPoint | None,
    rx: GeoPoint | None,
    lang: str,
    link: tuple[LinkPath, LinkBudgetResult] | None = None,
    coverage: CoverageResult | None = None,
    relief: str | None = None,
) -> folium.FeatureGroup:
    group = folium.FeatureGroup(name=tr("map.layer.link", lang))
    if coverage is not None:
        if relief is not None:
            relief_layer(coverage, lang=lang, data_url=relief).add_to(group)
        add_coverage_layers(group, coverage, lang, site_markers=False)
    if link is not None:
        add_link_layers(group, link[0], link[1], lang)
        return group
    for point, kind in ((tx, "tx"), (rx, "rx")):
        if point is not None:
            point_marker(point, kind, lang).add_to(group)
    return group


def network_layers(
    sites: list[tuple[str, GeoPoint, float | None]],
    lang: str,
    coverage: CoverageResult | None = None,
    show_server: bool = False,
    arrow_km: float = 0.6,
    relief: str | None = None,
) -> folium.FeatureGroup:
    """Coverage overlays (if any) and a marker per site of the table."""
    from radiocoverage.geo import destination_point
    from radiocoverage.rendering import server_colour

    group = folium.FeatureGroup(name=tr("map.layer.sites", lang))
    if coverage is not None:
        if relief is not None:
            relief_layer(coverage, lang=lang, data_url=relief).add_to(group)
        add_coverage_layers(group, coverage, lang, show_server=show_server, site_markers=False)
    for index, (name, location, azimuth) in enumerate(sites):
        folium.Marker(
            (location.lat, location.lon), tooltip=name, icon=folium.Icon(**TX_ICON)
        ).add_to(group)
        if azimuth is not None:
            tip = destination_point(location, azimuth, arrow_km)
            folium.PolyLine(
                [(location.lat, location.lon), (tip.lat, tip.lon)],
                color=server_colour(index),
                weight=4,
                tooltip=tr("map.azimuth_tooltip", lang, name=name, azimuth=azimuth),
            ).add_to(group)
    return group
