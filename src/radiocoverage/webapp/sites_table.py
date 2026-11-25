"""The editable table of sites of the network page (pure logic, no Streamlit)."""

import math
from dataclasses import dataclass

from radiocoverage.bands import BANDS
from radiocoverage.coverage import Site
from radiocoverage.geo import GeoPoint, is_in_spain
from radiocoverage.webapp.presets import BAND_PROFILES, ExampleNetwork

COLUMNS = ("name", "lat", "lon", "band", "power", "gain", "height", "azimuth", "beamwidth")


def new_row(
    name: str,
    lat: float,
    lon: float,
    band_key: str,
    power: float,
    gain: float,
    height: float,
    azimuth: float | None = None,
    beamwidth: float = 65.0,
) -> dict:
    return {
        "name": name, "lat": round(lat, 6), "lon": round(lon, 6), "band": band_key,
        "power": power, "gain": gain, "height": height, "azimuth": azimuth,
        "beamwidth": beamwidth,
    }  # fmt: skip


def example_rows(network: ExampleNetwork) -> list[dict]:
    profile = BAND_PROFILES[network.band_key]
    return [
        new_row(
            name,
            lat,
            lon,
            network.band_key,
            profile.tx_power_dbm,
            profile.tx_gain_dbi,
            profile.tx_height_m,
            azimuth,
        )  # fmt: skip
        for name, lat, lon, azimuth in network.sites
    ]


def _blank(value) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value)) or value == ""


def apply_editor_changes(base: list[dict], changes: dict | None, defaults: dict) -> list[dict]:
    """Rows after the edits recorded by ``st.data_editor`` (edited, deleted, added)."""
    rows = [dict(row) for row in base]
    if not changes:
        return rows
    for position, edit in changes.get("edited_rows", {}).items():
        index = int(position)
        if 0 <= index < len(rows):
            rows[index].update(edit)
    deleted = {int(i) for i in changes.get("deleted_rows", [])}
    rows = [row for i, row in enumerate(rows) if i not in deleted]
    for added in changes.get("added_rows", []):
        row = dict(defaults)
        row.update({k: v for k, v in added.items() if k in COLUMNS and not _blank(v)})
        rows.append(row)
    return rows


@dataclass(frozen=True)
class RowError:
    row: int  # 1-based, as shown to the user
    key: str  # text key of the problem


def rows_to_sites(rows: list[dict], tx_loss_db: float = 0.0) -> tuple[list[Site], list[RowError]]:
    """Valid sites of the table, and the problems found in the other rows."""
    sites: list[Site] = []
    errors: list[RowError] = []
    for number, row in enumerate(rows, start=1):
        if _blank(row.get("lat")) or _blank(row.get("lon")):
            errors.append(RowError(number, "network.error.coordinates"))
            continue
        try:
            location = GeoPoint(float(row["lat"]), float(row["lon"]))
        except (TypeError, ValueError):
            errors.append(RowError(number, "network.error.coordinates"))
            continue
        if not is_in_spain(location):
            errors.append(RowError(number, "network.error.outside"))
            continue
        band_key = row.get("band") or "b20"
        if band_key not in BANDS:
            errors.append(RowError(number, "network.error.band"))
            continue
        profile = BAND_PROFILES[band_key]
        band = BANDS[band_key]

        def number_or(key, default, row=row):
            value = row.get(key)
            return float(default) if _blank(value) else float(value)

        azimuth = None if _blank(row.get("azimuth")) else float(row["azimuth"]) % 360
        try:
            sites.append(
                Site(
                    name=str(row.get("name") or f"Site {number}"),
                    location=location,
                    frequency_mhz=band.centre_mhz,
                    tx_power_dbm=number_or("power", profile.tx_power_dbm),
                    tx_gain_dbi=number_or("gain", profile.tx_gain_dbi),
                    tx_loss_db=tx_loss_db,
                    height_m=number_or("height", profile.tx_height_m),
                    azimuth_deg=azimuth,
                    beamwidth_deg=number_or("beamwidth", 65.0),
                    band_name=f"{band.technology} {band.name}",
                )
            )
        except (TypeError, ValueError):
            errors.append(RowError(number, "network.error.values"))
    return sites, errors
