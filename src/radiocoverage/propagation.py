"""Propagation (path loss) models.

Phase 1 implements free-space path loss (Friis). Empirical models such as
Okumura-Hata and COST-231 will be added here in later phases.
"""

import math

from radiocoverage.units import SPEED_OF_LIGHT_M_S

# 20*log10(4*pi / c) expressed for distance in km and frequency in MHz.
# Evaluates to ~32.45 dB, the constant found in textbooks.
_FSPL_CONSTANT_DB = 20.0 * math.log10(4.0 * math.pi * 1e3 * 1e6 / SPEED_OF_LIGHT_M_S)


def _check_positive(name: str, value: float, unit: str) -> None:
    if not value > 0 or math.isinf(value):
        raise ValueError(f"{name} must be a positive finite number, got {value} {unit}")


def free_space_path_loss_db(distance_km: float, frequency_mhz: float) -> float:
    """Free-space path loss in dB.

    FSPL = 20*log10(d_km) + 20*log10(f_MHz) + 32.45

    Equivalent to (4*pi*d / lambda)^2 in linear terms. Valid in the far field
    (distance much larger than the wavelength) with a clear line of sight.
    """
    _check_positive("Distance", distance_km, "km")
    _check_positive("Frequency", frequency_mhz, "MHz")
    return 20.0 * math.log10(distance_km) + 20.0 * math.log10(frequency_mhz) + _FSPL_CONSTANT_DB


def free_space_distance_km(path_loss_db: float, frequency_mhz: float) -> float:
    """Distance in km at which free-space loss equals ``path_loss_db``.

    Inverse of :func:`free_space_path_loss_db`; used to estimate maximum range.
    """
    _check_positive("Frequency", frequency_mhz, "MHz")
    exponent = (path_loss_db - _FSPL_CONSTANT_DB - 20.0 * math.log10(frequency_mhz)) / 20.0
    return 10.0**exponent
