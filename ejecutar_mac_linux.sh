#!/usr/bin/env bash
# Arranca el visualizador de cobertura en macOS o Linux.
set -e
cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
else
  echo "No se encuentra Python. Instalalo desde https://www.python.org/downloads/"
  exit 1
fi
if ! "$PY" -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"; then
  echo "Hace falta Python 3.11 o mas reciente: https://www.python.org/downloads/"
  exit 1
fi

# La primera vez crea un entorno aislado e instala lo necesario.
if [ ! -f .venv/instalado.txt ]; then
  echo "Preparando el programa por primera vez. Puede tardar unos minutos..."
  [ -x .venv/bin/python ] || "$PY" -m venv .venv
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -e ".[web]"
  touch .venv/instalado.txt
fi

echo "Abriendo el visualizador en el navegador. Para cerrarlo pulsa Ctrl+C."
exec .venv/bin/python -m streamlit run app/streamlit_app.py
