import pytest

from radiocoverage.link_budget import LinkParameters, compute_link_budget
from radiocoverage.propagation import free_space_path_loss_db


def make_params(**overrides):
    values = dict(
        frequency_mhz=806.0,
        distance_km=10.0,
        tx_power_dbm=46.0,
        rx_sensitivity_dbm=-100.0,
        tx_antenna_gain_dbi=17.0,
        rx_antenna_gain_dbi=0.0,
        tx_cable_loss_db=2.0,
        rx_cable_loss_db=3.0,
        other_losses_db=0.0,
        required_margin_db=10.0,
    )
    values.update(overrides)
    return LinkParameters(**values)


def test_full_budget_by_hand():
    result = compute_link_budget(make_params())
    fspl = free_space_path_loss_db(10.0, 806.0)
    assert result.eirp_dbm == pytest.approx(46 + 17 - 2)
    assert result.path_loss_db == pytest.approx(fspl)
    assert result.rx_power_dbm == pytest.approx(61 - fspl + 0 - 3)
    assert result.margin_db == pytest.approx(result.rx_power_dbm + 100)
    assert result.is_viable


def test_every_db_of_gain_is_a_db_of_margin():
    base = compute_link_budget(make_params()).margin_db
    assert compute_link_budget(make_params(rx_antenna_gain_dbi=5)).margin_db == pytest.approx(
        base + 5
    )
    assert compute_link_budget(make_params(other_losses_db=20)).margin_db == pytest.approx(
        base - 20
    )
    assert compute_link_budget(make_params(rx_sensitivity_dbm=-90)).margin_db == pytest.approx(
        base - 10
    )


def test_link_fails_when_margin_below_required():
    result = compute_link_budget(make_params(other_losses_db=40.0, required_margin_db=10.0))
    assert result.margin_db < 10.0
    assert not result.is_viable


def test_exactly_required_margin_is_viable():
    first = compute_link_budget(make_params(required_margin_db=0.0))
    exact = compute_link_budget(make_params(required_margin_db=first.margin_db))
    assert exact.is_viable


def test_max_distance_gives_exactly_the_required_margin():
    result = compute_link_budget(make_params())
    at_limit = compute_link_budget(make_params(distance_km=result.max_distance_km))
    assert at_limit.margin_db == pytest.approx(10.0)


def test_max_distance_shorter_than_distance_when_failing():
    result = compute_link_budget(make_params(other_losses_db=60.0))
    assert not result.is_viable
    assert result.max_distance_km < 10.0


@pytest.mark.parametrize(
    "overrides",
    [
        {"distance_km": 0.0},
        {"distance_km": -2.0},
        {"frequency_mhz": 0.0},
        {"tx_cable_loss_db": -1.0},
        {"rx_cable_loss_db": -1.0},
        {"other_losses_db": -1.0},
        {"required_margin_db": -3.0},
    ],
)
def test_invalid_parameters_rejected(overrides):
    with pytest.raises(ValueError):
        make_params(**overrides)
