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

REM 4) Backend deps jen kdyz chybi (rychly check importu)
echo [4/9] Checking backend dependencies...
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

REM 5) Frontend deps jen kdyz chybi
echo [5/9] Checking frontend dependencies
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

REM 6) Spust backend v novem okne
echo [6/9] Starting backend...
set "BACKEND_DIR=%ROOT%backend"
set "VENV_ACTIVATE=%ROOT%venv\Scripts\activate.bat"

REM Předání FORCE_DEVICE do backend procesu (pokud je nastaveno)
if defined FORCE_DEVICE (
  echo Device mode: %FORCE_DEVICE%
  start "XTTS Backend" cmd /k "cd /d %BACKEND_DIR% && call %VENV_ACTIVATE% && set PYTHONPATH=%ROOT% && if not defined OUTPUT_HEADROOM_DB set OUTPUT_HEADROOM_DB=-9.0 && set FORCE_DEVICE=%FORCE_DEVICE% && python main.py"
) else (
  start "XTTS Backend" cmd /k "cd /d %BACKEND_DIR% && call %VENV_ACTIVATE% && set PYTHONPATH=%ROOT% && if not defined OUTPUT_HEADROOM_DB set OUTPUT_HEADROOM_DB=-9.0 && python main.py"
)

REM 7) Pockej az backend nabehne (max 60s)
echo [7/9] Waiting for backend on http://localhost:8000 ...
timeout /t 3 /nobreak >nul 2>&1
powershell -NoProfile -Command "for($i=0;$i -lt 60;$i++){try{Invoke-WebRequest -UseBasicParsing http://localhost:8000/api/models/status | Out-Null; exit 0}catch{Start-Sleep -Seconds 1}}; exit 1" >nul 2>&1

if errorlevel 1 (
  echo WARNING: Backend se nepodarilo overit do 60s. Frontend spoustim i tak...
) else (
  echo Backend is running.
)
echo.

REM 8) Spust frontend v novem okne
echo [8/9] Starting frontend...
start "XTTS Frontend" cmd /k "cd /d %FRONTEND_DIR% && npm run dev"

REM 9) Otevri prohlizec
echo [9/9] Opening browser...
timeout /t 2 /nobreak >nul 2>&1
start "" "http://localhost:3000"

echo.
echo Done. (Backend: :8000, Frontend: :3000)
echo.
echo Press any key to close this window...
pause >nul
exit /b 0


