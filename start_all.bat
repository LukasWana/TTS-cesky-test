@echo off
setlocal EnableExtensions

REM Zajisti, ze se okno nezavre - automaticky spust v cmd /k
if not "%1"=="INTERNAL" (
  cmd /k "%~f0" INTERNAL
  exit /b
)

REM %~dp0 vraci cestu s backslashem na konci, ale pro jistotu zajistime
set "ROOT=%~dp0"
if not "%ROOT:~-1%"=="\" set "ROOT=%ROOT%\"
set "LOG_DIR=%ROOT%logs"
set "BACKEND_LOG=%LOG_DIR%\backend.log"
set "CACHE_SCRIPT=%ROOT%scripts\start_cache.py"

echo XTTS-v2 Demo - START ALL
echo =======================
echo.

REM 0) Zkontrolovat zda máme --force-check flag
set "USE_CACHE=1"
if "%1"=="--force-check" set "USE_CACHE=0"
if "%2"=="--force-check" set "USE_CACHE=0"

REM 1) Vyber kompatibilni Python (3.11 -> 3.10 -> 3.9)
echo [1/11] Checking Python version...
set "PYTHON_CMD="

REM Zkus Python 3.11
py -3.11 --version >nul 2>&1
if not errorlevel 1 (
  set "PYTHON_CMD=py -3.11"
  goto :python_found
)

REM Zkus Python 3.10
py -3.10 --version >nul 2>&1
if not errorlevel 1 (
  set "PYTHON_CMD=py -3.10"
  goto :python_found
)

REM Zkus Python 3.9
py -3.9 --version >nul 2>&1
if not errorlevel 1 (
  set "PYTHON_CMD=py -3.9"
  goto :python_found
)

REM Python nenalezen
echo.
echo ERROR: Nebyla nalezena kompatibilni verze Pythonu (3.9-3.11).
echo Dostupne verze:
py --list 2>nul || echo py launcher not found
echo.
echo Please install Python 3.10 or 3.11 from https://www.python.org/downloads/
echo Make sure to check "Add Python to PATH" during installation.
echo.
pause
exit /b 1

:python_found
echo Found: %PYTHON_CMD%
%PYTHON_CMD% --version
echo.

REM 1.5) Zkontrolovat cache (teď když máme Python)
if "%USE_CACHE%"=="1" (
  echo [1.5/11] Checking cache...
  %PYTHON_CMD% "%CACHE_SCRIPT%" check >nul 2>&1
  if not errorlevel 1 (
    echo Cache is valid - using cached values for faster startup.
    set "CACHE_VALID=1"
  ) else (
    set "CACHE_VALID=0"
  )
  echo.
) else (
  set "CACHE_VALID=0"
)

REM 2) Node kontrola
if "%CACHE_VALID%"=="1" (
  echo [2/11] Node.js (cached - skipping check)
  node --version
  echo.
) else (
  echo [2/11] Checking Node.js...
  node --version >nul 2>&1
  if errorlevel 1 (
    echo ERROR: Node.js neni nainstalovany. Nainstalujte Node 18+.
    echo Download from: https://nodejs.org/
    echo.
    pause
    exit /b 1
  )
  node --version
  echo.
)

REM 3) Venv (jen kdyz neexistuje)
:recreate_venv
if "%CACHE_VALID%"=="1" (
  echo [3/11] Virtual environment (cached - skipping check)
  if not exist "%ROOT%venv\Scripts\python.exe" (
    echo WARNING: venv not found despite cache - recreating...
    set "CACHE_VALID=0"
  )
  if exist "%ROOT%venv\Scripts\python.exe" (
    echo Virtual environment exists.
    goto :venv_activated
  )
)

echo [3/11] Checking virtual environment...
if not exist "%ROOT%venv\Scripts\python.exe" (
  echo Creating venv with %PYTHON_CMD%...
  %PYTHON_CMD% -m venv "%ROOT%venv"
  if errorlevel 1 (
    echo ERROR: Vytvoreni venv selhalo.
    pause
    exit /b 1
  )
  echo Virtual environment created.
) else (
  echo Virtual environment exists.
)

:venv_activated
echo Activating virtual environment...
call "%ROOT%venv\Scripts\activate.bat"
if errorlevel 1 (
  echo ERROR: Aktivace venv selhala.
  pause
  exit /b 1
)
echo Virtual environment activated.
echo.

REM 3.5) Vynutit UTF-8 a vypnout wandb (Windows cp1252 jinak shazuje diakritiku / PYTHONUTF8 muze byt spatne nastavene globalne)
set "PYTHONUTF8="
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "WANDB_MODE=disabled"
set "WANDB_SILENT=true"

REM 4) Backend deps jen kdyz chybi (rychly check importu)
if "%CACHE_VALID%"=="1" (
  echo [4/11] Backend dependencies (cached - skipping check)
  echo Backend dependencies OK (skip pip install).
  goto :after_backend_check
)

echo [4/11] Checking backend dependencies...
python -c "import fastapi" >nul 2>&1
if errorlevel 1 goto :install_backend_deps
python -c "import TTS" >nul 2>&1
if errorlevel 1 goto :install_backend_deps
python -c "import librosa" >nul 2>&1
if errorlevel 1 goto :install_backend_deps
python -c "import soundfile" >nul 2>&1
if errorlevel 1 goto :install_backend_deps
python -c "import transformers" >nul 2>&1
if errorlevel 1 goto :install_backend_deps
python -c "import scipy" >nul 2>&1
if errorlevel 1 goto :install_backend_deps
python -c "import yt_dlp" >nul 2>&1
if errorlevel 1 goto :install_backend_deps

echo Backend dependencies OK (skip pip install).
goto :after_backend_check

:install_backend_deps
echo Installing backend dependencies (pip)...
python -m pip install --upgrade pip
if errorlevel 1 (
  echo ERROR: pip upgrade selhal.
  pause
  exit /b 1
)
pip install -r "%ROOT%requirements.txt"
if errorlevel 1 (
  echo ERROR: pip install selhal.
  pause
  exit /b 1
)
echo Backend dependencies installed.
goto :after_backend_check

:after_backend_check
echo.

REM 4.1) Kontrola Demucs (volitelné, ale doporučené pro separaci hlasu)
if "%CACHE_VALID%"=="1" (
  echo [4.1/11] Demucs (cached - skipping check)
  echo Demucs is already installed.
  echo.
  goto :after_demucs
)

echo [4.1/11] Checking Demucs installation...
python -c "import demucs" >nul 2>&1
if errorlevel 1 (
  echo Demucs is not installed. Installing...
  pip install "demucs>=4.0.0"
  if errorlevel 1 (
    echo WARNING: Demucs installation failed. Voice separation feature will not be available.
    echo You can install it later manually: pip install demucs
  ) else (
    echo Verifying Demucs installation...
    python -c "import demucs; print('Demucs OK')" >nul 2>&1
    if errorlevel 1 (
      echo WARNING: Demucs installation verification failed. Voice separation may not work.
    ) else (
      echo Demucs installed successfully.
    )
  )
) else (
  echo Demucs is already installed.
)
:after_demucs
echo.

REM 4.2) Pokud je vyzadovano GPU, zajisti CUDA build PyTorch (jinak torch bude CPU build z requirements.txt)
if /i "%FORCE_DEVICE%"=="cuda" goto :ensure_cuda_torch
goto :after_cuda_torch

:ensure_cuda_torch
echo [4.2/11] FORCE_DEVICE=cuda detected - ensuring CUDA PyTorch...
if not defined CUDA_URL set "CUDA_URL=cu121"
echo Using CUDA wheel index: %CUDA_URL%

REM Pokud uz je CUDA PyTorch OK, nic nepreinstalovavat (aby se to nedelo pri kazdem startu)
python "%ROOT%check_cuda_ready.py" >nul 2>&1
if not errorlevel 1 (
  echo CUDA PyTorch is already OK - skipping reinstall.
  echo.
  goto :after_cuda_torch
)

echo Uninstalling torch/torchaudio/torchcodec (if present)...
pip uninstall -y torch torchaudio torchcodec >nul 2>&1
echo Installing torch==2.1.0 + torchaudio==2.1.0 (%CUDA_URL%)...
pip install torch==2.1.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/%CUDA_URL%
if errorlevel 1 (
  echo ERROR: CUDA PyTorch install failed.
  echo Tip: zkuste spustit install_pytorch_gpu.bat a vybrat spravnou CUDA verzi.
  pause
  exit /b 1
)
echo Verifying CUDA availability...
python "%ROOT%check_gpu.py"
echo.
goto :after_cuda_torch

:after_cuda_torch

REM 4.5) Bark instalace (volitelne, ale doporucene)
if "%CACHE_VALID%"=="1" (
  echo [5/11] Bark (cached - skipping check)
  echo Bark is already installed.
  echo.
  goto :after_bark
)

echo [5/11] Checking Bark (Suno AI) installation...
python -c "from bark import generate_audio, preload_models, SAMPLE_RATE" >nul 2>&1
if errorlevel 1 (
  echo Bark is not installed. Installing from GitHub...
  pip install git+https://github.com/suno-ai/bark.git
  if errorlevel 1 (
    echo WARNING: Bark installation failed. Bark features will not be available.
    echo You can install it later manually: pip install git+https://github.com/suno-ai/bark.git
  ) else (
    echo Verifying Bark installation...
    python -c "from bark import generate_audio, preload_models, SAMPLE_RATE; print('Bark OK')" >nul 2>&1
    if errorlevel 1 (
      echo WARNING: Bark installation verification failed. Bark features may not work.
    ) else (
      echo Bark installed successfully.
    )
  )
) else (
  echo Bark is already installed.
)
:after_bark
echo.

REM 4.6) F5-TTS instalace (volitelne)
if "%CACHE_VALID%"=="1" (
  echo [6/11] F5-TTS (cached - skipping check)
  echo F5-TTS is already installed.
  echo.
  goto :f5_done
)

echo [6/11] Checking F5-TTS installation...
if exist "%ROOT%venv\Scripts\f5-tts_infer-cli.exe" (
  echo F5-TTS is already installed.
  goto :f5_done
)
echo F5-TTS is not installed. Installing from PyPI...
REM DULEZITE: neinstalovat deps, aby se neprepsal torch/torchaudio (GPU->CPU)
pip install f5-tts --no-deps
if errorlevel 1 (
  echo WARNING: F5-TTS installation with --no-deps failed. Trying with dependencies...
  pip install f5-tts
  if errorlevel 1 (
    echo WARNING: F5-TTS installation failed. F5-TTS features will not be available.
    echo You can install it later manually: pip install f5-tts
    echo Or run: install_f5tts.bat
    goto :f5_done
  )
  echo F5-TTS installed successfully with dependencies.
  if /i "%FORCE_DEVICE%"=="cuda" (
    python "%ROOT%check_cuda_ready.py" >nul 2>&1
    if errorlevel 1 (
      echo WARNING: PyTorch se mozna prepsal na CPU build po instalaci F5-TTS.
      echo Zkuste znovu spustit start_gpu.bat nebo install_pytorch_gpu.bat.
    )
  )
  goto :f5_done
)
echo F5-TTS installed successfully without dependencies.
:f5_done
echo.

REM 4.7) F5-TTS Slovak model download (volitelne)
if "%CACHE_VALID%"=="1" (
  echo [7/11] F5-TTS Slovak model (cached - skipping check)
  echo F5-TTS Slovak model is already downloaded.
  echo.
  goto :f5_slovak_done
)

echo [7/11] Checking F5-TTS Slovak model...
python -c "import sys; sys.path.insert(0, '.'); from backend.config import F5_SLOVAK_MODEL_DIR; from pathlib import Path; model_files = ['model_30000.safetensors', 'model_30000.txt']; exists = any((F5_SLOVAK_MODEL_DIR / f).exists() for f in model_files); sys.exit(0 if exists else 1)" >nul 2>&1
if not errorlevel 1 (
  echo F5-TTS Slovak model is already downloaded.
  goto :f5_slovak_done
)
echo F5-TTS Slovak model is not downloaded. Downloading from Hugging Face...
call "%ROOT%install_f5tts_slovak_model.bat" INTERNAL
if errorlevel 1 (
  echo WARNING: F5-TTS Slovak model download failed. Slovak F5-TTS features will not be available.
  echo You can download it later manually: install_f5tts_slovak_model.bat
  goto :f5_slovak_done
)
echo F5-TTS Slovak model downloaded successfully.
:f5_slovak_done
echo.

REM 8) Frontend deps jen kdyz chybi
set "FRONTEND_DIR=%ROOT%frontend"
if "%CACHE_VALID%"=="1" (
  echo [8/11] Frontend dependencies (cached - skipping check)
  echo Frontend dependencies OK - skipping npm install.
  echo.
  goto :after_frontend_deps
)

echo [8/11] Checking frontend dependencies
if not exist "%FRONTEND_DIR%\node_modules" (
  echo Installing frontend dependencies (npm)
  pushd "%FRONTEND_DIR%"
  call npm install
  if errorlevel 1 (
    popd
    echo ERROR: npm install selhal.
    pause
    exit /b 1
  )
  popd
  echo Frontend dependencies installed.
) else (
  echo Frontend dependencies OK - skipping npm install.
)
:after_frontend_deps
echo.

REM 8.5) Aktualizovat cache (až po aktivaci venv a kontrole závislostí)
if "%CACHE_VALID%"=="0" (
  echo [8.5/11] Updating cache...
  python "%CACHE_SCRIPT%" update >nul 2>&1
  if errorlevel 1 (
    echo WARNING: Cache update failed, continuing anyway...
  ) else (
    echo Cache updated.
  )
  echo.
)

REM 9) Spust backend v novem okne
echo [9/11] Starting backend...
set "BACKEND_DIR=%ROOT%backend"
set "VENV_ACTIVATE=%ROOT%venv\Scripts\activate.bat"

REM Priprav log soubor, abychom mohli cekat na "Application startup complete."
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1
if exist "%BACKEND_LOG%" del /q "%BACKEND_LOG%" >nul 2>&1

REM Předání FORCE_DEVICE do backend procesu (pokud je nastaveno)
REM Pouzit -X utf8 flag misto PYTHONUTF8 env var (aby se vyhnulo konfliktu s globalnim nastavenim)
REM Poznámka: Používáme Python wrapper script pro barevný výstup a zápis do log souboru
if defined FORCE_DEVICE (
  echo Device mode: %FORCE_DEVICE%
  start "XTTS Backend" cmd /k "cd /d %BACKEND_DIR% && call %VENV_ACTIVATE% && set PYTHONPATH=%ROOT% && set PYTHONIOENCODING=utf-8 && set WANDB_MODE=disabled && set WANDB_SILENT=true && set FORCE_DEVICE=%FORCE_DEVICE% && python run_with_logging.py"
) else (
  start "XTTS Backend" cmd /k "cd /d %BACKEND_DIR% && call %VENV_ACTIVATE% && set PYTHONPATH=%ROOT% && set PYTHONIOENCODING=utf-8 && set WANDB_MODE=disabled && set WANDB_SILENT=true && python run_with_logging.py"
)

REM 9.5) Sync Applio voices and start Applio
echo [9.5/12] Syncing Applio voices and starting Applio...
powershell -ExecutionPolicy Bypass -File "backend\applio\sync-voices.ps1" >nul
start "" cmd /c "cd /d backend\applio && env\python.exe app.py --open"
echo Applio started (check http://localhost:6969)
echo.

REM 10) Pockej, az backend dokonci startup
echo [10/12] Waiting for backend readiness...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$log = '%BACKEND_LOG%'; " ^
  "$needle = 'BACKEND IS READY'; " ^
  "$ready = $false; " ^
  "$deadline = (Get-Date).AddMinutes(5); " ^
  "while((Get-Date) -lt $deadline) { " ^
  "  try { $resp = Invoke-WebRequest -Uri 'http://localhost:8000/docs' -TimeoutSec 1 -UseBasicParsing; if($resp.StatusCode -eq 200) { $ready = $true; break } } catch { } " ^
  "  if(Test-Path $log) { if(Select-String -Path $log -SimpleMatch $needle -Quiet) { $ready = $true; break } } " ^
  "  Start-Sleep -Milliseconds 1000; " ^
  "  Write-Host -NoNewline '.'; " ^
  "} " ^
  "if($ready) { Write-Host ' Backend ready.' } else { Write-Host ' ERROR: Backend nedokoncil startup.'; exit 1 }"
if errorlevel 1 (
  echo.
  echo ERROR: Backend se nejevi jako ready. Frontend se nespusti.
  echo Tip: zkontrolujte log: "%BACKEND_LOG%"
  echo.
  if not "%2"=="--no-pause" pause
  exit /b 1
)
echo.

REM 11) Spust frontend v novem okne
echo [11/12] Starting frontend...
start "XTTS Frontend" cmd /k "cd /d %FRONTEND_DIR% && npm run dev"

REM 12) Otevri prohlizec
echo [12/12] Opening browser...
timeout /t 2 /nobreak >nul 2>&1
start "" "http://localhost:3000"
start "" "http://localhost:6969"

echo.
echo ============================================
echo All services started successfully!
echo ============================================
echo.
echo  Backend:    http://localhost:8000
echo  Frontend:   http://localhost:3000
echo  Applio:     http://localhost:6969 (optional)
echo.
echo Press any key to close this window...
pause >nul
exit /b 0


