@echo off
setlocal
cd /d "%~dp0"
title Visualizador de cobertura radio LTE/5G

rem Busca Python: primero el lanzador "py" y si no "python".
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY goto nopython
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul || goto oldpython

rem La primera vez crea un entorno aislado e instala lo necesario.
if not exist ".venv\instalado.txt" (
  echo.
  echo Preparando el programa por primera vez. Puede tardar unos minutos...
  echo.
  if not exist ".venv\Scripts\python.exe" %PY% -m venv .venv || goto error
  ".venv\Scripts\python.exe" -m pip install --upgrade pip || goto error
  ".venv\Scripts\python.exe" -m pip install -e ".[web]" || goto error
  echo ok> ".venv\instalado.txt"
)

echo.
echo Abriendo el visualizador en el navegador...
echo Para cerrarlo, cierra esta ventana.
echo.
".venv\Scripts\python.exe" -m streamlit run app\streamlit_app.py
goto end

:nopython
echo.
echo No se encuentra Python. Instalalo desde https://www.python.org/downloads/
echo y marca la casilla "Add python.exe to PATH" al instalarlo.
goto end

:oldpython
echo.
echo Hace falta Python 3.11 o mas reciente. Descargalo de https://www.python.org/downloads/
goto end

:error
echo.
echo Ha habido un error durante la instalacion. Comprueba tu conexion a Internet
echo y vuelve a ejecutar este archivo.

:end
echo.
pause
