@echo off
REM Batch wrapper pro test_voice_quality.py
REM Použití: scripts\test_voice_quality.bat voice_sample.wav

setlocal

REM Zajisti, ze se okno nezavre
if not "%1"=="INTERNAL" (
    cmd /k "%~f0" INTERNAL %*
    exit /b
)

REM Najdi Python v venv
set "ROOT=%~dp0.."
set "PYTHON_CMD="

if exist "%ROOT%venv\Scripts\python.exe" (
    set "PYTHON_CMD=%ROOT%venv\Scripts\python.exe"
) else (
    REM Zkus system Python
    py -3.10 --version >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_CMD=py -3.10"
    ) else (
        py -3.11 --version >nul 2>&1
        if not errorlevel 1 (
            set "PYTHON_CMD=py -3.11"
        ) else (
            set "PYTHON_CMD=python"
        )
    )
)

if "%PYTHON_CMD%"=="" (
    echo ERROR: Python nenalezen
    pause
    exit /b 1
)

REM Spust script s argumenty
"%PYTHON_CMD%" "%~dp0test_voice_quality.py" %*

pause













