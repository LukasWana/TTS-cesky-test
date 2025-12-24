@echo off
echo ========================================
echo Instalace audiocraft pro SFX generovani
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

echo Kontroluji, zda je audiocraft jiz nainstalovano...
python -c "import audiocraft" >nul 2>&1
if not errorlevel 1 (
  echo audiocraft je jiz nainstalovano!
  python -c "import audiocraft; print('Version:', audiocraft.__version__ if hasattr(audiocraft, '__version__') else 'unknown')"
  pause
  exit /b 0
)

echo.
echo ========================================
echo VAROVANI PRED INSTALACI
echo ========================================
echo.
echo Instalace audiocraft na Windows muze trvat dlouho
echo kvuli kompilaci FFmpeg/PyAV zavislosti (10-30 minut).
echo.
echo Pokud instalace selze, mozne duvody:
echo - Chybejici Visual Studio Build Tools (C++ kompilator)
echo - Nedostatek pameti pri kompilaci
echo - Problem s Python/PyTorch verzemi
echo.
echo POZNAMKA: SFX generovani je volitelne.
echo Aplikace funguje i bez audiocraft (TTS a MusicGen budou fungovat).
echo.
echo ========================================
set /p CONTINUE="Pokracovat s instalaci audiocraft? (y/n): "
if /i not "%CONTINUE%"=="y" (
  echo Instalace zrusena.
  pause
  exit /b 0
)

echo.
echo Upgrading pip...
python -m pip install --upgrade pip

echo.
echo ========================================
echo ZACINAM INSTALACI
echo ========================================
echo.
echo Installing audiocraft...
echo (Toto muze trvat 10-30 minut kvuli kompilaci...)
echo (Muzete sledovat progress nize)
echo.
echo ========================================
pip install audiocraft 2>&1 | tee install_log.txt
echo ========================================
set INSTALL_EXIT_CODE=%errorlevel%

REM Kontrola exit code a logu
findstr /i "error\|failed" install_log.txt >nul 2>&1
if not errorlevel 1 (
  set INSTALL_EXIT_CODE=1
)

if %INSTALL_EXIT_CODE% neq 0 (
  echo.
  echo ========================================
  echo INSTALACE SELHALA
  echo ========================================
  echo.
  echo Pip vratil chybu behem instalace.
  echo Toto je typicke na Windows kvuli PyAV kompilaci.
  echo.
  echo ZKUSTE ALTERNATIVNI METODY:
  echo.
  echo 1. CONDA PRISTUP (doporuceno):
  echo    conda install -c conda-forge av ffmpeg
  echo    pip install audiocraft
  echo.
  echo 2. PRE-BUILT WHEELS:
  echo    pip install audiocraft --no-build-isolation
  echo.
  echo 3. MANUAL FFmpeg:
  echo    Stahnete FFmpeg dev z: https://ffmpeg.org/download.html
  echo    Pridajte bin do PATH a zkuste pip install av
  echo.
  goto :post_install_check
)

REM Kontrola jestli je instalace skutecne funkcni
echo Testuji funkcnost audiocraft...
python -c "from audiocraft.models import AudioGen; print('AudioGen import OK')" >nul 2>&1
if errorlevel 1 (
  echo.
  echo ========================================
  echo INSTALACE NENI FUNKCNI
  echo ========================================
  echo.
  echo Pip rekl uspech, ale AudioGen nejde importovat.
  echo Toto je znamy problem na Windows s PyAV/FFmpeg.
  echo.
  echo RESENI:
  echo.
  echo 1. Pouzit pre-kompilovane wheels:
  echo    pip install audiocraft --no-build-isolation
  echo.
  echo 2. Nebo nainstalovat conda a pouzit:
  echo    conda install -c conda-forge av ffmpeg
  echo    pip install audiocraft
  echo.
  echo 3. Nebo pouzit WSL/Docker pro backend
  echo.
  echo 4. Alternativne: pouzit MusicGen pro SFX generovani
  echo    (zkuste prompty typu 'sci-fi laser sound effect')
  echo.
  echo SFX generovani je volitelne - aplikace funguje i bez toho.
  echo.
) else (
  echo.
  echo ========================================
  echo INSTALACE USPESNA A FUNKCNI
  echo ========================================
  echo.
  echo audiocraft je nainstalovano a funkcní!
  echo SFX generovani je nyni plne dostupne.
  echo Restartujte backend server, aby se zmeny projevily.
  echo.
)

pause

