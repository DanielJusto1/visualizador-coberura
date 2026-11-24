"""Export coverage predictions to KMZ for Google Earth and GIS tools."""

import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from radiocoverage.coverage import CoverageResult
from radiocoverage.rendering import png_bytes, server_rgba, signal_rgba


def _ground_overlay(name: str, href: str, bounds, visible: bool) -> str:
    (south, west), (north, east) = bounds
    return f"""  <GroundOverlay>
    <name>{escape(name)}</name>
    <visibility>{int(visible)}</visibility>
    <Icon><href>{href}</href></Icon>
    <LatLonBox>
      <north>{north:.7f}</north><south>{south:.7f}</south>
      <east>{east:.7f}</east><west>{west:.7f}</west>
    </LatLonBox>
  </GroundOverlay>
"""


def kml_document(result: CoverageResult) -> str:
    bounds = result.grid.bounds
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>\n',
        '<kml xmlns="http://www.opengis.net/kml/2.2">\n<Document>\n',
        "  <name>Radio coverage prediction</name>\n",
        _ground_overlay("Received power", "signal.png", bounds, True),
    ]
    if len(result.sites) > 1:
        parts.append(_ground_overlay("Best server", "best_server.png", bounds, False))
    for site in result.sites:
        parts.append(
            f"""  <Placemark>
    <name>{escape(site.name)}</name>
    <description>{escape(site.description)}</description>
    <Point><coordinates>{site.location.lon:.7f},{site.location.lat:.7f},0</coordinates></Point>
  </Placemark>
"""
        )
    parts.append("</Document>\n</kml>\n")
    return "".join(parts)


def save_kmz(result: CoverageResult, output: Path) -> Path:
    """Write a KMZ (zipped KML) with the coverage overlays and the sites."""
    output = Path(output)
    if output.suffix.lower() != ".kmz":
        raise ValueError(f"KMZ file must end in .kmz, got '{output.name}'")
    output.parent.mkdir(parents=True, exist_ok=True)
    # KML ground overlays are drawn in plain latitude/longitude: no reprojection needed.
    signal = signal_rgba(result.best_power_dbm, result.receiver.sensitivity_dbm)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as kmz:
        kmz.writestr("doc.kml", kml_document(result))
        kmz.writestr("signal.png", png_bytes(signal))
        if len(result.sites) > 1:
            kmz.writestr("best_server.png", png_bytes(server_rgba(result.best_server)))
    return output
