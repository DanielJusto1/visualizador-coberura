"""Horizontal radiation pattern of a sector antenna.

3GPP TR 36.814 model: A(theta) = -min(12 * (theta / theta_3dB)^2, A_m)

where theta is the angle from the boresight (antenna azimuth), theta_3dB the
half-power beamwidth (typically 65° for a three-sector site) and A_m the
front-to-back ratio.
"""

import numpy as np

DEFAULT_BEAMWIDTH_DEG = 65.0
DEFAULT_FRONT_TO_BACK_DB = 25.0


def angle_off_boresight_deg(bearing_deg, azimuth_deg: float):
    """Absolute angle (0-180°) between a direction and the antenna azimuth."""
    return np.abs((np.asarray(bearing_deg) - azimuth_deg + 180.0) % 360.0 - 180.0)


def sector_attenuation_db(
    angle_deg,
    beamwidth_deg: float = DEFAULT_BEAMWIDTH_DEG,
    front_to_back_db: float = DEFAULT_FRONT_TO_BACK_DB,
):
    """Attenuation (dB, >= 0) relative to the boresight gain at ``angle_deg`` off-axis."""
    if not 0 < beamwidth_deg <= 360:
        raise ValueError(f"Beamwidth must be between 0 and 360 degrees, got {beamwidth_deg}")
    if front_to_back_db < 0:
        raise ValueError("Front-to-back ratio cannot be negative")
    angle = np.asarray(angle_deg, dtype=float)
    attenuation = np.minimum(12.0 * (angle / beamwidth_deg) ** 2, front_to_back_db)
    return float(attenuation) if attenuation.ndim == 0 else attenuation
