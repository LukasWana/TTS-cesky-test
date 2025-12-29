@echo off
chcp 65001 >nul
echo ========================================
echo ParCzech4Speech - Stažení všech audio souborů
echo ========================================
echo.

cd /d "%~dp0"

python scripts\download_all_parczech_audio.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Chyba při spuštění scriptu!
    pause
    exit /b 1
)

pause



