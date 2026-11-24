import numpy as np
import pytest

from radiocoverage.antenna import angle_off_boresight_deg, sector_attenuation_db


def test_angle_off_boresight_wraps_around():
    assert angle_off_boresight_deg(350.0, 10.0) == pytest.approx(20.0)
    assert angle_off_boresight_deg(10.0, 350.0) == pytest.approx(20.0)
    assert angle_off_boresight_deg(190.0, 10.0) == pytest.approx(180.0)
    assert np.allclose(angle_off_boresight_deg(np.array([0, 90, 180]), 0.0), [0, 90, 180])


def test_sector_pattern():
    assert sector_attenuation_db(0.0) == 0.0
    assert sector_attenuation_db(32.5) == pytest.approx(3.0)  # half of the 65° beamwidth
    assert sector_attenuation_db(180.0) == pytest.approx(25.0)  # front-to-back ratio
    assert sector_attenuation_db(180.0, front_to_back_db=30.0) == pytest.approx(30.0)


@pytest.mark.parametrize("kwargs", [{"beamwidth_deg": 0}, {"front_to_back_db": -1}])
def test_invalid_pattern(kwargs):
    with pytest.raises(ValueError):
        sector_attenuation_db(10.0, **kwargs)
