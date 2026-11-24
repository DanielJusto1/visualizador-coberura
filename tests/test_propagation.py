import math

import pytest

from radiocoverage.propagation import free_space_distance_km, free_space_path_loss_db
from radiocoverage.units import wavelength_m


@pytest.mark.parametrize(
    ("distance_km", "frequency_mhz", "expected_db"),
    [
        (1.0, 2400.0, 100.05),  # classic Wi-Fi textbook value
        (1.0, 1.0, 32.45),  # the constant of the formula
        (10.0, 806.0, 110.57),  # LTE B20
        (0.5, 3600.0, 97.55),  # 5G n78
    ],
)
def test_reference_values(distance_km, frequency_mhz, expected_db):
    assert free_space_path_loss_db(distance_km, frequency_mhz) == pytest.approx(
        expected_db, abs=0.01
    )


def test_matches_friis_definition():
    distance_m = 3_000.0
    frequency_mhz = 1842.5
    friis_db = 20 * math.log10(4 * math.pi * distance_m / wavelength_m(frequency_mhz))
    assert free_space_path_loss_db(3.0, frequency_mhz) == pytest.approx(friis_db)


def test_doubling_distance_adds_6_db():
    base = free_space_path_loss_db(2.0, 1800.0)
    assert free_space_path_loss_db(4.0, 1800.0) - base == pytest.approx(6.0206, abs=1e-4)


def test_ten_times_distance_adds_20_db():
    base = free_space_path_loss_db(1.0, 800.0)
    assert free_space_path_loss_db(10.0, 800.0) - base == pytest.approx(20.0)


def test_higher_frequency_loses_more():
    assert free_space_path_loss_db(1.0, 3600.0) > free_space_path_loss_db(1.0, 800.0)


@pytest.mark.parametrize("distance_km", [0.05, 1.0, 12.3, 250.0])
def test_inverse_recovers_distance(distance_km):
    loss = free_space_path_loss_db(distance_km, 942.5)
    assert free_space_distance_km(loss, 942.5) == pytest.approx(distance_km)


@pytest.mark.parametrize(
    ("distance_km", "frequency_mhz"),
    [(0.0, 800.0), (-1.0, 800.0), (1.0, 0.0), (1.0, -5.0), (math.inf, 800.0), (math.nan, 800.0)],
)
def test_invalid_inputs_rejected(distance_km, frequency_mhz):
    with pytest.raises(ValueError):
        free_space_path_loss_db(distance_km, frequency_mhz)


# --- Empirical models ----------------------------------------------------------------

import numpy as np  # noqa: E402

from radiocoverage.propagation import (  # noqa: E402
    ENVIRONMENTS,
    MODELS,
    auto_model_key,
    cost231_hata_db,
    get_model,
    max_distance_km,
    okumura_hata_db,
    path_loss_db,
    rma_nlos_db,
    uma_nlos_db,
)


def test_okumura_hata_textbook_value():
    # 900 MHz, hb = 30 m, hm = 1.5 m, 1 km, medium city: 126.4 dB (classic worked example)
    assert okumura_hata_db(1.0, 900.0, 30.0, 1.5) == pytest.approx(126.40, abs=0.01)


def test_okumura_hata_distance_slope():
    # Slope is 44.9 - 6.55 log10(hb) dB per decade: 35.2 dB/decade for hb = 30 m
    diff = okumura_hata_db(10.0, 900.0, 30.0, 1.5) - okumura_hata_db(1.0, 900.0, 30.0, 1.5)
    assert diff == pytest.approx(44.9 - 6.55 * math.log10(30.0))


def test_hata_environment_ordering():
    losses = [okumura_hata_db(5.0, 806.0, 30.0, 1.5, env) for env in ENVIRONMENTS]
    dense, urban, suburban, rural = losses
    assert dense >= urban > suburban > rural


def test_cost231_formula():
    log_f = math.log10(1800.0)
    a_hm = (1.1 * log_f - 0.7) * 1.5 - (1.56 * log_f - 0.8)
    expected = 46.3 + 33.9 * log_f - 13.82 * math.log10(30.0) - a_hm
    assert cost231_hata_db(1.0, 1800.0, 30.0, 1.5) == pytest.approx(expected)
    dense = cost231_hata_db(1.0, 1800.0, 30.0, 1.5, "dense-urban")
    assert dense > cost231_hata_db(1.0, 1800.0, 30.0, 1.5)


def test_uma_nlos_formula():
    # 38.901 UMa NLOS dominates far from the site: 13.54 + 39.08 log10(d3D) + 20 log10(fc)
    d3d = math.hypot(1000.0, 25.0 - 1.5)
    expected = 13.54 + 39.08 * math.log10(d3d) + 20 * math.log10(3.5)
    assert uma_nlos_db(1.0, 3500.0, 25.0, 1.5) == pytest.approx(expected)


def test_rma_is_continuous_at_breakpoint_and_increasing():
    d = np.geomspace(0.02, 10, 400)
    assert np.all(np.diff(rma_nlos_db(d, 800.0, 35.0, 1.5)) > 0)
    breakpoint_km = 2 * math.pi * 35.0 * 1.5 * 0.8e9 / 299_792_458.0 / 1000
    just_before = rma_nlos_db(breakpoint_km * 0.9999, 800.0, 35.0, 1.5)
    just_after = rma_nlos_db(breakpoint_km * 1.0001, 800.0, 35.0, 1.5)
    assert just_after - just_before == pytest.approx(0.0, abs=0.05)


@pytest.mark.parametrize("model", list(MODELS))
def test_models_never_beat_free_space(model):
    frequency = {"okumura-hata": 900.0, "cost231-hata": 1800.0}.get(model, 2600.0)
    d = np.geomspace(0.02, 30, 50)
    loss = path_loss_db(model, d, frequency, 30.0, 1.5, "rural")
    assert np.all(loss >= free_space_path_loss_db(d, frequency) - 1e-9)
    assert np.all(np.diff(loss) > 0)


def test_array_and_scalar_agree():
    d = np.array([0.5, 1.0, 5.0])
    array = path_loss_db("auto", d, 806.0, 30.0, 1.5, "urban")
    assert isinstance(path_loss_db("auto", 1.0, 806.0), float)
    assert array[1] == pytest.approx(path_loss_db("auto", 1.0, 806.0, 30.0, 1.5, "urban"))


@pytest.mark.parametrize(
    ("frequency", "expected"),
    [(773, "okumura-hata"), (806, "okumura-hata"), (942.5, "okumura-hata"),
     (1842.5, "cost231-hata"), (2140, "3gpp"), (2655, "3gpp"), (3600, "3gpp")],
)  # fmt: skip
def test_auto_model_choice(frequency, expected):
    assert auto_model_key(frequency) == expected
    assert get_model("auto", frequency).key == expected


def test_model_frequency_range_is_enforced():
    with pytest.raises(ValueError, match="only valid from 150 to 1500"):
        get_model("okumura-hata", 3600.0)
    with pytest.raises(ValueError, match="Unknown propagation model"):
        get_model("magic", 800.0)
    with pytest.raises(ValueError, match="Unknown environment"):
        path_loss_db("auto", 1.0, 800.0, environment="jungle")
    with pytest.raises(ValueError):
        path_loss_db("auto", 1.0, 800.0, tx_height_m=0.0)


@pytest.mark.parametrize("model", ["free-space", "okumura-hata", "3gpp"])
def test_max_distance_inverts_path_loss(model):
    frequency = 900.0
    target = float(path_loss_db(model, 3.7, frequency, 30.0, 1.5, "suburban"))
    found = max_distance_km(model, target, frequency, 30.0, 1.5, "suburban")
    assert found == pytest.approx(3.7, rel=1e-6)


def test_max_distance_limits():
    assert max_distance_km("okumura-hata", 500.0, 900.0) == math.inf
    assert max_distance_km("okumura-hata", 10.0, 900.0) == 0.0


def test_validity_warnings():
    hata = MODELS["okumura-hata"]
    assert hata.validity_warnings(5.0, 30.0, 1.5) == []
    warnings = hata.validity_warnings(0.5, 20.0, 15.0)
    assert len(warnings) == 3
    assert "distance 0.5 km" in warnings[0]
    assert MODELS["free-space"].validity_warnings(1e4, 1.0, 1.0) == []
