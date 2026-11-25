"""Methodology page: what the tool computes and with which models."""

import math

import pandas as pd
import streamlit as st

from radiocoverage import __version__
from radiocoverage.bands import BANDS
from radiocoverage.propagation import MODELS
from radiocoverage.rendering import SIGNAL_CLASSES
from radiocoverage.webapp import style
from radiocoverage.webapp.texts import t

REPOSITORY = "https://github.com/DanielJusto1/visualizador-coberura"


def render() -> None:
    style.hero("📘", t("about.title"), t("about.subtitle"))

    c1, c2, c3 = st.columns(3)
    with c1:
        style.card(t("about.card.planner.title"), t("about.card.planner.text"))
    with c2:
        style.card(t("about.card.network.title"), t("about.card.network.text"))
    with c3:
        style.card(t("about.card.link.title"), t("about.card.link.text"))

    st.subheader(t("about.budget.title"))
    st.write(t("about.budget.text"))
    st.latex(r"P_{rx} = P_{tx} + G_{tx} - L_{tx} - L_{p}(d, f) - L_{dif} - L_{o} "
             r"+ G_{rx} - L_{rx}")  # fmt: skip
    st.latex(r"S = -174\ \mathrm{dBm/Hz} + 10\log_{10}B + NF + SNR_{min}"
             r"\qquad M = P_{rx} - S")  # fmt: skip

    st.subheader(t("about.models.title"))
    st.write(t("about.models.text"))
    st.latex(r"L_{FS} = 20\log_{10} d_{km} + 20\log_{10} f_{MHz} + 32.45")
    st.latex(r"L_{Hata} = 69.55 + 26.16\log_{10} f - 13.82\log_{10} h_b - a(h_m) "
             r"+ (44.9 - 6.55\log_{10} h_b)\log_{10} d")  # fmt: skip
    models = pd.DataFrame(
        [
            {
                t("q.model"): model.label,
                t("about.col.frequency"): "—" if model.key == "free-space"
                else f"{model.frequency_range_mhz[0]:g}–{model.frequency_range_mhz[1]:g} MHz",
                t("about.col.distance"): "—" if math.isinf(model.distance_range_km[1])
                else f"{model.distance_range_km[0]:g}–{model.distance_range_km[1]:g} km",
                t("about.col.reference"): model.reference,
            }
            for model in MODELS.values()
        ]
    )  # fmt: skip
    st.dataframe(models, hide_index=True, width="stretch")
    st.caption(t("about.models.auto"))

    st.subheader(t("about.terrain.title"))
    st.write(t("about.terrain.text"))
    st.latex(r"r_1 = \sqrt{\frac{\lambda\, d_1 d_2}{d_1 + d_2}} \qquad "
             r"h_{bulge} = \frac{d_1 d_2}{2 k R},\ k = 4/3")  # fmt: skip
    st.latex(r"\nu = h\sqrt{\frac{2(d_1+d_2)}{\lambda d_1 d_2}}")
    st.latex(r"J(\nu) = 6.9 + 20\log_{10}\left(\sqrt{(\nu-0.1)^2+1} + \nu - 0.1\right)")

    st.subheader(t("about.colours.title"))
    st.write(t("about.colours.text"))
    style.legend(
        [
            (c.colour, t(f"class.{c.label.lower()}") + ": "
             + t("about.colours.margin", margin=c.margin_db))
            for c in SIGNAL_CLASSES
        ]
    )  # fmt: skip

    st.subheader(t("about.bands.title"))
    bands = pd.DataFrame(
        [
            {
                t("q.band"): band.name,
                t("about.col.technology"): band.technology,
                t("about.col.downlink"):
                    f"{band.downlink_low_mhz:g}–{band.downlink_high_mhz:g} MHz",
                t("about.col.use"): band.typical_use,
            }
            for band in BANDS.values()
        ]
    )  # fmt: skip
    st.dataframe(bands, hide_index=True, width="stretch")

    st.subheader(t("about.limits.title"))
    st.markdown(t("about.limits.text"))

    st.subheader(t("about.sources.title"))
    st.markdown(t("about.sources.text"))
    st.caption(f"radiocoverage v{__version__} · [GitHub]({REPOSITORY})")
