"""Static PNG image of a coverage prediction over shaded relief (no internet needed)."""

import os
from pathlib import Path

import numpy as np

from radiocoverage.coverage import KM_PER_DEG_LAT, CoverageResult
from radiocoverage.rendering import (
    class_ranges_dbm,
    server_colour,
    server_rgba,
    signal_rgba,
)
from radiocoverage.terrain import ElevationSource


def site_labels(sites) -> dict:
    """One label per location: sectors of the same site share their common name."""
    groups: dict = {}
    for site in sites:
        groups.setdefault(site.location, []).append(site.name)
    labels = {}
    for location, names in groups.items():
        if len(names) == 1:
            labels[location] = names[0]
        else:
            common = os.path.commonprefix(names).rstrip(" -_S").strip()
            labels[location] = common or names[0]
    return labels


def hillshade(elevation: np.ndarray, dx_m: float, dy_m: float, azimuth=315.0, altitude=45.0):
    """Shaded relief in 0..1 (rows go north to south)."""
    dz_dy, dz_dx = np.gradient(elevation, dy_m, dx_m)
    dz_dy = -dz_dy  # rows increase southwards
    slope = np.arctan(np.hypot(dz_dx, dz_dy))
    aspect = np.arctan2(-dz_dx, dz_dy)
    az, alt = np.radians(360.0 - azimuth + 90.0), np.radians(altitude)
    shade = np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect)
    return np.clip(shade, 0, 1)


def plot_coverage(
    result: CoverageResult,
    output: Path,
    terrain: ElevationSource | None = None,
    layer: str = "signal",
    title: str = "",
) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    output = Path(output)
    if output.suffix.lower() != ".png":
        raise ValueError(f"Image file must end in .png, got '{output.name}'")
    (south, west), (north, east) = result.grid.bounds
    extent = (west, east, south, north)
    mid_lat = np.radians((south + north) / 2)

    fig, ax = plt.subplots(
        figsize=(8.5, 8.5 * (north - south) / ((east - west) * np.cos(mid_lat)) + 0.6), dpi=130
    )
    if terrain is not None:
        lats, lons = result.grid.mesh()
        elevation = terrain.elevation_m(lats, lons)
        dy = result.grid.lat_step * KM_PER_DEG_LAT * 1000
        dx = result.grid.lon_step * KM_PER_DEG_LAT * 1000 * np.cos(mid_lat)
        ax.imshow(hillshade(elevation, dx, dy), cmap="gray", extent=extent, vmin=0, vmax=1)
    else:
        ax.set_facecolor("#f0f0f0")

    if layer == "server" and len(result.sites) > 1:
        image = server_rgba(result.best_server)
        handles = [Patch(color=server_colour(i), label=s.name) for i, s in enumerate(result.sites)]
        legend_title = "Best server"
    else:
        image = signal_rgba(result.best_power_dbm, result.receiver.sensitivity_dbm)
        handles = [
            Patch(color=c.colour, label=f"{c.label}  {text}")
            for c, text in class_ranges_dbm(result.receiver.sensitivity_dbm)
        ]
        legend_title = "Received power"
    ax.imshow(image, extent=extent, interpolation="nearest")

    for location, names in site_labels(result.sites).items():
        ax.plot(location.lon, location.lat, marker="^", ms=10, color="white",
                markeredgecolor="black")  # fmt: skip
        ax.annotate(
            names,
            (location.lon, location.lat),
            textcoords="offset points",
            xytext=(6, 6),
            fontsize=8,
            bbox={"boxstyle": "round,pad=0.2", "fc": "white", "alpha": 0.8, "lw": 0},
        )
    for i, site in enumerate(result.sites):
        if site.is_sector:
            length = 0.12 * (north - south)
            az = np.radians(site.azimuth_deg)
            ax.annotate(
                "",
                xy=(
                    site.location.lon + length * np.sin(az) / np.cos(mid_lat),
                    site.location.lat + length * np.cos(az),
                ),
                xytext=(site.location.lon, site.location.lat),
                arrowprops={"arrowstyle": "->", "color": server_colour(i), "lw": 2},
            )

    ax.set_xlim(west, east)
    ax.set_ylim(south, north)
    ax.set_aspect(1 / np.cos(mid_lat))
    ax.set_xlabel("Longitude (°)")
    ax.set_ylabel("Latitude (°)")
    subtitle = (
        f"{result.environment}, {'terrain' if result.terrain else 'flat earth'} · covered "
        f"{result.covered_area_km2:.0f} km² ({result.covered_fraction:.0%})"
    )
    ax.set_title(f"{title}\n{subtitle}" if title else subtitle, fontsize=10)
    ax.legend(
        handles=handles,
        title=legend_title,
        loc="lower right",
        fontsize=8,
        title_fontsize=8,
        framealpha=0.9,
    )
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output)
    plt.close(fig)
    return output
