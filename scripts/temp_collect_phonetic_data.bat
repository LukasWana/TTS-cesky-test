@echo off
REM Jednorázový skript pro stažení dat z jazykových příruček
REM Tento soubor lze po použití smazat

setlocal

REM Zajisti, ze se okno nezavre
if not "%1"=="INTERNAL" (
    cmd /k "%~f0" INTERNAL %*
    exit /b
)

echo ========================================
echo Jednorazove stazeni fonetickych dat
echo ========================================
echo.

REM Najdi Python v venv
set "ROOT=%~dp0.."
set "PYTHON_EXE="
set "PYTHON_IS_FILE=0"

if exist "%ROOT%venv\Scripts\python.exe" (
    set "PYTHON_EXE=%ROOT%venv\Scripts\python.exe"
    set "PYTHON_IS_FILE=1"
    echo Pouzivam Python z venv...
) else (
    REM Zkus system Python
    py -3.11 --version >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_EXE=py -3.11"
        set "PYTHON_IS_FILE=0"
    ) else (
        py -3.10 --version >nul 2>&1
        if not errorlevel 1 (
            set "PYTHON_EXE=py -3.10"
            set "PYTHON_IS_FILE=0"
        ) else (
            python --version >nul 2>&1
            if not errorlevel 1 (
                set "PYTHON_EXE=python"
                set "PYTHON_IS_FILE=0"
            ) else (
                echo ERROR: Python nenalezen
                pause
                exit /b 1
            )
        )
    )
    echo Pouzivam systemovy Python...
)

REM Zkontroluj a nainstaluj potrebne knihovny
echo.
echo Kontroluji zavislosti...
if %PYTHON_IS_FILE%==1 (
    "%PYTHON_EXE%" -c "import requests" 2>nul
) else (
    %PYTHON_EXE% -c "import requests" 2>nul
)
if errorlevel 1 (
    echo Instaluji requests...
    if %PYTHON_IS_FILE%==1 (
        "%PYTHON_EXE%" -m pip install requests
    ) else (
        %PYTHON_EXE% -m pip install requests
    )
)

if %PYTHON_IS_FILE%==1 (
    "%PYTHON_EXE%" -c "import bs4" 2>nul
) else (
    %PYTHON_EXE% -c "import bs4" 2>nul
)
if errorlevel 1 (
    echo Instaluji beautifulsoup4...
    if %PYTHON_IS_FILE%==1 (
        "%PYTHON_EXE%" -m pip install beautifulsoup4
    ) else (
        %PYTHON_EXE% -m pip install beautifulsoup4
    )
)

echo.
echo Spoustim skript pro stazeni dat...
echo.

REM Spust skript
if %PYTHON_IS_FILE%==1 (
    "%PYTHON_EXE%" "%~dp0temp_collect_phonetic_data.py"
) else (
    %PYTHON_EXE% "%~dp0temp_collect_phonetic_data.py"
)

if errorlevel 1 (
    echo.
    echo ERROR: Skript selhal!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Hotovo! Data byla aktualizovana.
echo.
echo Tento BAT soubor a temp_collect_phonetic_data.py
echo muzete nyni smazat - uz nejsou potrebne.
echo ========================================
pause

