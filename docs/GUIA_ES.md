# Guía del proyecto (en español)

Esta guía explica **qué hace** el visualizador de cobertura y **cómo contarlo** en una
entrevista, sin entrar en el código.

## Qué es

Una herramienta de **planificación radio** para redes móviles **LTE y 5G en España**.
Responde a dos preguntas que se hace cualquier operador:

1. **¿Llega la señal de esta antena a este punto?** → presupuesto de enlace punto a punto.
2. **¿Qué zona cubre esta antena (o esta red de antenas)?** → mapa de cobertura.

Para responderlas usa los mismos modelos que se estudian en la carrera y que emplean las
herramientas profesionales: espacio libre, Okumura-Hata, COST-231, 3GPP TR 38.901 y la
difracción de la ITU-R P.526, con el relieve real de España.

## Cómo se construyó (las 5 fases)

| Fase | Qué añade |
|---|---|
| 1 | Calculadora de presupuesto de enlace por línea de comandos, con tests automáticos |
| 2 | Enlace entre dos coordenadas GPS en un mapa, con zona de Fresnel y curvatura terrestre |
| 3 | Modelos de propagación realistas y mapa de cobertura con antenas sectoriales |
| 4 | Relieve real: perfil del terreno, visibilidad, despejamiento de Fresnel y difracción |
| 5 | Redes con varias antenas, mapa de mejor servidor, exportación a Google Earth y web |

## Conceptos clave (para defenderlo)

- **Presupuesto de enlace**: suma en dB de todo lo que se gana y se pierde entre el
  transmisor y el receptor. `P_rx = P_tx + G_tx − pérdidas + G_rx`.
- **PIRE (EIRP)**: potencia que radia la antena en su dirección principal.
- **Pérdidas en espacio libre**: lo mínimo que se pierde por la distancia. Es el caso
  ideal; en la realidad se pierde bastante más.
- **Okumura-Hata / COST-231**: modelos empíricos, sacados de medidas reales, para
  frecuencias de 150 a 2000 MHz. Distinguen entorno urbano, suburbano y rural.
- **3GPP TR 38.901**: el modelo estándar para 5G (por ejemplo, la banda n78 de 3,5 GHz).
- **Sensibilidad**: la mínima potencia que el móvil necesita. Sale del ruido térmico
  (−174 dBm/Hz), del ancho de canal, de la figura de ruido y de la SNR mínima.
- **Margen**: lo que sobra por encima de la sensibilidad. Se exige un margen para cubrir
  las variaciones de la señal (desvanecimientos).
- **Zona de Fresnel**: el "tubo" alrededor de la línea recta por el que viaja la mayor
  parte de la energía. Debe estar libre al menos un 60 %.
- **Abultamiento terrestre (k = 4/3)**: la curvatura de la Tierra, corregida por la
  refracción de la atmósfera.
- **Difracción en filo de cuchillo**: la pérdida que añade una montaña que tapa el
  enlace. Se usa el método de Bullington recomendado por la ITU-R P.526.
- **Antena sectorial**: antena que apunta en una dirección (normalmente 3 por
  emplazamiento, cada 120°). Detrás pierde unos 25 dB.
- **Mejor servidor**: en cada punto, la antena que llega con más potencia; es la que
  daría servicio al móvil.

## Ejemplos incluidos

- **Bola del Mundo → Segovia (LTE 800 MHz, 22 km)**: en espacio libre parece que el
  enlace sobra (36,5 dB de margen). Con el modelo Okumura-Hata rural y el relieve real, el
  margen baja a 5 dB y no cumple los 10 dB exigidos. Es un buen ejemplo para explicar por
  qué hacen falta modelos realistas.
- **Red LTE 800 MHz alrededor de Segovia**: cinco sectores sobre el relieve real; en el
  mapa se ven las sombras que hacen las montañas de la Sierra de Guadarrama.
- **Red 5G n78 en el centro de Madrid**: cinco emplazamientos con tres sectores cada uno
  (Sol, Cibeles, Lavapiés, Plaza de España y Atocha); muestra lo poco que alcanza la
  banda de 3,5 GHz en ciudad.

## Cómo enseñarlo

- **En GitHub**: la página principal (README) muestra las imágenes, las funciones y la
  insignia verde de "tests passing".
- **Como web pública**: se puede publicar gratis en Streamlit Community Cloud.
  1. Entra en <https://share.streamlit.io> e inicia sesión con tu cuenta de GitHub.
  2. Pulsa **Create app** y elige el repositorio `visualizador-coberura`, la rama `main`
     y el archivo `app/streamlit_app.py`.
  3. Pulsa **Deploy**. En unos minutos tendrás un enlace para poner en el CV.

## Frase para el CV

> **Visualizador de cobertura radio LTE/5G (Python).** Herramienta de planificación que
> calcula presupuestos de enlace y mapas de cobertura en España con modelos Okumura-Hata,
> COST-231 y 3GPP TR 38.901, relieve real y difracción ITU-R P.526. Mapas interactivos,
> exportación a Google Earth, aplicación web y más de 220 tests automáticos.

## Preguntas que te pueden hacer

- *¿Por qué el resultado en espacio libre es tan distinto del de Hata?* Porque el espacio
  libre supone visión directa sin obstáculos; Hata incluye el efecto medio de edificios,
  vegetación y terreno a partir de medidas reales.
- *¿Por qué no usas el relieve en Madrid?* Porque el modelo de elevación no incluye
  edificios; en ciudad el modelo 3GPP urbano ya tiene en cuenta los edificios de forma
  estadística.
- *¿Qué mejorarías?* Calcular la RSRP en lugar de la potencia total, añadir interferencia
  entre celdas (SINR), usar el modelo de elevación del IGN a 5 m y calibrar los modelos
  con medidas reales tomadas con un móvil.
