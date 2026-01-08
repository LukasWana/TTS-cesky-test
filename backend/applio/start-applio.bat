@echo off
cd /d %~dp0
title Applio - Voice Conversion

REM Check if we're in System32 (prevent admin rights)
if "%cd:~0,17%"=="C:\Windows\System32" (
    color 0C
    echo ERROR: Applio should NOT be run as administrator.
    echo.
    pause
    exit /b 1
)

echo ============================================
echo  Applio - Voice Conversion Tool
echo ============================================
echo.
echo  Applio bezi na: http://localhost:6969
echo  Pro zastaveni zavrete toto okno nebo stisknete Ctrl+C
echo.
echo ============================================
echo.

REM Check for env directory
if not exist env (
    echo ERROR: Please run 'run-install.bat' first!
    echo.
    pause
    exit /b 1
)

REM Run Applio
env\python.exe app.py --open

echo.
pause
