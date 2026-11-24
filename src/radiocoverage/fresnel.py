"""Fresnel zones and Earth curvature.

The first Fresnel zone is the ellipsoid around the line of sight that carries
most of the radio energy. A link is considered clear of obstacles when at
least 60 % of it is free.
"""

import math

from radiocoverage.geo import EARTH_RADIUS_KM
from radiocoverage.units import wavelength_m

STANDARD_K_FACTOR = 4.0 / 3.0
"""Effective Earth radius factor for a standard atmosphere (ITU-R P.453)."""

CLEARANCE_RATIO = 0.6
"""Fraction of the first Fresnel zone that must be clear of obstacles."""


def fresnel_radius_m(d1_km: float, d2_km: float, frequency_mhz: float, zone: int = 1) -> float:
    """Radius of the n-th Fresnel zone at a point ``d1_km`` from Tx and ``d2_km`` from Rx.

    r_n = sqrt(n * lambda * d1 * d2 / (d1 + d2))
    """
    if d1_km < 0 or d2_km < 0:
        raise ValueError("Distances to the ends of the link cannot be negative")
    if d1_km + d2_km == 0:
        raise ValueError("The link must have a non-zero length")
    if zone < 1:
        raise ValueError(f"Fresnel zone number must be 1 or more, got {zone}")
    d1_m, d2_m = d1_km * 1000.0, d2_km * 1000.0
    return math.sqrt(zone * wavelength_m(frequency_mhz) * d1_m * d2_m / (d1_m + d2_m))


def earth_bulge_m(d1_km: float, d2_km: float, k_factor: float = STANDARD_K_FACTOR) -> float:
    """Height of the Earth's curvature above the Tx-Rx chord, in metres.

    h = d1 * d2 / (2 * k * R). Atmospheric refraction bends radio waves
    downwards, which is modelled as a larger Earth radius k * R.
    """
    if d1_km < 0 or d2_km < 0:
        raise ValueError("Distances to the ends of the link cannot be negative")
    if k_factor <= 0:
        raise ValueError(f"k factor must be positive, got {k_factor}")
    return d1_km * d2_km * 1000.0 / (2.0 * k_factor * EARTH_RADIUS_KM)
