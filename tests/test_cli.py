import subprocess
import sys
from pathlib import Path

import pytest

from radiocoverage.cli import main

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def run(capsys, *args):
    code = main(list(args))
    out, err = capsys.readouterr()
    return code, out, err


def test_link_with_flags(capsys):
    code, out, _ = run(
        capsys,
        "link",
        "--band",
        "B20",
        "--distance",
        "10",
        "--tx-power",
        "46",
        "--tx-gain",
        "17",
        "--tx-loss",
        "2",
        "--rx-loss",
        "3",
        "--sensitivity",
        "-100",
        "--margin",
        "10",
    )
    assert code == 0
    assert "LTE B20 (806 MHz)" in out
    assert "110.57 dB" in out  # free-space path loss
    assert "61.00 dBm" in out  # EIRP
    assert "LINK OK" in out


def test_link_with_frequency_reports_failure(capsys):
    code, out, _ = run(
        capsys,
        "link",
        "--frequency",
        "3600",
        "--distance",
        "50",
        "--tx-power",
        "20",
        "--sensitivity",
        "-90",
        "--other-losses",
        "30",
    )
    assert code == 0
    assert "LINK FAILS" in out


def test_sensitivity_from_noise(capsys):
    code, out, _ = run(
        capsys,
        "link",
        "--band",
        "n78",
        "--distance",
        "1",
        "--tx-power",
        "43",
        "--bandwidth",
        "100",
        "--noise-figure",
        "7",
        "--snr",
        "0",
    )
    assert code == 0
    assert "-86.98 dBm" in out  # -174 + 80 + 7 + 0
    assert "from kTB" in out


@pytest.mark.parametrize("example", sorted(EXAMPLES.glob("*.toml")), ids=lambda p: p.name)
def test_examples_run(capsys, example):
    code, out, err = run(capsys, "link", "--config", str(example))
    assert code == 0, err
    assert "Result:" in out


def test_command_line_overrides_config(capsys):
    config = str(EXAMPLES / "lte_b20_navacerrada_segovia.toml")
    # A distance on the command line replaces the coordinates from the file.
    _, out, _ = run(capsys, "link", "--config", config, "--distance", "1000")
    assert "1000.00 km" in out
    assert "Tx location" not in out
    assert "LINK FAILS" in out
    # A frequency on the command line replaces the band from the file.
    code, out, _ = run(capsys, "link", "--config", config, "--frequency", "1842.5")
    assert code == 0
    assert "1842.5 MHz" in out
    # A sensitivity on the command line replaces bandwidth/NF/SNR from the file.
    code, out, _ = run(capsys, "link", "--config", config, "--sensitivity", "-80")
    assert code == 0
    assert "-80.00 dBm" in out


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (["--distance", "1", "--tx-power", "43", "--sensitivity", "-90"], "missing frequency"),
        (["--band", "B20", "--tx-power", "43", "--sensitivity", "-90"], "missing link length"),
        (["--band", "B20", "--distance", "1", "--sensitivity", "-90"], "--tx-power"),
        (["--band", "B20", "--distance", "1", "--tx-power", "43"], "sensitivity"),
        (
            [
                "--band",
                "B20",
                "--frequency",
                "800",
                "--distance",
                "1",
                "--tx-power",
                "43",
                "--sensitivity",
                "-90",
            ],
            "not both",
        ),
        (
            ["--band", "B20", "--distance", "1", "--tx-power", "43", "--bandwidth", "10"],
            "--noise-figure",
        ),
        (
            ["--band", "B99", "--distance", "1", "--tx-power", "43", "--sensitivity", "-90"],
            "Unknown band",
        ),
        (
            ["--band", "B20", "--distance", "-1", "--tx-power", "43", "--sensitivity", "-90"],
            "distance_km",
        ),
        (["--config", "does_not_exist.toml"], "not found"),
    ],
)
def test_errors(capsys, args, message):
    code, out, err = run(capsys, "link", *args)
    assert code == 2
    assert message in err
    assert out == ""


def test_bad_config_files(capsys, tmp_path):
    bad_key = tmp_path / "bad_key.toml"
    bad_key.write_text('band = "B20"\ndistanse = 3\n')
    code, _, err = run(capsys, "link", "--config", str(bad_key))
    assert code == 2 and "distanse" in err

    bad_value = tmp_path / "bad_value.toml"
    bad_value.write_text('band = "B20"\ndistance = "far"\n')
    code, _, err = run(capsys, "link", "--config", str(bad_value))
    assert code == 2 and "must be a number" in err

    bad_toml = tmp_path / "bad.toml"
    bad_toml.write_text("band = \n")
    code, _, err = run(capsys, "link", "--config", str(bad_toml))
    assert code == 2 and "invalid TOML" in err


def test_bands_command(capsys):
    code, out, _ = run(capsys, "bands")
    assert code == 0
    for name in ("n28", "B20", "B8", "B3", "B1", "B7", "n78"):
        assert name in out


def test_runs_as_module():
    completed = subprocess.run(
        [sys.executable, "-m", "radiocoverage", "bands"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    assert "n78" in completed.stdout


MADRID = [
    "--tx-lat",
    "40.4233",
    "--tx-lon",
    "-3.6714",
    "--rx-lat",
    "40.4169",
    "--rx-lon",
    "-3.7035",
]
BASIC = ["--band", "n78", "--tx-power", "43", "--sensitivity", "-95"]


def test_link_with_coordinates(capsys):
    code, out, _ = run(capsys, "link", *BASIC, *MADRID)
    assert code == 0
    assert "40.42330°N, 3.67140°W" in out
    assert "2.81 km" in out
    assert "1st Fresnel radius" in out
    assert "Earth bulge" in out


def test_link_writes_map(capsys, tmp_path):
    output = tmp_path / "maps" / "madrid.html"
    code, out, err = run(capsys, "link", *BASIC, *MADRID, "--map", str(output))
    assert code == 0, err
    assert output.exists()
    assert f"Map saved to {output}" in out
    assert "LINK OK" in output.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("extra", "message"),
    [
        (MADRID[:6], "--rx-lon"),
        ([*MADRID, "--distance", "3"], "not both"),
        (["--tx-lat", "48.8566", "--tx-lon", "2.3522", *MADRID[4:]], "outside Spain"),
        (["--tx-lat", "40.4233", "--tx-lon", "3.6714", *MADRID[4:]], "west is negative"),
        (["--tx-lat", "95", "--tx-lon", "-3.6", *MADRID[4:]], "Latitude"),
        ([*MADRID[:4], "--rx-lat", "40.4233", "--rx-lon", "-3.6714"], "different locations"),
        (["--distance", "3", "--map", "x.html"], "needs the coordinates"),
        ([*MADRID, "--map", "map.png"], ".html"),
    ],
)
def test_coordinate_errors(capsys, extra, message):
    code, out, err = run(capsys, "link", *BASIC, *extra)
    assert code == 2
    assert message in err
    assert out == ""
