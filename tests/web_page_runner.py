"""Runs one page of the web interface; used by the AppTest tests in test_webapp.py."""

import importlib

import streamlit as st

from radiocoverage.webapp import style

style.inject_css()
module = importlib.import_module(f"radiocoverage.webapp.pages.{st.session_state['page']}")
module.render()
