@echo off
REM Spusteni backendu v LITE rezimu (jen XTTS a nezbytne veci)
REM Ignoruje Bark, MusicGen, Applio pro rychlejsi start

REM Vynutit UTF-8
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

REM Kontrola virtual environment
if not exist "..\venv\Scripts\activate.bat" (
    echo Virtual environment not found in ..\venv!
    pause
    exit /b 1
)

call ..\venv\Scripts\activate.bat

REM Nastavit PYTHONPATH na project root (o uroven vys nez tento skript)
cd ..
set PYTHONPATH=%PYTHONPATH%;%CD%
cd backend

echo [INFO] Starting Backend in LITE mode...
python -X utf8 main.py --lite

pause
