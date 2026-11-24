"""Point-to-point link budget.

EIRP          = P_tx + G_tx - L_tx
P_rx          = EIRP - path_loss - L_terrain - L_other + G_rx - L_rx
Margin        = P_rx - Sensitivity
Link is viable when Margin >= required margin (fade margin).
"""

import math
from dataclasses import dataclass

from radiocoverage.propagation import (
    ENVIRONMENTS,
    get_model,
    max_distance_km,
    path_loss_db,
)


def eirp_dbm(tx_power_dbm: float, tx_gain_dbi: float, tx_loss_db: float) -> float:
    """Effective isotropic radiated power."""
    return tx_power_dbm + tx_gain_dbi - tx_loss_db


@dataclass(frozen=True)
class LinkParameters:
    frequency_mhz: float
    distance_km: float
    tx_power_dbm: float
    rx_sensitivity_dbm: float
    tx_antenna_gain_dbi: float = 0.0
    rx_antenna_gain_dbi: float = 0.0
    tx_cable_loss_db: float = 0.0
    rx_cable_loss_db: float = 0.0
    other_losses_db: float = 0.0
    required_margin_db: float = 0.0
    model: str = "free-space"
    environment: str = "urban"
    tx_height_m: float = 30.0
    rx_height_m: float = 1.5
    terrain_loss_db: float = 0.0

    def __post_init__(self) -> None:
        for name in ("frequency_mhz", "distance_km", "tx_height_m", "rx_height_m"):
            value = getattr(self, name)
            if not value > 0 or math.isinf(value):
                raise ValueError(f"{name} must be a positive finite number, got {value}")
        for name in ("tx_cable_loss_db", "rx_cable_loss_db", "other_losses_db", "terrain_loss_db"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} is a loss and cannot be negative")
        if self.required_margin_db < 0:
            raise ValueError("required_margin_db cannot be negative")
        if self.environment not in ENVIRONMENTS:
            raise ValueError(
                f"Unknown environment '{self.environment}'. Available: {', '.join(ENVIRONMENTS)}"
            )
        get_model(self.model, self.frequency_mhz)  # validates name and frequency range


@dataclass(frozen=True)
class LinkBudgetResult:
    parameters: LinkParameters
    model_key: str
    eirp_dbm: float
    path_loss_db: float
    rx_power_dbm: float
    margin_db: float
    max_distance_km: float
    warnings: tuple[str, ...] = ()

    @property
    def is_viable(self) -> bool:
        return self.margin_db >= self.parameters.required_margin_db

    @property
    def model_label(self) -> str:
        return get_model(self.model_key, self.parameters.frequency_mhz).label


def compute_link_budget(params: LinkParameters) -> LinkBudgetResult:
    """Compute the link budget for ``params`` with the selected propagation model."""
    model = get_model(params.model, params.frequency_mhz)
    eirp = eirp_dbm(params.tx_power_dbm, params.tx_antenna_gain_dbi, params.tx_cable_loss_db)
    loss = float(
        path_loss_db(
            model.key,
            params.distance_km,
            params.frequency_mhz,
            params.tx_height_m,
            params.rx_height_m,
            params.environment,
        )
    )
    rx_power = (
        eirp
        - loss
        - params.terrain_loss_db
        - params.other_losses_db
        + params.rx_antenna_gain_dbi
        - params.rx_cable_loss_db
    )
    margin = rx_power - params.rx_sensitivity_dbm

    # Largest model path loss the link tolerates while keeping the required margin
    # (terrain losses are specific to this path, so they are not extrapolated).
    max_loss = loss + params.terrain_loss_db + margin - params.required_margin_db
    max_range = max_distance_km(
        model.key,
        max_loss,
        params.frequency_mhz,
        params.tx_height_m,
        params.rx_height_m,
        params.environment,
    )
    warnings = tuple(
        model.validity_warnings(params.distance_km, params.tx_height_m, params.rx_height_m)
    )

    return LinkBudgetResult(
        parameters=params,
        model_key=model.key,
        eirp_dbm=eirp,
        path_loss_db=loss,
        rx_power_dbm=rx_power,
        margin_db=margin,
        max_distance_km=max_range,
        warnings=warnings,
    )
