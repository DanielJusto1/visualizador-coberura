"""Shared look and feel of the interactive maps: base layers, controls, panels, relief."""

from html import escape

import folium
import numpy as np
from folium.plugins import Fullscreen, MousePosition

from radiocoverage.i18n import tr

FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"

_IGN_WMTS = (
    "https://www.ign.es/wmts/{service}?layer={layer}&style=default"
    "&tilematrixset=GoogleMapsCompatible&Service=WMTS&Request=GetTile&Version=1.0.0"
    "&Format=image/{fmt}&TileMatrix={{z}}&TileCol={{x}}&TileRow={{y}}"
)
_IGN_ATTRIBUTION = '&copy; <a href="https://www.ign.es">Instituto Geográfico Nacional de España</a>'


def add_base_layers(m: folium.Map, lang: str = "en") -> None:
    """Light grey base map (default), OpenStreetMap, topographic map and the IGN maps.

    All of them are free to use without an API key.
    """
    folium.TileLayer(
        "Esri.WorldGrayCanvas", name=tr("map.layer.light", lang), max_native_zoom=16, max_zoom=19
    ).add_to(m)
    folium.TileLayer("OpenStreetMap", name="OpenStreetMap", show=False).add_to(m)
    folium.TileLayer("OpenTopoMap", name=tr("map.layer.topo", lang), show=False).add_to(m)
    folium.TileLayer(
        tiles=_IGN_WMTS.format(service="ign-base", layer="IGNBaseTodo", fmt="jpeg"),
        attr=_IGN_ATTRIBUTION,
        name=tr("map.layer.ign", lang),
        max_zoom=20,
        show=False,
    ).add_to(m)
    folium.TileLayer(
        tiles=_IGN_WMTS.format(service="pnoa-ma", layer="OI.OrthoimageCoverage", fmt="jpeg"),
        attr=_IGN_ATTRIBUTION,
        name=tr("map.layer.pnoa", lang),
        max_zoom=20,
        show=False,
    ).add_to(m)


def add_controls(m: folium.Map, lang: str = "en") -> None:
    """Full-screen button and the coordinates under the mouse pointer."""
    Fullscreen(
        position="topright",
        title=tr("map.fullscreen", lang),
        title_cancel=tr("map.fullscreen_exit", lang),
    ).add_to(m)
    MousePosition(
        position="bottomleft",
        separator=" · ",
        num_digits=5,
        prefix="Lat · Lon:",
        empty_string="Lat · Lon",
        lat_first=True,
    ).add_to(m)


def html_table(rows: list[tuple[str, str]]) -> str:
    cells = "".join(
        f"<tr><td style='padding:2px 10px 2px 0;color:#5b6475;white-space:nowrap'>{escape(k)}</td>"
        f"<td style='padding:2px 0;text-align:right;color:#1b2430'><b>{escape(v)}</b></td></tr>"
        for k, v in rows
    )
    return f"<table style='border-collapse:collapse;font-size:12px'>{cells}</table>"


def panel(content: str, position: str = "top:12px;left:56px", max_width: int = 360) -> str:
    """A floating white card used for legends and summaries."""
    return (
        f"<div style='position:fixed;{position};z-index:1000;background:rgba(255,255,255,.96);"
        "padding:12px 14px;border-radius:10px;box-shadow:0 2px 12px rgba(16,24,40,.18);"
        f"font-family:{FONT};font-size:12px;color:#1b2430;max-width:{max_width}px'>"
        f"{content}</div>"
    )


def badge(text: str, colour: str) -> str:
    return (
        f"<span style='display:inline-block;padding:2px 10px;border-radius:999px;"
        f"background:{colour};color:white;font-weight:600;font-size:12px;"
        f"letter-spacing:.02em'>{escape(text)}</span>"
    )


def swatch(colour: str) -> str:
    return (
        "<span style='display:inline-block;width:12px;height:12px;margin-right:6px;"
        f"vertical-align:middle;background:{colour};opacity:.85;border-radius:3px;"
        "border:1px solid rgba(0,0,0,.25)'></span>"
    )


def relief_rgba(elevation: np.ndarray, dx_m: float, dy_m: float) -> np.ndarray:
    """Semi-transparent grey shaded relief (RGBA uint8) to lay under coverage overlays."""
    from radiocoverage.coverage_plot import hillshade

    shade = hillshade(elevation, dx_m, dy_m)
    grey = (shade * 255).astype(np.uint8)
    alpha = np.full(grey.shape, 150, dtype=np.uint8)
    return np.dstack([grey, grey, grey, alpha])
