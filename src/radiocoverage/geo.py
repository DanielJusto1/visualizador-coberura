"""Geographic calculations on a spherical Earth.

The spherical model (mean radius 6371 km) is accurate to about 0.5 % against
the WGS84 ellipsoid, far better than the uncertainty of any propagation model.
"""

import math
from dataclasses import dataclass

EARTH_RADIUS_KM = 6371.0088
"""Mean Earth radius (IUGG), in km."""

# Approximate bounding boxes (lat_min, lat_max, lon_min, lon_max) of Spanish territory.
SPAIN_REGIONS: dict[str, tuple[float, float, float, float]] = {
    "Mainland Spain": (35.95, 43.9, -9.4, 3.35),
    "Balearic Islands": (38.6, 40.1, 1.1, 4.4),
    "Canary Islands": (27.5, 29.5, -18.3, -13.3),
    "Ceuta": (35.86, 35.93, -5.40, -5.26),
    "Melilla": (35.26, 35.33, -2.98, -2.91),
}


@dataclass(frozen=True)
class GeoPoint:
    """A location given by latitude and longitude in decimal degrees (WGS84)."""

    lat: float
    lon: float

    def __post_init__(self) -> None:
        if not -90.0 <= self.lat <= 90.0:
            raise ValueError(f"Latitude must be between -90 and 90 degrees, got {self.lat}")
        if not -180.0 <= self.lon <= 180.0:
            raise ValueError(f"Longitude must be between -180 and 180 degrees, got {self.lon}")

    def __str__(self) -> str:
        ns = "N" if self.lat >= 0 else "S"
        ew = "E" if self.lon >= 0 else "W"
        return f"{abs(self.lat):.5f}°{ns}, {abs(self.lon):.5f}°{ew}"


def is_in_spain(point: GeoPoint) -> bool:
    """True if ``point`` lies inside the approximate bounding area of Spain."""
    return any(
        lat_min <= point.lat <= lat_max and lon_min <= point.lon <= lon_max
        for lat_min, lat_max, lon_min, lon_max in SPAIN_REGIONS.values()
    )


def distance_km(a: GeoPoint, b: GeoPoint) -> float:
    """Great-circle distance between two points (haversine formula)."""
    lat1, lon1, lat2, lon2 = map(math.radians, (a.lat, a.lon, b.lat, b.lon))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(h)))


def bearing_deg(a: GeoPoint, b: GeoPoint) -> float:
    """Initial bearing (azimuth) from ``a`` to ``b``, clockwise from true north, 0-360°."""
    lat1, lon1, lat2, lon2 = map(math.radians, (a.lat, a.lon, b.lat, b.lon))
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return math.degrees(math.atan2(x, y)) % 360.0


def destination_point(start: GeoPoint, bearing: float, dist_km: float) -> GeoPoint:
    """Point reached travelling ``dist_km`` from ``start`` along ``bearing`` degrees."""
    lat1, lon1 = math.radians(start.lat), math.radians(start.lon)
    theta = math.radians(bearing)
    delta = dist_km / EARTH_RADIUS_KM
    lat2 = math.asin(
        math.sin(lat1) * math.cos(delta) + math.cos(lat1) * math.sin(delta) * math.cos(theta)
    )
    lon2 = lon1 + math.atan2(
        math.sin(theta) * math.sin(delta) * math.cos(lat1),
        math.cos(delta) - math.sin(lat1) * math.sin(lat2),
    )
    lon_deg = (math.degrees(lon2) + 540.0) % 360.0 - 180.0
    return GeoPoint(math.degrees(lat2), lon_deg)


def intermediate_point(a: GeoPoint, b: GeoPoint, fraction: float) -> GeoPoint:
    """Point at ``fraction`` (0 = a, 1 = b) of the great-circle path from ``a`` to ``b``."""
    if not 0.0 <= fraction <= 1.0:
        raise ValueError(f"fraction must be between 0 and 1, got {fraction}")
    total_km = distance_km(a, b)
    if total_km == 0.0:
        return a
    return destination_point(a, bearing_deg(a, b), total_km * fraction)
