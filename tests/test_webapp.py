from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(Path(__file__).resolve().parent.parent / "app" / "streamlit_app.py")


def button(app, key):
    return next(b for b in app.button if b.key == key)


def test_app_loads():
    app = AppTest.from_file(APP, default_timeout=60).run()
    assert not app.exception
    assert "Radio coverage visualizer" in app.title[0].value


def test_coverage_tab():
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.slider(key="cov_r").set_value(2.0)
    button(app, "cov_run").click()
    app.run()
    assert not app.exception
    assert not app.error
    labels = [metric.label for metric in app.metric]
    assert "Covered area" in labels


def test_link_tab():
    app = AppTest.from_file(APP, default_timeout=60).run()
    button(app, "link_run").click()
    app.run()
    assert not app.exception
    assert any("LINK" in message.value for message in [*app.success, *app.error])
    assert "Distance" in [metric.label for metric in app.metric]
