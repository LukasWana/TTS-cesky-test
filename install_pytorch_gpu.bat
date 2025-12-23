@echo off
REM Instalace PyTorch s CUDA podporou pro RTX 3060
REM Tento skript nainstaluje PyTorch 2.1.0 s CUDA 11.8 (kompatibilní s RTX 3060)

setlocal

echo ========================================
echo Instalace PyTorch s CUDA podporou
echo ========================================
echo.

REM Zajisti, ze se okno nezavre
if not "%1"=="INTERNAL" (
    cmd /k "%~f0" INTERNAL
    exit /b
)

REM Najdi Python v venv
set "ROOT=%~dp0"
set "PYTHON_CMD="

if exist "%ROOT%venv\Scripts\python.exe" (
    set "PYTHON_CMD=%ROOT%venv\Scripts\python.exe"
    echo Pouzivam Python z venv: %PYTHON_CMD%
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
    echo Pouzivam system Python: %PYTHON_CMD%
)

if "%PYTHON_CMD%"=="" (
    echo ERROR: Python nenalezen
    pause
    exit /b 1
)

echo.
echo Kontroluji aktualni PyTorch verzi...
"%PYTHON_CMD%" -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}')"

echo.
echo ========================================
echo Vyberte CUDA verzi:
echo ========================================
echo 1. CUDA 11.8 (doporučeno pro RTX 3060)
echo 2. CUDA 12.1 (novější, pokud máte CUDA 12+)
echo 3. Zrušit
echo.
set /p CUDA_CHOICE="Zadejte volbu (1-3): "

if "%CUDA_CHOICE%"=="1" (
    set "CUDA_URL=cu118"
    set "CUDA_VER=11.8"
) else if "%CUDA_CHOICE%"=="2" (
    set "CUDA_URL=cu121"
    set "CUDA_VER=12.1"
) else (
    echo Instalace zrusena.
    pause
    exit /b 0
)

echo.
echo ========================================
echo Instaluji PyTorch 2.1.0 s CUDA %CUDA_VER%...
echo ========================================
echo.

REM Aktivace venv pokud existuje
if exist "%ROOT%venv\Scripts\activate.bat" (
    call "%ROOT%venv\Scripts\activate.bat"
)

REM Odinstalace starého PyTorch
echo Odinstaluji stary PyTorch...
"%PYTHON_CMD%" -m pip uninstall torch torchaudio -y

REM Instalace PyTorch s CUDA
echo Instaluji PyTorch s CUDA podporou...
"%PYTHON_CMD%" -m pip install torch==2.1.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/%CUDA_URL%

if errorlevel 1 (
    echo.
    echo ERROR: Instalace selhala!
    echo Zkontrolujte, zda mate nainstalovany CUDA toolkit.
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Overuji instalaci...
echo ========================================
"%PYTHON_CMD%" -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA version: {torch.version.cuda if torch.version.cuda else \"N/A\"}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"

if errorlevel 1 (
    echo.
    echo WARNING: CUDA neni dostupna po instalaci.
    echo Zkontrolujte:
    echo 1. Je nainstalovany NVIDIA GPU driver?
    echo 2. Je nainstalovany CUDA toolkit?
    echo 3. Je GPU viditelna v Device Manager?
    echo.
) else (
    echo.
    echo ========================================
    echo SUCCESS: PyTorch s CUDA je nainstalovan!
    echo ========================================
    echo.
    echo Pro pouziti GPU restartujte backend server.
    echo.
)

pause












