"""Command line interface.

Usage examples::

    radiocoverage link --band B20 --distance 5 --tx-power 46 --tx-gain 17 --sensitivity -100
    radiocoverage link --config examples/lte_b20_navacerrada_segovia.toml --map link.html
    radiocoverage coverage --config examples/coverage_5g_n78_madrid.toml --map coverage.html
    radiocoverage coverage --config examples/network_lte_b20_segovia.toml --kmz network.kmz
    radiocoverage bands
    radiocoverage models
"""

import argparse
import math
import sys
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from radiocoverage import __version__
from radiocoverage.bands import BANDS, Band, get_band
from radiocoverage.geo import GeoPoint, is_in_spain
from radiocoverage.link_budget import LinkBudgetResult, LinkParameters, compute_link_budget
from radiocoverage.path import LinkPath
from radiocoverage.propagation import ENVIRONMENTS, MODEL_CHOICES, MODELS
from radiocoverage.receiver import sensitivity_dbm


class ConfigError(ValueError):
    """Invalid or incomplete user input."""


# --- Option definitions --------------------------------------------------------------


@dataclass(frozen=True)
class Option:
    name: str
    kind: type
    help: str
    default: object = None
    choices: tuple[str, ...] | None = None

    @property
    def flag(self) -> str:
        return "--" + self.name.replace("_", "-")


RADIO = (
    Option("band", str, "LTE/5G band name, e.g. B20 or n78 (see 'bands')"),
    Option("frequency", float, "carrier frequency in MHz (alternative to --band)"),
)
TX = (
    Option("tx_power", float, "transmitter output power in dBm"),
    Option("tx_gain", float, "transmitter antenna gain in dBi", 0.0),
    Option("tx_loss", float, "transmitter cable/connector loss in dB", 0.0),
    Option("tx_height", float, "transmitter antenna height above ground in m", 30.0),
)
RX = (
    Option("rx_gain", float, "receiver antenna gain in dBi", 0.0),
    Option("rx_loss", float, "receiver cable/connector/body loss in dB", 0.0),
    Option("rx_height", float, "receiver antenna height above ground in m", 1.5),
    Option("other_losses", float, "additional losses in dB (penetration, foliage...)", 0.0),
    Option("margin", float, "required fade margin in dB", 0.0),
    Option("sensitivity", float, "receiver sensitivity in dBm"),
    Option("bandwidth", float, "channel bandwidth in MHz, to derive the sensitivity"),
    Option("noise_figure", float, "receiver noise figure in dB, to derive the sensitivity"),
    Option("snr", float, "minimum SNR in dB required by the receiver, to derive the sensitivity"),
)
PROPAGATION = (
    Option("model", str, "propagation model", None, MODEL_CHOICES),
    Option("environment", str, "environment for empirical models", "urban", ENVIRONMENTS),
    Option("terrain", bool, "use real terrain elevation (downloads and caches tiles)", False),
    Option("terrain_zoom", float, "zoom level of the elevation tiles (12 = ~30 m)", 12.0),
)
LINK_GEOMETRY = (
    Option("distance", float, "distance between transmitter and receiver in km"),
    Option("tx_lat", float, "transmitter latitude in decimal degrees"),
    Option("tx_lon", float, "transmitter longitude in decimal degrees (west is negative)"),
    Option("rx_lat", float, "receiver latitude in decimal degrees"),
    Option("rx_lon", float, "receiver longitude in decimal degrees (west is negative)"),
)
COVERAGE_GEOMETRY = (
    Option("tx_lat", float, "site latitude in decimal degrees"),
    Option("tx_lon", float, "site longitude in decimal degrees (west is negative)"),
    Option("azimuth", float, "sector antenna azimuth in degrees (omit for omnidirectional)"),
    Option("beamwidth", float, "sector antenna horizontal beamwidth in degrees", 65.0),
    Option("radius", float, "radius of the analysed area around the site(s) in km", 10.0),
    Option("resolution", float, "grid resolution in metres", 100.0),
)

LINK_OPTIONS = (*RADIO, *LINK_GEOMETRY, *TX, *RX, *PROPAGATION)
COVERAGE_OPTIONS = (*RADIO, *COVERAGE_GEOMETRY, *TX, *RX, *PROPAGATION)
DEFAULT_MODEL = {"link": "free-space", "coverage": "auto"}

SITE_KEYS = {
    "name": str,
    "band": str,
    "frequency": float,
    "lat": float,
    "lon": float,
    "height": float,
    "tx_power": float,
    "tx_gain": float,
    "tx_loss": float,
    "azimuth": float,
    "beamwidth": float,
}

_COORDINATE_KEYS = ("tx_lat", "tx_lon", "rx_lat", "rx_lon")
_NOISE_KEYS = ("bandwidth", "noise_figure", "snr")
# Options that are alternatives to each other: setting one on the command line
# discards the whole group from the config file.
_EXCLUSIVE_GROUPS = (
    ({"band"}, {"frequency"}),
    ({"distance"}, {"rx_lat", "rx_lon"}),
    ({"sensitivity"}, set(_NOISE_KEYS)),
)


def _flag(name: str) -> str:
    return "--" + name.replace("_", "-")


# --- Parser ---------------------------------------------------------------------------


def _add_options(parser: argparse.ArgumentParser, options: Sequence[Option], model_default: str):
    for option in options:
        default = model_default if option.name == "model" else option.default
        suffix = f" (default: {default:g})" if isinstance(default, float) else ""
        if isinstance(default, str):
            suffix = f" (default: {default})"
        if option.kind is bool:
            parser.add_argument(
                option.flag, dest=option.name, action=argparse.BooleanOptionalAction,
                default=None, help=option.help,
            )  # fmt: skip
        else:
            parser.add_argument(
                option.flag,
                dest=option.name,
                type=option.kind,
                choices=option.choices,
                help=option.help + suffix,
            )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="radiocoverage",
        description="Radio link budget and coverage prediction for LTE/5G in Spain.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    link = subparsers.add_parser(
        "link",
        help="point-to-point link budget, optionally over real terrain",
        description=(
            "Compute a link budget. Give the frequency with --band or --frequency; the "
            "length with --distance or with the coordinates of both ends (which must be "
            "in Spain); and the receiver sensitivity with --sensitivity or derive it from "
            "--bandwidth, --noise-figure and --snr. Values can also be read from a TOML "
            "file with --config; command line options take precedence."
        ),
    )
    link.add_argument("--config", type=Path, help="TOML file with link parameters")
    link.add_argument("--map", type=Path, metavar="FILE.html", help="save an interactive map")
    link.add_argument(
        "--profile", type=Path, metavar="FILE.png",
        help="save the terrain profile chart (implies --terrain)",
    )  # fmt: skip
    _add_options(link, LINK_OPTIONS, DEFAULT_MODEL["link"])

    coverage = subparsers.add_parser(
        "coverage",
        help="coverage map of one site, or of a network of sites from a config file",
        description=(
            "Predict the received power over a grid around one site (given by options) "
            "or several sites (given as [[sites]] tables in the --config file), and save "
            "it as an interactive map, a KMZ for Google Earth and/or a PNG image."
        ),
    )
    coverage.add_argument("--config", type=Path, help="TOML file with coverage parameters")
    coverage.add_argument("--map", type=Path, metavar="FILE.html", help="save an interactive map")
    coverage.add_argument("--kmz", type=Path, metavar="FILE.kmz", help="save a KMZ file")
    coverage.add_argument(
        "--image", type=Path, metavar="FILE.png", help="save a static image of the coverage"
    )
    _add_options(coverage, COVERAGE_OPTIONS, DEFAULT_MODEL["coverage"])

    subparsers.add_parser("bands", help="list the LTE/5G bands available in Spain")
    subparsers.add_parser("models", help="list the propagation models")
    web = subparsers.add_parser("web", help="open the web interface in the browser")
    web.add_argument("--port", type=int, default=8501, help="local port (default: 8501)")
    return parser


# --- Config files ---------------------------------------------------------------------


def _check_type(value: object, kind: type, where: str) -> None:
    if kind is float:
        ok = isinstance(value, int | float) and not isinstance(value, bool)
        expected = "a number"
    elif kind is bool:
        ok = isinstance(value, bool)
        expected = "true or false"
    else:
        ok = isinstance(value, str)
        expected = 'a text value in quotes, e.g. "B20"'
    if not ok:
        raise ConfigError(f"{where} must be {expected}")


def _load_config(path: Path, options: Sequence[Option], allow_sites: bool) -> dict:
    try:
        with path.open("rb") as file:
            data = tomllib.load(file)
    except FileNotFoundError:
        raise ConfigError(f"config file not found: {path}") from None
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML in {path}: {exc}") from None

    kinds = {option.name: option.kind for option in options}
    valid = set(kinds) | ({"sites"} if allow_sites else set())
    unknown = sorted(set(data) - valid)
    if unknown:
        raise ConfigError(
            f"unknown key(s) in {path}: {', '.join(unknown)}. "
            f"Valid keys: {', '.join(sorted(valid))}"
        )
    for key, value in data.items():
        if key == "sites":
            if not isinstance(value, list) or not all(isinstance(s, dict) for s in value):
                raise ConfigError(f"'sites' in {path} must be a list of [[sites]] tables")
            for number, site in enumerate(value, start=1):
                extra = sorted(set(site) - set(SITE_KEYS))
                if extra:
                    raise ConfigError(
                        f"unknown key(s) in site {number} of {path}: {', '.join(extra)}. "
                        f"Valid keys: {', '.join(sorted(SITE_KEYS))}"
                    )
                for site_key, site_value in site.items():
                    _check_type(site_value, SITE_KEYS[site_key], f"'{site_key}' in site {number}")
        else:
            _check_type(value, kinds[key], f"'{key}' in {path}")
    return data


def _merge_options(
    cli: dict[str, object], config: dict[str, object], options: Sequence[Option], command: str
) -> dict[str, object]:
    """Combine config file values with command line values (command line wins)."""
    config = dict(config)
    for group_a, group_b in _EXCLUSIVE_GROUPS:
        for given, other in ((group_a, group_b), (group_b, group_a)):
            if any(cli.get(key) is not None for key in given):
                for key in other:
                    config.pop(key, None)
    if cli.get("distance") is not None:
        for key in _COORDINATE_KEYS:
            config.pop(key, None)

    merged: dict[str, object] = {}
    for option in options:
        value = cli.get(option.name)
        if value is None:
            value = config.get(option.name)
        if value is None:
            value = DEFAULT_MODEL[command] if option.name == "model" else option.default
        if option.choices and value is not None and value not in option.choices:
            raise ConfigError(
                f"invalid {option.name} '{value}'. Choose from: {', '.join(option.choices)}"
            )
        merged[option.name] = value
    merged["sites"] = config.get("sites")
    return merged


# --- Resolving options ----------------------------------------------------------------


def _resolve_frequency(options: dict, where: str = "") -> tuple[float, Band | None]:
    band_name, frequency = options.get("band"), options.get("frequency")
    if band_name is not None and frequency is not None:
        raise ConfigError(f"use either band or frequency, not both{where}")
    if band_name is not None:
        band = get_band(str(band_name))
        return band.centre_mhz, band
    if frequency is not None:
        return float(frequency), None
    raise ConfigError(f"missing frequency: use --band or --frequency{where}")


def _resolve_sensitivity(options: dict) -> tuple[float, str]:
    noise_given = [key for key in _NOISE_KEYS if options[key] is not None]
    if options["sensitivity"] is not None and noise_given:
        raise ConfigError("use either --sensitivity or --bandwidth/--noise-figure/--snr, not both")
    if options["sensitivity"] is not None:
        return float(options["sensitivity"]), "given"
    if len(noise_given) == len(_NOISE_KEYS):
        value = sensitivity_dbm(
            float(options["bandwidth"]), float(options["noise_figure"]), float(options["snr"])
        )
        note = (
            f"from kTB: {options['bandwidth']:g} MHz, "
            f"NF {options['noise_figure']:g} dB, SNR {options['snr']:g} dB"
        )
        return value, note
    missing = [_flag(key) for key in _NOISE_KEYS if key not in noise_given]
    if noise_given:
        raise ConfigError(f"to derive the sensitivity also give: {', '.join(missing)}")
    raise ConfigError(
        "missing receiver sensitivity: use --sensitivity, or --bandwidth, --noise-figure and --snr"
    )


def _point_in_spain(lat: float, lon: float, name: str) -> GeoPoint:
    point = GeoPoint(lat, lon)
    if not is_in_spain(point):
        raise ConfigError(
            f"the {name} ({point}) is outside Spain; this tool only covers Spanish "
            "territory (check the sign of the longitude: west is negative)"
        )
    return point


def _terrain_zoom(options: dict) -> int:
    zoom = float(options["terrain_zoom"])
    if zoom != int(zoom):
        raise ConfigError("--terrain-zoom must be a whole number")
    return int(zoom)


def _terrain_source(options: dict):
    from radiocoverage.terrain import TerrariumTiles

    return TerrariumTiles(zoom=_terrain_zoom(options))


@dataclass(frozen=True)
class ResolvedLink:
    params: LinkParameters
    band: Band | None
    sensitivity_note: str
    path: LinkPath | None


def _resolve_path(options: dict, frequency_mhz: float) -> LinkPath | None:
    given = [key for key in _COORDINATE_KEYS if options[key] is not None]
    if not given:
        return None
    if options["distance"] is not None:
        raise ConfigError("use either --distance or coordinates, not both")
    if len(given) != len(_COORDINATE_KEYS):
        missing = [_flag(key) for key in _COORDINATE_KEYS if key not in given]
        raise ConfigError(f"incomplete coordinates, also give: {', '.join(missing)}")
    tx = _point_in_spain(float(options["tx_lat"]), float(options["tx_lon"]), "transmitter")
    rx = _point_in_spain(float(options["rx_lat"]), float(options["rx_lon"]), "receiver")
    return LinkPath(tx, rx, frequency_mhz)


def _resolve_link(options: dict) -> ResolvedLink:
    """Turn raw options into validated link parameters and, if given, its geometry."""
    frequency_mhz, band = _resolve_frequency(options)
    path = _resolve_path(options, frequency_mhz)
    if path is None and options["distance"] is None:
        raise ConfigError(
            "missing link length: use --distance, or --tx-lat, --tx-lon, --rx-lat and --rx-lon"
        )
    if options["tx_power"] is None:
        raise ConfigError("missing required option --tx-power")
    rx_sensitivity, note = _resolve_sensitivity(options)
    params = LinkParameters(
        frequency_mhz=frequency_mhz,
        distance_km=path.distance_km if path is not None else float(options["distance"]),
        tx_power_dbm=float(options["tx_power"]),
        rx_sensitivity_dbm=rx_sensitivity,
        tx_antenna_gain_dbi=float(options["tx_gain"]),
        rx_antenna_gain_dbi=float(options["rx_gain"]),
        tx_cable_loss_db=float(options["tx_loss"]),
        rx_cable_loss_db=float(options["rx_loss"]),
        other_losses_db=float(options["other_losses"]),
        required_margin_db=float(options["margin"]),
        model=str(options["model"]),
        environment=str(options["environment"]),
        tx_height_m=float(options["tx_height"]),
        rx_height_m=float(options["rx_height"]),
    )
    return ResolvedLink(params, band, note, path)


def _resolve_sites(options: dict) -> list:
    from radiocoverage.coverage import Site

    entries = options["sites"]
    if entries is None:
        if options["tx_lat"] is None or options["tx_lon"] is None:
            raise ConfigError(
                "missing site location: use --tx-lat and --tx-lon, "
                "or [[sites]] tables in the config file"
            )
        entries = [{"name": "Site", "lat": options["tx_lat"], "lon": options["tx_lon"]}]
        use_top_level_geometry = True
    else:
        if not entries:
            raise ConfigError("the config file has an empty 'sites' list")
        if options["tx_lat"] is not None or options["tx_lon"] is not None:
            raise ConfigError("use either --tx-lat/--tx-lon or [[sites]] tables, not both")
        use_top_level_geometry = False

    sites = []
    for number, entry in enumerate(entries, start=1):
        where = f" (site {number})" if not use_top_level_geometry else ""
        name = entry.get("name", f"Site {number}")
        if "lat" not in entry or "lon" not in entry:
            raise ConfigError(f"site {number} needs 'lat' and 'lon'")
        merged = {
            "band": entry.get("band"),
            "frequency": entry.get("frequency"),
        }
        if merged["band"] is None and merged["frequency"] is None:
            merged = {"band": options["band"], "frequency": options["frequency"]}
        frequency_mhz, band = _resolve_frequency(merged, where)
        tx_power = entry.get("tx_power", options["tx_power"])
        if tx_power is None:
            raise ConfigError(f"missing transmitter power: use --tx-power{where}")
        azimuth = entry.get("azimuth", options["azimuth"] if use_top_level_geometry else None)
        sites.append(
            Site(
                name=name,
                location=_point_in_spain(
                    float(entry["lat"]), float(entry["lon"]), f"site '{name}'"
                ),
                frequency_mhz=frequency_mhz,
                tx_power_dbm=float(tx_power),
                tx_gain_dbi=float(entry.get("tx_gain", options["tx_gain"])),
                tx_loss_db=float(entry.get("tx_loss", options["tx_loss"])),
                height_m=float(entry.get("height", options["tx_height"])),
                azimuth_deg=None if azimuth is None else float(azimuth),
                beamwidth_deg=float(entry.get("beamwidth", options["beamwidth"])),
                band_name=f"{band.technology} {band.name}" if band else "",
            )
        )
    return sites


# --- Reports --------------------------------------------------------------------------


def _row(label: str, value: float, unit: str, sign: str = "") -> str:
    return f"  {label:<26}{sign:<2}{value:>10.2f} {unit}"


def _text_row(label: str, text: str) -> str:
    return f"  {label:<26}{text}"


def format_report(
    result: LinkBudgetResult,
    band: Band | None = None,
    note: str = "",
    path: LinkPath | None = None,
    profile=None,
) -> str:
    """Render a link budget as a human readable table."""
    p = result.parameters
    width = 50
    if band is not None:
        title = f"Link budget - {band.technology} {band.name} ({band.centre_mhz:g} MHz)"
    else:
        title = f"Link budget - {p.frequency_mhz:g} MHz"
    free_space = result.model_key == "free-space"

    lines = [
        title,
        "=" * width,
        "Transmitter",
        _row("Tx power", p.tx_power_dbm, "dBm"),
        _row("Tx antenna gain", p.tx_antenna_gain_dbi, "dBi", "+"),
        _row("Tx cable loss", p.tx_cable_loss_db, "dB", "-"),
        _row("EIRP", result.eirp_dbm, "dBm", "="),
        "Path",
    ]
    if path is not None:
        lines += [
            _text_row("Tx location", str(path.tx)),
            _text_row("Rx location", str(path.rx)),
            _row("Azimuth Tx -> Rx", path.bearing_deg, "deg"),
        ]
    lines += [
        _row("Frequency", p.frequency_mhz, "MHz"),
        _row("Distance", p.distance_km, "km"),
        _text_row("Propagation model", result.model_label),
    ]
    if not free_space:
        lines += [
            _text_row("Environment", p.environment),
            _row("Tx antenna height", p.tx_height_m, "m"),
            _row("Rx antenna height", p.rx_height_m, "m"),
        ]
    loss_label = "Free-space path loss" if free_space else "Path loss"
    lines.append(_row(loss_label, result.path_loss_db, "dB", "-"))
    if profile is not None:
        lines += [
            _text_row("Terrain", profile.status),
            _row("Min. Fresnel clearance", profile.min_clearance_ratio * 100, "%"),
            _row("Diffraction loss", profile.diffraction_loss_db, "dB", "-"),
        ]
    lines.append(_row("Other losses", p.other_losses_db, "dB", "-"))
    if path is not None:
        lines += [
            _row("1st Fresnel radius (mid)", path.fresnel_radius_midpoint_m, "m"),
            _row("60% clearance (mid)", path.clearance_midpoint_m, "m"),
            _row("Earth bulge (mid, k=4/3)", path.earth_bulge_midpoint_m(), "m"),
        ]
    lines += [
        "Receiver",
        _row("Rx antenna gain", p.rx_antenna_gain_dbi, "dBi", "+"),
        _row("Rx cable loss", p.rx_cable_loss_db, "dB", "-"),
        _row("Received power", result.rx_power_dbm, "dBm", "="),
        _row("Sensitivity", p.rx_sensitivity_dbm, "dBm"),
    ]
    if note and note != "given":
        lines.append(f"    ({note})")
    lines += [
        _row("Margin", result.margin_db, "dB"),
        _row("Required margin", p.required_margin_db, "dB"),
        "-" * width,
    ]
    verdict = "LINK OK" if result.is_viable else "LINK FAILS"
    lines.append(
        f"Result: {verdict} (margin {result.margin_db:.2f} dB, "
        f"required {p.required_margin_db:.2f} dB)"
    )
    range_label = "Max range in free space" if free_space else "Max range with this model"
    if profile is not None:
        range_label += " (no terrain)"
    if math.isinf(result.max_distance_km):
        lines.append(f"{range_label}: more than 2000 km")
    else:
        lines.append(f"{range_label}: {result.max_distance_km:.2f} km")
    for warning in result.warnings:
        lines.append(f"Warning: {warning}")
    if free_space and profile is None:
        lines.append("Note: free space is a best case; real LTE/5G range is much shorter.")
    return "\n".join(lines)


def format_coverage_report(result, radius_km: float, resolution_m: float) -> str:
    receiver = result.receiver
    width = 60
    title = "Coverage prediction" if len(result.sites) == 1 else "Network coverage prediction"
    lines = [title, "=" * width, "Sites"]
    for number, site in enumerate(result.sites, start=1):
        lines.append(f"  {number}. {site.description}")
        lines.append(f"     at {site.location}")
    models = ", ".join(sorted({result.model_label(site) for site in result.sites}))
    rows, cols = result.grid.shape
    lines += [
        "Propagation",
        _text_row("Model", models),
        _text_row("Environment", result.environment),
        _text_row(
            "Terrain", "real elevation, Bullington diffraction" if result.terrain else "flat earth"
        ),
        "Receiver",
        _row("Sensitivity", receiver.sensitivity_dbm, "dBm"),
        _row("Required margin", receiver.required_margin_db, "dB"),
        _row("Coverage threshold", receiver.threshold_dbm, "dBm"),
        "Area",
        _text_row("Grid", f"{rows} x {cols} points, {resolution_m:g} m, radius {radius_km:g} km"),
        _row("Analysed area", result.area_km2, "km2"),
        _row("Covered area", result.covered_area_km2, "km2"),
        _row("Covered fraction", result.covered_fraction * 100, "%"),
    ]
    if len(result.sites) > 1:
        lines.append("Best server areas")
        for site, area in zip(result.sites, result.served_area_km2(), strict=True):
            lines.append(_row(site.name[:24], area, "km2"))
    return "\n".join(lines)


def format_bands() -> str:
    lines = [f"{'Band':<6}{'Tech':<7}{'Downlink (MHz)':<18}{'Centre':>8}  Typical use"]
    for band in BANDS.values():
        downlink = f"{band.downlink_low_mhz:g}-{band.downlink_high_mhz:g}"
        lines.append(
            f"{band.name:<6}{band.technology:<7}{downlink:<18}"
            f"{band.centre_mhz:>8g}  {band.typical_use}"
        )
    return "\n".join(lines)


def format_models() -> str:
    lines = [f"{'Model':<14}{'Frequency (MHz)':<18}{'Distance (km)':<16}Reference"]
    for model in MODELS.values():
        low, high = model.frequency_range_mhz
        d_low, d_high = model.distance_range_km
        freq = "any" if model.key == "free-space" else f"{low:g}-{high:g}"
        dist = "any" if math.isinf(d_high) else f"{d_low:g}-{d_high:g}"
        lines.append(f"{model.key:<14}{freq:<18}{dist:<16}{model.reference}")
    lines.append(
        "auto          picks okumura-hata below 1500 MHz, cost231-hata up to 2000 MHz "
        "and 3gpp above"
    )
    lines.append(f"Environments: {', '.join(ENVIRONMENTS)}")
    return "\n".join(lines)


# --- Commands -------------------------------------------------------------------------


def _run_link(args: argparse.Namespace) -> list[str]:
    config = _load_config(args.config, LINK_OPTIONS, allow_sites=False) if args.config else {}
    cli_values = {option.name: getattr(args, option.name) for option in LINK_OPTIONS}
    options = _merge_options(cli_values, config, LINK_OPTIONS, "link")
    if args.profile is not None:
        options["terrain"] = True
    _terrain_zoom(options)
    link = _resolve_link(options)
    if args.map is not None and link.path is None:
        raise ConfigError("--map needs the coordinates of both ends of the link")
    if args.profile is not None and args.profile.suffix.lower() != ".png":
        raise ConfigError(f"profile file must end in .png, got '{args.profile.name}'")

    profile = None
    params = link.params
    if options["terrain"]:
        if link.path is None:
            raise ConfigError("--terrain needs the coordinates of both ends of the link")
        from dataclasses import replace

        from radiocoverage.profile import terrain_profile

        profile = terrain_profile(
            link.path, _terrain_source(options), params.tx_height_m, params.rx_height_m
        )
        params = replace(params, terrain_loss_db=profile.diffraction_loss_db)

    result = compute_link_budget(params)
    lines = [format_report(result, link.band, link.sensitivity_note, link.path, profile)]

    profile_png = None
    if profile is not None and (args.profile is not None or args.map is not None):
        import tempfile

        from radiocoverage.profile import plot_profile

        title = f"{link.path.tx} → {link.path.rx}"
        if args.profile is not None:
            plot_profile(profile, args.profile, title)
            profile_png = args.profile.read_bytes()
            lines.append(f"Terrain profile saved to {args.profile}")
        else:
            with tempfile.TemporaryDirectory() as tmp:
                png = plot_profile(profile, Path(tmp) / "profile.png", title)
                profile_png = png.read_bytes()
    if args.map is not None:
        from radiocoverage.link_map import save_link_map

        saved = save_link_map(link.path, result, args.map, link.band, profile, profile_png)
        lines.append(f"Map saved to {saved}")
    return lines


def _run_coverage(args: argparse.Namespace) -> list[str]:
    from radiocoverage.coverage import Receiver, compute_coverage

    config = _load_config(args.config, COVERAGE_OPTIONS, allow_sites=True) if args.config else {}
    cli_values = {option.name: getattr(args, option.name) for option in COVERAGE_OPTIONS}
    options = _merge_options(cli_values, config, COVERAGE_OPTIONS, "coverage")
    for output, suffix in ((args.map, ".html"), (args.kmz, ".kmz"), (args.image, ".png")):
        if output is not None and output.suffix.lower() != suffix:
            raise ConfigError(f"output file '{output.name}' must end in {suffix}")

    _terrain_zoom(options)
    sites = _resolve_sites(options)
    sensitivity, _ = _resolve_sensitivity(options)
    receiver = Receiver(
        sensitivity_dbm=sensitivity,
        height_m=float(options["rx_height"]),
        gain_dbi=float(options["rx_gain"]),
        loss_db=float(options["rx_loss"]),
        other_losses_db=float(options["other_losses"]),
        required_margin_db=float(options["margin"]),
    )
    terrain = _terrain_source(options) if options["terrain"] else None
    radius, resolution = float(options["radius"]), float(options["resolution"])
    result = compute_coverage(
        sites,
        receiver,
        radius_km=radius,
        resolution_m=resolution,
        model=str(options["model"]),
        environment=str(options["environment"]),
        terrain=terrain,
    )

    lines = [format_coverage_report(result, radius, resolution)]
    if args.map is not None:
        from radiocoverage.coverage_map import save_coverage_map

        lines.append(f"Map saved to {save_coverage_map(result, args.map, terrain)}")
    if args.kmz is not None:
        from radiocoverage.kmz import save_kmz

        lines.append(f"KMZ saved to {save_kmz(result, args.kmz)}")
    if args.image is not None:
        from radiocoverage.coverage_plot import plot_coverage

        saved = plot_coverage(result, args.image, terrain=terrain)
        lines.append(f"Image saved to {saved}")
    return lines


# Theme of the web interface, also passed on the command line so that it applies
# whatever folder the app is started from (see .streamlit/config.toml).
WEB_OPTIONS = {
    "server.showEmailPrompt": "false",
    "browser.gatherUsageStats": "false",
    "client.toolbarMode": "minimal",
    "theme.base": "light",
    "theme.primaryColor": "#1f4fd1",
    "theme.backgroundColor": "#ffffff",
    "theme.secondaryBackgroundColor": "#f4f6fb",
    "theme.textColor": "#1b2430",
}


def web_command(port: int = 8501) -> list[str]:
    """The command that starts the Streamlit web interface."""
    import radiocoverage.webapp

    entry = Path(radiocoverage.webapp.__file__).parent / "streamlit_entry.py"
    options = [f"--{name}={value}" for name, value in WEB_OPTIONS.items()]
    return [sys.executable, "-m", "streamlit", "run", str(entry), f"--server.port={port}",
            *options]  # fmt: skip


def run_web(port: int = 8501) -> int:
    import importlib.util
    import subprocess

    if (
        importlib.util.find_spec("streamlit") is None
        or importlib.util.find_spec("streamlit_folium") is None
    ):
        print(
            "error: the web interface needs extra packages; install them with\n"
            '  pip install -e ".[web]"',
            file=sys.stderr,
        )
        return 2
    try:
        return subprocess.call(web_command(port))
    except KeyboardInterrupt:  # pragma: no cover - user closes the app
        return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "bands":
        print(format_bands())
        return 0
    if args.command == "models":
        print(format_models())
        return 0
    if args.command == "web":
        return run_web(args.port)

    try:
        lines = _run_link(args) if args.command == "link" else _run_coverage(args)
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
