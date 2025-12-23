@echo off

REM Kontrola, zda venv existuje
if not exist "venv\Scripts\activate.bat" (
    echo Virtual environment not found!
    echo Please run run.bat first to create the environment.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

REM Kontrola Python verze v venv
python --version

set PYTHONPATH=%PYTHONPATH%;%CD%
REM Výchozí headroom (pokud už není nastaven zvenku)
if not defined OUTPUT_HEADROOM_DB set OUTPUT_HEADROOM_DB=-9.0

cd backend
python main.py

