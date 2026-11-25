"""User interface texts in Spanish and English.

Every entry is ``key: (spanish, english)``. Texts may contain ``{placeholders}``
that are filled with :func:`tr`'s keyword arguments.
"""

LANGUAGES = {"es": "Español", "en": "English"}
DEFAULT_LANGUAGE = "es"

_TEXT: dict[str, tuple[str, str]] = {
    # --- Maps ---------------------------------------------------------------------
    "map.layer.light": ("Mapa claro", "Light map"),
    "map.layer.topo": ("Mapa topográfico", "Topographic map"),
    "map.layer.ign": ("Mapa base IGN", "IGN base map"),
    "map.layer.pnoa": ("Ortofoto IGN (PNOA)", "IGN aerial imagery (PNOA)"),
    "map.layer.signal": ("Potencia recibida", "Received power"),
    "map.layer.server": ("Mejor servidor", "Best server"),
    "map.layer.relief": ("Relieve sombreado", "Shaded relief"),
    "map.layer.fresnel": ("Primera zona de Fresnel (planta)", "First Fresnel zone (top view)"),
    "map.layer.sites": ("Emplazamientos", "Sites"),
    "map.layer.link": ("Enlace", "Link"),
    "map.fullscreen": ("Pantalla completa", "Full screen"),
    "map.fullscreen_exit": ("Salir de pantalla completa", "Exit full screen"),
    "map.tx": ("Transmisor (estación base)", "Transmitter (base station)"),
    "map.rx": ("Receptor (terminal)", "Receiver (user equipment)"),
    "map.coverage_title": ("Predicción de cobertura", "Coverage prediction"),
    "map.network_title": ("Cobertura de la red", "Network coverage"),
    "map.fresnel_tooltip": (
        "Primera zona de Fresnel: radio de {radius:.1f} m en el centro",
        "First Fresnel zone: {radius:.1f} m radius at mid-path",
    ),
    "map.link_tooltip": (
        "{distance:.2f} km · margen {margin:.1f} dB",
        "{distance:.2f} km · margin {margin:.1f} dB",
    ),
    "map.azimuth_tooltip": ("{name}: azimut {azimuth:g}°", "{name}: azimuth {azimuth:g}°"),
    # --- Verdicts and classes -----------------------------------------------------
    "verdict.ok": ("ENLACE VIABLE", "LINK OK"),
    "verdict.fail": ("ENLACE NO VIABLE", "LINK FAILS"),
    "class.excellent": ("Excelente", "Excellent"),
    "class.good": ("Buena", "Good"),
    "class.fair": ("Aceptable", "Fair"),
    "class.weak": ("Débil", "Weak"),
    "terrain.clear": ("despejado (≥ 60 % de Fresnel libre)", "clear (≥ 60% of Fresnel zone free)"),
    "terrain.partial": (
        "con visión directa, Fresnel parcialmente obstruido",
        "line of sight, Fresnel zone partly obstructed",
    ),
    "terrain.blocked": ("obstruido (sin visión directa)", "obstructed (no line of sight)"),
    "env.dense-urban": ("urbano denso", "dense urban"),
    "env.urban": ("urbano", "urban"),
    "env.suburban": ("suburbano", "suburban"),
    "env.rural": ("rural", "rural"),
    "omni": ("omnidireccional", "omnidirectional"),
    "range.to": ("a", "to"),
    # --- Quantities (tables, popups, legends) --------------------------------------
    "q.site": ("Emplazamiento", "Site"),
    "q.location": ("Ubicación", "Location"),
    "q.transmitter": ("Transmisor", "Transmitter"),
    "q.receiver": ("Receptor", "Receiver"),
    "q.band": ("Banda", "Band"),
    "q.frequency": ("Frecuencia", "Frequency"),
    "q.distance": ("Distancia", "Distance"),
    "q.azimuth": ("Azimut", "Azimuth"),
    "q.azimuth_tx_rx": ("Azimut Tx→Rx", "Azimuth Tx→Rx"),
    "q.azimuth_rx_tx": ("Azimut Rx→Tx", "Azimuth Rx→Tx"),
    "q.tx_power": ("Potencia Tx", "Tx power"),
    "q.tx_gain": ("Ganancia antena Tx", "Tx antenna gain"),
    "q.tx_loss": ("Pérdidas cable Tx", "Tx cable loss"),
    "q.eirp": ("PIRE", "EIRP"),
    "q.antenna_height": ("Altura de antena", "Antenna height"),
    "q.tx_height": ("Altura antena Tx", "Tx antenna height"),
    "q.rx_height": ("Altura antena Rx", "Rx antenna height"),
    "q.beamwidth": ("ancho de haz {beamwidth:g}°", "beamwidth {beamwidth:g}°"),
    "q.model": ("Modelo", "Model"),
    "q.environment": ("Entorno", "Environment"),
    "q.terrain": ("Relieve", "Terrain"),
    "q.terrain_yes": ("sí (difracción Bullington)", "yes (Bullington diffraction)"),
    "q.terrain_no": ("no (tierra plana)", "no (flat earth)"),
    "q.path_loss": ("Pérdidas de propagación", "Path loss"),
    "q.free_space_loss": ("Pérdidas en espacio libre", "Free-space path loss"),
    "q.diffraction_loss": ("Pérdidas por difracción", "Diffraction loss"),
    "q.other_losses": ("Otras pérdidas", "Other losses"),
    "q.rx_gain": ("Ganancia antena Rx", "Rx antenna gain"),
    "q.rx_loss": ("Pérdidas Rx (cuerpo, cable)", "Rx losses (body, cable)"),
    "q.rx_power": ("Potencia recibida", "Received power"),
    "q.sensitivity": ("Sensibilidad", "Sensitivity"),
    "q.margin": ("Margen", "Margin"),
    "q.required_margin": ("Margen exigido", "Required margin"),
    "q.margin_required": (
        "{margin:.1f} dB (exigido {required:.1f})",
        "{margin:.1f} dB (required {required:.1f})",
    ),
    "q.fresnel_radius": ("Radio 1ª zona de Fresnel", "1st Fresnel radius"),
    "q.fresnel_clearance": ("Despejamiento mínimo de Fresnel", "Min. Fresnel clearance"),
    "q.earth_bulge": ("Abultamiento terrestre", "Earth bulge"),
    "q.at_midpath": ("{value:.1f} m en el centro", "{value:.1f} m at mid-path"),
    "q.covered_area": ("Área cubierta", "Covered area"),
    "q.max_range": ("Alcance máximo", "Max range"),
    "q.point_antenna": ("Orientar la antena a", "Point antenna to"),
    "q.tx_at": ("El Tx está a un azimut de", "Tx is at azimuth"),
    "validity.distance": ("la distancia", "the distance"),
    "validity.tx_height": ("la altura de la estación base", "the base station height"),
    "validity.rx_height": ("la altura del receptor", "the receiver height"),
    "validity.warning": (
        "{model}: {quantity} ({value:.4g} {unit}) está fuera del rango de validez "
        "({low:g}–{high:g} {unit}); el resultado es una extrapolación.",
        "{model}: {quantity} ({value:.4g} {unit}) is outside the validity range "
        "({low:g}–{high:g} {unit}); the result is an extrapolation.",
    ),
    # --- Tables and charts of the web interface ------------------------------------
    "web.section.tx": ("Transmisor", "Transmitter"),
    "web.section.path": ("Trayecto", "Path"),
    "web.section.rx": ("Receptor", "Receiver"),
    "web.section.result": ("Resultado", "Result"),
    "web.result.verdict": ("Veredicto", "Verdict"),
    "web.chart.distance_km": (
        "Distancia desde el transmisor (km)",
        "Distance from transmitter (km)",
    ),
    "web.chart.height_m": ("Altura sobre el nivel del mar (m)", "Height above sea level (m)"),
    "web.chart.ground": ("Terreno", "Ground"),
    "web.chart.los": ("Línea de visión", "Line of sight"),
    "web.chart.clearance": ("Despejamiento", "Clearance"),
    "web.chart.free_space": ("Espacio libre", "Free space"),
    "web.chart.power_dbm": ("Potencia recibida (dBm)", "Received power (dBm)"),
    "web.chart.required_level": ("Nivel exigido", "Required level"),
}


def tr(key: str, lang: str = "en", **values) -> str:
    """Text for ``key`` in ``lang`` (``es`` or ``en``), with placeholders filled in."""
    spanish, english = _TEXT[key]
    text = spanish if lang == "es" else english
    return text.format(**values) if values else text


def keys() -> list[str]:
    return list(_TEXT)


def has(key: str) -> bool:
    return key in _TEXT
