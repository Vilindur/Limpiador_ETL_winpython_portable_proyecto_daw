@echo off
TITLE Portal de Datos Portable
CLS

:: ==========================================
:: 1. PREPARACIÓN
:: ==========================================
cd /d "%~dp0"

:: Buscamos la carpeta de Python
set PYTHON_DIR=
for /d %%i in (python-*.amd64) do set PYTHON_DIR=%%i

IF NOT DEFINED PYTHON_DIR (
    color 4F
    echo [ERROR] No encuentro la carpeta 'python-*.amd64'.
    pause
    exit
)

echo [INFO] Cargando sistema...

:: ==========================================
:: 2. LIMPIEZA RÁPIDA (Solo nivel raíz)
:: ==========================================
if exist "__pycache__" rd /s /q "__pycache__"

:: ==========================================
:: 3. EJECUCIÓN (CONFIGURACIÓN SEGURA)
:: ==========================================
echo [INFO] Iniciando aplicacion...
echo.
echo  ---------------------------------------------------
echo   NO CIERRES ESTA VENTANA.
echo   La aplicacion esta activa mientras esto este abierto.
echo  ---------------------------------------------------
echo.

:: Usamos SOLO las banderas que sabemos que funcionan en DEBUG
"%PYTHON_DIR%\python.exe" -m streamlit run Home.py --server.headless=true --global.developmentMode=false

:: Si llegamos aqui, es que la aplicacion se cerro.
:: Comprobamos si fue por error
if %errorlevel% neq 0 (
    color 4F
    echo.
    echo [ALERTA] La aplicacion se cerro inesperadamente.
    echo Codigo de error: %errorlevel%
    echo.
    pause
)