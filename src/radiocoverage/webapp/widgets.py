"""Parameter controls shared by the pages (rendered in the sidebar)."""

import streamlit as st

from radiocoverage.bands import BANDS
from radiocoverage.propagation import ENVIRONMENTS, MODEL_CHOICES
from radiocoverage.receiver import sensitivity_dbm
from radiocoverage.webapp.presets import BAND_KEYS, BAND_PROFILES, TERMINAL_LOCATIONS
from radiocoverage.webapp.settings import RadioSettings
from radiocoverage.webapp.texts import current_language, labels, t


def band_label(key: str) -> str:
    band = BANDS[key]
    return f"{band.name} · {band.technology} {band.centre_mhz:g} MHz"


def _where_label():
    lang = current_language()
    return lambda k: t(f"web.where.{k}", lang, loss=TERMINAL_LOCATIONS[k])


def _environment_label():
    lang = current_language()
    return lambda k: t(f"env.{k}", lang).capitalize()


def _profile_values(band_key: str) -> dict[str, object]:
    profile = BAND_PROFILES[band_key]
    return {
        "txp": profile.tx_power_dbm,
        "txg": profile.tx_gain_dbi,
        "txh": profile.tx_height_m,
        "bw": profile.bandwidth_mhz,
        "nf": profile.noise_figure_db,
        "snr": profile.snr_db,
        "env": profile.environment,
    }


def init_defaults(prefix: str, band_key: str = "b20", **overrides) -> None:
    """Give every control of a page its starting value (only the first time)."""
    defaults = {
        "band": band_key,
        "txl": 2.0,
        "rxh": 1.5,
        "rxg": 0.0,
        "rxl": 3.0,
        "where": "outdoor",
        "extra": 0.0,
        "margin": 6.0,
        "model": "auto",
        "terrain": False,
        **_profile_values(band_key),
        **overrides,
    }
    for name, value in defaults.items():
        st.session_state.setdefault(f"{prefix}_{name}", value)


def apply_band_profile(prefix: str) -> None:
    """When the band changes, load its typical values into the other controls."""
    for name, value in _profile_values(st.session_state[f"{prefix}_band"]).items():
        st.session_state[f"{prefix}_{name}"] = value


def radio_settings(prefix: str, show_terrain: bool = True) -> RadioSettings:
    """Base station, terminal and propagation controls. Returns the chosen settings."""
    ss = st.session_state
    sidebar = st.sidebar
    sidebar.markdown(f"#### {t('web.params.title')}")

    with sidebar.expander(
        t("web.params.base_station"), expanded=True, icon=":material/cell_tower:"
    ):
        st.selectbox(
            t("q.band"), BAND_KEYS, key=f"{prefix}_band", format_func=band_label,
            on_change=apply_band_profile, args=(prefix,), help=t("help.band"),
        )  # fmt: skip
        c1, c2 = st.columns(2)
        c1.number_input(t("web.tx_power"), -10.0, 70.0, step=1.0, key=f"{prefix}_txp",
                        help=t("help.tx_power"))  # fmt: skip
        c2.number_input(t("web.antenna_gain"), -10.0, 40.0, step=1.0, key=f"{prefix}_txg",
                        help=t("help.tx_gain"))  # fmt: skip
        c3, c4 = st.columns(2)
        c3.number_input(t("web.height"), 1.0, 300.0, step=1.0, key=f"{prefix}_txh",
                        help=t("help.tx_height"))  # fmt: skip
        c4.number_input(t("web.cable_loss"), 0.0, 20.0, step=0.5, key=f"{prefix}_txl",
                        help=t("help.tx_loss"))  # fmt: skip
        eirp = ss[f"{prefix}_txp"] + ss[f"{prefix}_txg"] - ss[f"{prefix}_txl"]
        st.caption(t("web.eirp_caption", eirp=eirp, watts=10 ** ((eirp - 30) / 10)))

    with sidebar.expander(t("web.params.terminal"), icon=":material/smartphone:"):
        st.selectbox(
            t("web.terminal_location"), list(TERMINAL_LOCATIONS), key=f"{prefix}_where",
            format_func=_where_label(),
            help=t("help.where"),
        )  # fmt: skip
        c1, c2 = st.columns(2)
        c1.number_input(t("web.height"), 0.5, 50.0, step=0.5, key=f"{prefix}_rxh",
                        help=t("help.rx_height"))  # fmt: skip
        c2.number_input(t("web.body_loss"), 0.0, 20.0, step=0.5, key=f"{prefix}_rxl",
                        help=t("help.rx_loss"))  # fmt: skip
        c3, c4 = st.columns(2)
        c3.number_input(t("web.antenna_gain"), -10.0, 30.0, step=1.0, key=f"{prefix}_rxg",
                        help=t("help.rx_gain"))  # fmt: skip
        c4.number_input(t("web.extra_loss"), 0.0, 60.0, step=1.0, key=f"{prefix}_extra",
                        help=t("help.extra_loss"))  # fmt: skip
        st.markdown(f"**{t('web.receiver_sensitivity')}**")
        c5, c6, c7 = st.columns(3)
        c5.number_input(t("web.bandwidth"), 0.2, 400.0, step=5.0, key=f"{prefix}_bw",
                        help=t("help.bandwidth"))  # fmt: skip
        c6.number_input("NF (dB)", 0.0, 20.0, step=0.5, key=f"{prefix}_nf",
                        help=t("help.noise_figure"))  # fmt: skip
        c7.number_input("SNR (dB)", -15.0, 40.0, step=0.5, key=f"{prefix}_snr",
                        help=t("help.snr"))  # fmt: skip
        sensitivity = sensitivity_dbm(ss[f"{prefix}_bw"], ss[f"{prefix}_nf"], ss[f"{prefix}_snr"])
        st.caption(t("web.sensitivity_caption", value=sensitivity))
        st.slider(t("web.fade_margin"), 0.0, 20.0, step=0.5, key=f"{prefix}_margin",
                  help=t("help.margin"))  # fmt: skip

    with sidebar.expander(t("web.params.propagation"), icon=":material/waves:"):
        st.selectbox(
            t("q.model"), MODEL_CHOICES, key=f"{prefix}_model",
            format_func=labels("web.model."), help=t("help.model"),
        )  # fmt: skip
        st.selectbox(
            t("q.environment"), ENVIRONMENTS, key=f"{prefix}_env",
            format_func=_environment_label(), help=t("help.environment"),
        )  # fmt: skip
        if show_terrain:
            st.toggle(t("web.real_terrain"), key=f"{prefix}_terrain", help=t("help.terrain"))

    where_loss = TERMINAL_LOCATIONS[ss[f"{prefix}_where"]]
    return RadioSettings(
        band_key=ss[f"{prefix}_band"],
        tx_power_dbm=float(ss[f"{prefix}_txp"]),
        tx_gain_dbi=float(ss[f"{prefix}_txg"]),
        tx_loss_db=float(ss[f"{prefix}_txl"]),
        tx_height_m=float(ss[f"{prefix}_txh"]),
        rx_height_m=float(ss[f"{prefix}_rxh"]),
        rx_gain_dbi=float(ss[f"{prefix}_rxg"]),
        rx_loss_db=float(ss[f"{prefix}_rxl"]),
        other_losses_db=float(where_loss + ss[f"{prefix}_extra"]),
        sensitivity_dbm=float(sensitivity),
        margin_db=float(ss[f"{prefix}_margin"]),
        model=ss[f"{prefix}_model"],
        environment=ss[f"{prefix}_env"],
        terrain=bool(ss[f"{prefix}_terrain"]) if show_terrain else False,
    )
