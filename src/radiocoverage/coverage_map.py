"""Interactive HTML coverage map (Leaflet via folium)."""

from html import escape
from pathlib import Path

import folium

from radiocoverage.coverage import CoverageResult
from radiocoverage.geo import destination_point
from radiocoverage.link_map import add_base_layers, html_table
from radiocoverage.rendering import (
    class_ranges_dbm,
    mercator_resample,
    png_data_url,
    server_colour,
    server_rgba,
    signal_rgba,
)


def _legend_html(result: CoverageResult) -> str:
    receiver = result.receiver
    swatch = (
        "<span style='display:inline-block;width:12px;height:12px;margin-right:6px;"
        "vertical-align:middle;background:{};opacity:.85;border:1px solid #999'></span>"
    )
    classes = "".join(
        f"<div>{swatch.format(c.colour)}{escape(c.label)} "
        f"<span style='color:#666'>({escape(text)})</span></div>"
        for c, text in class_ranges_dbm(receiver.sensitivity_dbm)
    )
    models = sorted({result.model_label(site) for site in result.sites})
    rows = [
        ("Model", ", ".join(models)),
        ("Environment", result.environment),
        ("Terrain", "yes (Bullington diffraction)" if result.terrain else "no (flat earth)"),
        ("Sensitivity", f"{receiver.sensitivity_dbm:.1f} dBm"),
        ("Required margin", f"{receiver.required_margin_db:.1f} dB"),
        ("Covered area", f"{result.covered_area_km2:.1f} km² ({result.covered_fraction:.0%})"),
    ]
    servers = ""
    if len(result.sites) > 1:
        servers = "<div style='margin-top:6px;font-weight:bold'>Best server</div>" + "".join(
            f"<div>{swatch.format(server_colour(i))}{escape(site.name)} "
            f"<span style='color:#666'>({area:.1f} km²)</span></div>"
            for i, (site, area) in enumerate(
                zip(result.sites, result.served_area_km2(), strict=True)
            )
        )
    title = "Coverage prediction" if len(result.sites) == 1 else "Network coverage"
    return (
        "<div style='position:fixed;top:12px;left:56px;z-index:1000;background:white;"
        "padding:10px 12px;border-radius:6px;box-shadow:0 1px 5px rgba(0,0,0,.4);"
        "font-family:Arial,sans-serif;font-size:12px;max-width:330px'>"
        f"<div style='font-size:14px;font-weight:bold;margin-bottom:4px'>{title}</div>"
        f"{html_table(rows)}"
        f"<div style='margin-top:6px;font-weight:bold'>Received power</div>{classes}{servers}"
        "</div>"
    )


def build_coverage_map(result: CoverageResult) -> folium.Map:
    (south, west), (north, east) = result.grid.bounds
    m = folium.Map(
        location=((south + north) / 2, (west + east) / 2), tiles=None, control_scale=True
    )
    add_base_layers(m)

    signal = signal_rgba(result.best_power_dbm, result.receiver.sensitivity_dbm)
    folium.raster_layers.ImageOverlay(
        png_data_url(mercator_resample(signal, south, north)),
        bounds=[[south, west], [north, east]],
        name="Received power",
        pixelated=True,
    ).add_to(m)
    if len(result.sites) > 1:
        servers = server_rgba(result.best_server)
        folium.raster_layers.ImageOverlay(
            png_data_url(mercator_resample(servers, south, north)),
            bounds=[[south, west], [north, east]],
            name="Best server",
            pixelated=True,
            show=False,
        ).add_to(m)

    arrow_km = max(0.3, 0.12 * min(north - south, east - west) * 111.32)
    for index, site in enumerate(result.sites):
        colour = server_colour(index)
        popup = html_table(
            [
                ("Site", site.name),
                ("Location", str(site.location)),
                ("Band", site.band_name or f"{site.frequency_mhz:g} MHz"),
                ("Frequency", f"{site.frequency_mhz:g} MHz"),
                ("EIRP", f"{site.eirp_dbm:.1f} dBm"),
                ("Antenna height", f"{site.height_m:g} m"),
                (
                    "Azimuth",
                    f"{site.azimuth_deg:g}° (beamwidth {site.beamwidth_deg:g}°)"
                    if site.is_sector
                    else "omnidirectional",
                ),
                ("Model", result.model_label(site)),
            ]
        )
        folium.Marker(
            (site.location.lat, site.location.lon),
            tooltip=site.name,
            popup=folium.Popup(popup, max_width=340),
            icon=folium.Icon(color="darkblue", icon="tower-cell", prefix="fa"),
        ).add_to(m)
        if site.is_sector:
            tip = destination_point(site.location, site.azimuth_deg, arrow_km)
            folium.PolyLine(
                [(site.location.lat, site.location.lon), (tip.lat, tip.lon)],
                color=colour,
                weight=4,
                tooltip=f"{site.name}: azimuth {site.azimuth_deg:g}°",
            ).add_to(m)

    m.get_root().html.add_child(folium.Element(_legend_html(result)))
    folium.LayerControl(collapsed=False).add_to(m)
    m.fit_bounds([[south, west], [north, east]], padding_top_left=(360, 10))
    return m


def save_coverage_map(result: CoverageResult, output: Path) -> Path:
    output = Path(output)
    if output.suffix.lower() not in {".html", ".htm"}:
        raise ValueError(f"Map file must end in .html, got '{output.name}'")
    output.parent.mkdir(parents=True, exist_ok=True)
    build_coverage_map(result).save(str(output))
    return output
