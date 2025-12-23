@echo off
echo XTTS-v2 Demo Setup
echo ==================

REM Hledání kompatibilní verze Pythonu (3.9-3.11)
set PYTHON_CMD=
set PYTHON_VERSION=

REM Zkus Python 3.11
py -3.11 --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=py -3.11
    for /f "tokens=2" %%i in ('py -3.11 --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo Found Python 3.11: %PYTHON_VERSION%
    goto :found_python
)

REM Zkus Python 3.10
py -3.10 --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=py -3.10
    for /f "tokens=2" %%i in ('py -3.10 --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo Found Python 3.10: %PYTHON_VERSION%
    goto :found_python
)

REM Zkus Python 3.9
py -3.9 --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=py -3.9
    for /f "tokens=2" %%i in ('py -3.9 --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo Found Python 3.9: %PYTHON_VERSION%
    goto :found_python
)

REM Pokud není kompatibilní verze, zobraz chybu
echo.
echo ERROR: No compatible Python version found!
echo.
echo TTS requires Python 3.9, 3.10, or 3.11
echo.
echo Available Python versions:
py --list
echo.
echo Please install Python 3.10 or 3.11 from: https://www.python.org/downloads/
echo Make sure to check "Add Python to PATH" during installation.
echo.
pause
exit /b 1

:found_python
echo Using: %PYTHON_CMD%
echo.

node --version >nul 2>&1
if errorlevel 1 (
    echo Node.js not found! Please install Node.js 18+
    pause
    exit /b 1
)

echo Creating virtual environment with %PYTHON_VERSION%...
if not exist "venv\Scripts\python.exe" (
  %PYTHON_CMD% -m venv venv
  if errorlevel 1 (
      echo Failed to create virtual environment!
      pause
      exit /b 1
  )
) else (
  echo venv already exists (skip create).
)
call venv\Scripts\activate.bat

REM Backend deps jen kdyz chybi (rychly check importu)
python -c "import fastapi,uvicorn; import TTS; import librosa; import soundfile; import scipy" >nul 2>&1
if errorlevel 1 (
  echo Installing Python dependencies...
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  if errorlevel 1 (
    echo pip install failed.
    pause
    exit /b 1
  )
) else (
  echo Backend dependencies OK (skip pip install).
)

REM Bark instalace (volitelne, ale doporucene)
echo.
echo Checking Bark (Suno AI) installation...
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

REM Frontend deps jen kdyz chybi
if not exist "frontend\node_modules" (
  echo Installing frontend dependencies...
  cd frontend
  call npm install
  if errorlevel 1 (
    cd ..
    echo npm install failed.
    pause
    exit /b 1
  )
  cd ..
) else (
  echo Frontend dependencies OK (skip npm install).
)

mkdir models uploads outputs 2>nul
mkdir frontend\assets\demo-voices 2>nul

echo.
echo Setup complete!
echo.
echo To start the application:
echo.
echo Doporučeno: spustit vse jednim prikazem:
echo    start_all.bat
echo.
echo Then open: http://localhost:3000
pause
