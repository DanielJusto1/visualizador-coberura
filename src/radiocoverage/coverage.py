"""Coverage prediction over a regular latitude/longitude grid.

For every grid point and every site:

    P_rx = P_tx + G_tx - A(angle) - L_tx - L_path(model) - L_terrain - L_other + G_rx - L_rx

where A(angle) is the attenuation of the sector antenna pattern towards that
point. With several sites, the *best server* of a point is the site received
with the highest power.
"""

import math
from dataclasses import dataclass

import numpy as np

from radiocoverage.antenna import (
    DEFAULT_BEAMWIDTH_DEG,
    DEFAULT_FRONT_TO_BACK_DB,
    angle_off_boresight_deg,
    sector_attenuation_db,
)
from radiocoverage.geo import GeoPoint, bearing_deg_array, distance_km_array
from radiocoverage.link_budget import eirp_dbm
from radiocoverage.profile import radial_diffraction_db
from radiocoverage.propagation import get_model, path_loss_db
from radiocoverage.terrain import ElevationSource

KM_PER_DEG_LAT = 111.32
MAX_GRID_POINTS = 1_000_000


@dataclass(frozen=True)
class Site:
    """A base station sector (or an omnidirectional site when azimuth is None)."""

    name: str
    location: GeoPoint
    frequency_mhz: float
    tx_power_dbm: float
    tx_gain_dbi: float = 0.0
    tx_loss_db: float = 0.0
    height_m: float = 30.0
    azimuth_deg: float | None = None
    beamwidth_deg: float = DEFAULT_BEAMWIDTH_DEG
    front_to_back_db: float = DEFAULT_FRONT_TO_BACK_DB
    band_name: str = ""

    def __post_init__(self) -> None:
        if not self.frequency_mhz > 0:
            raise ValueError(f"Site '{self.name}': frequency must be positive")
        if not self.height_m > 0:
            raise ValueError(f"Site '{self.name}': antenna height must be positive")
        if self.tx_loss_db < 0:
            raise ValueError(f"Site '{self.name}': cable loss cannot be negative")
        if self.azimuth_deg is not None and not 0 <= self.azimuth_deg <= 360:
            raise ValueError(f"Site '{self.name}': azimuth must be between 0 and 360 degrees")
        sector_attenuation_db(0.0, self.beamwidth_deg, self.front_to_back_db)  # validates

    @property
    def eirp_dbm(self) -> float:
        return eirp_dbm(self.tx_power_dbm, self.tx_gain_dbi, self.tx_loss_db)

    @property
    def is_sector(self) -> bool:
        return self.azimuth_deg is not None

    @property
    def description(self) -> str:
        band = self.band_name or f"{self.frequency_mhz:g} MHz"
        pattern = f"sector {self.azimuth_deg:g}°" if self.is_sector else "omni"
        return f"{self.name} ({band}, {pattern}, {self.height_m:g} m, EIRP {self.eirp_dbm:.1f} dBm)"


@dataclass(frozen=True)
class Receiver:
    sensitivity_dbm: float
    height_m: float = 1.5
    gain_dbi: float = 0.0
    loss_db: float = 0.0
    other_losses_db: float = 0.0
    required_margin_db: float = 0.0

    def __post_init__(self) -> None:
        if not self.height_m > 0:
            raise ValueError("Receiver height must be positive")
        for name in ("loss_db", "other_losses_db", "required_margin_db"):
            if getattr(self, name) < 0:
                raise ValueError(f"Receiver {name} cannot be negative")

    @property
    def threshold_dbm(self) -> float:
        """Minimum received power for a point to count as covered."""
        return self.sensitivity_dbm + self.required_margin_db


@dataclass(frozen=True)
class Grid:
    """Pixel centres of a regular grid. Rows go from north to south."""

    lats: np.ndarray
    lons: np.ndarray

    @property
    def shape(self) -> tuple[int, int]:
        return (self.lats.size, self.lons.size)

    @property
    def lat_step(self) -> float:
        return float(abs(self.lats[0] - self.lats[1])) if self.lats.size > 1 else 0.0

    @property
    def lon_step(self) -> float:
        return float(abs(self.lons[1] - self.lons[0])) if self.lons.size > 1 else 0.0

    @property
    def bounds(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """((south, west), (north, east)) of the outer pixel edges."""
        half_lat, half_lon = self.lat_step / 2, self.lon_step / 2
        return (
            (float(self.lats.min() - half_lat), float(self.lons.min() - half_lon)),
            (float(self.lats.max() + half_lat), float(self.lons.max() + half_lon)),
        )

    def mesh(self) -> tuple[np.ndarray, np.ndarray]:
        return np.meshgrid(self.lats, self.lons, indexing="ij")

    def pixel_area_km2(self) -> np.ndarray:
        """Area of every pixel (shrinks slightly towards the north)."""
        height = self.lat_step * KM_PER_DEG_LAT
        width = self.lon_step * KM_PER_DEG_LAT * np.cos(np.radians(self.lats))
        return np.repeat((height * width)[:, None], self.lons.size, axis=1)


def make_grid(south: float, west: float, north: float, east: float, resolution_m: float) -> Grid:
    """Regular grid covering a box with pixels of about ``resolution_m`` metres."""
    if not resolution_m > 0:
        raise ValueError(f"Resolution must be positive, got {resolution_m} m")
    if not (south < north and west < east):
        raise ValueError("Invalid grid bounds")
    mid_lat = math.radians((south + north) / 2)
    lat_step = resolution_m / 1000.0 / KM_PER_DEG_LAT
    lon_step = resolution_m / 1000.0 / (KM_PER_DEG_LAT * math.cos(mid_lat))
    rows = max(2, math.ceil((north - south) / lat_step))
    cols = max(2, math.ceil((east - west) / lon_step))
    if rows * cols > MAX_GRID_POINTS:
        raise ValueError(
            f"The grid would have {rows * cols:,} points (limit {MAX_GRID_POINTS:,}); "
            "use a coarser resolution or a smaller radius"
        )
    lats = north - lat_step * (np.arange(rows) + 0.5)
    lons = west + lon_step * (np.arange(cols) + 0.5)
    return Grid(lats, lons)


def grid_around(points: list[GeoPoint], radius_km: float, resolution_m: float) -> Grid:
    """Grid covering every point plus ``radius_km`` around it."""
    if not radius_km > 0:
        raise ValueError(f"Radius must be positive, got {radius_km} km")
    dlat = radius_km / KM_PER_DEG_LAT
    south = min(p.lat for p in points) - dlat
    north = max(p.lat for p in points) + dlat
    dlon = radius_km / (KM_PER_DEG_LAT * math.cos(math.radians(max(abs(south), abs(north)))))
    west = min(p.lon for p in points) - dlon
    east = max(p.lon for p in points) + dlon
    return make_grid(south, west, north, east, resolution_m)


def site_received_power_dbm(
    site: Site,
    grid: Grid,
    receiver: Receiver,
    model: str = "auto",
    environment: str = "urban",
    terrain: ElevationSource | None = None,
    terrain_samples: int = 48,
) -> np.ndarray:
    """Received power (dBm) from one site at every grid point."""
    lats, lons = grid.mesh()
    distances = distance_km_array(site.location, lats, lons)
    loss = path_loss_db(
        model,
        np.maximum(distances, 1e-3),
        site.frequency_mhz,
        site.height_m,
        receiver.height_m,
        environment,
    )
    power = site.eirp_dbm - loss - receiver.other_losses_db + receiver.gain_dbi - receiver.loss_db
    if site.is_sector:
        angles = angle_off_boresight_deg(
            bearing_deg_array(site.location, lats, lons), site.azimuth_deg
        )
        power = power - sector_attenuation_db(angles, site.beamwidth_deg, site.front_to_back_db)
    if terrain is not None:
        diffraction = radial_diffraction_db(
            site.location,
            site.height_m,
            lats,
            lons,
            distances,
            receiver.height_m,
            site.frequency_mhz,
            terrain,
            samples=terrain_samples,
        ).reshape(grid.shape)
        power = power - diffraction
    return power


@dataclass(frozen=True)
class CoverageResult:
    grid: Grid
    sites: tuple[Site, ...]
    receiver: Receiver
    model: str
    environment: str
    terrain: bool
    power_dbm: np.ndarray  # shape (n_sites, rows, cols)

    @property
    def best_power_dbm(self) -> np.ndarray:
        return self.power_dbm.max(axis=0)

    @property
    def covered(self) -> np.ndarray:
        return self.best_power_dbm >= self.receiver.threshold_dbm

    @property
    def best_server(self) -> np.ndarray:
        """Index of the strongest site per pixel, -1 where there is no coverage."""
        return np.where(self.covered, self.power_dbm.argmax(axis=0), -1)

    @property
    def area_km2(self) -> float:
        return float(self.grid.pixel_area_km2().sum())

    @property
    def covered_area_km2(self) -> float:
        return float(self.grid.pixel_area_km2()[self.covered].sum())

    @property
    def covered_fraction(self) -> float:
        return self.covered_area_km2 / self.area_km2

    def served_area_km2(self) -> list[float]:
        areas = self.grid.pixel_area_km2()
        server = self.best_server
        return [float(areas[server == i].sum()) for i in range(len(self.sites))]

    def model_label(self, site: Site) -> str:
        return get_model(self.model, site.frequency_mhz).label


def compute_coverage(
    sites: list[Site] | tuple[Site, ...],
    receiver: Receiver,
    radius_km: float = 10.0,
    resolution_m: float = 100.0,
    model: str = "auto",
    environment: str = "urban",
    terrain: ElevationSource | None = None,
    terrain_samples: int = 48,
    grid: Grid | None = None,
) -> CoverageResult:
    """Predict the coverage of one or more sites."""
    if not sites:
        raise ValueError("At least one site is needed")
    for site in sites:
        get_model(model, site.frequency_mhz)  # fail early on an invalid model/frequency
    if grid is None:
        grid = grid_around([s.location for s in sites], radius_km, resolution_m)
    power = np.stack(
        [
            site_received_power_dbm(
                site, grid, receiver, model, environment, terrain, terrain_samples
            )
            for site in sites
        ]
    )
    return CoverageResult(
        grid=grid,
        sites=tuple(sites),
        receiver=receiver,
        model=model,
        environment=environment,
        terrain=terrain is not None,
        power_dbm=power,
    )
