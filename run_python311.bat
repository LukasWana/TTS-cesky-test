@echo off
echo XTTS-v2 Demo Setup (Python 3.10/3.11)
echo ======================================

REM Hledání Python 3.11 nebo 3.10
set PYTHON_CMD=
set PYTHON_VERSION=

REM Zkus Python 3.11
py -3.11 --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=py -3.11
    for /f "tokens=2" %%i in ('py -3.11 --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo Using Python 3.11: %PYTHON_VERSION%
    goto :found_python
)

REM Zkus Python 3.10
py -3.10 --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=py -3.10
    for /f "tokens=2" %%i in ('py -3.10 --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo Using Python 3.10: %PYTHON_VERSION%
    goto :found_python
)

echo Python 3.10 or 3.11 not found!
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

node --version >nul 2>&1
if errorlevel 1 (
    echo Node.js not found! Please install Node.js 18+
    pause
    exit /b 1
)

echo Creating virtual environment with %PYTHON_VERSION%...
%PYTHON_CMD% -m venv venv
if errorlevel 1 (
    echo Failed to create virtual environment!
    pause
    exit /b 1
)
call venv\Scripts\activate.bat

echo Installing Python dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo Installing frontend dependencies...
cd frontend
call npm install
cd ..

mkdir models uploads outputs 2>nul
mkdir frontend\assets\demo-voices 2>nul

echo.
echo Setup complete!
echo.
echo To start the application:
echo.
echo 1. Start backend:
echo    venv\Scripts\activate.bat
echo    cd backend
echo    python main.py
echo.
echo 2. Start frontend (in new terminal):
echo    cd frontend
echo    npm run dev
echo.
echo Then open: http://localhost:3000
pause

