import pytest

from radiocoverage.geo import (
    GeoPoint,
    bearing_deg,
    destination_point,
    distance_km,
    intermediate_point,
    is_in_spain,
)

MADRID = GeoPoint(40.4168, -3.7038)
BARCELONA = GeoPoint(41.3874, 2.1686)
SEVILLA = GeoPoint(37.3891, -5.9845)


def test_madrid_barcelona_distance():
    assert distance_km(MADRID, BARCELONA) == pytest.approx(505, abs=2)


def test_distance_is_symmetric_and_zero_on_itself():
    assert distance_km(MADRID, SEVILLA) == pytest.approx(distance_km(SEVILLA, MADRID))
    assert distance_km(MADRID, MADRID) == 0.0


def test_one_degree_of_latitude_is_111_km():
    assert distance_km(GeoPoint(40, -3), GeoPoint(41, -3)) == pytest.approx(111.2, abs=0.1)


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        (GeoPoint(41.0, -3.0), 0.0),
        (GeoPoint(40.0, -2.0), 90.0),
        (GeoPoint(39.0, -3.0), 180.0),
        (GeoPoint(40.0, -4.0), 270.0),
    ],
)
def test_cardinal_bearings(target, expected):
    assert bearing_deg(GeoPoint(40.0, -3.0), target) == pytest.approx(expected, abs=0.7)


def test_madrid_to_barcelona_points_east_north_east():
    assert 70 < bearing_deg(MADRID, BARCELONA) < 80


@pytest.mark.parametrize("bearing", [0.0, 45.0, 137.5, 270.0])
def test_destination_round_trip(bearing):
    end = destination_point(MADRID, bearing, 25.0)
    assert distance_km(MADRID, end) == pytest.approx(25.0)
    difference = (bearing_deg(MADRID, end) - bearing + 180) % 360 - 180
    assert difference == pytest.approx(0.0, abs=1e-6)


def test_intermediate_point():
    mid = intermediate_point(MADRID, BARCELONA, 0.5)
    assert distance_km(MADRID, mid) == pytest.approx(distance_km(mid, BARCELONA))
    assert distance_km(intermediate_point(MADRID, BARCELONA, 0.0), MADRID) < 1e-9
    end = intermediate_point(MADRID, BARCELONA, 1.0)
    assert distance_km(end, BARCELONA) < 1e-6
    assert intermediate_point(MADRID, MADRID, 0.5) == MADRID
    with pytest.raises(ValueError):
        intermediate_point(MADRID, BARCELONA, 1.5)


@pytest.mark.parametrize(
    ("point", "inside"),
    [
        (MADRID, True),
        (BARCELONA, True),
        (GeoPoint(39.5696, 2.6502), True),  # Palma
        (GeoPoint(39.8885, 4.2658), True),  # Mahón
        (GeoPoint(42.3196, 3.3225), True),  # Cap de Creus
        (GeoPoint(28.4636, -16.2518), True),  # Santa Cruz de Tenerife
        (GeoPoint(35.8894, -5.3198), True),  # Ceuta
        (GeoPoint(35.2923, -2.9381), True),  # Melilla
        (GeoPoint(48.8566, 2.3522), False),  # Paris
        (GeoPoint(34.0209, -6.8416), False),  # Rabat
        (GeoPoint(40.4168, 3.7038), False),  # Madrid with the wrong longitude sign
    ],
)
def test_is_in_spain(point, inside):
    assert is_in_spain(point) is inside


@pytest.mark.parametrize(("lat", "lon"), [(91, 0), (-91, 0), (0, 181), (0, -181)])
def test_invalid_coordinates(lat, lon):
    with pytest.raises(ValueError):
        GeoPoint(lat, lon)


def test_point_text():
    assert str(GeoPoint(40.5, -3.25)) == "40.50000°N, 3.25000°W"
    assert str(GeoPoint(-33.9, 18.4)) == "33.90000°S, 18.40000°E"
