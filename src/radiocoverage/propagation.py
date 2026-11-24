"""Propagation (path loss) models.

Implemented models:

* ``free-space``   Friis free-space loss. Clear line of sight, best case.
* ``okumura-hata`` Empirical model for 150-1500 MHz macro cells (Hata, 1980).
* ``cost231-hata`` COST-231 extension of Hata for 1500-2000 MHz.
* ``3gpp``         3GPP TR 38.901 NLOS models: Urban Macro (UMa) for urban and
                   suburban environments, Rural Macro (RMa) for rural ones.
* ``auto``         Picks the most suitable of the above for the frequency.

Every model accepts a scalar distance or a numpy array of distances, so the
same code computes a single link or a whole coverage grid. Empirical models are
never allowed to predict less loss than free space.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from radiocoverage.units import SPEED_OF_LIGHT_M_S

# 20*log10(4*pi / c) expressed for distance in km and frequency in MHz.
# Evaluates to ~32.45 dB, the constant found in textbooks.
_FSPL_CONSTANT_DB = 20.0 * math.log10(4.0 * math.pi * 1e3 * 1e6 / SPEED_OF_LIGHT_M_S)

ENVIRONMENTS = ("dense-urban", "urban", "suburban", "rural")
"""Environment classes understood by the empirical models."""

MIN_DISTANCE_KM = 0.01
"""Distances below 10 m are clamped to this value to avoid log(0) at the site."""

Distance = float | np.ndarray


def _check_positive(name: str, value: float, unit: str) -> None:
    if not value > 0 or math.isinf(value):
        raise ValueError(f"{name} must be a positive finite number, got {value} {unit}")


def _check_distance(distance_km: Distance) -> np.ndarray:
    d = np.asarray(distance_km, dtype=float)
    if not np.all(np.isfinite(d)) or np.any(d <= 0):
        raise ValueError(f"Distance must be a positive finite number, got {distance_km} km")
    return d


def _same_type(result: np.ndarray, like: Distance) -> Distance:
    return float(result) if np.ndim(like) == 0 else result


def free_space_path_loss_db(distance_km: Distance, frequency_mhz: float) -> Distance:
    """Free-space path loss in dB.

    FSPL = 20*log10(d_km) + 20*log10(f_MHz) + 32.45

    Equivalent to (4*pi*d / lambda)^2 in linear terms. Valid in the far field
    (distance much larger than the wavelength) with a clear line of sight.
    """
    d = _check_distance(distance_km)
    _check_positive("Frequency", frequency_mhz, "MHz")
    loss = 20.0 * np.log10(d) + 20.0 * math.log10(frequency_mhz) + _FSPL_CONSTANT_DB
    return _same_type(loss, distance_km)


def free_space_distance_km(path_loss_db: float, frequency_mhz: float) -> float:
    """Distance in km at which free-space loss equals ``path_loss_db``.

    Inverse of :func:`free_space_path_loss_db`; used to estimate maximum range.
    """
    _check_positive("Frequency", frequency_mhz, "MHz")
    exponent = (path_loss_db - _FSPL_CONSTANT_DB - 20.0 * math.log10(frequency_mhz)) / 20.0
    return 10.0**exponent


# --- Okumura-Hata family -------------------------------------------------------------


def _mobile_height_correction_db(frequency_mhz: float, rx_height_m: float, large_city: bool):
    """Correction factor a(h_m) of the Hata model."""
    log_f = math.log10(frequency_mhz)
    if large_city:
        if frequency_mhz <= 300:
            return 8.29 * math.log10(1.54 * rx_height_m) ** 2 - 1.1
        return 3.2 * math.log10(11.75 * rx_height_m) ** 2 - 4.97
    return (1.1 * log_f - 0.7) * rx_height_m - (1.56 * log_f - 0.8)


def _environment_correction_db(frequency_mhz: float, environment: str) -> float:
    """Hata corrections from urban to suburban and open (rural) areas."""
    log_f = math.log10(frequency_mhz)
    if environment == "suburban":
        return -2.0 * math.log10(frequency_mhz / 28.0) ** 2 - 5.4
    if environment == "rural":
        return -4.78 * log_f**2 + 18.33 * log_f - 40.94
    return 0.0


def okumura_hata_db(
    distance_km: Distance,
    frequency_mhz: float,
    tx_height_m: float,
    rx_height_m: float,
    environment: str = "urban",
) -> Distance:
    """Okumura-Hata median path loss (150-1500 MHz)."""
    d = _check_distance(distance_km)
    log_hb = math.log10(tx_height_m)
    a_hm = _mobile_height_correction_db(
        frequency_mhz, rx_height_m, large_city=environment == "dense-urban"
    )
    loss = (
        69.55
        + 26.16 * math.log10(frequency_mhz)
        - 13.82 * log_hb
        - a_hm
        + (44.9 - 6.55 * log_hb) * np.log10(d)
        + _environment_correction_db(frequency_mhz, environment)
    )
    return _same_type(loss, distance_km)


def cost231_hata_db(
    distance_km: Distance,
    frequency_mhz: float,
    tx_height_m: float,
    rx_height_m: float,
    environment: str = "urban",
) -> Distance:
    """COST-231 Hata median path loss (1500-2000 MHz)."""
    d = _check_distance(distance_km)
    log_hb = math.log10(tx_height_m)
    dense = environment == "dense-urban"
    a_hm = _mobile_height_correction_db(frequency_mhz, rx_height_m, large_city=dense)
    loss = (
        46.3
        + 33.9 * math.log10(frequency_mhz)
        - 13.82 * log_hb
        - a_hm
        + (44.9 - 6.55 * log_hb) * np.log10(d)
        + (3.0 if dense else 0.0)
        + _environment_correction_db(frequency_mhz, environment)
    )
    return _same_type(loss, distance_km)


# --- 3GPP TR 38.901 ------------------------------------------------------------------


def _distance_3d_m(distance_km: np.ndarray, tx_height_m: float, rx_height_m: float):
    d2d = np.maximum(distance_km * 1000.0, MIN_DISTANCE_KM * 1000.0)
    return d2d, np.sqrt(d2d**2 + (tx_height_m - rx_height_m) ** 2)


def uma_nlos_db(
    distance_km: Distance, frequency_mhz: float, tx_height_m: float, rx_height_m: float
) -> Distance:
    """3GPP TR 38.901 Urban Macro (UMa) NLOS path loss."""
    d = _check_distance(distance_km)
    fc_ghz = frequency_mhz / 1000.0
    d2d, d3d = _distance_3d_m(d, tx_height_m, rx_height_m)
    breakpoint_m = (
        4.0 * (tx_height_m - 1.0) * (rx_height_m - 1.0) * fc_ghz * 1e9 / SPEED_OF_LIGHT_M_S
    )
    los_near = 28.0 + 22.0 * np.log10(d3d) + 20.0 * math.log10(fc_ghz)
    los_far = (
        28.0
        + 40.0 * np.log10(d3d)
        + 20.0 * math.log10(fc_ghz)
        - 9.0 * math.log10(breakpoint_m**2 + (tx_height_m - rx_height_m) ** 2)
    )
    los = np.where(d2d <= breakpoint_m, los_near, los_far)
    nlos = 13.54 + 39.08 * np.log10(d3d) + 20.0 * math.log10(fc_ghz) - 0.6 * (rx_height_m - 1.5)
    return _same_type(np.maximum(los, nlos), distance_km)


def rma_nlos_db(
    distance_km: Distance,
    frequency_mhz: float,
    tx_height_m: float,
    rx_height_m: float,
    building_height_m: float = 5.0,
    street_width_m: float = 20.0,
) -> Distance:
    """3GPP TR 38.901 Rural Macro (RMa) NLOS path loss."""
    d = _check_distance(distance_km)
    fc_ghz = frequency_mhz / 1000.0
    h, w = building_height_m, street_width_m
    d2d, d3d = _distance_3d_m(d, tx_height_m, rx_height_m)
    breakpoint_m = 2.0 * math.pi * tx_height_m * rx_height_m * fc_ghz * 1e9 / SPEED_OF_LIGHT_M_S

    def los_near(dist_m):
        return (
            20.0 * np.log10(40.0 * math.pi * dist_m * fc_ghz / 3.0)
            + min(0.03 * h**1.72, 10.0) * np.log10(dist_m)
            - min(0.044 * h**1.72, 14.77)
            + 0.002 * math.log10(h) * dist_m
        )

    los_far = los_near(breakpoint_m) + 40.0 * np.log10(d3d / breakpoint_m)
    los = np.where(d2d <= breakpoint_m, los_near(d3d), los_far)
    log_hb = math.log10(tx_height_m)
    nlos = (
        161.04
        - 7.1 * math.log10(w)
        + 7.5 * math.log10(h)
        - (24.37 - 3.7 * (h / tx_height_m) ** 2) * log_hb
        + (43.42 - 3.1 * log_hb) * (np.log10(d3d) - 3.0)
        + 20.0 * math.log10(fc_ghz)
        - (3.2 * math.log10(11.75 * rx_height_m) ** 2 - 4.97)
    )
    return _same_type(np.maximum(los, nlos), distance_km)


def three_gpp_db(
    distance_km: Distance,
    frequency_mhz: float,
    tx_height_m: float,
    rx_height_m: float,
    environment: str = "urban",
) -> Distance:
    """3GPP TR 38.901: RMa in rural environments, UMa elsewhere."""
    if environment == "rural":
        return rma_nlos_db(distance_km, frequency_mhz, tx_height_m, rx_height_m)
    return uma_nlos_db(distance_km, frequency_mhz, tx_height_m, rx_height_m)


# --- Model registry ------------------------------------------------------------------


@dataclass(frozen=True)
class PropagationModel:
    key: str
    label: str
    frequency_range_mhz: tuple[float, float]
    distance_range_km: tuple[float, float]
    tx_height_range_m: tuple[float, float]
    rx_height_range_m: tuple[float, float]
    function: Callable[..., Distance]
    reference: str

    def validity_warnings(
        self, distance_km: float, tx_height_m: float, rx_height_m: float
    ) -> list[str]:
        """Human readable notes when a link is outside the model's validity range."""
        checks = (
            ("distance", distance_km, self.distance_range_km, "km"),
            ("base station height", tx_height_m, self.tx_height_range_m, "m"),
            ("receiver height", rx_height_m, self.rx_height_range_m, "m"),
        )
        return [
            f"{self.label}: {name} {value:.4g} {unit} is outside the validity range "
            f"{low:g}-{high:g} {unit}"
            for name, value, (low, high), unit in checks
            if not low <= value <= high
        ]


def _free_space_model(distance_km, frequency_mhz, tx_height_m, rx_height_m, environment):
    return free_space_path_loss_db(distance_km, frequency_mhz)


MODELS: dict[str, PropagationModel] = {
    model.key: model
    for model in (
        PropagationModel(
            "free-space",
            "Free space (Friis)",
            (1.0, 1e6),
            (0.0, math.inf),
            (0.0, math.inf),
            (0.0, math.inf),
            _free_space_model,
            "ITU-R P.525",
        ),
        PropagationModel(
            "okumura-hata",
            "Okumura-Hata",
            (150.0, 1500.0),
            (1.0, 20.0),
            (30.0, 200.0),
            (1.0, 10.0),
            okumura_hata_db,
            "Hata, IEEE Trans. Veh. Technol., 1980",
        ),
        PropagationModel(
            "cost231-hata",
            "COST-231 Hata",
            (1500.0, 2000.0),
            (1.0, 20.0),
            (30.0, 200.0),
            (1.0, 10.0),
            cost231_hata_db,
            "COST Action 231 final report, 1999",
        ),
        PropagationModel(
            "3gpp",
            "3GPP TR 38.901 (UMa/RMa NLOS)",
            (500.0, 7000.0),
            (0.01, 5.0),
            (10.0, 150.0),
            (1.0, 22.5),
            three_gpp_db,
            "3GPP TR 38.901, Table 7.4.1-1",
        ),
    )
}

MODEL_CHOICES = ("auto", *MODELS)


def auto_model_key(frequency_mhz: float) -> str:
    """Most suitable empirical model for a carrier frequency."""
    if frequency_mhz < 1500.0:
        return "okumura-hata"
    if frequency_mhz <= 2000.0:
        return "cost231-hata"
    return "3gpp"


def get_model(key: str, frequency_mhz: float) -> PropagationModel:
    """Resolve a model name (``auto`` included) and check the frequency range."""
    if key == "auto":
        key = auto_model_key(frequency_mhz)
    try:
        model = MODELS[key]
    except KeyError:
        raise ValueError(
            f"Unknown propagation model '{key}'. Available: {', '.join(MODEL_CHOICES)}"
        ) from None
    low, high = model.frequency_range_mhz
    if not low <= frequency_mhz <= high:
        raise ValueError(
            f"{model.label} is only valid from {low:g} to {high:g} MHz, "
            f"not {frequency_mhz:g} MHz (try --model auto)"
        )
    return model


def path_loss_db(
    model_key: str,
    distance_km: Distance,
    frequency_mhz: float,
    tx_height_m: float = 30.0,
    rx_height_m: float = 1.5,
    environment: str = "urban",
) -> Distance:
    """Path loss in dB for any registered model, never below free-space loss."""
    if environment not in ENVIRONMENTS:
        raise ValueError(
            f"Unknown environment '{environment}'. Available: {', '.join(ENVIRONMENTS)}"
        )
    _check_positive("Base station height", tx_height_m, "m")
    _check_positive("Receiver height", rx_height_m, "m")
    model = get_model(model_key, frequency_mhz)
    d = np.maximum(_check_distance(distance_km), MIN_DISTANCE_KM)
    free_space = free_space_path_loss_db(d, frequency_mhz)
    if model.key == "free-space":
        loss = free_space
    else:
        loss = np.maximum(
            model.function(d, frequency_mhz, tx_height_m, rx_height_m, environment), free_space
        )
    return _same_type(np.asarray(loss), distance_km)


def max_distance_km(
    model_key: str,
    allowed_loss_db: float,
    frequency_mhz: float,
    tx_height_m: float = 30.0,
    rx_height_m: float = 1.5,
    environment: str = "urban",
    upper_limit_km: float = 2000.0,
) -> float:
    """Largest distance whose path loss does not exceed ``allowed_loss_db``.

    Returns ``math.inf`` beyond ``upper_limit_km`` and 0 if even the shortest
    distance exceeds the allowed loss. Path loss grows with distance in every
    model, so a bisection on log-distance is enough.
    """
    if get_model(model_key, frequency_mhz).key == "free-space":
        return free_space_distance_km(allowed_loss_db, frequency_mhz)

    def loss(d_km: float) -> float:
        return float(
            path_loss_db(model_key, d_km, frequency_mhz, tx_height_m, rx_height_m, environment)
        )

    low, high = MIN_DISTANCE_KM, upper_limit_km
    if loss(high) <= allowed_loss_db:
        return math.inf
    if loss(low) > allowed_loss_db:
        return 0.0
    for _ in range(60):
        mid = math.sqrt(low * high)
        if loss(mid) <= allowed_loss_db:
            low = mid
        else:
            high = mid
    return low
