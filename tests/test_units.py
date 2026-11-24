import math

import pytest

from radiocoverage.units import (
    db_to_linear,
    dbm_to_mw,
    dbm_to_w,
    linear_to_db,
    mw_to_dbm,
    w_to_dbm,
    wavelength_m,
)


@pytest.mark.parametrize(
    ("dbm", "mw"),
    [(0.0, 1.0), (10.0, 10.0), (20.0, 100.0), (30.0, 1000.0), (-30.0, 0.001)],
)
def test_dbm_mw_reference_values(dbm, mw):
    assert dbm_to_mw(dbm) == pytest.approx(mw)
    assert mw_to_dbm(mw) == pytest.approx(dbm)


def test_dbm_watts():
    assert dbm_to_w(30.0) == pytest.approx(1.0)
    assert w_to_dbm(40.0) == pytest.approx(46.02, abs=0.01)  # typical LTE macro cell


@pytest.mark.parametrize("dbm", [-120.0, -50.5, 0.0, 17.3, 46.0])
def test_dbm_round_trip(dbm):
    assert mw_to_dbm(dbm_to_mw(dbm)) == pytest.approx(dbm)


def test_doubling_power_adds_3_db():
    assert linear_to_db(2.0) == pytest.approx(3.0103, abs=1e-4)
    assert db_to_linear(3.0103) == pytest.approx(2.0, abs=1e-4)


@pytest.mark.parametrize("bad", [0.0, -1.0])
def test_non_positive_power_rejected(bad):
    with pytest.raises(ValueError):
        mw_to_dbm(bad)
    with pytest.raises(ValueError):
        w_to_dbm(bad)
    with pytest.raises(ValueError):
        linear_to_db(bad)


def test_wavelength():
    assert wavelength_m(300.0) == pytest.approx(0.99931, abs=1e-5)
    assert wavelength_m(3500.0) == pytest.approx(0.08565, abs=1e-5)
    with pytest.raises(ValueError):
        wavelength_m(0.0)


def test_wavelength_times_frequency_is_c():
    assert wavelength_m(800.0) * 800e6 == pytest.approx(299_792_458.0)
    assert not math.isnan(wavelength_m(1e-3))
