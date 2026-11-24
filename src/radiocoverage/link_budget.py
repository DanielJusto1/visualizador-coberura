"""Point-to-point link budget.

EIRP          = P_tx + G_tx - L_tx
P_rx          = EIRP - path_loss - L_other + G_rx - L_rx
Margin        = P_rx - Sensitivity
Link is viable when Margin >= required margin (fade margin).
"""

import math
from dataclasses import dataclass

from radiocoverage.propagation import free_space_distance_km, free_space_path_loss_db


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

    def __post_init__(self) -> None:
        for name in ("frequency_mhz", "distance_km"):
            value = getattr(self, name)
            if not value > 0 or math.isinf(value):
                raise ValueError(f"{name} must be a positive finite number, got {value}")
        for name in ("tx_cable_loss_db", "rx_cable_loss_db", "other_losses_db"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} is a loss and cannot be negative")
        if self.required_margin_db < 0:
            raise ValueError("required_margin_db cannot be negative")


@dataclass(frozen=True)
class LinkBudgetResult:
    parameters: LinkParameters
    eirp_dbm: float
    path_loss_db: float
    rx_power_dbm: float
    margin_db: float
    max_distance_km: float

    @property
    def is_viable(self) -> bool:
        return self.margin_db >= self.parameters.required_margin_db


def compute_link_budget(params: LinkParameters) -> LinkBudgetResult:
    """Compute the free-space link budget for ``params``."""
    eirp_dbm = params.tx_power_dbm + params.tx_antenna_gain_dbi - params.tx_cable_loss_db
    path_loss_db = free_space_path_loss_db(params.distance_km, params.frequency_mhz)
    rx_power_dbm = (
        eirp_dbm
        - path_loss_db
        - params.other_losses_db
        + params.rx_antenna_gain_dbi
        - params.rx_cable_loss_db
    )
    margin_db = rx_power_dbm - params.rx_sensitivity_dbm

    # Largest path loss the link tolerates while keeping the required margin.
    max_path_loss_db = path_loss_db + margin_db - params.required_margin_db
    max_distance_km = free_space_distance_km(max_path_loss_db, params.frequency_mhz)

    return LinkBudgetResult(
        parameters=params,
        eirp_dbm=eirp_dbm,
        path_loss_db=path_loss_db,
        rx_power_dbm=rx_power_dbm,
        margin_db=margin_db,
        max_distance_km=max_distance_km,
    )
