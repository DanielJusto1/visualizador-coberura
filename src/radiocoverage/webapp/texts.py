"""Texts of the web interface in Spanish and English (``key: (spanish, english)``)."""

import streamlit as st

from radiocoverage.i18n import DEFAULT_LANGUAGE, LANGUAGES, tr
from radiocoverage.i18n import has as core_has

WEB_TEXT: dict[str, tuple[str, str]] = {
    # Navigation and frame
    "nav.tools": ("Herramientas", "Tools"),
    "nav.info": ("Información", "Information"),
    "nav.planner": ("Planificador en mapa", "Map planner"),
    "nav.network": ("Red y cobertura", "Network coverage"),
    "nav.link": ("Enlace por coordenadas", "Link by coordinates"),
    "nav.about": ("Metodología", "Methodology"),
    "web.footer": (
        "RadioCoverage v{version} · Datos: IGN, OpenStreetMap, Esri, Terrarium (AWS)",
        "RadioCoverage v{version} · Data: IGN, OpenStreetMap, Esri, Terrarium (AWS)",
    ),
    "web.computing": ("Calculando…", "Computing…"),
    # Parameters (sidebar)
    "web.params.title": ("Parámetros", "Parameters"),
    "web.params.base_station": ("Estación base", "Base station"),
    "web.params.terminal": ("Terminal (receptor)", "Terminal (receiver)"),
    "web.params.propagation": ("Propagación", "Propagation"),
    "web.params.area": ("Área de cálculo", "Analysis area"),
    "web.tx_power": ("Potencia (dBm)", "Power (dBm)"),
    "web.antenna_gain": ("Ganancia (dBi)", "Gain (dBi)"),
    "web.height": ("Altura (m)", "Height (m)"),
    "web.cable_loss": ("Pérd. cable (dB)", "Cable loss (dB)"),
    "web.body_loss": ("Pérd. cuerpo (dB)", "Body loss (dB)"),
    "web.extra_loss": ("Pérd. extra (dB)", "Extra loss (dB)"),
    "web.terminal_location": ("Ubicación del terminal", "Terminal location"),
    "web.where.outdoor": ("Exterior (+{loss:g} dB)", "Outdoors (+{loss:g} dB)"),
    "web.where.vehicle": ("Dentro de un vehículo (+{loss:g} dB)", "In a vehicle (+{loss:g} dB)"),
    "web.where.indoor": ("Interior de edificio (+{loss:g} dB)", "Indoors (+{loss:g} dB)"),
    "web.receiver_sensitivity": ("Sensibilidad del receptor", "Receiver sensitivity"),
    "web.bandwidth": ("Canal (MHz)", "Channel (MHz)"),
    "web.sensitivity_caption": (
        "Sensibilidad resultante: **{value:.1f} dBm** (−174 dBm/Hz + 10·log B + NF + SNR)",
        "Resulting sensitivity: **{value:.1f} dBm** (−174 dBm/Hz + 10·log B + NF + SNR)",
    ),
    "web.fade_margin": ("Margen de desvanecimiento (dB)", "Fade margin (dB)"),
    "web.eirp_caption": (
        "PIRE: **{eirp:.1f} dBm** ({watts:,.0f} W)",
        "EIRP: **{eirp:.1f} dBm** ({watts:,.0f} W)",
    ),
    "web.real_terrain": ("Usar el relieve real", "Use real terrain"),
    "web.model.auto": ("Automático", "Automatic"),
    "web.model.free-space": ("Espacio libre (Friis)", "Free space (Friis)"),
    "web.model.okumura-hata": ("Okumura-Hata (150–1500 MHz)", "Okumura-Hata (150–1500 MHz)"),
    "web.model.cost231-hata": ("COST-231 Hata (1500–2000 MHz)", "COST-231 Hata (1500–2000 MHz)"),
    "web.model.3gpp": ("3GPP TR 38.901 (0,5–7 GHz)", "3GPP TR 38.901 (0.5–7 GHz)"),
    "web.radius": ("Radio (km)", "Radius (km)"),
    "web.resolution": ("Resolución (m)", "Resolution (m)"),
    "web.covered_fraction": ("Fracción cubierta", "Covered fraction"),
    # Help tooltips
    "help.band": (
        "Banda LTE/5G de los operadores españoles. Al cambiarla se cargan valores típicos.",
        "LTE/5G band used by Spanish operators. Changing it loads typical values.",
    ),
    "help.tx_power": (
        "Potencia a la salida del transmisor. 46 dBm = 40 W, habitual en un sector macro.",
        "Transmitter output power. 46 dBm = 40 W, typical for a macro sector.",
    ),
    "help.tx_gain": (
        "Ganancia de la antena en su dirección principal (15–18 dBi en un sector LTE).",
        "Antenna gain on its main direction (15–18 dBi for an LTE sector).",
    ),
    "help.tx_height": ("Altura de la antena sobre el suelo.", "Antenna height above ground."),
    "help.tx_loss": (
        "Pérdidas de cables y conectores entre el equipo y la antena.",
        "Cable and connector losses between the radio and the antenna.",
    ),
    "help.where": (
        "Pérdidas típicas de penetración según dónde esté el usuario.",
        "Typical penetration loss depending on where the user is.",
    ),
    "help.rx_height": (
        "Altura del terminal sobre el suelo (1,5 m para un móvil en la mano).",
        "Terminal height above ground (1.5 m for a handheld phone).",
    ),
    "help.rx_loss": (
        "Pérdidas por el cuerpo del usuario o cables del receptor.",
        "Losses due to the user's body or receiver cables.",
    ),
    "help.rx_gain": ("Ganancia de la antena del terminal.", "Terminal antenna gain."),
    "help.extra_loss": (
        "Pérdidas adicionales: vegetación, lluvia, margen de interferencia…",
        "Additional losses: foliage, rain, interference margin…",
    ),
    "help.bandwidth": ("Ancho del canal en MHz.", "Channel bandwidth in MHz."),
    "help.noise_figure": (
        "Figura de ruido del receptor (7–9 dB en un móvil).",
        "Receiver noise figure (7–9 dB for a phone).",
    ),
    "help.snr": (
        "Relación señal a ruido mínima para demodular (−1 dB ≈ QPSK con poca redundancia).",
        "Minimum signal-to-noise ratio to demodulate (−1 dB ≈ low-rate QPSK).",
    ),
    "help.margin": (
        "Reserva para las variaciones de la señal (desvanecimientos). El enlace es viable si "
        "el margen supera este valor.",
        "Reserve for signal variations (fading). The link is viable when the margin exceeds "
        "this value.",
    ),
    "help.model": (
        "Modelo de pérdidas de propagación. «Automático» elige el adecuado para la banda.",
        "Path loss model. 'Automatic' picks the right one for the band.",
    ),
    "help.environment": (
        "Tipo de zona para los modelos empíricos (más edificios = más pérdidas).",
        "Area type for the empirical models (more buildings = more loss).",
    ),
    "help.terrain": (
        "Descarga la elevación del terreno (unos segundos la primera vez) y calcula la "
        "difracción sobre montañas (ITU-R P.526).",
        "Downloads terrain elevation (a few seconds the first time) and computes the "
        "diffraction over hills (ITU-R P.526).",
    ),
    "help.radius": (
        "Distancia analizada alrededor de los emplazamientos.",
        "Distance analysed around the sites.",
    ),  # fmt: skip
    "help.resolution": (
        "Tamaño de cada píxel del mapa. Más fino = más detalle pero más lento.",
        "Size of each map pixel. Finer = more detail but slower.",
    ),
    "help.planner_mode": (
        "Elige qué extremo colocas con el siguiente clic en el mapa.",
        "Choose which end the next click on the map places.",
    ),
    "help.fit": ("Centra el mapa en el enlace.", "Centre the map on the link."),
    "help.swap": ("Intercambia transmisor y receptor.", "Swap transmitter and receiver."),
    "help.sector_to_rx": (
        "Usa una antena sectorial (65°) apuntando al receptor en lugar de una omnidireccional.",
        "Use a 65° sector antenna pointing at the receiver instead of an omnidirectional one.",
    ),
    "help.click_to_add": (
        "Si está activado, cada clic en el mapa añade un emplazamiento a la tabla.",
        "When on, every click on the map adds a site to the table.",
    ),
    "help.azimuth_column": (
        "Dirección de la antena en grados (0 = norte, 90 = este). Vacío = omnidireccional.",
        "Antenna direction in degrees (0 = north, 90 = east). Empty = omnidirectional.",
    ),
    "help.link_place": (
        "Elige un lugar conocido o escribe las coordenadas debajo.",
        "Pick a well-known place or type the coordinates below.",
    ),
    "help.metric.distance": ("Azimut Tx→Rx: {azimuth:.1f}°", "Azimuth Tx→Rx: {azimuth:.1f}°"),
    "help.metric.rx_power": (
        "Sensibilidad: {sensitivity:.1f} dBm",
        "Sensitivity: {sensitivity:.1f} dBm",
    ),
    "help.metric.margin": (
        "La flecha indica cuánto sobra (o falta) respecto al margen exigido de {required:.1f} dB.",
        "The arrow shows how much is left (or missing) over the required {required:.1f} dB.",
    ),
    # Results
    "web.tab.map": ("Mapa", "Map"),
    "web.tab.budget": ("Presupuesto", "Budget"),
    "web.tab.profile": ("Perfil del terreno", "Terrain profile"),
    "web.tab.power": ("Potencia vs distancia", "Power vs distance"),
    "web.tab.export": ("Exportar", "Export"),
    "web.col.section": ("Bloque", "Block"),
    "web.col.item": ("Concepto", "Item"),
    "web.col.value": ("Valor", "Value"),
    "web.profile.disabled": (
        "Activa «Usar el relieve real» en Propagación (barra lateral) para ver el perfil del "
        "terreno, la zona de Fresnel y la difracción.",
        "Turn on 'Use real terrain' under Propagation (sidebar) to see the terrain profile, "
        "the Fresnel zone and the diffraction.",
    ),
    "web.profile.caption": (
        "Relieve {status} · despejamiento mínimo {clearance:.0f} % de la 1ª zona de Fresnel · "
        "difracción {loss:.1f} dB (filo equivalente a {edge:.2f} km). Pasa el ratón para ver "
        "alturas; rueda para hacer zoom.",
        "Terrain {status} · minimum clearance {clearance:.0f}% of the 1st Fresnel zone · "
        "diffraction {loss:.1f} dB (equivalent edge at {edge:.2f} km). Hover for heights; "
        "scroll to zoom.",
    ),
    "web.power.caption": (
        "Potencia recibida según la distancia con el modelo elegido (sin relieve) y en espacio "
        "libre. Las líneas rojas son la sensibilidad y el nivel exigido (sensibilidad + margen); "
        "el punto es este enlace.",
        "Received power against distance with the chosen model (no terrain) and in free "
        "space. Red lines are the sensitivity and the required level (sensitivity + margin); "
        "the dot is this link.",
    ),
    "web.download.csv": ("Presupuesto (CSV)", "Budget (CSV)"),
    "web.download.map": ("Mapa (HTML)", "Map (HTML)"),
    "web.download.profile": ("Perfil (PNG)", "Profile (PNG)"),
    "web.download.image": ("Imagen (PNG)", "Image (PNG)"),
    # Planner page
    "planner.title": ("Planificador en mapa", "Map planner"),
    "planner.subtitle": (
        "Haz clic en el mapa para colocar el transmisor y el receptor: el presupuesto de enlace "
        "se calcula al instante.",
        "Click on the map to place the transmitter and the receiver: the link budget is "
        "computed instantly.",
    ),
    "planner.place": ("Siguiente clic coloca", "Next click places"),
    "planner.mode.tx": ("📡 Transmisor", "📡 Transmitter"),
    "planner.mode.rx": ("📱 Receptor", "📱 Receiver"),
    "planner.goto": ("Ir a", "Go to"),
    "planner.goto_placeholder": ("Elige un lugar de España…", "Choose a place in Spain…"),
    "planner.fit": ("Encuadrar", "Fit"),
    "planner.swap": ("Invertir", "Swap"),
    "planner.clear": ("Borrar", "Clear"),
    "planner.map_hint": (
        "Haz clic en el mapa para colocar el {target}. Puedes cambiar el fondo con el botón de "
        "capas y ver el mapa a pantalla completa.",
        "Click on the map to place the {target}. Change the background with the layers button "
        "and use the full-screen button for a bigger map.",
    ),
    "planner.step1.title": ("Coloca el transmisor", "Place the transmitter"),
    "planner.step1.text": (
        "Haz clic donde estaría la estación base (por ejemplo, en un cerro o una azotea).",
        "Click where the base station would be (for example on a hill or a rooftop).",
    ),
    "planner.step2.title": ("Coloca el receptor", "Place the receiver"),
    "planner.step2.text": (
        "Haz clic donde estaría el usuario. Puedes seguir haciendo clic para moverlo.",
        "Click where the user would be. Keep clicking to move it.",
    ),
    "planner.step3.title": ("Analiza el resultado", "Analyse the result"),
    "planner.step3.text": (
        "Ajusta banda, potencia y modelo en la barra lateral; activa el relieve real para ver el "
        "perfil del terreno.",
        "Tune band, power and model in the sidebar; turn on real terrain to see the terrain "
        "profile.",
    ),
    "planner.msg.tx_placed": ("Transmisor colocado", "Transmitter placed"),
    "planner.msg.rx_placed": ("Receptor colocado", "Receiver placed"),
    "planner.msg.swapped": (
        "Transmisor y receptor intercambiados",
        "Transmitter and receiver swapped",
    ),
    "planner.msg.cleared": ("Mapa borrado", "Map cleared"),
    "planner.msg.outside": (
        "Ese punto está fuera de España: esta herramienta solo cubre territorio español.",
        "That point is outside Spain: this tool only covers Spanish territory.",
    ),
    "planner.msg.invalid": ("Coordenadas no válidas", "Invalid coordinates"),
    "planner.msg.too_close": (
        "El transmisor y el receptor están demasiado cerca (menos de 20 m).",
        "Transmitter and receiver are too close (less than 20 m).",
    ),
    "planner.coords.title": ("Coordenadas exactas", "Exact coordinates"),
    "planner.coords.caption": (
        "Ajusta la posición escribiendo las coordenadas (grados decimales; oeste negativo).",
        "Fine-tune the position by typing coordinates (decimal degrees; west is negative).",
    ),
    "planner.coverage.title": ("Cobertura del transmisor", "Transmitter coverage"),
    "planner.coverage.caption": (
        "Calcula la zona que cubre el transmisor con los parámetros de la barra lateral.",
        "Compute the area served by the transmitter with the sidebar parameters.",
    ),
    "planner.coverage.sector": (
        "Antena sectorial hacia el receptor",
        "Sector antenna towards the receiver",
    ),
    "planner.coverage.compute": ("Calcular cobertura", "Compute coverage"),
    "planner.coverage.remove": ("Quitar cobertura del mapa", "Remove coverage from the map"),
    # Network page
    "network.title": ("Red y cobertura", "Network coverage"),
    "network.subtitle": (
        "Diseña una red de emplazamientos: haz clic en el mapa para añadirlos, ajústalos en la "
        "tabla y calcula la cobertura y el mejor servidor.",
        "Design a network of sites: click on the map to add them, tune them in the table and "
        "compute the coverage and the best server.",
    ),
    "network.example": ("Red de ejemplo", "Example network"),
    "network.example.madrid_5g": (
        "5G n78 · centro de Madrid (15 sectores)",
        "5G n78 · central Madrid (15 sectors)",
    ),  # fmt: skip
    "network.example.segovia_lte": (
        "LTE 800 · Segovia y Guadarrama (con relieve)",
        "LTE 800 · Segovia and Guadarrama (with terrain)",
    ),  # fmt: skip
    "network.load": ("Cargar", "Load"),
    "network.click_to_add": ("Añadir con clic", "Click to add"),
    "network.clear": ("Vaciar", "Clear"),
    "network.layer": ("Capa", "Layer"),
    "network.map_hint": (
        "Haz clic en el mapa para añadir emplazamientos, o carga una red de ejemplo.",
        "Click on the map to add sites, or load an example network.",
    ),
    "network.site_name": ("Emplazamiento {number}", "Site {number}"),
    "network.table_title": ("Emplazamientos ({count})", "Sites ({count})"),
    "network.table_caption": (
        "Edita cualquier celda (doble clic); añade filas con «+» y bórralas seleccionándolas. "
        "Azimut vacío = antena omnidireccional.",
        "Edit any cell (double-click); add rows with '+' and delete them by selecting them. "
        "Empty azimuth = omnidirectional antenna.",
    ),
    "network.col.name": ("Nombre", "Name"),
    "network.col.power": ("Potencia (dBm)", "Power (dBm)"),
    "network.col.gain": ("Ganancia (dBi)", "Gain (dBi)"),
    "network.col.height": ("Altura (m)", "Height (m)"),
    "network.col.azimuth": ("Azimut (°)", "Azimuth (°)"),
    "network.col.beamwidth": ("Haz (°)", "Beam (°)"),
    "network.col.served": ("Área servida", "Served area"),
    "network.col.share": ("Cuota", "Share"),
    "network.results_title": ("Resultados", "Results"),
    "network.compute": ("Calcular cobertura", "Compute coverage"),
    "network.no_result": (
        "Añade emplazamientos y pulsa «Calcular cobertura».",
        "Add sites and press 'Compute coverage'.",
    ),
    "network.stale": (
        "Has cambiado la red o los parámetros: pulsa «Calcular cobertura» para actualizar.",
        "The network or the parameters changed: press 'Compute coverage' to update.",
    ),
    "network.sites": ("Sectores", "Sectors"),
    "network.result_caption": (
        "Modelo: {model} · área analizada {area:.1f} km² · umbral de cobertura {threshold:.1f} dBm",
        "Model: {model} · analysed area {area:.1f} km² · coverage threshold {threshold:.1f} dBm",
    ),
    "network.row_problem": ("Fila {row}: {problem}", "Row {row}: {problem}"),
    "network.error.coordinates": ("faltan las coordenadas", "missing coordinates"),
    "network.error.outside": ("está fuera de España", "it is outside Spain"),
    "network.error.band": ("banda desconocida", "unknown band"),
    "network.error.values": ("valores no válidos", "invalid values"),
    "network.msg.added": ("Emplazamiento añadido", "Site added"),
    "network.msg.loaded": ("Red de ejemplo cargada", "Example network loaded"),
    # Link page
    "link.title": ("Enlace por coordenadas", "Link by coordinates"),
    "link.subtitle": (
        "Calcula un enlace entre dos puntos exactos: elige lugares conocidos o escribe las "
        "coordenadas.",
        "Compute a link between two exact points: pick well-known places or type the coordinates.",
    ),
    "link.place": ("Lugar", "Place"),
    "link.lat": ("Latitud", "Latitude"),
    "link.lon": ("Longitud", "Longitude"),
    # About page
    "about.title": ("Metodología", "Methodology"),
    "about.subtitle": (
        "Qué calcula la herramienta, con qué modelos y cómo interpretar los resultados.",
        "What the tool computes, with which models and how to read the results.",
    ),
    "about.card.planner.title": ("📍 Planificador en mapa", "📍 Map planner"),
    "about.card.planner.text": (
        "Dos clics: transmisor y receptor. Presupuesto de enlace, perfil del terreno y "
        "cobertura del transmisor.",
        "Two clicks: transmitter and receiver. Link budget, terrain profile and transmitter "
        "coverage.",
    ),
    "about.card.network.title": ("🗼 Red y cobertura", "🗼 Network coverage"),
    "about.card.network.text": (
        "Varios emplazamientos y sectores: mapa de potencia recibida, mejor servidor y "
        "exportación a Google Earth.",
        "Several sites and sectors: received power map, best server and Google Earth export.",
    ),
    "about.card.link.title": ("🛰️ Enlace por coordenadas", "🛰️ Link by coordinates"),
    "about.card.link.text": (
        "El mismo análisis que el planificador, introduciendo coordenadas exactas.",
        "The same analysis as the planner, with exact coordinates.",
    ),
    "about.budget.title": ("Presupuesto de enlace", "Link budget"),
    "about.budget.text": (
        "Todo se calcula en decibelios, de modo que ganancias y pérdidas se suman. La "
        "sensibilidad sale del ruido térmico y el enlace es viable si el margen supera el "
        "margen de desvanecimiento exigido.",
        "Everything is computed in decibels, so gains and losses simply add up. The "
        "sensitivity comes from thermal noise and the link is viable when the margin exceeds "
        "the required fade margin.",
    ),
    "about.models.title": ("Modelos de propagación", "Propagation models"),
    "about.models.text": (
        "Las pérdidas de propagación se estiman con modelos empíricos obtenidos de campañas de "
        "medidas; nunca se permite que predigan menos pérdidas que el espacio libre.",
        "Path loss is estimated with empirical models derived from measurement campaigns; "
        "they are never allowed to predict less loss than free space.",
    ),
    "about.models.auto": (
        "«Automático» usa Okumura-Hata por debajo de 1500 MHz, COST-231 Hata hasta 2000 MHz y "
        "3GPP TR 38.901 por encima (UMa en ciudad, RMa en zonas rurales).",
        "'Automatic' uses Okumura-Hata below 1500 MHz, COST-231 Hata up to 2000 MHz and "
        "3GPP TR 38.901 above (UMa in cities, RMa in rural areas).",
    ),
    "about.col.frequency": ("Frecuencias", "Frequencies"),
    "about.col.distance": ("Distancias", "Distances"),
    "about.col.reference": ("Referencia", "Reference"),
    "about.col.technology": ("Tecnología", "Technology"),
    "about.col.downlink": ("Bajada", "Downlink"),
    "about.col.use": ("Uso típico", "Typical use"),
    "about.terrain.title": ("Relieve, Fresnel y difracción", "Terrain, Fresnel and diffraction"),
    "about.terrain.text": (
        "Con el relieve real se traza el perfil del terreno entre las antenas, se añade la "
        "curvatura terrestre (k = 4/3) y se comprueba que al menos el 60 % de la primera zona "
        "de Fresnel esté libre. Los obstáculos se reducen a un filo de cuchillo equivalente "
        "(método de Bullington, ITU-R P.526).",
        "With real terrain the profile between the antennas is traced, the Earth curvature "
        "(k = 4/3) is added and at least 60% of the first Fresnel zone must be clear. "
        "Obstacles are reduced to one equivalent knife edge (Bullington method, ITU-R P.526).",
    ),
    "about.colours.title": ("Colores del mapa de cobertura", "Coverage map colours"),
    "about.colours.text": (
        "El color indica cuánto supera la señal la sensibilidad del receptor. Donde no hay "
        "color, la señal no llega.",
        "The colour shows how far the signal exceeds the receiver sensitivity. Where there is "
        "no colour, the signal does not reach.",
    ),
    "about.colours.margin": (
        "≥ {margin:g} dB sobre la sensibilidad",
        "≥ {margin:g} dB above sensitivity",
    ),  # fmt: skip
    "about.bands.title": ("Bandas LTE/5G en España", "LTE/5G bands in Spain"),
    "about.limits.title": ("Limitaciones", "Limitations"),
    "about.limits.text": (
        "- Los modelos empíricos dan la pérdida **mediana**: la señal real varía varios dB "
        "alrededor (desvanecimiento lento); el margen cubre esa variación.\n"
        "- El modelo de elevación (~30 m) no incluye edificios ni vegetación: en ciudad es más "
        "representativo el modelo urbano de 3GPP.\n"
        "- La potencia mostrada es la total del canal (no RSRP); no se calcula interferencia "
        "ni capacidad.",
        "- Empirical models give the **median** loss: real signals vary several dB around it "
        "(slow fading); the margin covers that variation.\n"
        "- The elevation model (~30 m) has no buildings or vegetation: in cities the 3GPP "
        "urban model is more representative.\n"
        "- The power shown is the total over the channel (not RSRP); interference and "
        "capacity are not computed.",
    ),
    "about.sources.title": ("Fuentes y referencias", "Sources and references"),
    "about.sources.text": (
        "- Elevación: teselas *Terrarium* (Tilezen / AWS Open Data, a partir de SRTM).\n"
        "- Mapas: © OpenStreetMap, © Esri, © OpenTopoMap, © Instituto Geográfico Nacional "
        "(mapa base y PNOA).\n"
        "- M. Hata (1980); COST 231 (1999); 3GPP TR 38.901 y TR 36.814; ITU-R P.525 y P.526.",
        "- Elevation: *Terrarium* tiles (Tilezen / AWS Open Data, from SRTM).\n"
        "- Maps: © OpenStreetMap, © Esri, © OpenTopoMap, © Instituto Geográfico Nacional "
        "(base map and PNOA).\n"
        "- M. Hata (1980); COST 231 (1999); 3GPP TR 38.901 and TR 36.814; ITU-R P.525 and P.526.",
    ),
}


def current_language() -> str:
    lang = st.session_state.get("lang", DEFAULT_LANGUAGE)
    return lang if lang in LANGUAGES else DEFAULT_LANGUAGE


def has(key: str) -> bool:
    return key in WEB_TEXT or core_has(key)


def t(key: str, lang: str | None = None, **values) -> str:
    """Text for ``key`` in ``lang`` (by default, the language chosen in the sidebar)."""
    lang = lang or current_language()
    if key in WEB_TEXT:
        spanish, english = WEB_TEXT[key]
        text = spanish if lang == "es" else english
        return text.format(**values) if values else text
    return tr(key, lang, **values)


def labels(prefix: str, **values):
    """``format_func`` for option widgets: ``key -> t(prefix + key)``.

    The language is fixed when the widget is created, so the labels stay consistent
    even if Streamlit calls the function outside the page run.
    """
    lang = current_language()
    return lambda option: t(f"{prefix}{option}", lang, **values)
