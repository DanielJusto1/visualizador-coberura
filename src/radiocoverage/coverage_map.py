"""Interactive HTML coverage map (Leaflet via folium)."""

from html import escape
from pathlib import Path

import folium
import numpy as np

from radiocoverage.coverage import KM_PER_DEG_LAT, CoverageResult
from radiocoverage.geo import destination_point
from radiocoverage.i18n import tr
from radiocoverage.link_map import TX_ICON
from radiocoverage.mapstyle import (
    add_base_layers,
    add_controls,
    html_table,
    panel,
    relief_rgba,
    swatch,
)
from radiocoverage.rendering import (
    class_ranges_dbm,
    mercator_resample,
    png_data_url,
    server_colour,
    server_rgba,
    signal_rgba,
)
from radiocoverage.terrain import ElevationSource


def class_label(signal_class, lang: str) -> str:
    return tr(f"class.{signal_class.label.lower()}", lang)


def legend_html(result: CoverageResult, lang: str = "en") -> str:
    receiver = result.receiver
    classes = "".join(
        f"<div style='margin:2px 0'>{swatch(c.colour)}{escape(class_label(c, lang))} "
        f"<span style='color:#6b7280'>({escape(text)})</span></div>"
        for c, text in class_ranges_dbm(receiver.sensitivity_dbm, tr("range.to", lang))
    )
    models = sorted({result.model_label(site) for site in result.sites})
    rows = [
        (tr("q.model", lang), ", ".join(models)),
        (tr("q.environment", lang), tr(f"env.{result.environment}", lang)),
        (tr("q.terrain", lang), tr("q.terrain_yes" if result.terrain else "q.terrain_no", lang)),
        (tr("q.sensitivity", lang), f"{receiver.sensitivity_dbm:.1f} dBm"),
        (tr("q.required_margin", lang), f"{receiver.required_margin_db:.1f} dB"),
        (
            tr("q.covered_area", lang),
            f"{result.covered_area_km2:.1f} km² ({result.covered_fraction:.0%})",
        ),
    ]
    servers = ""
    if len(result.sites) > 1:
        servers = (
            f"<div style='margin-top:8px;font-weight:700'>{tr('map.layer.server', lang)}</div>"
            + "".join(
                f"<div style='margin:2px 0'>{swatch(server_colour(i))}{escape(site.name)} "
                f"<span style='color:#6b7280'>({area:.1f} km²)</span></div>"
                for i, (site, area) in enumerate(
                    zip(result.sites, result.served_area_km2(), strict=True)
                )
            )
        )
    title = tr("map.coverage_title" if len(result.sites) == 1 else "map.network_title", lang)
    return panel(
        f"<div style='font-size:14px;font-weight:700;margin-bottom:6px'>{title}</div>"
        f"{html_table(rows)}"
        f"<div style='margin-top:8px;font-weight:700'>{tr('map.layer.signal', lang)}</div>"
        f"{classes}{servers}",
        max_width=340,
    )


def relief_data_url(result: CoverageResult, terrain: ElevationSource) -> str:
    """PNG (data URL) of the shaded relief of the analysed area."""
    (south, _), (north, _) = result.grid.bounds
    lats, lons = result.grid.mesh()
    elevation = terrain.elevation_m(lats, lons)
    mid_lat = np.radians((south + north) / 2)
    dy = result.grid.lat_step * KM_PER_DEG_LAT * 1000
    dx = result.grid.lon_step * KM_PER_DEG_LAT * 1000 * np.cos(mid_lat)
    return png_data_url(mercator_resample(relief_rgba(elevation, dx, dy), south, north))


def relief_layer(
    result: CoverageResult,
    terrain: ElevationSource | None = None,
    lang: str = "en",
    data_url: str | None = None,
) -> folium.raster_layers.ImageOverlay:
    """Shaded relief of the analysed area, to show why the terrain casts radio shadows."""
    (south, west), (north, east) = result.grid.bounds
    return folium.raster_layers.ImageOverlay(
        data_url or relief_data_url(result, terrain),
        bounds=[[south, west], [north, east]],
        name=tr("map.layer.relief", lang),
    )


def add_coverage_layers(
    target: folium.Map | folium.FeatureGroup,
    result: CoverageResult,
    lang: str = "en",
    show_server: bool = False,
    site_markers: bool = True,
) -> None:
    """Received power (and best server) overlays plus the sites, on a map or group."""
    (south, west), (north, east) = result.grid.bounds
    bounds = [[south, west], [north, east]]
    signal = signal_rgba(result.best_power_dbm, result.receiver.sensitivity_dbm)
    folium.raster_layers.ImageOverlay(
        png_data_url(mercator_resample(signal, south, north)),
        bounds=bounds,
        name=tr("map.layer.signal", lang),
        pixelated=True,
        show=not show_server,
    ).add_to(target)
    if len(result.sites) > 1:
        servers = server_rgba(result.best_server)
        folium.raster_layers.ImageOverlay(
            png_data_url(mercator_resample(servers, south, north)),
            bounds=bounds,
            name=tr("map.layer.server", lang),
            pixelated=True,
            show=show_server,
        ).add_to(target)
    if not site_markers:
        return

    arrow_km = max(0.3, 0.12 * min(north - south, east - west) * KM_PER_DEG_LAT)
    for index, site in enumerate(result.sites):
        azimuth = (
            f"{site.azimuth_deg:g}° ({tr('q.beamwidth', lang, beamwidth=site.beamwidth_deg)})"
            if site.is_sector
            else tr("omni", lang)
        )
        popup = html_table(
            [
                (tr("q.site", lang), site.name),
                (tr("q.location", lang), str(site.location)),
                (tr("q.band", lang), site.band_name or f"{site.frequency_mhz:g} MHz"),
                (tr("q.frequency", lang), f"{site.frequency_mhz:g} MHz"),
                (tr("q.eirp", lang), f"{site.eirp_dbm:.1f} dBm"),
                (tr("q.antenna_height", lang), f"{site.height_m:g} m"),
                (tr("q.azimuth", lang), azimuth),
                (tr("q.model", lang), result.model_label(site)),
            ]
        )
        folium.Marker(
            (site.location.lat, site.location.lon),
            tooltip=site.name,
            popup=folium.Popup(popup, max_width=340),
            icon=folium.Icon(**TX_ICON),
        ).add_to(target)
        if site.is_sector:
            tip = destination_point(site.location, site.azimuth_deg, arrow_km)
            folium.PolyLine(
                [(site.location.lat, site.location.lon), (tip.lat, tip.lon)],
                color=server_colour(index),
                weight=4,
                tooltip=tr("map.azimuth_tooltip", lang, name=site.name, azimuth=site.azimuth_deg),
            ).add_to(target)


def build_coverage_map(
    result: CoverageResult, terrain: ElevationSource | None = None, lang: str = "en"
) -> folium.Map:
    (south, west), (north, east) = result.grid.bounds
    m = folium.Map(
        location=((south + north) / 2, (west + east) / 2), tiles=None, control_scale=True
    )
    add_base_layers(m, lang)
    add_controls(m, lang)
    if terrain is not None:
        relief_layer(result, terrain, lang).add_to(m)
    add_coverage_layers(m, result, lang)
    m.get_root().html.add_child(folium.Element(legend_html(result, lang)))
    folium.LayerControl(collapsed=False).add_to(m)
    m.fit_bounds([[south, west], [north, east]], padding_top_left=(360, 10))
    return m


def save_coverage_map(
    result: CoverageResult,
    output: Path,
    terrain: ElevationSource | None = None,
    lang: str = "en",
) -> Path:
    output = Path(output)
    if output.suffix.lower() not in {".html", ".htm"}:
        raise ValueError(f"Map file must end in .html, got '{output.name}'")
    output.parent.mkdir(parents=True, exist_ok=True)
    build_coverage_map(result, terrain, lang).save(str(output))
    return output
