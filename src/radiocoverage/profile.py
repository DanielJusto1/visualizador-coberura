"""Terrain profile of a radio link: line of sight, Fresnel clearance and diffraction.

Diffraction over obstacles uses the ITU-R P.526 knife-edge approximation

    J(v) = 6.9 + 20*log10( sqrt((v - 0.1)^2 + 1) + v - 0.1 )   for v > -0.78

with the Fresnel-Kirchhoff parameter v = h * sqrt(2 * (d1 + d2) / (lambda * d1 * d2)),
where h is the height of the obstacle above the line joining the two antennas.
The whole profile is reduced to one equivalent knife edge with the Bullington
construction recommended by ITU-R P.526-15 (section 4.5.1).
"""

import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from radiocoverage.fresnel import CLEARANCE_RATIO, STANDARD_K_FACTOR
from radiocoverage.geo import EARTH_RADIUS_KM, GeoPoint
from radiocoverage.path import LinkPath
from radiocoverage.terrain import ElevationSource
from radiocoverage.units import wavelength_m

NU_THRESHOLD = -0.78
"""Below this Fresnel parameter the knife-edge loss is negligible (ITU-R P.526)."""

END_EXCLUSION_M = 50.0
"""Terrain closer than this to either antenna is ignored: a ~30 m elevation model cannot
resolve obstacles at that scale, and local clutter dominates there anyway."""


def knife_edge_loss_db(nu):
    """Single knife-edge diffraction loss J(v) in dB (ITU-R P.526, eq. 31)."""
    v = np.asarray(nu, dtype=float)
    with np.errstate(invalid="ignore"):
        loss = 6.9 + 20.0 * np.log10(np.sqrt((v - 0.1) ** 2 + 1.0) + v - 0.1)
    loss = np.where(v > NU_THRESHOLD, loss, 0.0)
    return float(loss) if loss.ndim == 0 else loss


def fresnel_nu(height_m, d1_m, d2_m, wavelength: float):
    """Fresnel-Kirchhoff diffraction parameter v."""
    return np.asarray(height_m) * np.sqrt(
        2.0 * (np.asarray(d1_m) + np.asarray(d2_m)) / (wavelength * d1_m * d2_m)
    )


def earth_bulge_profile_m(distances_km: np.ndarray, k_factor: float = STANDARD_K_FACTOR):
    total = distances_km[-1]
    return distances_km * (total - distances_km) * 1000.0 / (2.0 * k_factor * EARTH_RADIUS_KM)


@dataclass(frozen=True)
class DiffractionEdge:
    """Equivalent knife edge of a profile (Bullington construction)."""

    distance_m: np.ndarray | float
    height_m: np.ndarray | float
    nu: np.ndarray | float
    loss_db: np.ndarray | float
    line_of_sight: np.ndarray | bool


def bullington_edge(
    d1_m: np.ndarray,
    total_m: np.ndarray | float,
    ground_m: np.ndarray,
    tx_top_m: np.ndarray | float,
    rx_top_m: np.ndarray | float,
    wavelength: float,
) -> DiffractionEdge:
    """Bullington equivalent knife edge (ITU-R P.526-15, section 4.5.1).

    Works on one profile (1-D arrays) or on many profiles at once (2-D arrays,
    one profile per row, samples along the last axis). ``ground_m`` must already
    include the Earth bulge and samples too close to the antennas should be set
    to ``-inf`` so they are ignored.

    * Line of sight: the edge is the terrain point with the largest v.
    * No line of sight: the edge sits where the steepest ray from the transmitter
      meets the steepest ray from the receiver.
    """
    total = np.asarray(total_m, dtype=float)
    tx_top = np.asarray(tx_top_m, dtype=float)
    rx_top = np.asarray(rx_top_m, dtype=float)
    d2_m = total[..., None] - d1_m if total.ndim else total - d1_m
    tx_col = tx_top[..., None] if tx_top.ndim else tx_top
    rx_col = rx_top[..., None] if rx_top.ndim else rx_top
    tot_col = total[..., None] if total.ndim else total

    with np.errstate(divide="ignore", invalid="ignore"):
        slope_tx = np.max((ground_m - tx_col) / d1_m, axis=-1)  # steepest ray from Tx
        slope_rx = np.max((ground_m - rx_col) / d2_m, axis=-1)  # steepest ray from Rx
        slope_los = (rx_top - tx_top) / total
        line = tx_col + (rx_col - tx_col) * d1_m / tot_col
        nu_points = fresnel_nu(ground_m - line, d1_m, d2_m, wavelength)
    nu_points = np.where(np.isfinite(nu_points), nu_points, -np.inf)
    index = np.argmax(nu_points, axis=-1)
    nu_los = np.take_along_axis(nu_points, np.expand_dims(index, -1), -1)[..., 0]
    d_los = np.take_along_axis(
        np.broadcast_to(d1_m, ground_m.shape), np.expand_dims(index, -1), -1
    )[..., 0]
    h_los = np.take_along_axis(ground_m, np.expand_dims(index, -1), -1)[..., 0]

    line_of_sight = slope_tx < slope_los
    with np.errstate(divide="ignore", invalid="ignore"):
        d_b = (rx_top - tx_top + slope_rx * total) / (slope_tx + slope_rx)
        d_b = np.clip(d_b, 1e-3, total - 1e-3)
        h_b = tx_top + slope_tx * d_b
        chord = (tx_top * (total - d_b) + rx_top * d_b) / total
        nu_b = fresnel_nu(h_b - chord, d_b, total - d_b, wavelength)

    nu = np.where(line_of_sight, nu_los, nu_b)
    nu = np.where(np.isfinite(nu), nu, -np.inf)
    edge = DiffractionEdge(
        distance_m=np.where(line_of_sight, d_los, d_b),
        height_m=np.where(line_of_sight, h_los, h_b),
        nu=nu,
        loss_db=knife_edge_loss_db(np.maximum(nu, -10.0)),
        line_of_sight=line_of_sight,
    )
    if np.ndim(nu) == 0:
        return DiffractionEdge(
            *(
                v.item() if hasattr(v, "item") else v
                for v in (edge.distance_m, edge.height_m, edge.nu, edge.loss_db, edge.line_of_sight)
            )
        )
    return edge


@dataclass(frozen=True)
class TerrainProfile:
    """Elevation profile between two antennas and its radio analysis."""

    distances_km: np.ndarray
    elevations_m: np.ndarray
    tx_height_m: float
    rx_height_m: float
    frequency_mhz: float
    k_factor: float = STANDARD_K_FACTOR
    edge: DiffractionEdge | None = field(default=None, compare=False)

    @property
    def diffraction_loss_db(self) -> float:
        return float(self.edge.loss_db) if self.edge is not None else 0.0

    @property
    def length_km(self) -> float:
        return float(self.distances_km[-1])

    @property
    def bulge_m(self) -> np.ndarray:
        return earth_bulge_profile_m(self.distances_km, self.k_factor)

    @property
    def ground_m(self) -> np.ndarray:
        """Terrain raised by the Earth bulge, relative to the straight chord."""
        return self.elevations_m + self.bulge_m

    @property
    def tx_antenna_m(self) -> float:
        return float(self.elevations_m[0] + self.tx_height_m)

    @property
    def rx_antenna_m(self) -> float:
        return float(self.elevations_m[-1] + self.rx_height_m)

    @property
    def line_of_sight_m(self) -> np.ndarray:
        t = self.distances_km / self.length_km
        return self.tx_antenna_m + (self.rx_antenna_m - self.tx_antenna_m) * t

    @property
    def fresnel_radius_m(self) -> np.ndarray:
        d1 = self.distances_km * 1000.0
        d2 = (self.length_km - self.distances_km) * 1000.0
        return np.sqrt(wavelength_m(self.frequency_mhz) * d1 * d2 / (d1 + d2))

    @property
    def clearance_m(self) -> np.ndarray:
        """Height of the line of sight above the (bulged) terrain."""
        return self.line_of_sight_m - self.ground_m

    @property
    def _analysed(self) -> np.ndarray:
        """Interior samples far enough from both antennas to be analysed."""
        d_m = self.distances_km * 1000.0
        return (d_m >= END_EXCLUSION_M) & (d_m[-1] - d_m >= END_EXCLUSION_M)

    @property
    def min_clearance_ratio(self) -> float:
        """Smallest clearance as a fraction of the first Fresnel zone."""
        mask = self._analysed
        if not mask.any():
            return math.inf
        return float(np.min(self.clearance_m[mask] / self.fresnel_radius_m[mask]))

    @property
    def has_line_of_sight(self) -> bool:
        return bool(np.all(self.clearance_m[self._analysed] > 0))

    @property
    def fresnel_clear(self) -> bool:
        return self.min_clearance_ratio >= CLEARANCE_RATIO

    @property
    def status(self) -> str:
        if self.fresnel_clear:
            return "clear (>= 60% of 1st Fresnel zone free)"
        if self.has_line_of_sight:
            return "line of sight, but Fresnel zone partly obstructed"
        return "obstructed (no line of sight)"


def terrain_profile(
    path: LinkPath,
    terrain: ElevationSource,
    tx_height_m: float,
    rx_height_m: float,
    spacing_m: float = 30.0,
    k_factor: float = STANDARD_K_FACTOR,
    max_samples: int = 4000,
) -> TerrainProfile:
    """Sample the terrain along ``path`` and analyse its obstruction."""
    samples = int(min(max(path.distance_km * 1000.0 / spacing_m, 16), max_samples)) + 1
    t = np.linspace(0.0, 1.0, samples)
    # Linear interpolation of coordinates is accurate enough for links of tens of km.
    lats = path.tx.lat + (path.rx.lat - path.tx.lat) * t
    lons = path.tx.lon + (path.rx.lon - path.tx.lon) * t
    elevations = np.asarray(terrain.elevation_m(lats, lons), dtype=float)
    distances_km = t * path.distance_km

    base = TerrainProfile(
        distances_km, elevations, tx_height_m, rx_height_m, path.frequency_mhz, k_factor
    )
    ground = np.where(base._analysed, base.ground_m, -np.inf)
    edge = bullington_edge(
        distances_km * 1000.0,
        distances_km[-1] * 1000.0,
        ground,
        base.tx_antenna_m,
        base.rx_antenna_m,
        wavelength_m(path.frequency_mhz),
    )
    return TerrainProfile(
        distances_km, elevations, tx_height_m, rx_height_m, path.frequency_mhz, k_factor, edge
    )


def radial_diffraction_db(
    site: GeoPoint,
    site_height_m: float,
    lats: np.ndarray,
    lons: np.ndarray,
    distances_km: np.ndarray,
    rx_height_m: float,
    frequency_mhz: float,
    terrain: ElevationSource,
    samples: int = 48,
    k_factor: float = STANDARD_K_FACTOR,
    chunk: int = 20_000,
) -> np.ndarray:
    """Bullington diffraction loss from ``site`` to every point of a grid.

    Each grid point gets its own radial profile with ``samples`` points, so hills
    and mountains cast realistic radio shadows on the coverage map.
    """
    lats, lons, distances_km = (np.asarray(a, float).ravel() for a in (lats, lons, distances_km))
    wavelength = wavelength_m(frequency_mhz)
    site_ground = float(terrain.elevation_m(np.array([site.lat]), np.array([site.lon]))[0])
    tx_top = site_ground + site_height_m
    t = np.linspace(0.0, 1.0, samples + 2)[1:-1]
    result = np.zeros(lats.shape)

    for start in range(0, lats.size, chunk):
        sl = slice(start, start + chunk)
        lat_pts, lon_pts, dist = lats[sl], lons[sl], np.maximum(distances_km[sl], 1e-3)
        rx_top = terrain.elevation_m(lat_pts, lon_pts) + rx_height_m
        sample_lats = site.lat + np.outer(lat_pts - site.lat, t)
        sample_lons = site.lon + np.outer(lon_pts - site.lon, t)
        ground = terrain.elevation_m(sample_lats, sample_lons)
        d1_km = np.outer(dist, t)
        d2_km = np.outer(dist, 1.0 - t)
        ground = ground + d1_km * d2_km * 1000.0 / (2.0 * k_factor * EARTH_RADIUS_KM)
        too_close = (d1_km * 1000.0 < END_EXCLUSION_M) | (d2_km * 1000.0 < END_EXCLUSION_M)
        ground = np.where(too_close, -np.inf, ground)
        edge = bullington_edge(d1_km * 1000.0, dist * 1000.0, ground, tx_top, rx_top, wavelength)
        result[sl] = edge.loss_db
    return result


def plot_profile(profile: TerrainProfile, output: Path, title: str = "") -> Path:
    """Save a PNG chart of the terrain, line of sight and first Fresnel zone."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output = Path(output)
    if output.suffix.lower() != ".png":
        raise ValueError(f"Profile file must end in .png, got '{output.name}'")
    d = profile.distances_km
    ground = profile.ground_m
    los = profile.line_of_sight_m
    radius = profile.fresnel_radius_m
    floor = min(float(ground.min()), float((los - radius).min()))
    floor -= 0.05 * (max(float(ground.max()), float(los.max())) - floor) + 5.0

    fig, ax = plt.subplots(figsize=(10, 4.2), dpi=120)
    ax.fill_between(d, floor, ground, color="#a6845c", alpha=0.85, label="Terrain + Earth bulge")
    ax.fill_between(
        d, los - radius, los + radius, color="#4575b4", alpha=0.18, label="1st Fresnel zone"
    )
    ax.plot(
        d,
        los - CLEARANCE_RATIO * radius,
        color="#4575b4",
        lw=0.8,
        ls="--",
        label="60% Fresnel clearance",
    )
    ax.plot(d, los, color="#d73027", lw=1.6, label="Line of sight")
    ax.plot([0], [profile.tx_antenna_m], marker="^", color="#08306b", ms=9, ls="none")
    ax.plot([d[-1]], [profile.rx_antenna_m], marker="o", color="#08306b", ms=7, ls="none")
    ax.annotate("Tx", (0, profile.tx_antenna_m), textcoords="offset points", xytext=(4, 6))
    ax.annotate("Rx", (d[-1], profile.rx_antenna_m), textcoords="offset points", xytext=(-16, 6))
    edge = profile.edge
    if edge is not None and edge.loss_db > 0:
        edge_km = float(edge.distance_m) / 1000.0
        if not edge.line_of_sight:
            ax.plot(
                [0, edge_km, d[-1]],
                [profile.tx_antenna_m, edge.height_m, profile.rx_antenna_m],
                color="black",
                lw=0.8,
                ls=":",
            )
        ax.plot(
            [edge_km],
            [edge.height_m],
            marker="v",
            color="black",
            ms=7,
            ls="none",
            label="Equivalent knife edge",
        )
        near_end = edge_km > 0.85 * d[-1]
        ax.annotate(
            f"{edge.loss_db:.1f} dB",
            (edge_km, edge.height_m),
            textcoords="offset points",
            xytext=(-28 if near_end else 0, 10),
            ha="center",
            fontsize=8,
        )
    ax.set_xlim(0, d[-1])
    ax.set_ylim(bottom=floor)
    ax.set_xlabel("Distance from transmitter (km)")
    ax.set_ylabel("Height above sea level (m)")
    subtitle = (
        f"{profile.status} · diffraction loss {profile.diffraction_loss_db:.1f} dB · "
        f"k = {profile.k_factor:.2f}"
    )
    ax.set_title(f"{title}\n{subtitle}" if title else subtitle, fontsize=10)
    ax.grid(alpha=0.3)
    ax.legend(loc="upper right", fontsize=8, framealpha=0.9)
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output)
    plt.close(fig)
    return output
