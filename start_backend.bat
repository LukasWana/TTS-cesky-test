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

REM Doinstaluj backend dependencies pokud chybí (hlavně MusicGen / transformers)
python -c "import transformers" >nul 2>&1
if errorlevel 1 (
    echo [INFO] transformers nejsou nainstalovane - instaluji requirements.txt...
    python -m pip install --upgrade pip
    pip install -r "%~dp0requirements.txt"
    if errorlevel 1 (
        echo ERROR: pip install selhal.
        pause
        exit /b 1
    )
)

set PYTHONPATH=%PYTHONPATH%;%CD%
REM Výchozí headroom (pokud už není nastaven zvenku)
if not defined OUTPUT_HEADROOM_DB set OUTPUT_HEADROOM_DB=-9.0

cd backend
python main.py

