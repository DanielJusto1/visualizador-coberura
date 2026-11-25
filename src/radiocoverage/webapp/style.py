"""Visual identity of the web interface: CSS and small HTML building blocks."""

from html import escape

import streamlit as st

PRIMARY = "#1f4fd1"

CSS = """
<style>
.block-container {padding-top: 3.2rem; padding-bottom: 3rem; max-width: 1480px;}
h1, h2, h3 {letter-spacing: -0.01em;}
.rc-hero {display: flex; align-items: center; gap: 14px; margin-bottom: .2rem;}
.rc-hero-icon {width: 44px; height: 44px; border-radius: 12px; display: flex;
  align-items: center; justify-content: center; font-size: 24px;
  background: linear-gradient(135deg, #1f4fd1 0%, #3fa1ff 100%); color: white;
  box-shadow: 0 4px 14px rgba(31, 79, 209, .25);}
.rc-hero h1 {font-size: 1.75rem; margin: 0; padding: 0; line-height: 1.2;}
.rc-subtitle {color: #5b6475; margin: 0 0 1rem 58px; font-size: .98rem;}
.rc-verdict {border-radius: 12px; padding: 14px 18px; margin: 0 0 12px 0;
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  flex-wrap: wrap; border: 1px solid;}
.rc-verdict.ok {background: #ecf8f0; border-color: #b9e3c7; color: #0f5c2e;}
.rc-verdict.fail {background: #fdeeee; border-color: #f3c2c0; color: #8a1c17;}
.rc-verdict-title {font-size: 1.15rem; font-weight: 700; letter-spacing: .02em;}
.rc-verdict-detail {font-size: .95rem; opacity: .9;}
.rc-steps {display: grid; gap: 10px; margin-top: 4px;}
.rc-step {display: flex; gap: 12px; align-items: flex-start; padding: 12px 14px;
  border-radius: 12px; border: 1px solid #e3e7ef; background: #fafbfd;}
.rc-step.active {border-color: #9db5f5; background: #f1f5ff;}
.rc-step.done {opacity: .65;}
.rc-step-num {flex: 0 0 28px; height: 28px; border-radius: 50%; display: flex;
  align-items: center; justify-content: center; font-weight: 700; font-size: .9rem;
  background: #e3e9fb; color: #1f4fd1;}
.rc-step.active .rc-step-num {background: #1f4fd1; color: white;}
.rc-step.done .rc-step-num {background: #1a9850; color: white;}
.rc-step-title {font-weight: 600; margin-bottom: 2px;}
.rc-step-text {color: #5b6475; font-size: .9rem;}
.rc-pill {display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: .8rem;
  font-weight: 600; background: #eef2fb; color: #1f4fd1; margin-right: 6px;}
.rc-coords {font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .85rem;
  color: #374151;}
.rc-card {border: 1px solid #e3e7ef; border-radius: 12px; padding: 14px 16px;
  background: white; height: 100%;}
.rc-card h4 {margin: 0 0 6px 0; font-size: 1rem;}
.rc-card p {color: #5b6475; font-size: .9rem; margin: 0;}
.rc-legend {display: flex; flex-wrap: wrap; gap: 6px 14px; font-size: .85rem; color: #374151;}
.rc-swatch {display: inline-block; width: 12px; height: 12px; border-radius: 3px;
  margin-right: 5px; vertical-align: -1px; border: 1px solid rgba(0,0,0,.2);}
.rc-footer {color: #8a93a3; font-size: .78rem; line-height: 1.5;}
div[data-testid="stMetric"] {background: #fafbfd;}
div[data-testid="stMetricValue"] {font-size: 1.45rem;}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def hero(icon: str, title: str, subtitle: str) -> None:
    st.markdown(
        f"<div class='rc-hero'><div class='rc-hero-icon'>{icon}</div>"
        f"<h1>{escape(title)}</h1></div><p class='rc-subtitle'>{escape(subtitle)}</p>",
        unsafe_allow_html=True,
    )


def verdict(ok: bool, title: str, detail: str) -> None:
    icon = "✔" if ok else "✖"
    css = "ok" if ok else "fail"
    st.markdown(
        f"<div class='rc-verdict {css}'><span class='rc-verdict-title'>{icon} "
        f"{escape(title)}</span><span class='rc-verdict-detail'>{escape(detail)}</span></div>",
        unsafe_allow_html=True,
    )


def steps(items: list[tuple[str, str, str]]) -> None:
    """Numbered steps; each item is (state, title, text) with state active/done/todo."""
    html = "".join(
        f"<div class='rc-step {state}'><div class='rc-step-num'>"
        f"{'✓' if state == 'done' else number}</div><div><div class='rc-step-title'>"
        f"{escape(title)}</div><div class='rc-step-text'>{escape(text)}</div></div></div>"
        for number, (state, title, text) in enumerate(items, start=1)
    )
    st.markdown(f"<div class='rc-steps'>{html}</div>", unsafe_allow_html=True)


def legend(entries: list[tuple[str, str]]) -> None:
    html = "".join(
        f"<span><span class='rc-swatch' style='background:{colour}'></span>{escape(label)}</span>"
        for colour, label in entries
    )
    st.markdown(f"<div class='rc-legend'>{html}</div>", unsafe_allow_html=True)


def card(title: str, text: str) -> None:
    st.markdown(
        f"<div class='rc-card'><h4>{escape(title)}</h4><p>{escape(text)}</p></div>",
        unsafe_allow_html=True,
    )
