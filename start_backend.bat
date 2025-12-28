@echo off

REM Vynutit UTF-8 a vypnout wandb (Windows cp1252 / spatne globalni PYTHONUTF8 muze shodit Python pri startu)
set "PYTHONUTF8="
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "WANDB_MODE=disabled"
set "WANDB_SILENT=true"

REM Nastavit kódování konzole na UTF-8 pro správné zobrazování českých znaků
chcp 65001 >nul 2>&1

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

REM Kontrola Demucs (volitelné, ale doporučené pro separaci hlasu)
python -c "import demucs" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Demucs neni nainstalovan - instaluji...
    pip install "demucs>=4.0.0"
    if errorlevel 1 (
        echo WARNING: Instalace Demucs selhala. Separace hlasu od pozadi nebude dostupna.
        echo Muzete nainstalovat pozdeji: pip install demucs
    ) else (
        echo Demucs nainstalovan uspesne.
    )
)

set PYTHONPATH=%PYTHONPATH%;%CD%
REM Výchozí headroom (pokud už není nastaven zvenku)
REM POZOR: Musí odpovídat výchozí hodnotě v backend/config.py (-18.0 dB)!
REM Změna této hodnoty může způsobit přebuzení audio!
if not defined OUTPUT_HEADROOM_DB set OUTPUT_HEADROOM_DB=-18.0

cd backend
REM Pouzit -X utf8 flag misto PYTHONUTF8 env var (aby se vyhnulo konfliktu s globalnim nastavenim)
python -X utf8 main.py

