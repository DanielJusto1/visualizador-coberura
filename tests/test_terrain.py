import numpy as np
import pytest

from radiocoverage.terrain import (
    TILE_SIZE,
    FlatTerrain,
    SyntheticTerrain,
    TerrainError,
    TerrariumTiles,
    decode_terrarium,
    encode_terrarium,
    lonlat_to_pixel,
)


def test_terrarium_round_trip():
    elevation = np.linspace(-50, 3700, TILE_SIZE * TILE_SIZE).reshape(TILE_SIZE, TILE_SIZE)
    decoded = decode_terrarium(encode_terrarium(elevation))
    assert np.allclose(decoded, elevation, atol=1 / 256)


def test_lonlat_to_pixel():
    x, y = lonlat_to_pixel(np.array([0.0]), np.array([0.0]), zoom=0)
    assert x[0] == pytest.approx(128) and y[0] == pytest.approx(128)


def make_fake_fetch(calls):
    """Tiles whose elevation equals the global pixel column (a linear ramp)."""

    def fetch(url):
        z, x, y = (int(part) for part in url.removesuffix(".png").split("/")[-3:])
        calls.append((z, x, y))
        columns = x * TILE_SIZE + np.arange(TILE_SIZE) + 0.5
        return encode_terrarium(np.tile(columns, (TILE_SIZE, 1)) / 100.0)

    return fetch


def test_tiles_bilinear_and_cache(tmp_path):
    calls = []
    tiles = TerrariumTiles(zoom=10, cache_dir=tmp_path, fetch=make_fake_fetch(calls))
    lats = np.array([40.0, 40.5, 41.0])
    lons = np.array([-3.7, -3.2, -4.1])
    x, _ = lonlat_to_pixel(lats, lons, 10)
    elevation = tiles.elevation_m(lats, lons)
    assert np.allclose(elevation, x / 100.0, atol=0.01)
    assert calls  # downloaded

    calls.clear()
    again = TerrariumTiles(zoom=10, cache_dir=tmp_path, fetch=make_fake_fetch(calls))
    assert np.allclose(again.elevation_m(lats, lons), elevation)
    assert calls == []  # served from the disk cache


def test_elevation_keeps_shape(tmp_path):
    tiles = TerrariumTiles(zoom=8, cache_dir=tmp_path, fetch=make_fake_fetch([]))
    lats, lons = np.meshgrid(np.linspace(40, 40.2, 4), np.linspace(-3.8, -3.6, 5), indexing="ij")
    assert tiles.elevation_m(lats, lons).shape == (4, 5)


def test_too_many_tiles(tmp_path):
    tiles = TerrariumTiles(zoom=12, cache_dir=tmp_path, fetch=make_fake_fetch([]), max_tiles=4)
    with pytest.raises(TerrainError, match="elevation tiles"):
        tiles.elevation_m(np.array([40.0, 41.0]), np.array([-4.0, -3.0]))


def test_corrupt_tile(tmp_path):
    tiles = TerrariumTiles(zoom=10, cache_dir=tmp_path, fetch=lambda url: b"not a png")
    with pytest.raises(TerrainError, match="invalid elevation tile"):
        tiles.elevation_m(np.array([40.0]), np.array([-3.7]))
    assert not list(tmp_path.rglob("*.png"))  # bad file not left in the cache


def test_download_errors_become_terrain_errors(tmp_path):
    def failing(url):
        raise TerrainError("offline")

    with pytest.raises(OSError, match="offline"):
        TerrariumTiles(cache_dir=tmp_path, fetch=failing).elevation_m(
            np.array([40.0]), np.array([-3.7])
        )


def test_invalid_zoom():
    with pytest.raises(ValueError):
        TerrariumTiles(zoom=20)


def test_flat_and_synthetic_terrain():
    assert np.all(FlatTerrain(600).elevation_m(np.zeros((2, 3)), np.zeros((2, 3))) == 600)
    ridge = SyntheticTerrain(lambda lat, lon: 100 * lat)
    assert ridge.elevation_m(np.array([1.0, 2.0]), np.array([0.0, 0.0])).tolist() == [100, 200]
