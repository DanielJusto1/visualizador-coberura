"""LTE and 5G NR frequency bands deployed in Spain.

Frequencies are the downlink (base station to phone) ranges. The centre
frequency is used for path loss calculations.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Band:
    name: str
    technology: str
    downlink_low_mhz: float
    downlink_high_mhz: float
    typical_use: str

    @property
    def centre_mhz(self) -> float:
        return (self.downlink_low_mhz + self.downlink_high_mhz) / 2.0

    @property
    def width_mhz(self) -> float:
        return self.downlink_high_mhz - self.downlink_low_mhz


BANDS: dict[str, Band] = {
    band.name.lower(): band
    for band in (
        Band("n28", "5G NR", 758.0, 788.0, "700 MHz, rural and indoor 5G coverage"),
        Band("B20", "LTE", 791.0, 821.0, "800 MHz, rural and indoor coverage"),
        Band("B8", "LTE", 925.0, 960.0, "900 MHz, rural coverage (also GSM/UMTS)"),
        Band("B3", "LTE", 1805.0, 1880.0, "1800 MHz, main capacity layer"),
        Band("B1", "LTE", 2110.0, 2170.0, "2100 MHz, urban capacity (also UMTS)"),
        Band("B7", "LTE", 2620.0, 2690.0, "2600 MHz, dense urban capacity"),
        Band("n78", "5G NR", 3400.0, 3800.0, "3.5 GHz, main 5G capacity band"),
    )
}


def get_band(name: str) -> Band:
    """Look up a band by name, case-insensitive (e.g. ``"b20"`` or ``"n78"``)."""
    try:
        return BANDS[name.lower()]
    except KeyError:
        available = ", ".join(b.name for b in BANDS.values())
        raise ValueError(f"Unknown band '{name}'. Available bands: {available}") from None
