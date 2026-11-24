# Radio Coverage Visualizer — LTE/5G in Spain

![tests](https://github.com/DanielJusto1/visualizador-coberura/actions/workflows/tests.yml/badge.svg)

A Python tool to plan and visualize radio coverage of LTE and 5G NR networks in Spain:
from a single-link budget calculator up to coverage maps over real terrain.

> **Resumen (ES):** herramienta en Python para calcular y visualizar la cobertura radio
> de redes LTE y 5G en España. Calcula el presupuesto de enlace entre una estación base y
> un terminal, con las bandas que usan los operadores españoles, y dibuja el enlace en un
> mapa interactivo con la zona de Fresnel y la cartografía del IGN.

## Features

**Link budget (phase 1)**
- Transmitted power, antenna gains, cable losses, EIRP, free-space path loss, received
  power, receiver sensitivity and link margin.
- **Spanish LTE/5G bands** built in: n28 (700 MHz), B20 (800), B8 (900), B3 (1800),
  B1 (2100), B7 (2600) and n78 (3.5 GHz).
- **Receiver sensitivity from thermal noise** (kTB + noise figure + required SNR).
- **Maximum range** that still meets the required fade margin.

**Point-to-point link on a map (phase 2)**
- Transmitter and receiver given by **GPS coordinates** anywhere in Spain (mainland,
  Balearic and Canary Islands, Ceuta and Melilla).
- Great-circle distance and **antenna azimuth** in both directions.
- **First Fresnel zone** radius, 60 % clearance and **Earth bulge** (k = 4/3).
- **Interactive HTML map** with the link coloured by result (green OK / red fails), the
  Fresnel zone footprint, a results panel and three base layers: OpenStreetMap,
  IGN base map and IGN aerial imagery (PNOA).

**General**
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

Run one of the included examples and open the generated map in your browser:

```bash
radiocoverage link --config examples/5g_n78_madrid_centre.toml --map maps/madrid.html
```

```
Link budget - 5G NR n78 (3600 MHz)
==================================================
Transmitter
  Tx power                         43.00 dBm
  Tx antenna gain           +      24.00 dBi
  Tx cable loss             -       0.00 dB
  EIRP                      =      67.00 dBm
Path
  Tx location               40.42330°N, 3.67140°W
  Rx location               40.41690°N, 3.70350°W
  Azimuth Tx -> Rx                255.33 deg
  Frequency                      3600.00 MHz
  Distance                          2.81 km
  Free-space path loss      -     112.54 dB
  Other losses              -      20.00 dB
  1st Fresnel radius (mid)          7.65 m
  60% clearance (mid)               4.59 m
  Earth bulge (mid, k=4/3)          0.12 m
Receiver
  Rx antenna gain           +       0.00 dBi
  Rx cable loss             -       3.00 dB
  Received power            =     -68.54 dBm
  Sensitivity                     -95.00 dBm
  Margin                           26.46 dB
  Required margin                   8.00 dB
--------------------------------------------------
Result: LINK OK (margin 26.46 dB, required 8.00 dB)
Max range in free space: 23.51 km
Note: free space is a best case; real LTE/5G range is much shorter.
Map saved to maps/madrid.html
```

Other ways to use it:

```bash
# Rural LTE 800 MHz link: Sierra de Guadarrama to Segovia
radiocoverage link --config examples/lte_b20_navacerrada_segovia.toml --map maps/segovia.html

# Every value as an option, with coordinates
radiocoverage link --band B3 --tx-lat 37.3891 --tx-lon -5.9845 --rx-lat 37.4100 --rx-lon -5.9300 \
    --tx-power 46 --tx-gain 17 --sensitivity -100 --map maps/sevilla.html

# Only a distance, no map
radiocoverage link --band B20 --distance 10 --tx-power 46 --sensitivity -100

# List the available bands
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
| Distance (haversine) | `d = 2R·asin(√(sin²(Δφ/2) + cos φ₁ cos φ₂ sin²(Δλ/2)))` |
| n-th Fresnel zone radius | `r_n = √(n·λ·d₁·d₂ / (d₁ + d₂))` |
| Earth bulge | `h = d₁·d₂ / (2·k·R)`, with k = 4/3 |

All power quantities are handled in decibels, so gains and losses simply add up.
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
    geo.py           coordinates, distance, azimuth, Spanish territory check
    fresnel.py       Fresnel zones and Earth bulge
    path.py          geometry of a Tx-Rx radio path
    link_map.py      interactive map (folium / Leaflet)
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
2. ✅ **Point-to-point link on a map**: coordinates, distance, azimuth, Fresnel zone,
   Earth bulge, interactive map with IGN cartography.
3. **Coverage maps** with empirical models (Okumura-Hata, COST-231 Hata) over a grid.
4. **Real terrain** from the Spanish national elevation model (IGN MDT): elevation profile,
   line of sight, Fresnel obstruction and knife-edge diffraction (ITU-R P.526).
5. **Web interface** with multiple sites, best-server map and KML export.

## Data sources

Base maps © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors and
© [Instituto Geográfico Nacional de España](https://www.ign.es) (IGN base map and PNOA
aerial imagery, CC BY 4.0).

## License

MIT — see [LICENSE](LICENSE).
