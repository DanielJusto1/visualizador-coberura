"""Geometry of a radio path between two geographic points."""

from dataclasses import dataclass

from radiocoverage.fresnel import (
    CLEARANCE_RATIO,
    STANDARD_K_FACTOR,
    earth_bulge_m,
    fresnel_radius_m,
)
from radiocoverage.geo import (
    GeoPoint,
    bearing_deg,
    destination_point,
    distance_km,
    intermediate_point,
)


@dataclass(frozen=True)
class LinkPath:
    tx: GeoPoint
    rx: GeoPoint
    frequency_mhz: float

    def __post_init__(self) -> None:
        if self.tx == self.rx or self.distance_km == 0.0:
            raise ValueError("Transmitter and receiver must be at different locations")

    @property
    def distance_km(self) -> float:
        return distance_km(self.tx, self.rx)

    @property
    def bearing_deg(self) -> float:
        """Azimuth from the transmitter towards the receiver."""
        return bearing_deg(self.tx, self.rx)

    @property
    def reverse_bearing_deg(self) -> float:
        """Azimuth from the receiver towards the transmitter."""
        return bearing_deg(self.rx, self.tx)

    @property
    def midpoint(self) -> GeoPoint:
        return intermediate_point(self.tx, self.rx, 0.5)

    @property
    def fresnel_radius_midpoint_m(self) -> float:
        """Radius of the first Fresnel zone at mid-path, where it is widest."""
        half = self.distance_km / 2.0
        return fresnel_radius_m(half, half, self.frequency_mhz)

    @property
    def clearance_midpoint_m(self) -> float:
        """Free height needed above obstacles at mid-path (60 % of the first zone)."""
        return CLEARANCE_RATIO * self.fresnel_radius_midpoint_m

    def earth_bulge_midpoint_m(self, k_factor: float = STANDARD_K_FACTOR) -> float:
        half = self.distance_km / 2.0
        return earth_bulge_m(half, half, k_factor)

    def fresnel_outline(self, samples: int = 64) -> list[GeoPoint]:
        """Closed outline of the first Fresnel zone seen from above (for maps)."""
        if samples < 2:
            raise ValueError("At least 2 samples are needed")
        total_km = self.distance_km
        centre_line = [
            intermediate_point(self.tx, self.rx, i / samples) for i in range(samples + 1)
        ]
        left: list[GeoPoint] = []
        right: list[GeoPoint] = []
        for i, point in enumerate(centre_line):
            d1 = total_km * i / samples
            d2 = total_km - d1
            radius_km = fresnel_radius_m(d1, d2, self.frequency_mhz) / 1000.0
            if i < samples:
                heading = bearing_deg(point, self.rx)
            else:
                heading = bearing_deg(centre_line[i - 1], point)
            left.append(destination_point(point, heading - 90.0, radius_km))
            right.append(destination_point(point, heading + 90.0, radius_km))
        return left + right[::-1] + [left[0]]
