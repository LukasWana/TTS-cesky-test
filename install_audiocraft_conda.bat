@echo off
echo ========================================
echo Instalace audiocraft pres CONDA (doporuceno pro Windows)
echo ========================================
echo.

REM Zkontroluj, zda je venv aktivni
if not defined VIRTUAL_ENV (
  if exist "venv\Scripts\activate.bat" (
    echo Aktivuji virtual environment...
    call venv\Scripts\activate.bat
  ) else (
    echo ERROR: Virtual environment nenalezen!
    echo Spustte nejprve run.bat nebo aktivujte venv manualne.
    pause
    exit /b 1
  )
)

echo Kontroluji, zda je conda dostupny...
conda --version >nul 2>&1
if errorlevel 1 (
  echo.
  echo ERROR: Conda neni nainstalovana!
  echo.
  echo Pro pouziti teto metody nainstalujte Miniconda nebo Anaconda:
  echo https://docs.conda.io/projects/miniconda
  echo.
  echo Nebo pouzive standardni pip metodu: install_audiocraft.bat
  echo.
  pause
  exit /b 1
)

echo Kontroluji, zda je audiocraft jiz nainstalovano...
python -c "from audiocraft.models import AudioGen; print('AudioGen OK')" >nul 2>&1
if not errorlevel 1 (
  echo audiocraft je jiz nainstalovano a funkcní!
  pause
  exit /b 0
)

echo.
echo ========================================
echo VAROVANI
echo ========================================
echo.
echo Tato metoda pouziva conda pro instalaci FFmpeg a PyAV,
echo pote pip pro audiocraft. Je mnohem spolehlivejsi nez pip-only.
echo.
echo POZNAMKA: SFX generovani je volitelne.
echo Aplikace funguje i bez audiocraft.
echo.
set /p CONTINUE="Pokracovat s instalaci? (y/n): "
if /i not "%CONTINUE%"=="y" (
  echo Instalace zrusena.
  pause
  exit /b 0
)

echo.
echo ========================================
echo KROK 1: Instalace FFmpeg a PyAV pres conda
echo ========================================
echo.
conda install -c conda-forge av ffmpeg -y
if errorlevel 1 (
  echo.
  echo ERROR: Conda instalace selhala!
  echo Zkuste pip uninstall av ffmpeg (pokud nainstalovano)
  echo a spustte znovu.
  pause
  exit /b 1
)

echo.
echo ========================================
echo KROK 2: Instalace audiocraft pres pip
echo ========================================
echo.
pip install audiocraft
if errorlevel 1 (
  echo.
  echo WARNING: Pip instalace audiocraft selhala,
  echo ale FFmpeg/PyAV by mely byt funkcní.
  echo Zkuste pip install audiocraft --no-build-isolation
)

echo.
echo ========================================
echo TESTOVANI FUNKCNOSTI
echo ========================================
echo.
echo Testuji AudioGen import...
python -c "from audiocraft.models import AudioGen; print('✅ AudioGen import OK')" >nul 2>&1
if errorlevel 1 (
  echo ❌ AudioGen nejde importovat
  echo.
  echo MOZNE RESENI:
  echo 1. Restartujte terminal a zkuste znovu
  echo 2. pip install audiocraft --no-build-isolation
  echo 3. conda install -c conda-forge audiocraft (pokud existuje)
  echo.
) else (
  echo.
  echo ========================================
  echo USPESNE DOKONCENO!
  echo ========================================
  echo.
  echo audiocraft je nainstalovano pres conda a funkcní!
  echo SFX generovani je nyni dostupne.
  echo Restartujte backend server.
  echo.
)

pause



