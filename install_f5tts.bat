@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM Skript pro instalaci F5-TTS
REM Tento skript lze spustit samostatně nebo se volá automaticky z start_all.bat

REM Zajisti, ze se okno nezavre
if not "%1"=="INTERNAL" (
  cmd /k "%~f0" INTERNAL
  exit /b
)

echo ========================================
echo F5-TTS Installation
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

REM Vynutit UTF-8 a vypnout wandb (aby nespadla diakritika / spatne globalni PYTHONUTF8)
set "PYTHONUTF8="
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "WANDB_MODE=disabled"
set "WANDB_SILENT=true"

echo.
echo Checking if F5-TTS is already installed...
REM Pozn.: f5-tts_infer-cli --help muze trvat dele nez 5s, proto checkujeme primarne exe ve venv
if exist "%ROOT%venv\Scripts\f5-tts_infer-cli.exe" (
    echo F5-TTS is already installed!
    echo.
    echo Verifying installation...
    REM Jen informativni (bez failu): vypiseme, ze exe existuje.
    echo Found: %ROOT%venv\Scripts\f5-tts_infer-cli.exe
    if errorlevel 1 (
        echo WARNING: F5-TTS CLI verification failed. Consider reinstalling.
    ) else (
        echo F5-TTS installation verified successfully.
    )
    pause
    exit /b 0
)

echo.
echo F5-TTS is not installed. Installing from PyPI...
echo This may take a few minutes...
echo.

REM Kontrola FFmpeg (důležité pro F5-TTS)
echo.
echo ========================================
echo KONTROLA FFMPEG
echo ========================================
echo.
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo WARNING: FFmpeg nebyl nalezen v PATH!
    echo.
    echo F5-TTS vyzaduje FFmpeg full-shared verzi pro TorchCodec.
    echo.
    echo Pro instalaci FFmpeg:
    echo 1. Stahnete z: https://www.gyan.dev/ffmpeg/builds/
    echo 2. Vyberte: ffmpeg-release-full-shared.7z
    echo 3. Rozbalte a pridejte 'bin' slozku do PATH
    echo 4. Nebo pouzijte conda: conda install -c conda-forge ffmpeg
    echo.
    echo POZOR: Bez FFmpeg full-shared verze F5-TTS nebude fungovat!
    echo.
    set /p CONTINUE_FFMPEG="Pokracovat s instalaci F5-TTS i bez FFmpeg? (y/n): "
    if /i not "!CONTINUE_FFMPEG!"=="y" (
        echo Instalace zrusena.
        pause
        exit /b 0
    )
) else (
    echo FFmpeg je nainstalovan.
    ffmpeg -version | findstr /i "version"
    echo.
)

REM Poznámka o požadavcích
echo.
echo ========================================
echo POZNAMKA O POZADAVCICH
echo ========================================
echo.
echo F5-TTS vyzaduje PyTorch s CUDA (pro GPU) nebo CPU verzi.
echo Pokud nemate PyTorch, bude nainstalovan automaticky.
echo Pro GPU podporu ujistete se, ze mate spravnou CUDA verzi.
echo.
echo DULEZITE: F5-TTS vyzaduje FFmpeg full-shared verzi pro TorchCodec.
echo Pokud instalace selze kvuli libtorchcodec, nainstalujte FFmpeg.
echo.
echo ========================================
echo.

REM Pokud je vyzadovano GPU, zajisti CUDA build PyTorch (jinak pip muze natáhnout CPU build)
if /i "%FORCE_DEVICE%"=="cuda" (
    echo.
    echo ========================================
    echo GPU MODE DETEKOVAN (FORCE_DEVICE=cuda)
    echo ========================================
    echo.
    if "%CUDA_URL%"=="" set "CUDA_URL=cu121"
    echo Using CUDA wheel index: %CUDA_URL%
    echo Uninstalling torch/torchaudio/torchcodec (if present)...
    pip uninstall -y torch torchaudio torchcodec >nul 2>&1
    echo Installing torch==2.1.0 + torchaudio==2.1.0 (%CUDA_URL%)...
    if %PYTHON_IS_FILE%==1 (
        "%PYTHON_EXE%" -m pip install torch==2.1.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/%CUDA_URL%
    ) else (
        %PYTHON_EXE% -m pip install torch==2.1.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/%CUDA_URL%
    )
    if errorlevel 1 (
        echo ERROR: CUDA PyTorch install failed.
        echo Tip: spustte install_pytorch_gpu.bat a vyberte spravnou CUDA verzi.
        pause
        exit /b 1
    )
    echo Verifying CUDA availability...
    REM Pozn.: v batch blocku se nesmi objevit zavorky na prikazove radce (rozbije to parser),
    REM proto pouzivame existujici check_gpu.py namisto python -c "..."
    if %PYTHON_IS_FILE%==1 (
        "%PYTHON_EXE%" "%ROOT%check_gpu.py"
    ) else (
        %PYTHON_EXE% "%ROOT%check_gpu.py"
    )
    echo.
)

if %PYTHON_IS_FILE%==1 (
    "%PYTHON_EXE%" -m pip install --upgrade pip
    echo Installing f5-tts...
    REM DULEZITE: neinstalovat deps, aby se neprepsal torch/torchaudio (GPU->CPU)
    "%PYTHON_EXE%" -m pip install f5-tts --no-deps
) else (
    %PYTHON_EXE% -m pip install --upgrade pip
    echo Installing f5-tts...
    REM DULEZITE: neinstalovat deps, aby se neprepsal torch/torchaudio (GPU->CPU)
    %PYTHON_EXE% -m pip install f5-tts --no-deps
)

if errorlevel 1 (
    echo.
    echo ERROR: F5-TTS installation failed!
    echo.
    echo Possible reasons:
    echo - Network connection issues
    echo - Insufficient disk space
    echo - PyTorch installation conflicts
    echo - Missing system dependencies
    echo - FFmpeg not properly installed (F5-TTS requires FFmpeg full-shared)
    echo.
    echo Please check the error messages above and try again.
    echo.
    echo DULEZITE: Pokud chyba obsahuje "libtorchcodec" nebo "FFmpeg":
    echo 1. Nainstalujte FFmpeg full-shared verzi:
    echo    - Stahnete z: https://www.gyan.dev/ffmpeg/builds/
    echo    - Vyberte: ffmpeg-release-full-shared.7z
    echo    - Rozbalte a pridejte 'bin' slozku do PATH
    echo 2. Nebo pouzijte conda: conda install -c conda-forge ffmpeg
    echo 3. Po instalaci FFmpeg zkuste znovu: install_f5tts.bat
    echo.
    echo ALTERNATIVNI INSTALACE (lokální vývoj):
    echo   git clone https://github.com/SWivid/F5-TTS.git
    echo   cd F5-TTS
    echo   pip install -e .
    echo.
    pause
    exit /b 1
)

echo.
echo Verifying F5-TTS installation...
if %PYTHON_IS_FILE%==1 (
    "%PYTHON_EXE%" -c "import subprocess; result = subprocess.run(['f5-tts_infer-cli', '--help'], capture_output=True, text=True, timeout=5); print('F5-TTS installed successfully!' if result.returncode == 0 else 'F5-TTS CLI not found')"
) else (
    %PYTHON_EXE% -c "import subprocess; result = subprocess.run(['f5-tts_infer-cli', '--help'], capture_output=True, text=True, timeout=5); print('F5-TTS installed successfully!' if result.returncode == 0 else 'F5-TTS CLI not found')"
)

if errorlevel 1 (
    echo.
    echo WARNING: F5-TTS installation verification failed.
    echo F5-TTS may not work correctly. Please check the error messages above.
    echo.
    echo Zkuste restartovat terminal nebo zkontrolovat PATH.
    pause
    exit /b 1
)

echo.
echo ========================================
echo F5-TTS installation completed successfully!
echo ========================================
echo.
echo You can now use F5-TTS features in the application.
echo Restart the backend server to use F5-TTS.
echo.
pause
exit /b 0

