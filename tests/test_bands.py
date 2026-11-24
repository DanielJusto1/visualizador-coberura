import pytest

from radiocoverage.bands import BANDS, get_band


def test_band_lookup_is_case_insensitive():
    assert get_band("b20") is get_band("B20")
    assert get_band("N78").name == "n78"


def test_centre_frequencies():
    assert get_band("B20").centre_mhz == pytest.approx(806.0)
    assert get_band("n78").centre_mhz == pytest.approx(3600.0)
    assert get_band("B3").width_mhz == pytest.approx(75.0)


def test_all_bands_are_consistent():
    for band in BANDS.values():
        assert band.downlink_low_mhz < band.downlink_high_mhz
        assert band.technology in {"LTE", "5G NR"}


def test_unknown_band():
    with pytest.raises(ValueError, match="Available bands"):
        get_band("B99")
