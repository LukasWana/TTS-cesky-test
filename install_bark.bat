@echo off
setlocal EnableExtensions

REM Skript pro instalaci Bark (Suno AI) modelu
REM Tento skript lze spustit samostatně nebo se volá automaticky z start_all.bat

REM Zajisti, ze se okno nezavre
if not "%1"=="INTERNAL" (
  cmd /k "%~f0" INTERNAL
  exit /b
)

echo ========================================
echo Bark (Suno AI) Installation
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
                echo Please install Python 3.9-3.11 or activate virtual environment first.
                pause
                exit /b 1
            )
        )
    )
    echo Pouzivam systemovy Python...
)

echo.
echo Checking if Bark is already installed...
if %PYTHON_IS_FILE%==1 (
    "%PYTHON_EXE%" -c "from bark import generate_audio, preload_models, SAMPLE_RATE" >nul 2>&1
) else (
    %PYTHON_EXE% -c "from bark import generate_audio, preload_models, SAMPLE_RATE" >nul 2>&1
)

if not errorlevel 1 (
    echo Bark is already installed!
    echo.
    echo Verifying installation...
    if %PYTHON_IS_FILE%==1 (
        "%PYTHON_EXE%" -c "from bark import generate_audio, preload_models, SAMPLE_RATE; print('Bark version OK')"
    ) else (
        %PYTHON_EXE% -c "from bark import generate_audio, preload_models, SAMPLE_RATE; print('Bark version OK')"
    )
    if errorlevel 1 (
        echo WARNING: Bark import verification failed. Consider reinstalling.
    ) else (
        echo Bark installation verified successfully.
    )
    pause
    exit /b 0
)

echo.
echo Bark is not installed. Installing from GitHub...
echo This may take a few minutes...
echo.

if %PYTHON_IS_FILE%==1 (
    "%PYTHON_EXE%" -m pip install --upgrade pip
    "%PYTHON_EXE%" -m pip install git+https://github.com/suno-ai/bark.git
) else (
    %PYTHON_EXE% -m pip install --upgrade pip
    %PYTHON_EXE% -m pip install git+https://github.com/suno-ai/bark.git
)

if errorlevel 1 (
    echo.
    echo ERROR: Bark installation failed!
    echo.
    echo Possible reasons:
    echo - Git is not installed (Bark requires git to install from GitHub)
    echo - Network connection issues
    echo - Insufficient disk space
    echo.
    echo Please check the error messages above and try again.
    echo.
    pause
    exit /b 1
)

echo.
echo Verifying Bark installation...
if %PYTHON_IS_FILE%==1 (
    "%PYTHON_EXE%" -c "from bark import generate_audio, preload_models, SAMPLE_RATE; print('Bark installed successfully!')"
) else (
    %PYTHON_EXE% -c "from bark import generate_audio, preload_models, SAMPLE_RATE; print('Bark installed successfully!')"
)

if errorlevel 1 (
    echo.
    echo WARNING: Bark installation verification failed.
    echo Bark may not work correctly. Please check the error messages above.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Bark installation completed successfully!
echo ========================================
echo.
echo You can now use Bark features in the application.
echo.
pause
exit /b 0

