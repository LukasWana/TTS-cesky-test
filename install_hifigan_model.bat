@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM Skript pro stahování HiFi-GAN modelu z Hugging Face
REM Tento skript lze spustit samostatně nebo se volá automaticky z start_all.bat

REM Zajisti, ze se okno nezavre
if not "%1"=="INTERNAL" (
  cmd /k "%~f0" INTERNAL
  exit /b
)

echo ========================================
echo HiFi-GAN Model Download
echo ========================================
echo.

REM Najdi Python v venv nebo system
set "ROOT=%~dp0"
set "PYTHON_EXE="
set "PYTHON_IS_FILE=0"

if exist "%ROOT%venv\Scripts\python.exe" (
    set "PYTHON_EXE=%ROOT%venv\Scripts\python.exe"
    set "PYTHON_IS_FILE=1"
    echo Pouzivam Python z venv...
    call "%ROOT%venv\Scripts\activate.bat"
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
                echo Please install Python 3.10-3.11 or activate virtual environment first.
                pause
                exit /b 1
            )
        )
    )
    echo Pouzivam systemovy Python...
)

REM Vynutit UTF-8
set "PYTHONUTF8="
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

echo.
echo Kontroluji, zda je model jiz stazen...
echo.

REM Zkontroluj, zda je huggingface-hub nainstalován
if %PYTHON_IS_FILE%==1 (
    "%PYTHON_EXE%" -c "import huggingface_hub" >nul 2>&1
) else (
    %PYTHON_EXE% -c "import huggingface_hub" >nul 2>&1
)

if errorlevel 1 (
    echo huggingface-hub neni nainstalovan. Instaluji...
    if %PYTHON_IS_FILE%==1 (
        "%PYTHON_EXE%" -m pip install huggingface-hub
    ) else (
        %PYTHON_EXE% -m pip install huggingface-hub
    )
    if errorlevel 1 (
        echo ERROR: Instalace huggingface-hub selhala!
        pause
        exit /b 1
    )
)

echo.
echo Spoustim stahovani HiFi-GAN modelu...
echo Model: espnet/kan-bayashi_ljspeech_joint_finetune_conformer_fastspeech2_hifigan
echo Velikost: ~50-100 MB
echo.
echo POZOR: Stahovani muze trvat nekolik minut podle rychlosti internetu.
echo.

if %PYTHON_IS_FILE%==1 (
    "%PYTHON_EXE%" "%ROOT%install_hifigan_model.py"
) else (
    %PYTHON_EXE% "%ROOT%install_hifigan_model.py"
)

if errorlevel 1 (
    echo.
    echo ========================================
    echo ERROR: Stahovani modelu selhalo!
    echo ========================================
    echo.
    echo Mozne priciny:
    echo - Problem s internetovym pripojenim
    echo - Nedostatek mista na disku
    echo - Problem s Hugging Face API
    echo.
    echo Zkuste:
    echo 1. Zkontrolovat internetove pripojeni
    echo 2. Zkontrolovat dostupne misto na disku (potrebujete alespon 200 MB)
    echo 3. Spustit skript znovu (resume_download=True pokracuje v prerusenem stahovani)
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo HiFi-GAN model download completed!
echo ========================================
echo.
echo Model je nyni pripraven k pouziti v models/hifigan/
echo.
pause
exit /b 0
