"""Interactive HTML map of a point-to-point link (Leaflet via folium)."""

from html import escape
from pathlib import Path

import folium

from radiocoverage.bands import Band
from radiocoverage.link_budget import LinkBudgetResult
from radiocoverage.path import LinkPath

OK_COLOUR = "#1a9850"
FAIL_COLOUR = "#d73027"
FRESNEL_COLOUR = "#4575b4"

_IGN_WMTS = (
    "https://www.ign.es/wmts/{service}?layer={layer}&style=default"
    "&tilematrixset=GoogleMapsCompatible&Service=WMTS&Request=GetTile&Version=1.0.0"
    "&Format=image/{fmt}&TileMatrix={{z}}&TileCol={{x}}&TileRow={{y}}"
)
_IGN_ATTRIBUTION = '&copy; <a href="https://www.ign.es">Instituto Geográfico Nacional de España</a>'


def _add_base_layers(m: folium.Map) -> None:
    folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(m)
    folium.TileLayer(
        tiles=_IGN_WMTS.format(service="ign-base", layer="IGNBaseTodo", fmt="jpeg"),
        attr=_IGN_ATTRIBUTION,
        name="IGN base map",
        max_zoom=20,
        show=False,
    ).add_to(m)
    folium.TileLayer(
        tiles=_IGN_WMTS.format(service="pnoa-ma", layer="OI.OrthoimageCoverage", fmt="jpeg"),
        attr=_IGN_ATTRIBUTION,
        name="IGN aerial imagery (PNOA)",
        max_zoom=20,
        show=False,
    ).add_to(m)


def _summary_rows(path: LinkPath, result: LinkBudgetResult) -> list[tuple[str, str]]:
    p = result.parameters
    return [
        ("Distance", f"{path.distance_km:.2f} km"),
        ("Azimuth Tx→Rx", f"{path.bearing_deg:.1f}°"),
        ("EIRP", f"{result.eirp_dbm:.1f} dBm"),
        ("Free-space loss", f"{result.path_loss_db:.1f} dB"),
        ("Received power", f"{result.rx_power_dbm:.1f} dBm"),
        ("Sensitivity", f"{p.rx_sensitivity_dbm:.1f} dBm"),
        ("Margin", f"{result.margin_db:.1f} dB (required {p.required_margin_db:.1f})"),
        ("1st Fresnel radius", f"{path.fresnel_radius_midpoint_m:.1f} m at mid-path"),
        ("Earth bulge", f"{path.earth_bulge_midpoint_m():.1f} m at mid-path (k=4/3)"),
    ]


def _html_table(rows: list[tuple[str, str]]) -> str:
    cells = "".join(
        f"<tr><td style='padding:1px 8px 1px 0;color:#555'>{escape(k)}</td>"
        f"<td style='padding:1px 0;text-align:right'><b>{escape(v)}</b></td></tr>"
        for k, v in rows
    )
    return f"<table style='border-collapse:collapse;font-size:12px'>{cells}</table>"


def build_link_map(
    path: LinkPath, result: LinkBudgetResult, band: Band | None = None
) -> folium.Map:
    """Create a map with both ends of the link, the radio path and its Fresnel zone."""
    viable = result.is_viable
    colour = OK_COLOUR if viable else FAIL_COLOUR
    verdict = "LINK OK" if viable else "LINK FAILS"
    if band is not None:
        title = f"{band.technology} {band.name} · {band.centre_mhz:g} MHz"
    else:
        title = f"{result.parameters.frequency_mhz:g} MHz"

    m = folium.Map(location=(path.midpoint.lat, path.midpoint.lon), tiles=None, control_scale=True)
    _add_base_layers(m)

    p = result.parameters
    tx_popup = _html_table(
        [
            ("Transmitter", str(path.tx)),
            ("Tx power", f"{p.tx_power_dbm:.1f} dBm"),
            ("Antenna gain", f"{p.tx_antenna_gain_dbi:.1f} dBi"),
            ("EIRP", f"{result.eirp_dbm:.1f} dBm"),
            ("Point antenna to", f"{path.bearing_deg:.1f}°"),
        ]
    )
    rx_popup = _html_table(
        [
            ("Receiver", str(path.rx)),
            ("Received power", f"{result.rx_power_dbm:.1f} dBm"),
            ("Margin", f"{result.margin_db:.1f} dB"),
            ("Tx is at azimuth", f"{path.reverse_bearing_deg:.1f}°"),
        ]
    )
    folium.Marker(
        (path.tx.lat, path.tx.lon),
        tooltip="Transmitter (base station)",
        popup=folium.Popup(tx_popup, max_width=320),
        icon=folium.Icon(color="darkblue", icon="tower-cell", prefix="fa"),
    ).add_to(m)
    folium.Marker(
        (path.rx.lat, path.rx.lon),
        tooltip="Receiver (user equipment)",
        popup=folium.Popup(rx_popup, max_width=320),
        icon=folium.Icon(color="green" if viable else "red", icon="mobile-screen", prefix="fa"),
    ).add_to(m)

    fresnel = folium.FeatureGroup(name="First Fresnel zone (top view)")
    folium.Polygon(
        [(pt.lat, pt.lon) for pt in path.fresnel_outline()],
        color=FRESNEL_COLOUR,
        weight=1,
        fill=True,
        fill_opacity=0.2,
        tooltip=f"First Fresnel zone: {path.fresnel_radius_midpoint_m:.1f} m radius at mid-path",
    ).add_to(fresnel)
    fresnel.add_to(m)

    folium.PolyLine(
        [(path.tx.lat, path.tx.lon), (path.rx.lat, path.rx.lon)],
        color=colour,
        weight=4,
        tooltip=f"{path.distance_km:.2f} km · margin {result.margin_db:.1f} dB",
    ).add_to(m)

    panel = (
        "<div style='position:fixed;top:12px;left:56px;z-index:1000;background:white;"
        "padding:10px 12px;border-radius:6px;box-shadow:0 1px 5px rgba(0,0,0,.4);"
        "font-family:Arial,sans-serif;max-width:340px'>"
        f"<div style='font-size:14px;font-weight:bold;margin-bottom:2px'>{escape(title)}</div>"
        f"<div style='color:{colour};font-weight:bold;margin-bottom:6px'>{verdict}</div>"
        f"{_html_table(_summary_rows(path, result))}"
        "<div style='font-size:10px;color:#777;margin-top:6px'>"
        "Free-space model: best case, no terrain or clutter.</div></div>"
    )
    m.get_root().html.add_child(folium.Element(panel))

    folium.LayerControl(collapsed=True).add_to(m)
    m.fit_bounds(
        [
            (min(path.tx.lat, path.rx.lat), min(path.tx.lon, path.rx.lon)),
            (max(path.tx.lat, path.rx.lat), max(path.tx.lon, path.rx.lon)),
        ],
        padding=(60, 60),
    )
    return m


def save_link_map(
    path: LinkPath, result: LinkBudgetResult, output: Path, band: Band | None = None
) -> Path:
    """Build the map and write it as a standalone HTML file."""
    output = Path(output)
    if output.suffix.lower() not in {".html", ".htm"}:
        raise ValueError(f"Map file must end in .html, got '{output.name}'")
    output.parent.mkdir(parents=True, exist_ok=True)
    build_link_map(path, result, band).save(str(output))
    return output
