# Radio Coverage Visualizer — LTE/5G in Spain

![tests](https://github.com/DanielJusto1/visualizador-coberura/actions/workflows/tests.yml/badge.svg)

A Python tool to plan and visualize radio coverage of LTE and 5G NR networks in Spain:
from a single-link budget calculator up to coverage maps over real terrain.

> **Resumen (ES):** herramienta en Python para calcular y visualizar la cobertura radio
> de redes LTE y 5G en España. La fase actual es una calculadora de presupuesto de enlace
> por línea de comandos, con las bandas que usan los operadores españoles y tests automáticos.

## Features (phase 1)

- **Link budget**: transmitted power, antenna gains, cable losses, EIRP, free-space path
  loss, received power, receiver sensitivity and link margin.
- **Spanish LTE/5G bands** built in: n28 (700 MHz), B20 (800), B8 (900), B3 (1800),
  B1 (2100), B7 (2600) and n78 (3.5 GHz).
- **Receiver sensitivity from thermal noise** (kTB + noise figure + required SNR).
- **Maximum range** that still meets the required fade margin.
- Parameters from the command line or from a **TOML config file**.
- **Automated tests** (pytest) run on every push with GitHub Actions.

## Quick start

Requires Python 3.11 or newer.

```bash
git clone https://github.com/DanielJusto1/visualizador-coberura.git
cd visualizador-coberura
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Run one of the included examples:

```bash
radiocoverage link --config examples/lte_b20_rural.toml
```

```
Link budget - LTE B20 (806 MHz)
==================================================
Transmitter
  Tx power                         46.00 dBm
  Tx antenna gain           +      17.00 dBi
  Tx cable loss             -       2.00 dB
  EIRP                      =      61.00 dBm
Path
  Frequency                       806.00 MHz
  Distance                         10.00 km
  Free-space path loss      -     110.57 dB
  Other losses              -       0.00 dB
Receiver
  Rx antenna gain           +       0.00 dBi
  Rx cable loss             -       3.00 dB
  Received power            =     -52.57 dBm
  Sensitivity                     -95.98 dBm
    (from kTB: 10 MHz, NF 9 dB, SNR -1 dB)
  Margin                           43.40 dB
  Required margin                  10.00 dB
--------------------------------------------------
Result: LINK OK (margin 43.40 dB, required 10.00 dB)
Max range in free space: 467.77 km
Note: free space is a best case; real LTE/5G range is much shorter.
```

Or pass every value as an option:

```bash
radiocoverage link --band n78 --distance 0.5 --tx-power 43 --tx-gain 24 \
    --other-losses 20 --sensitivity -95 --margin 8
```

List the available bands:

```bash
radiocoverage bands
```

Run `radiocoverage link --help` to see every option.

## Theory

| Quantity | Formula |
|---|---|
| EIRP | `EIRP = P_tx + G_tx − L_tx` |
| Free-space path loss (Friis) | `FSPL = 20·log10(d_km) + 20·log10(f_MHz) + 32.45` |
| Received power | `P_rx = EIRP − FSPL − L_other + G_rx − L_rx` |
| Thermal noise | `N = −174 dBm/Hz + 10·log10(B_Hz)` |
| Sensitivity | `S = N + NF + SNR_min` |
| Margin | `M = P_rx − S` (link OK when `M ≥ M_required`) |

All quantities are handled in decibels, so gains and losses simply add up.
Free-space loss is valid with clear line of sight in the far field; it is an optimistic
upper bound for mobile networks. Realistic empirical models come in phase 3.

## Project structure

```
src/radiocoverage/
    units.py         dB/dBm/W conversions, wavelength
    propagation.py   path loss models (free space)
    receiver.py      thermal noise and sensitivity
    bands.py         LTE/5G bands used in Spain
    link_budget.py   link budget calculation
    cli.py           command line interface
tests/               automated tests (pytest)
examples/            ready-to-run link configurations
```

## Running the tests

```bash
pytest
```

## Roadmap

1. ✅ **Link budget calculator** (command line, tests).
2. **Point-to-point link on a map**: Tx/Rx coordinates, great-circle distance,
   Fresnel zone, interactive map.
3. **Coverage maps** with empirical models (Okumura-Hata, COST-231 Hata) over a grid.
4. **Real terrain** from the Spanish national elevation model (IGN MDT): elevation profile,
   line of sight, Fresnel obstruction and knife-edge diffraction (ITU-R P.526).
5. **Web interface** with multiple sites, best-server map and KML export.

## License

MIT — see [LICENSE](LICENSE).
