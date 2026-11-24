"""Unit conversions used throughout radio link calculations.

Every quantity carries its unit in the variable name (``_dbm``, ``_mhz``, ``_km``)
to avoid mixing scales, which is the most common source of errors in RF work.
"""

import math

SPEED_OF_LIGHT_M_S = 299_792_458.0
"""Speed of light in vacuum, in metres per second (exact by definition)."""

BOLTZMANN_J_K = 1.380649e-23
"""Boltzmann constant, in joules per kelvin (exact by definition)."""

REFERENCE_TEMPERATURE_K = 290.0
"""Standard reference temperature for noise calculations (ITU-R / IEEE)."""


def db_to_linear(value_db: float) -> float:
    """Convert a power ratio in dB to a linear ratio."""
    return 10.0 ** (value_db / 10.0)


def linear_to_db(ratio: float) -> float:
    """Convert a linear power ratio to dB."""
    if ratio <= 0:
        raise ValueError(f"Power ratio must be positive, got {ratio}")
    return 10.0 * math.log10(ratio)


def dbm_to_mw(power_dbm: float) -> float:
    """Convert power in dBm to milliwatts."""
    return db_to_linear(power_dbm)


def mw_to_dbm(power_mw: float) -> float:
    """Convert power in milliwatts to dBm."""
    if power_mw <= 0:
        raise ValueError(f"Power must be positive, got {power_mw} mW")
    return linear_to_db(power_mw)


def dbm_to_w(power_dbm: float) -> float:
    """Convert power in dBm to watts."""
    return dbm_to_mw(power_dbm) / 1000.0


def w_to_dbm(power_w: float) -> float:
    """Convert power in watts to dBm."""
    if power_w <= 0:
        raise ValueError(f"Power must be positive, got {power_w} W")
    return mw_to_dbm(power_w * 1000.0)


def wavelength_m(frequency_mhz: float) -> float:
    """Wavelength in metres for a frequency in MHz (lambda = c / f)."""
    if frequency_mhz <= 0:
        raise ValueError(f"Frequency must be positive, got {frequency_mhz} MHz")
    return SPEED_OF_LIGHT_M_S / (frequency_mhz * 1e6)
