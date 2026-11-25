"""Entry point of the web interface: page setup, sidebar and navigation."""

from pathlib import Path

import streamlit as st

from radiocoverage import __version__
from radiocoverage.i18n import LANGUAGES
from radiocoverage.webapp import style
from radiocoverage.webapp.pages import about, link, network, planner
from radiocoverage.webapp.texts import current_language, t

ASSETS = Path(__file__).parent / "assets"
REPOSITORY = "https://github.com/DanielJusto1/visualizador-coberura"


def _language_selector() -> None:
    """Spanish / English switch. The choice is also kept in the URL (``?lang=en``)."""
    if "lang" not in st.session_state:
        requested = st.query_params.get("lang")
        st.session_state["lang"] = requested if requested in LANGUAGES else "es"
    choice = st.sidebar.segmented_control(
        "🌐", list(LANGUAGES), format_func=lambda k: LANGUAGES[k], key="lang_choice",
        default=st.session_state["lang"], label_visibility="collapsed",
    )  # fmt: skip
    if choice and choice != st.session_state["lang"]:
        st.session_state["lang"] = choice
        st.query_params["lang"] = choice
        st.rerun()


def _footer() -> None:
    st.sidebar.markdown(
        f"<div class='rc-footer'>{t('web.footer', version=__version__)}<br>"
        f"<a href='{REPOSITORY}' target='_blank'>GitHub</a></div>",
        unsafe_allow_html=True,
    )


def run() -> None:
    st.set_page_config(
        page_title="RadioCoverage · LTE/5G",
        page_icon=str(ASSETS / "icon.svg"),
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={"About": f"RadioCoverage v{__version__} · {REPOSITORY}"},
    )
    st.logo(str(ASSETS / "logo.svg"), size="large", link=REPOSITORY,
            icon_image=str(ASSETS / "icon.svg"))  # fmt: skip
    style.inject_css()
    _language_selector()
    current_language()

    pages = {
        t("nav.tools"): [
            st.Page(planner.render, title=t("nav.planner"), icon=":material/add_location_alt:",
                    url_path="planner", default=True),
            st.Page(network.render, title=t("nav.network"), icon=":material/cell_tower:",
                    url_path="network"),
            st.Page(link.render, title=t("nav.link"), icon=":material/settings_input_antenna:",
                    url_path="link"),
        ],
        t("nav.info"): [
            st.Page(about.render, title=t("nav.about"), icon=":material/menu_book:",
                    url_path="about"),
        ],
    }  # fmt: skip
    navigation = st.navigation(pages)
    navigation.run()
    _footer()
