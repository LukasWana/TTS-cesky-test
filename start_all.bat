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

echo XTTS-v2 Demo - START ALL
echo =======================
echo.

REM 1) Vyber kompatibilni Python (3.11 -> 3.10 -> 3.9)
echo [1/9] Checking Python version...
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

REM 2) Node kontrola
echo [2/9] Checking Node.js...
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

REM 3) Venv (jen kdyz neexistuje)
echo [3/9] Checking virtual environment...
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
goto :backend_deps_done

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

:backend_deps_done
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
echo.

REM 4.6) F5-TTS instalace (volitelne)
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
echo [8/11] Checking frontend dependencies
set "FRONTEND_DIR=%ROOT%frontend"
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
echo.

REM 8) Spust backend v novem okne
echo [8/11] Starting backend...
set "BACKEND_DIR=%ROOT%backend"
set "VENV_ACTIVATE=%ROOT%venv\Scripts\activate.bat"

REM Priprav log soubor, abychom mohli cekat na "Application startup complete."
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1
if exist "%BACKEND_LOG%" del /q "%BACKEND_LOG%" >nul 2>&1

REM Předání FORCE_DEVICE do backend procesu (pokud je nastaveno)
REM Pouzit -X utf8 flag misto PYTHONUTF8 env var (aby se vyhnulo konfliktu s globalnim nastavenim)
if defined FORCE_DEVICE (
  echo Device mode: %FORCE_DEVICE%
  start "XTTS Backend" cmd /k "cd /d %BACKEND_DIR% && call %VENV_ACTIVATE% && set PYTHONPATH=%ROOT% && set PYTHONIOENCODING=utf-8 && set WANDB_MODE=disabled && set WANDB_SILENT=true && set FORCE_DEVICE=%FORCE_DEVICE% && powershell -NoProfile -ExecutionPolicy Bypass -Command ""python -X utf8 main.py 2^>^&1 ^| Tee-Object -FilePath '%BACKEND_LOG%'"""
) else (
  start "XTTS Backend" cmd /k "cd /d %BACKEND_DIR% && call %VENV_ACTIVATE% && set PYTHONPATH=%ROOT% && set PYTHONIOENCODING=utf-8 && set WANDB_MODE=disabled && set WANDB_SILENT=true && powershell -NoProfile -ExecutionPolicy Bypass -Command ""python -X utf8 main.py 2^>^&1 ^| Tee-Object -FilePath '%BACKEND_LOG%'"""
)

REM 9) Pockej, az backend dokonci startup (hlaska z uvicornu)
echo [9/11] Waiting for backend readiness...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$log = '%BACKEND_LOG%';" ^
  "$needle = 'Application startup complete.';" ^
  "$deadline = (Get-Date).AddMinutes(3);" ^
  "while((Get-Date) -lt $deadline) {" ^
  "  if(Test-Path $log) { if(Select-String -Path $log -SimpleMatch $needle -Quiet) { Write-Host 'Backend ready.'; exit 0 } }" ^
  "  Start-Sleep -Milliseconds 250" ^
  "}" ^
  "Write-Host 'ERROR: Backend nedokoncil startup do 3 minut (nenalezena hlaska Application startup complete.).'; exit 1"
if errorlevel 1 (
  echo.
  echo ERROR: Backend se nejevi jako ready. Frontend se nespusti.
  echo Tip: zkontrolujte log: "%BACKEND_LOG%"
  echo.
  pause
  exit /b 1
)
echo.

REM 10) Spust frontend v novem okne
echo [10/11] Starting frontend...
start "XTTS Frontend" cmd /k "cd /d %FRONTEND_DIR% && npm run dev"

REM 11) Otevri prohlizec
echo [11/11] Opening browser...
timeout /t 2 /nobreak >nul 2>&1
start "" "http://localhost:3000"

echo.
echo Done. (Backend: :8000, Frontend: :3000)
echo.
echo Press any key to close this window...
pause >nul
exit /b 0


