"""Interactive HTML map of a point-to-point link (Leaflet via folium)."""

import base64
from html import escape
from pathlib import Path

import folium

from radiocoverage.bands import Band
from radiocoverage.i18n import tr
from radiocoverage.link_budget import LinkBudgetResult
from radiocoverage.mapstyle import add_base_layers, add_controls, badge, html_table, panel
from radiocoverage.path import LinkPath
from radiocoverage.profile import TerrainProfile

__all__ = ["add_base_layers", "build_link_map", "html_table", "save_link_map"]

OK_COLOUR = "#1a9850"
FAIL_COLOUR = "#d73027"
FRESNEL_COLOUR = "#4575b4"
TX_ICON = {"color": "darkblue", "icon": "tower-cell", "prefix": "fa"}


def link_title(result: LinkBudgetResult, band: Band | None) -> str:
    if band is not None:
        return f"{band.technology} {band.name} · {band.centre_mhz:g} MHz"
    return f"{result.parameters.frequency_mhz:g} MHz"


def summary_rows(
    path: LinkPath, result: LinkBudgetResult, profile: TerrainProfile | None, lang: str = "en"
) -> list[tuple[str, str]]:
    p = result.parameters
    rows = [
        (tr("q.distance", lang), f"{path.distance_km:.2f} km"),
        (tr("q.azimuth_tx_rx", lang), f"{path.bearing_deg:.1f}°"),
        (tr("q.eirp", lang), f"{result.eirp_dbm:.1f} dBm"),
        (tr("q.model", lang), result.model_label),
        (tr("q.path_loss", lang), f"{result.path_loss_db:.1f} dB"),
    ]
    if profile is not None:
        rows += [
            (tr("q.terrain", lang), tr(f"terrain.{profile.status_key}", lang)),
            (tr("q.diffraction_loss", lang), f"{profile.diffraction_loss_db:.1f} dB"),
        ]
    return rows + [
        (tr("q.rx_power", lang), f"{result.rx_power_dbm:.1f} dBm"),
        (tr("q.sensitivity", lang), f"{p.rx_sensitivity_dbm:.1f} dBm"),
        (
            tr("q.margin", lang),
            tr("q.margin_required", lang, margin=result.margin_db, required=p.required_margin_db),
        ),
        (
            tr("q.fresnel_radius", lang),
            tr("q.at_midpath", lang, value=path.fresnel_radius_midpoint_m),
        ),
        (tr("q.earth_bulge", lang), tr("q.at_midpath", lang, value=path.earth_bulge_midpoint_m())),
    ]


def add_link_layers(
    target: folium.Map | folium.FeatureGroup,
    path: LinkPath,
    result: LinkBudgetResult,
    lang: str = "en",
) -> None:
    """Markers, radio path and Fresnel zone of a link, added to a map or feature group."""
    viable = result.is_viable
    colour = OK_COLOUR if viable else FAIL_COLOUR
    p = result.parameters
    tx_popup = html_table(
        [
            (tr("q.transmitter", lang), str(path.tx)),
            (tr("q.tx_power", lang), f"{p.tx_power_dbm:.1f} dBm"),
            (tr("q.tx_gain", lang), f"{p.tx_antenna_gain_dbi:.1f} dBi"),
            (tr("q.eirp", lang), f"{result.eirp_dbm:.1f} dBm"),
            (tr("q.point_antenna", lang), f"{path.bearing_deg:.1f}°"),
        ]
    )
    rx_popup = html_table(
        [
            (tr("q.receiver", lang), str(path.rx)),
            (tr("q.rx_power", lang), f"{result.rx_power_dbm:.1f} dBm"),
            (tr("q.margin", lang), f"{result.margin_db:.1f} dB"),
            (tr("q.tx_at", lang), f"{path.reverse_bearing_deg:.1f}°"),
        ]
    )
    folium.Polygon(
        [(pt.lat, pt.lon) for pt in path.fresnel_outline()],
        color=FRESNEL_COLOUR,
        weight=1,
        fill=True,
        fill_opacity=0.2,
        tooltip=tr("map.fresnel_tooltip", lang, radius=path.fresnel_radius_midpoint_m),
    ).add_to(target)
    folium.PolyLine(
        [(path.tx.lat, path.tx.lon), (path.rx.lat, path.rx.lon)],
        color=colour,
        weight=4,
        opacity=0.9,
        tooltip=tr("map.link_tooltip", lang, distance=path.distance_km, margin=result.margin_db),
    ).add_to(target)
    folium.Marker(
        (path.tx.lat, path.tx.lon),
        tooltip=tr("map.tx", lang),
        popup=folium.Popup(tx_popup, max_width=320),
        icon=folium.Icon(**TX_ICON),
    ).add_to(target)
    folium.Marker(
        (path.rx.lat, path.rx.lon),
        tooltip=tr("map.rx", lang),
        popup=folium.Popup(rx_popup, max_width=320),
        icon=folium.Icon(color="green" if viable else "red", icon="mobile-screen", prefix="fa"),
    ).add_to(target)


def build_link_map(
    path: LinkPath,
    result: LinkBudgetResult,
    band: Band | None = None,
    profile: TerrainProfile | None = None,
    profile_png: bytes | None = None,
    lang: str = "en",
) -> folium.Map:
    """Create a map with both ends of the link, the radio path and its Fresnel zone."""
    viable = result.is_viable
    colour = OK_COLOUR if viable else FAIL_COLOUR
    verdict = tr("verdict.ok" if viable else "verdict.fail", lang)

    m = folium.Map(location=(path.midpoint.lat, path.midpoint.lon), tiles=None, control_scale=True)
    add_base_layers(m, lang)
    add_controls(m, lang)

    fresnel = folium.FeatureGroup(name=tr("map.layer.fresnel", lang))
    add_link_layers(fresnel, path, result, lang)
    fresnel.add_to(m)

    content = (
        f"<div style='font-size:14px;font-weight:700;margin-bottom:6px'>"
        f"{escape(link_title(result, band))}</div>"
        f"<div style='margin-bottom:8px'>{badge(verdict, colour)}</div>"
        f"{html_table(summary_rows(path, result, profile, lang))}"
    )
    m.get_root().html.add_child(folium.Element(panel(content, max_width=400)))
    if profile_png is not None:
        encoded = base64.b64encode(profile_png).decode("ascii")
        m.get_root().html.add_child(
            folium.Element(
                panel(
                    f"<img src='data:image/png;base64,{encoded}' style='width:min(560px,90vw)' "
                    "alt='Terrain profile'>",
                    position="bottom:28px;right:12px",
                    max_width=600,
                )
            )
        )

    folium.LayerControl(collapsed=True).add_to(m)
    m.fit_bounds(
        [
            (min(path.tx.lat, path.rx.lat), min(path.tx.lon, path.rx.lon)),
            (max(path.tx.lat, path.rx.lat), max(path.tx.lon, path.rx.lon)),
        ],
        padding_top_left=(420, 40),
        padding_bottom_right=(40, 280 if profile_png is not None else 40),
    )
    return m


def save_link_map(
    path: LinkPath,
    result: LinkBudgetResult,
    output: Path,
    band: Band | None = None,
    profile: TerrainProfile | None = None,
    profile_png: bytes | None = None,
    lang: str = "en",
) -> Path:
    """Build the map and write it as a standalone HTML file."""
    output = Path(output)
    if output.suffix.lower() not in {".html", ".htm"}:
        raise ValueError(f"Map file must end in .html, got '{output.name}'")
    output.parent.mkdir(parents=True, exist_ok=True)
    build_link_map(path, result, band, profile, profile_png, lang).save(str(output))
    return output
