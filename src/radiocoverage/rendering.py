"""Colours and images shared by the coverage map, the KMZ export and the static plot."""

import base64
import io
import math
from dataclasses import dataclass

import numpy as np

OVERLAY_ALPHA = 175


@dataclass(frozen=True)
class SignalClass:
    label: str
    margin_db: float  # minimum margin above the receiver sensitivity
    colour: str


SIGNAL_CLASSES = (
    SignalClass("Excellent", 30.0, "#1a9850"),
    SignalClass("Good", 20.0, "#91cf60"),
    SignalClass("Fair", 10.0, "#fee08b"),
    SignalClass("Weak", 0.0, "#fc8d59"),
)
"""Signal levels by margin above sensitivity. Below sensitivity: no service (transparent)."""

SERVER_COLOURS = (
    "#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f",
    "#edc948", "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac",
)  # fmt: skip


def hex_to_rgb(colour: str) -> tuple[int, int, int]:
    colour = colour.lstrip("#")
    return tuple(int(colour[i : i + 2], 16) for i in (0, 2, 4))


def class_ranges_dbm(sensitivity_dbm: float) -> list[tuple[SignalClass, str]]:
    """Legend text for every signal class, in dBm."""
    out = []
    upper = None
    for signal_class in SIGNAL_CLASSES:
        lower = sensitivity_dbm + signal_class.margin_db
        text = f"≥ {lower:.0f} dBm" if upper is None else f"{lower:.0f} to {upper:.0f} dBm"
        out.append((signal_class, text))
        upper = lower
    return out


def signal_rgba(power_dbm: np.ndarray, sensitivity_dbm: float) -> np.ndarray:
    """RGBA image (uint8) of signal classes; transparent below sensitivity."""
    rgba = np.zeros((*power_dbm.shape, 4), dtype=np.uint8)
    margin = power_dbm - sensitivity_dbm
    upper = np.inf
    for signal_class in SIGNAL_CLASSES:
        mask = (margin >= signal_class.margin_db) & (margin < upper)
        rgba[mask] = (*hex_to_rgb(signal_class.colour), OVERLAY_ALPHA)
        upper = signal_class.margin_db
    return rgba


def server_colour(index: int) -> str:
    return SERVER_COLOURS[index % len(SERVER_COLOURS)]


def server_rgba(best_server: np.ndarray) -> np.ndarray:
    """RGBA image (uint8) colouring each pixel by its best server (-1 = transparent)."""
    rgba = np.zeros((*best_server.shape, 4), dtype=np.uint8)
    for index in np.unique(best_server[best_server >= 0]):
        rgba[best_server == index] = (*hex_to_rgb(server_colour(int(index))), OVERLAY_ALPHA)
    return rgba


def _mercator_y(lat_deg: np.ndarray | float) -> np.ndarray | float:
    lat = np.radians(lat_deg)
    return np.log(np.tan(math.pi / 4 + lat / 2))


def mercator_resample(rgba: np.ndarray, south: float, north: float) -> np.ndarray:
    """Re-sample image rows (north to south, equally spaced in latitude) so they are
    equally spaced in Web Mercator, as Leaflet expects for image overlays."""
    rows = rgba.shape[0]
    y_top, y_bottom = _mercator_y(north), _mercator_y(south)
    target_y = y_top + (y_bottom - y_top) * (np.arange(rows) + 0.5) / rows
    target_lat = np.degrees(2 * np.arctan(np.exp(target_y)) - math.pi / 2)
    source_row = np.clip(((north - target_lat) / (north - south) * rows).astype(int), 0, rows - 1)
    return rgba[source_row]


def png_bytes(rgba: np.ndarray) -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.fromarray(np.ascontiguousarray(rgba), "RGBA").save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def png_data_url(rgba: np.ndarray) -> str:
    return "data:image/png;base64," + base64.b64encode(png_bytes(rgba)).decode("ascii")
