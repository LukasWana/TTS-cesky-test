@echo off
echo ========================================
echo Kontrola audiocraft instalace
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

echo.
echo Test 1: Kontrola zda je audiocraft nainstalovano...
pip list | findstr /i "audiocraft" >nul 2>&1
if errorlevel 1 (
  echo ❌ audiocraft neni nainstalovano
  echo Spustte install_audiocraft.bat pro instalaci.
  goto :end
) else (
  echo ✅ audiocraft je nainstalovano v pip
)

echo.
echo Test 2: Kontrola importu audiocraft...
python -c "import audiocraft; print('Version:', getattr(audiocraft, '__version__', 'unknown'))" >nul 2>&1
if errorlevel 1 (
  echo ❌ Nelze importovat audiocraft
  echo Problem s instalaci - zkuste preinstalovat.
  goto :end
) else (
  echo ✅ audiocraft lze importovat
)

echo.
echo Test 3: Kontrola AudioGen modelu...
python -c "from audiocraft.models import AudioGen; print('AudioGen OK')" >nul 2>&1
if errorlevel 1 (
  echo ❌ AudioGen nejde importovat (problem s PyAV/FFmpeg)
  echo Toto je znamy problem na Windows.
  echo.
  echo RESENI:
  echo 1. pip uninstall audiocraft av
  echo    conda install -c conda-forge av ffmpeg
  echo    pip install audiocraft
  echo.
  echo 2. Nebo pouzive MusicGen pro SFX generovani
  goto :end
) else (
  echo ✅ AudioGen lze importovat
)

echo.
echo Test 4: Kontrola CUDA dostupnosti...
python -c "import torch; print('CUDA available:', torch.cuda.is_available())" 2>nul
if errorlevel 1 (
  echo ❌ Problem s PyTorch
) else (
  echo ✅ PyTorch funguje
)

echo.
echo ========================================
echo Vsechny testy probehly uspesne!
echo ========================================
echo.
echo SFX generovani by melo fungovat.
echo Restartujte backend server pokud bezite.

:end
echo.
pause



