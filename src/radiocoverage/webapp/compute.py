"""Cached computations for the web interface.

Streamlit re-runs the page script on every interaction, so heavy results
(terrain profiles, coverage grids, rendered files) are cached by their inputs.
"""

import tempfile
from dataclasses import replace
from pathlib import Path

import streamlit as st

from radiocoverage.coverage import CoverageResult, Receiver, Site, compute_coverage
from radiocoverage.geo import GeoPoint
from radiocoverage.link_budget import LinkBudgetResult, compute_link_budget
from radiocoverage.path import LinkPath
from radiocoverage.profile import TerrainProfile, plot_profile, terrain_profile
from radiocoverage.terrain import TerrariumTiles
from radiocoverage.webapp.settings import RadioSettings


@st.cache_resource(show_spinner=False)
def terrain_source() -> TerrariumTiles:
    """One shared elevation source per server, so tiles are downloaded only once."""
    return TerrariumTiles()


@st.cache_data(show_spinner=False, max_entries=128)
def link_analysis(
    tx: GeoPoint, rx: GeoPoint, settings: RadioSettings
) -> tuple[LinkPath, LinkBudgetResult, TerrainProfile | None]:
    path = LinkPath(tx, rx, settings.frequency_mhz)
    profile = None
    if settings.terrain:
        profile = terrain_profile(
            path, terrain_source(), settings.tx_height_m, settings.rx_height_m
        )
    loss = profile.diffraction_loss_db if profile is not None else 0.0
    budget = compute_link_budget(settings.link_parameters(path.distance_km, loss))
    return path, budget, profile


@st.cache_data(show_spinner=False, max_entries=16)
def coverage_analysis(
    sites: tuple[Site, ...],
    receiver: Receiver,
    radius_km: float,
    resolution_m: float,
    model: str,
    environment: str,
    terrain: bool,
) -> CoverageResult:
    return compute_coverage(
        sites,
        receiver,
        radius_km=radius_km,
        resolution_m=resolution_m,
        model=model,
        environment=environment,
        terrain=terrain_source() if terrain else None,
    )


@st.cache_data(show_spinner=False, max_entries=32)
def profile_png(tx: GeoPoint, rx: GeoPoint, settings: RadioSettings) -> bytes:
    _, _, profile = link_analysis(tx, rx, replace(settings, terrain=True))
    with tempfile.TemporaryDirectory() as tmp:
        return plot_profile(profile, Path(tmp) / "profile.png", f"{tx} → {rx}").read_bytes()


@st.cache_data(show_spinner=False, max_entries=16)
def relief_url(bounds: tuple, shape: tuple, _result: CoverageResult) -> str:
    """Shaded relief image of a coverage area (cached by the grid it covers)."""
    from radiocoverage.coverage_map import relief_data_url

    return relief_data_url(_result, terrain_source())


@st.cache_data(show_spinner=False, max_entries=8)
def coverage_files_cached(signature: tuple, _result: CoverageResult, lang: str) -> dict[str, bytes]:
    """Files of a result, cached by the signature of the inputs that produced it."""
    return coverage_files(_result, lang)


def coverage_files(result: CoverageResult, lang: str) -> dict[str, bytes]:
    """KMZ, HTML map and PNG image of a coverage result."""
    from radiocoverage.coverage_map import save_coverage_map
    from radiocoverage.coverage_plot import plot_coverage
    from radiocoverage.kmz import save_kmz

    terrain = terrain_source() if result.terrain else None
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        return {
            "kmz": save_kmz(result, folder / "coverage.kmz").read_bytes(),
            "html": save_coverage_map(result, folder / "coverage.html", terrain, lang).read_bytes(),
            "png": plot_coverage(result, folder / "coverage.png", terrain=terrain).read_bytes(),
        }
