"""Command line interface.

Usage examples::

    radiocoverage link --band B20 --distance 5 --tx-power 46 --tx-gain 17 --sensitivity -100
    radiocoverage link --band n78 --tx-lat 40.4233 --tx-lon -3.6713 \
        --rx-lat 40.4169 --rx-lon -3.7035 --tx-power 43 --sensitivity -95 --map link.html
    radiocoverage link --config examples/lte_b20_navacerrada_segovia.toml
    radiocoverage bands
"""

import argparse
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
from radiocoverage.receiver import sensitivity_dbm

# Option name (as used in the config file) -> (help text, default value).
_NUMERIC_OPTIONS: dict[str, tuple[str, float | None]] = {
    "frequency": ("carrier frequency in MHz (alternative to --band)", None),
    "distance": ("distance between transmitter and receiver in km", None),
    "tx_lat": ("transmitter latitude in decimal degrees (alternative to --distance)", None),
    "tx_lon": ("transmitter longitude in decimal degrees (west is negative)", None),
    "rx_lat": ("receiver latitude in decimal degrees", None),
    "rx_lon": ("receiver longitude in decimal degrees (west is negative)", None),
    "tx_power": ("transmitter output power in dBm", None),
    "tx_gain": ("transmitter antenna gain in dBi", 0.0),
    "rx_gain": ("receiver antenna gain in dBi", 0.0),
    "tx_loss": ("transmitter cable/connector loss in dB", 0.0),
    "rx_loss": ("receiver cable/connector/body loss in dB", 0.0),
    "other_losses": ("additional losses in dB (penetration, foliage, rain...)", 0.0),
    "margin": ("required fade margin in dB", 0.0),
    "sensitivity": ("receiver sensitivity in dBm", None),
    "bandwidth": ("channel bandwidth in MHz, to derive the sensitivity", None),
    "noise_figure": ("receiver noise figure in dB, to derive the sensitivity", None),
    "snr": ("minimum SNR in dB required by the receiver, to derive the sensitivity", None),
}
_ALL_OPTIONS = {"band", *_NUMERIC_OPTIONS}

# Options that are alternatives to each other: setting one on the command line
# discards the whole group from the config file.
_COORDINATE_KEYS = ("tx_lat", "tx_lon", "rx_lat", "rx_lon")
_EXCLUSIVE_GROUPS = (
    ({"band"}, {"frequency"}),
    ({"distance"}, set(_COORDINATE_KEYS)),
    ({"sensitivity"}, {"bandwidth", "noise_figure", "snr"}),
)


class ConfigError(ValueError):
    """Invalid or incomplete user input."""


@dataclass(frozen=True)
class ResolvedLink:
    params: LinkParameters
    band: Band | None
    sensitivity_note: str
    path: LinkPath | None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="radiocoverage",
        description="Radio link budget and coverage tools for LTE/5G in Spain.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    link = subparsers.add_parser(
        "link",
        help="compute a point-to-point link budget (free space)",
        description=(
            "Compute a free-space link budget. Give the frequency with --band or "
            "--frequency; the length with --distance or with the coordinates of both "
            "ends (--tx-lat, --tx-lon, --rx-lat, --rx-lon), which must be in Spain; and "
            "the receiver sensitivity directly with --sensitivity or derive it from "
            "--bandwidth, --noise-figure and --snr. Values can also be read from a TOML "
            "file with --config; command line options take precedence."
        ),
    )
    link.add_argument("--config", type=Path, help="TOML file with link parameters")
    link.add_argument(
        "--map",
        type=Path,
        metavar="FILE.html",
        help="save an interactive map of the link (needs coordinates)",
    )
    link.add_argument("--band", help="LTE/5G band name, e.g. B20 or n78 (see 'bands')")
    for name, (help_text, default) in _NUMERIC_OPTIONS.items():
        suffix = f" (default: {default:g})" if default is not None else ""
        link.add_argument(
            "--" + name.replace("_", "-"), dest=name, type=float, help=help_text + suffix
        )

    subparsers.add_parser("bands", help="list the LTE/5G bands available in Spain")
    return parser


def _load_config(path: Path) -> dict[str, object]:
    try:
        with path.open("rb") as file:
            data = tomllib.load(file)
    except FileNotFoundError:
        raise ConfigError(f"config file not found: {path}") from None
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML in {path}: {exc}") from None

    unknown = sorted(set(data) - _ALL_OPTIONS)
    if unknown:
        raise ConfigError(
            f"unknown key(s) in {path}: {', '.join(unknown)}. "
            f"Valid keys: {', '.join(sorted(_ALL_OPTIONS))}"
        )
    for key, value in data.items():
        if key == "band":
            if not isinstance(value, str):
                raise ConfigError(f"'band' in {path} must be a text value, e.g. \"B20\"")
        elif isinstance(value, bool) or not isinstance(value, int | float):
            raise ConfigError(f"'{key}' in {path} must be a number")
    return data


def _merge_options(cli: dict[str, object], config: dict[str, object]) -> dict[str, object]:
    """Combine config file values with command line values (command line wins)."""
    config = dict(config)
    for group_a, group_b in _EXCLUSIVE_GROUPS:
        for given, other in ((group_a, group_b), (group_b, group_a)):
            if any(cli.get(key) is not None for key in given):
                for key in other:
                    config.pop(key, None)

    merged: dict[str, object] = {}
    for key in _ALL_OPTIONS:
        value = cli.get(key)
        merged[key] = value if value is not None else config.get(key)
    for key, (_, default) in _NUMERIC_OPTIONS.items():
        if merged[key] is None and default is not None:
            merged[key] = default
    return merged


def _resolve_path(options: dict[str, object], frequency_mhz: float) -> LinkPath | None:
    given = [key for key in _COORDINATE_KEYS if options[key] is not None]
    if not given:
        return None
    if options["distance"] is not None:
        raise ConfigError("use either --distance or coordinates, not both")
    if len(given) != len(_COORDINATE_KEYS):
        missing = [f"--{key.replace('_', '-')}" for key in _COORDINATE_KEYS if key not in given]
        raise ConfigError(f"incomplete coordinates, also give: {', '.join(missing)}")
    tx = GeoPoint(float(options["tx_lat"]), float(options["tx_lon"]))
    rx = GeoPoint(float(options["rx_lat"]), float(options["rx_lon"]))
    for name, point in (("transmitter", tx), ("receiver", rx)):
        if not is_in_spain(point):
            raise ConfigError(
                f"the {name} ({point}) is outside Spain; this tool only covers Spanish "
                "territory (check the sign of the longitude: west is negative)"
            )
    return LinkPath(tx, rx, frequency_mhz)


def _resolve_link(options: dict[str, object]) -> ResolvedLink:
    """Turn raw options into validated link parameters and, if given, its geometry."""
    band = None
    if options["band"] is not None and options["frequency"] is not None:
        raise ConfigError("use either --band or --frequency, not both")
    if options["band"] is not None:
        band = get_band(str(options["band"]))
        frequency_mhz = band.centre_mhz
    elif options["frequency"] is not None:
        frequency_mhz = float(options["frequency"])
    else:
        raise ConfigError("missing frequency: use --band or --frequency")

    path = _resolve_path(options, frequency_mhz)
    if path is None and options["distance"] is None:
        raise ConfigError(
            "missing link length: use --distance, or --tx-lat, --tx-lon, --rx-lat and --rx-lon"
        )
    if options["tx_power"] is None:
        raise ConfigError("missing required option --tx-power")

    noise_keys = ("bandwidth", "noise_figure", "snr")
    noise_given = [key for key in noise_keys if options[key] is not None]
    if options["sensitivity"] is not None and noise_given:
        raise ConfigError("use either --sensitivity or --bandwidth/--noise-figure/--snr, not both")
    if options["sensitivity"] is not None:
        rx_sensitivity_dbm = float(options["sensitivity"])
        sensitivity_note = "given"
    elif len(noise_given) == len(noise_keys):
        rx_sensitivity_dbm = sensitivity_dbm(
            float(options["bandwidth"]), float(options["noise_figure"]), float(options["snr"])
        )
        sensitivity_note = (
            f"from kTB: {options['bandwidth']:g} MHz, "
            f"NF {options['noise_figure']:g} dB, SNR {options['snr']:g} dB"
        )
    else:
        missing = [f"--{key.replace('_', '-')}" for key in noise_keys if key not in noise_given]
        if noise_given:
            raise ConfigError(f"to derive the sensitivity also give: {', '.join(missing)}")
        raise ConfigError(
            "missing receiver sensitivity: use --sensitivity, or "
            "--bandwidth, --noise-figure and --snr"
        )

    params = LinkParameters(
        frequency_mhz=frequency_mhz,
        distance_km=path.distance_km if path is not None else float(options["distance"]),
        tx_power_dbm=float(options["tx_power"]),
        rx_sensitivity_dbm=rx_sensitivity_dbm,
        tx_antenna_gain_dbi=float(options["tx_gain"]),
        rx_antenna_gain_dbi=float(options["rx_gain"]),
        tx_cable_loss_db=float(options["tx_loss"]),
        rx_cable_loss_db=float(options["rx_loss"]),
        other_losses_db=float(options["other_losses"]),
        required_margin_db=float(options["margin"]),
    )
    return ResolvedLink(params, band, sensitivity_note, path)


def format_report(
    result: LinkBudgetResult,
    band: Band | None = None,
    note: str = "",
    path: LinkPath | None = None,
) -> str:
    """Render a link budget as a human readable table."""
    p = result.parameters
    width = 50

    def row(label: str, value: float, unit: str, sign: str = "") -> str:
        return f"  {label:<26}{sign:<2}{value:>10.2f} {unit}"

    if band is not None:
        title = f"Link budget - {band.technology} {band.name} ({band.centre_mhz:g} MHz)"
    else:
        title = f"Link budget - {p.frequency_mhz:g} MHz"

    lines = [
        title,
        "=" * width,
        "Transmitter",
        row("Tx power", p.tx_power_dbm, "dBm"),
        row("Tx antenna gain", p.tx_antenna_gain_dbi, "dBi", "+"),
        row("Tx cable loss", p.tx_cable_loss_db, "dB", "-"),
        row("EIRP", result.eirp_dbm, "dBm", "="),
        "Path",
    ]
    if path is not None:
        lines += [
            f"  {'Tx location':<26}{path.tx}",
            f"  {'Rx location':<26}{path.rx}",
            row("Azimuth Tx -> Rx", path.bearing_deg, "deg"),
        ]
    lines += [
        row("Frequency", p.frequency_mhz, "MHz"),
        row("Distance", p.distance_km, "km"),
        row("Free-space path loss", result.path_loss_db, "dB", "-"),
        row("Other losses", p.other_losses_db, "dB", "-"),
    ]
    if path is not None:
        lines += [
            row("1st Fresnel radius (mid)", path.fresnel_radius_midpoint_m, "m"),
            row("60% clearance (mid)", path.clearance_midpoint_m, "m"),
            row("Earth bulge (mid, k=4/3)", path.earth_bulge_midpoint_m(), "m"),
        ]
    lines += [
        "Receiver",
        row("Rx antenna gain", p.rx_antenna_gain_dbi, "dBi", "+"),
        row("Rx cable loss", p.rx_cable_loss_db, "dB", "-"),
        row("Received power", result.rx_power_dbm, "dBm", "="),
        row("Sensitivity", p.rx_sensitivity_dbm, "dBm"),
    ]
    if note and note != "given":
        lines.append(f"    ({note})")
    lines += [
        row("Margin", result.margin_db, "dB"),
        row("Required margin", p.required_margin_db, "dB"),
        "-" * width,
    ]
    verdict = "LINK OK" if result.is_viable else "LINK FAILS"
    lines.append(
        f"Result: {verdict} (margin {result.margin_db:.2f} dB, "
        f"required {p.required_margin_db:.2f} dB)"
    )
    lines.append(f"Max range in free space: {result.max_distance_km:.2f} km")
    lines.append("Note: free space is a best case; real LTE/5G range is much shorter.")
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


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "bands":
        print(format_bands())
        return 0

    try:
        config = _load_config(args.config) if args.config else {}
        cli_values = {key: getattr(args, key) for key in _ALL_OPTIONS}
        options = _merge_options(cli_values, config)
        link = _resolve_link(options)
        if args.map is not None and link.path is None:
            raise ConfigError("--map needs the coordinates of both ends of the link")
        result = compute_link_budget(link.params)
        report = format_report(result, link.band, link.sensitivity_note, link.path)
        map_file = None
        if args.map is not None:
            from radiocoverage.link_map import save_link_map

            map_file = save_link_map(link.path, result, args.map, link.band)
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(report)
    if map_file is not None:
        print(f"Map saved to {map_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
