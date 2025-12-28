@echo off
echo ========================================
echo Automaticka instalace audiocraft
echo ========================================
echo.

REM Zkontroluj, zda je venv aktivni
if not defined VIRTUAL_ENV (
  if exist "venv\Scripts\activate.bat" (
    echo Aktivuji virtual environment...
    call venv\Scripts\activate.bat
  ) else (
    echo ERROR: Virtual environment nenalezen!
    pause
    exit /b 1
  )
)

echo Spoustim automatickou instalaci s alternativnimi metodami...
echo.

python install_audiocraft_helper.py

echo.
pause





