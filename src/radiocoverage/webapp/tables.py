"""Tables shown in the web interface (pure functions, no Streamlit)."""

import math

from radiocoverage.i18n import tr
from radiocoverage.link_budget import LinkBudgetResult
from radiocoverage.path import LinkPath
from radiocoverage.profile import TerrainProfile


def _fmt(value: float, unit: str, sign: str = "") -> str:
    return f"{sign}{value:.2f} {unit}".strip() if sign else f"{value:.2f} {unit}"


def link_budget_rows(
    result: LinkBudgetResult,
    path: LinkPath | None = None,
    profile: TerrainProfile | None = None,
    lang: str = "en",
) -> list[dict[str, str]]:
    """Link budget as rows with ``section``, ``item`` and ``value`` (ready for a table)."""
    p = result.parameters
    tx, prop, rx, res = (
        tr("web.section.tx", lang),
        tr("web.section.path", lang),
        tr("web.section.rx", lang),
        tr("web.section.result", lang),
    )
    rows: list[tuple[str, str, str]] = [
        (tx, tr("q.tx_power", lang), _fmt(p.tx_power_dbm, "dBm")),
        (tx, tr("q.tx_gain", lang), _fmt(p.tx_antenna_gain_dbi, "dBi", "+ ")),
        (tx, tr("q.tx_loss", lang), _fmt(p.tx_cable_loss_db, "dB", "− ")),
        (tx, tr("q.eirp", lang), _fmt(result.eirp_dbm, "dBm", "= ")),
    ]
    if path is not None:
        rows += [
            (prop, tr("q.distance", lang), f"{path.distance_km:.3f} km"),
            (prop, tr("q.azimuth_tx_rx", lang), f"{path.bearing_deg:.1f}°"),
        ]
    rows += [
        (prop, tr("q.frequency", lang), f"{p.frequency_mhz:g} MHz"),
        (prop, tr("q.model", lang), result.model_label),
    ]
    if result.model_key != "free-space":
        rows.append((prop, tr("q.environment", lang), tr(f"env.{p.environment}", lang)))
    loss_label = "q.free_space_loss" if result.model_key == "free-space" else "q.path_loss"
    rows.append((prop, tr(loss_label, lang), _fmt(result.path_loss_db, "dB", "− ")))
    if profile is not None:
        rows += [
            (prop, tr("q.terrain", lang), tr(f"terrain.{profile.status_key}", lang)),
            (
                prop,
                tr("q.fresnel_clearance", lang),
                f"{profile.min_clearance_ratio * 100:.0f} %"
                if math.isfinite(profile.min_clearance_ratio)
                else "—",
            ),
            (prop, tr("q.diffraction_loss", lang), _fmt(profile.diffraction_loss_db, "dB", "− ")),
        ]
    rows.append((prop, tr("q.other_losses", lang), _fmt(p.other_losses_db, "dB", "− ")))
    rows += [
        (rx, tr("q.rx_gain", lang), _fmt(p.rx_antenna_gain_dbi, "dBi", "+ ")),
        (rx, tr("q.rx_loss", lang), _fmt(p.rx_cable_loss_db, "dB", "− ")),
        (rx, tr("q.rx_power", lang), _fmt(result.rx_power_dbm, "dBm", "= ")),
        (rx, tr("q.sensitivity", lang), _fmt(p.rx_sensitivity_dbm, "dBm")),
        (res, tr("q.margin", lang), _fmt(result.margin_db, "dB")),
        (res, tr("q.required_margin", lang), _fmt(p.required_margin_db, "dB")),
        (res, tr("web.result.verdict", lang),
         tr("verdict.ok" if result.is_viable else "verdict.fail", lang)),
        (res, tr("q.max_range", lang),
         "> 2000 km" if math.isinf(result.max_distance_km) else f"{result.max_distance_km:.2f} km"),
    ]  # fmt: skip
    keys = ("section", "item", "value")
    return [dict(zip(keys, row, strict=True)) for row in rows]


def budget_csv(rows: list[dict[str, str]]) -> str:
    """CSV text of the budget rows (semicolon separated, as Spanish spreadsheets expect)."""
    lines = ["section;item;value"]
    lines += [
        ";".join(row[k].replace(";", ",") for k in ("section", "item", "value")) for row in rows
    ]
    return "\n".join(lines) + "\n"
