"""Receiver sensitivity from thermal noise.

Sensitivity = -174 dBm/Hz + 10*log10(B) + NF + SNR_min

where -174 dBm/Hz is the thermal noise density kT at 290 K, B the occupied
bandwidth in Hz, NF the receiver noise figure and SNR_min the minimum
signal-to-noise ratio the demodulator needs.
"""

import math

from radiocoverage.units import BOLTZMANN_J_K, REFERENCE_TEMPERATURE_K, mw_to_dbm

THERMAL_NOISE_DENSITY_DBM_HZ = mw_to_dbm(BOLTZMANN_J_K * REFERENCE_TEMPERATURE_K * 1000.0)
"""kT at 290 K in dBm/Hz (about -173.98)."""


def thermal_noise_dbm(bandwidth_mhz: float) -> float:
    """Thermal noise power kTB in dBm over ``bandwidth_mhz``."""
    if not bandwidth_mhz > 0 or math.isinf(bandwidth_mhz):
        raise ValueError(f"Bandwidth must be a positive finite number, got {bandwidth_mhz} MHz")
    return THERMAL_NOISE_DENSITY_DBM_HZ + 10.0 * math.log10(bandwidth_mhz * 1e6)


def sensitivity_dbm(bandwidth_mhz: float, noise_figure_db: float, required_snr_db: float) -> float:
    """Minimum received power (dBm) for the receiver to demodulate the signal."""
    if noise_figure_db < 0:
        raise ValueError(f"Noise figure cannot be negative, got {noise_figure_db} dB")
    return thermal_noise_dbm(bandwidth_mhz) + noise_figure_db + required_snr_db
