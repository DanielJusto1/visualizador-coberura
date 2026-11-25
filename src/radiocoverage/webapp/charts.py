"""Interactive charts (Altair) for the web interface."""

import altair as alt
import numpy as np
import pandas as pd

from radiocoverage.fresnel import CLEARANCE_RATIO
from radiocoverage.i18n import tr
from radiocoverage.link_budget import LinkBudgetResult
from radiocoverage.profile import TerrainProfile
from radiocoverage.propagation import free_space_path_loss_db, path_loss_db

TERRAIN = "#b08d57"
FRESNEL = "#4c78a8"
LOS = "#d62728"
MODEL = "#1f4fd1"
FREE_SPACE = "#9aa4b2"
OK = "#1a9850"
FAIL = "#d73027"


def profile_frame(profile: TerrainProfile, max_points: int = 1500) -> pd.DataFrame:
    step = max(1, len(profile.distances_km) // max_points)
    sl = slice(None, None, step)
    los = profile.line_of_sight_m[sl]
    radius = profile.fresnel_radius_m[sl]
    ground = profile.ground_m[sl]
    return pd.DataFrame(
        {
            "distance_km": profile.distances_km[sl],
            "elevation_m": profile.elevations_m[sl],
            "ground_m": ground,
            "los_m": los,
            "fresnel_low_m": los - radius,
            "fresnel_high_m": los + radius,
            "clearance60_m": los - CLEARANCE_RATIO * radius,
            "clearance_m": los - ground,
        }
    )


def profile_chart(profile: TerrainProfile, lang: str = "en", height: int = 320) -> alt.Chart:
    """Terrain (with Earth bulge), line of sight and first Fresnel zone."""
    data = profile_frame(profile)
    floor = float(min(data["ground_m"].min(), data["fresnel_low_m"].min()))
    floor -= 0.05 * (float(data["fresnel_high_m"].max()) - floor) + 5
    x = alt.X("distance_km:Q", title=tr("web.chart.distance_km", lang),
              scale=alt.Scale(domain=[0, profile.length_km], nice=False))  # fmt: skip
    y_title = tr("web.chart.height_m", lang)
    tooltip = [
        alt.Tooltip("distance_km:Q", title=tr("q.distance", lang) + " (km)", format=".2f"),
        alt.Tooltip("elevation_m:Q", title=tr("web.chart.ground", lang) + " (m)", format=".0f"),
        alt.Tooltip("los_m:Q", title=tr("web.chart.los", lang) + " (m)", format=".0f"),
        alt.Tooltip("clearance_m:Q", title=tr("web.chart.clearance", lang) + " (m)", format=".1f"),
    ]
    base = alt.Chart(data).encode(x=x)
    terrain = base.mark_area(color=TERRAIN, opacity=0.85, line={"color": "#8a6a3b"}).encode(
        y=alt.Y("ground_m:Q", title=y_title, scale=alt.Scale(domainMin=floor, zero=False)),
        y2=alt.datum(floor),
    )
    fresnel = base.mark_area(color=FRESNEL, opacity=0.18).encode(
        y="fresnel_low_m:Q", y2="fresnel_high_m:Q"
    )
    clearance = base.mark_line(color=FRESNEL, strokeDash=[5, 4], strokeWidth=1).encode(
        y="clearance60_m:Q"
    )
    los = base.mark_line(color=LOS, strokeWidth=2).encode(y="los_m:Q")
    hover = alt.selection_point(fields=["distance_km"], nearest=True, on="pointerover",
                                empty=False, clear="pointerout")  # fmt: skip
    rule = (
        base.mark_rule(color="#6b7280")
        .encode(opacity=alt.condition(hover, alt.value(0.6), alt.value(0)), tooltip=tooltip)
        .add_params(hover)
    )
    layers = [terrain, fresnel, clearance, los, rule]
    edge = profile.edge
    if edge is not None and edge.loss_db > 0:
        point = pd.DataFrame(
            {
                "distance_km": [float(edge.distance_m) / 1000.0],
                "height_m": [float(edge.height_m)],
                "label": [f"{float(edge.loss_db):.1f} dB"],
            }
        )
        marker = alt.Chart(point).encode(x="distance_km:Q", y="height_m:Q")
        layers += [
            marker.mark_point(shape="triangle-down", size=120, filled=True, color="black"),
            marker.mark_text(dy=-14, fontSize=11, fontWeight="bold").encode(text="label:N"),
        ]
    return alt.layer(*layers).properties(height=height).interactive(bind_y=False)


def power_distance_frame(
    result: LinkBudgetResult, distance_km: float, points: int = 160
) -> pd.DataFrame:
    p = result.parameters
    top = max(distance_km * 2.5, 1.0)
    d = np.geomspace(0.05, top, points)
    gains = result.eirp_dbm - p.other_losses_db + p.rx_antenna_gain_dbi - p.rx_cable_loss_db
    model = gains - path_loss_db(
        result.model_key, d, p.frequency_mhz, p.tx_height_m, p.rx_height_m, p.environment
    )
    free = gains - free_space_path_loss_db(d, p.frequency_mhz)
    return pd.DataFrame({"distance_km": d, "model_dbm": model, "free_space_dbm": free})


def power_distance_chart(
    result: LinkBudgetResult, distance_km: float, lang: str = "en", height: int = 320
) -> alt.Chart:
    """Received power against distance, with sensitivity, required level and this link."""
    p = result.parameters
    frame = power_distance_frame(result, distance_km)
    model_name = result.model_label
    long = pd.concat(
        [
            frame.assign(curve=model_name, power_dbm=frame["model_dbm"]),
            frame.assign(curve=tr("web.chart.free_space", lang), power_dbm=frame["free_space_dbm"]),
        ]
    )
    colour = alt.Color(
        "curve:N",
        title=None,
        scale=alt.Scale(domain=[model_name, tr("web.chart.free_space", lang)],
                        range=[MODEL, FREE_SPACE]),
        legend=alt.Legend(orient="top"),
    )  # fmt: skip
    lines = (
        alt.Chart(long)
        .mark_line(strokeWidth=2)
        .encode(
            x=alt.X("distance_km:Q", title=tr("web.chart.distance_km", lang),
                    scale=alt.Scale(type="log")),
            y=alt.Y("power_dbm:Q", title=tr("web.chart.power_dbm", lang)),
            color=colour,
            tooltip=[
                alt.Tooltip("curve:N", title=tr("q.model", lang)),
                alt.Tooltip("distance_km:Q", title=tr("q.distance", lang) + " (km)", format=".2f"),
                alt.Tooltip("power_dbm:Q", title=tr("q.rx_power", lang) + " (dBm)", format=".1f"),
            ],
        )
    )  # fmt: skip
    thresholds = pd.DataFrame(
        {
            "power_dbm": [p.rx_sensitivity_dbm, p.rx_sensitivity_dbm + p.required_margin_db],
            "label": [tr("q.sensitivity", lang), tr("web.chart.required_level", lang)],
            "dash": ["solid", "dashed"],
        }
    )
    rules = (
        alt.Chart(thresholds)
        .mark_rule(color=FAIL, strokeWidth=1.2)
        .encode(
            y="power_dbm:Q",
            strokeDash=alt.StrokeDash("dash:N", legend=None,
                                      scale=alt.Scale(domain=["solid", "dashed"],
                                                      range=[[1, 0], [6, 4]])),
            tooltip=[alt.Tooltip("label:N", title=" "),
                     alt.Tooltip("power_dbm:Q", title="dBm", format=".1f")],
        )
    )  # fmt: skip
    point = pd.DataFrame(
        {
            "distance_km": [distance_km],
            "power_dbm": [result.rx_power_dbm],
            "label": [f"{result.rx_power_dbm:.1f} dBm"],
        }
    )
    marker = alt.Chart(point).encode(x="distance_km:Q", y="power_dbm:Q")
    link = [
        marker.mark_point(size=110, filled=True, color=OK if result.is_viable else FAIL),
        marker.mark_text(dx=10, align="left", fontWeight="bold").encode(text="label:N"),
    ]
    return alt.layer(lines, rules, *link).properties(height=height)
