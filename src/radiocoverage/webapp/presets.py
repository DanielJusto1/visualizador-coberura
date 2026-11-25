"""Ready-made values for the web interface: places, band profiles and example networks."""

from dataclasses import dataclass

from radiocoverage.bands import BANDS

SPAIN_VIEW = ((40.2, -3.7), 6)
"""Map centre and zoom that show the Iberian Peninsula and the Balearic Islands."""

# name: (lat, lon, zoom)
PLACES: dict[str, tuple[float, float, int]] = {
    "Madrid · Puerta del Sol": (40.4169, -3.7035, 14),
    "Madrid · Torrespaña": (40.4233, -3.6714, 14),
    "Barcelona · Plaça de Catalunya": (41.3870, 2.1701, 14),
    "Valencia · Plaza del Ayuntamiento": (39.4699, -0.3763, 14),
    "Sevilla · Catedral": (37.3858, -5.9931, 14),
    "Zaragoza · Plaza del Pilar": (41.6563, -0.8786, 14),
    "Málaga · Centro": (36.7213, -4.4214, 14),
    "Bilbao · Guggenheim": (43.2687, -2.9340, 14),
    "A Coruña · Torre de Hércules": (43.3859, -8.4065, 13),
    "Palma · Catedral": (39.5675, 2.6483, 14),
    "Las Palmas de Gran Canaria": (28.1235, -15.4363, 13),
    "Santa Cruz de Tenerife": (28.4636, -16.2518, 13),
    "Segovia · Plaza Mayor": (40.9481, -4.1253, 13),
    "Sierra de Guadarrama · Bola del Mundo": (40.7930, -3.9620, 12),
    "Granada · Alhambra": (37.1761, -3.5881, 13),
    "Sierra Nevada · Pico Veleta": (37.0564, -3.3660, 12),
    "Picos de Europa · Fuente Dé": (43.1440, -4.8120, 12),
}


@dataclass(frozen=True)
class BandProfile:
    """Typical base station and receiver values for a band."""

    tx_power_dbm: float
    tx_gain_dbi: float
    tx_height_m: float
    bandwidth_mhz: float
    noise_figure_db: float
    snr_db: float
    environment: str


BAND_PROFILES: dict[str, BandProfile] = {
    "n28": BandProfile(46.0, 15.0, 30.0, 10.0, 7.0, -1.0, "rural"),
    "b20": BandProfile(46.0, 17.0, 30.0, 10.0, 9.0, -1.0, "rural"),
    "b8": BandProfile(46.0, 17.0, 30.0, 10.0, 9.0, -1.0, "rural"),
    "b3": BandProfile(46.0, 18.0, 30.0, 20.0, 9.0, -1.0, "urban"),
    "b1": BandProfile(46.0, 18.0, 30.0, 15.0, 9.0, -1.0, "urban"),
    "b7": BandProfile(46.0, 18.0, 25.0, 20.0, 9.0, -1.0, "urban"),
    "n78": BandProfile(49.0, 24.0, 25.0, 100.0, 7.0, -3.0, "urban"),
}

# Extra loss depending on where the terminal is (typical planning values).
TERMINAL_LOCATIONS: dict[str, float] = {"outdoor": 0.0, "vehicle": 8.0, "indoor": 15.0}

BAND_KEYS = list(BANDS)
"""Band keys in frequency order (``n28``, ``b20`` ... ``n78``)."""


@dataclass(frozen=True)
class ExampleNetwork:
    band_key: str
    environment: str
    terrain: bool
    radius_km: float
    resolution_m: int
    # (name, lat, lon, azimuth or None)
    sites: tuple[tuple[str, float, float, float | None], ...]


def _sectors(name: str, lat: float, lon: float, first_azimuth: float):
    return tuple((f"{name} S{i + 1}", lat, lon, (first_azimuth + 120 * i) % 360) for i in range(3))


EXAMPLE_NETWORKS: dict[str, ExampleNetwork] = {
    "madrid_5g": ExampleNetwork(
        "n78",
        "urban",
        False,
        1.0,
        25,
        _sectors("Sol", 40.4169, -3.7035, 0)
        + _sectors("Cibeles", 40.4193, -3.6931, 20)
        + _sectors("Lavapiés", 40.4087, -3.7008, 40)
        + _sectors("Plaza de España", 40.4237, -3.7122, 10)
        + _sectors("Atocha", 40.4066, -3.6907, 30),
    ),
    "segovia_lte": ExampleNetwork(
        "b20",
        "rural",
        True,
        15.0,
        150,
        _sectors("Bola del Mundo", 40.7930, -3.9620, 330)
        + (("Segovia", 40.9481, -4.1253, None), ("La Granja", 40.8986, -4.0036, 300.0)),
    ),
}
