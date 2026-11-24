"""Command line interface.

Usage examples::

    radiocoverage link --band B20 --distance 5 --tx-power 46 --tx-gain 17 --sensitivity -100
    radiocoverage link --config examples/lte_b20_rural.toml
    radiocoverage bands
"""

import argparse
import sys
import tomllib
from collections.abc import Sequence
from pathlib import Path

from radiocoverage import __version__
from radiocoverage.bands import BANDS, Band, get_band
from radiocoverage.link_budget import LinkBudgetResult, LinkParameters, compute_link_budget
from radiocoverage.receiver import sensitivity_dbm

# Option name (as used in the config file) -> (help text, default value).
_NUMERIC_OPTIONS: dict[str, tuple[str, float | None]] = {
    "frequency": ("carrier frequency in MHz (alternative to --band)", None),
    "distance": ("distance between transmitter and receiver in km", None),
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
_EXCLUSIVE_GROUPS = (
    ({"band"}, {"frequency"}),
    ({"sensitivity"}, {"bandwidth", "noise_figure", "snr"}),
)


class ConfigError(ValueError):
    """Invalid or incomplete user input."""


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
            "--frequency, and the receiver sensitivity directly with --sensitivity or "
            "derive it from --bandwidth, --noise-figure and --snr. Values can also be "
            "read from a TOML file with --config; command line options take precedence."
        ),
    )
    link.add_argument("--config", type=Path, help="TOML file with link parameters")
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


def _resolve_link(options: dict[str, object]) -> tuple[LinkParameters, Band | None, str]:
    """Turn raw options into validated link parameters.

    Returns the parameters, the band (if any) and a note describing how the
    sensitivity was obtained.
    """
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

    for key in ("distance", "tx_power"):
        if options[key] is None:
            raise ConfigError(f"missing required option --{key.replace('_', '-')}")

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
        distance_km=float(options["distance"]),
        tx_power_dbm=float(options["tx_power"]),
        rx_sensitivity_dbm=rx_sensitivity_dbm,
        tx_antenna_gain_dbi=float(options["tx_gain"]),
        rx_antenna_gain_dbi=float(options["rx_gain"]),
        tx_cable_loss_db=float(options["tx_loss"]),
        rx_cable_loss_db=float(options["rx_loss"]),
        other_losses_db=float(options["other_losses"]),
        required_margin_db=float(options["margin"]),
    )
    return params, band, sensitivity_note


def format_report(result: LinkBudgetResult, band: Band | None = None, note: str = "") -> str:
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
        row("Frequency", p.frequency_mhz, "MHz"),
        row("Distance", p.distance_km, "km"),
        row("Free-space path loss", result.path_loss_db, "dB", "-"),
        row("Other losses", p.other_losses_db, "dB", "-"),
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
        params, band, note = _resolve_link(options)
        result = compute_link_budget(params)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(format_report(result, band, note))
    return 0


if __name__ == "__main__":
    sys.exit(main())
