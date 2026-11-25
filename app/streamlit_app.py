"""Web interface for radiocoverage (Streamlit).

Run locally with:

    streamlit run app/streamlit_app.py

or simply double-click ``ejecutar_windows.bat`` / run ``./ejecutar_mac_linux.sh``.
"""

import sys
from pathlib import Path

# Make the package importable when the app runs from a fresh clone (e.g. Streamlit Cloud).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from radiocoverage.webapp.main import run  # noqa: E402

run()
