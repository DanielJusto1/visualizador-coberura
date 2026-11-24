"""Terrain elevation sources.

Real terrain comes from the open *Terrarium* elevation tiles (Tilezen / AWS Open
Data, built from SRTM and other public digital elevation models). Tiles are
downloaded on demand and cached on disk, so each area is fetched only once.

Each tile is a 256x256 PNG where elevation = R*256 + G + B/256 - 32768 metres.
"""

import io
import math
import os
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

import numpy as np

TERRARIUM_URL = "https://elevation-tiles-prod.s3.amazonaws.com/terrarium/{z}/{x}/{y}.png"
TILE_SIZE = 256
DEFAULT_ZOOM = 12
"""Zoom 12 gives ~29 m pixels in Spain, close to the resolution of the source data."""


class TerrainError(OSError):
    """Elevation data could not be obtained."""


class ElevationSource(Protocol):
    def elevation_m(self, lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
        """Ground elevation above sea level, in metres, for arrays of coordinates."""


class FlatTerrain:
    """Constant elevation everywhere (useful as a reference and in tests)."""

    def __init__(self, elevation_m: float = 0.0) -> None:
        self.value = float(elevation_m)

    def elevation_m(self, lats, lons) -> np.ndarray:
        return np.full(np.broadcast(np.asarray(lats), np.asarray(lons)).shape, self.value)


class SyntheticTerrain:
    """Elevation given by a function ``f(lats, lons) -> metres`` (tests and demos)."""

    def __init__(self, function: Callable[[np.ndarray, np.ndarray], np.ndarray]) -> None:
        self.function = function

    def elevation_m(self, lats, lons) -> np.ndarray:
        return np.asarray(self.function(np.asarray(lats, float), np.asarray(lons, float)), float)


def default_cache_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
    return Path(base) / "radiocoverage" / "terrarium"


def lonlat_to_pixel(lats, lons, zoom: int) -> tuple[np.ndarray, np.ndarray]:
    """Global Web Mercator pixel coordinates (float) at ``zoom``."""
    lat = np.clip(np.asarray(lats, float), -85.0511, 85.0511)
    size = TILE_SIZE * 2**zoom
    x = (np.asarray(lons, float) + 180.0) / 360.0 * size
    lat_rad = np.radians(lat)
    y = (1.0 - np.log(np.tan(lat_rad) + 1.0 / np.cos(lat_rad)) / math.pi) / 2.0 * size
    return x, y


def decode_terrarium(png_bytes: bytes) -> np.ndarray:
    """Decode a Terrarium PNG tile into a 256x256 array of elevations in metres."""
    from PIL import Image

    with Image.open(io.BytesIO(png_bytes)) as image:
        rgb = np.asarray(image.convert("RGB"), dtype=np.float32)
    return rgb[..., 0] * 256.0 + rgb[..., 1] + rgb[..., 2] / 256.0 - 32768.0


def encode_terrarium(elevation_m: np.ndarray) -> bytes:
    """Encode an array of elevations as a Terrarium PNG (inverse of decode)."""
    from PIL import Image

    value = np.asarray(elevation_m, dtype=np.float64) + 32768.0
    r = np.floor(value / 256.0)
    g = np.floor(value - r * 256.0)
    b = np.round((value - r * 256.0 - g) * 256.0)
    rgb = np.clip(np.stack([r, g, b], axis=-1), 0, 255).astype(np.uint8)
    buffer = io.BytesIO()
    Image.fromarray(rgb, "RGB").save(buffer, format="PNG")
    return buffer.getvalue()


def _download(url: str) -> bytes:
    import requests

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise TerrainError(f"could not download elevation tile {url}: {exc}") from None
    return response.content


class TerrariumTiles:
    """Elevation from Terrarium tiles with an on-disk cache and bilinear interpolation."""

    def __init__(
        self,
        zoom: int = DEFAULT_ZOOM,
        cache_dir: Path | None = None,
        fetch: Callable[[str], bytes] = _download,
        max_tiles: int = 800,
    ) -> None:
        if not 1 <= zoom <= 15:
            raise ValueError(f"Terrain zoom must be between 1 and 15, got {zoom}")
        self.zoom = zoom
        self.cache_dir = Path(cache_dir) if cache_dir is not None else default_cache_dir()
        self.fetch = fetch
        self.max_tiles = max_tiles
        self._tiles: dict[tuple[int, int], np.ndarray] = {}

    @property
    def pixel_size_m(self) -> float:
        """Pixel size at 40°N, a typical latitude for Spain."""
        return 40_075_016.7 / (TILE_SIZE * 2**self.zoom) * math.cos(math.radians(40.0))

    def _tile(self, x: int, y: int) -> np.ndarray:
        key = (x, y)
        if key not in self._tiles:
            path = self.cache_dir / str(self.zoom) / str(x) / f"{y}.png"
            if path.exists():
                data = path.read_bytes()
            else:
                data = self.fetch(TERRARIUM_URL.format(z=self.zoom, x=x, y=y))
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            try:
                self._tiles[key] = decode_terrarium(data)
            except Exception as exc:  # corrupt download or cache entry
                path.unlink(missing_ok=True)
                raise TerrainError(f"invalid elevation tile {self.zoom}/{x}/{y}: {exc}") from None
        return self._tiles[key]

    def _pixels(self, ix: np.ndarray, iy: np.ndarray) -> np.ndarray:
        """Elevation of integer global pixels (fetching the tiles they belong to)."""
        limit = TILE_SIZE * 2**self.zoom - 1
        ix = np.clip(ix, 0, limit)
        iy = np.clip(iy, 0, limit)
        tx0, tx1 = int(ix.min()) // TILE_SIZE, int(ix.max()) // TILE_SIZE
        ty0, ty1 = int(iy.min()) // TILE_SIZE, int(iy.max()) // TILE_SIZE
        count = (tx1 - tx0 + 1) * (ty1 - ty0 + 1)
        if count > self.max_tiles:
            raise TerrainError(
                f"the area needs {count} elevation tiles (limit {self.max_tiles}); "
                "use a smaller radius or a lower terrain zoom"
            )
        # Assemble the tiles into one mosaic and index it directly (fast for big grids).
        mosaic = np.empty(((ty1 - ty0 + 1) * TILE_SIZE, (tx1 - tx0 + 1) * TILE_SIZE))
        for ty in range(ty0, ty1 + 1):
            for tx in range(tx0, tx1 + 1):
                row, col = (ty - ty0) * TILE_SIZE, (tx - tx0) * TILE_SIZE
                mosaic[row : row + TILE_SIZE, col : col + TILE_SIZE] = self._tile(tx, ty)
        return mosaic[iy - ty0 * TILE_SIZE, ix - tx0 * TILE_SIZE]

    def elevation_m(self, lats, lons) -> np.ndarray:
        lats, lons = np.broadcast_arrays(np.asarray(lats, float), np.asarray(lons, float))
        shape = lats.shape
        x, y = lonlat_to_pixel(lats.ravel(), lons.ravel(), self.zoom)
        # Pixel centres sit at integer + 0.5.
        x, y = x - 0.5, y - 0.5
        x0, y0 = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
        fx, fy = x - x0, y - y0
        corners = self._pixels(
            np.concatenate([x0, x0 + 1, x0, x0 + 1]), np.concatenate([y0, y0, y0 + 1, y0 + 1])
        )
        z00, z10, z01, z11 = np.split(corners, 4)
        top = z00 * (1 - fx) + z10 * fx
        bottom = z01 * (1 - fx) + z11 * fx
        return (top * (1 - fy) + bottom * fy).reshape(shape)
