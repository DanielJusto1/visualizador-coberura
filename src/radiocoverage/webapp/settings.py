"""Plain data objects that describe what the user chose in the interface.

They are frozen (hashable), so Streamlit can cache computations keyed on them,
and they do not depend on Streamlit, so they are easy to test.
"""

from dataclasses import dataclass

from radiocoverage.bands import BANDS, Band
from radiocoverage.coverage import Receiver, Site
from radiocoverage.geo import GeoPoint
from radiocoverage.link_budget import LinkParameters


@dataclass(frozen=True)
class RadioSettings:
    band_key: str
    tx_power_dbm: float
    tx_gain_dbi: float
    tx_loss_db: float
    tx_height_m: float
    rx_height_m: float
    rx_gain_dbi: float
    rx_loss_db: float
    other_losses_db: float
    sensitivity_dbm: float
    margin_db: float
    model: str
    environment: str
    terrain: bool

    @property
    def band(self) -> Band:
        return BANDS[self.band_key]

    @property
    def band_label(self) -> str:
        return f"{self.band.technology} {self.band.name}"

    @property
    def frequency_mhz(self) -> float:
        return self.band.centre_mhz

    @property
    def eirp_dbm(self) -> float:
        return self.tx_power_dbm + self.tx_gain_dbi - self.tx_loss_db

    def link_parameters(self, distance_km: float, terrain_loss_db: float = 0.0) -> LinkParameters:
        return LinkParameters(
            frequency_mhz=self.frequency_mhz,
            distance_km=distance_km,
            tx_power_dbm=self.tx_power_dbm,
            rx_sensitivity_dbm=self.sensitivity_dbm,
            tx_antenna_gain_dbi=self.tx_gain_dbi,
            rx_antenna_gain_dbi=self.rx_gain_dbi,
            tx_cable_loss_db=self.tx_loss_db,
            rx_cable_loss_db=self.rx_loss_db,
            other_losses_db=self.other_losses_db,
            required_margin_db=self.margin_db,
            model=self.model,
            environment=self.environment,
            tx_height_m=self.tx_height_m,
            rx_height_m=self.rx_height_m,
            terrain_loss_db=terrain_loss_db,
        )

    def receiver(self) -> Receiver:
        return Receiver(
            sensitivity_dbm=self.sensitivity_dbm,
            height_m=self.rx_height_m,
            gain_dbi=self.rx_gain_dbi,
            loss_db=self.rx_loss_db,
            other_losses_db=self.other_losses_db,
            required_margin_db=self.margin_db,
        )

    def site(
        self, name: str, location: GeoPoint, azimuth_deg: float | None = None, beamwidth=65.0
    ) -> Site:
        return Site(
            name=name,
            location=location,
            frequency_mhz=self.frequency_mhz,
            tx_power_dbm=self.tx_power_dbm,
            tx_gain_dbi=self.tx_gain_dbi,
            tx_loss_db=self.tx_loss_db,
            height_m=self.tx_height_m,
            azimuth_deg=azimuth_deg,
            beamwidth_deg=beamwidth,
            band_name=self.band_label,
        )
