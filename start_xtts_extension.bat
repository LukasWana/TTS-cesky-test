@echo off
REM ========================================================================
REM XTTS WebSocket Server for Chrome Extension
REM Lightweight backend - only TTS generation, no MusicGen/Bark/ASR
REM ========================================================================

setlocal EnableDelayedExpansion

REM UTF-8 encoding settings
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set WANDB_MODE=disabled
set WANDB_SILENT=true

chcp 65001 >nul 2>&1

echo ========================================================================
echo  XTTS WebSocket Server - Chrome Extension Backend
echo ========================================================================
echo.

REM Set paths
set "SCRIPT_DIR=%~dp0"
set "VENV_PYTHON=%SCRIPT_DIR%venv\Scripts\python.exe"
set "BACKEND_DIR=%SCRIPT_DIR%backend"

REM Check if venv Python exists
if not exist "!VENV_PYTHON!" (
    echo [ERROR] Virtual environment not found at: !VENV_PYTHON!
    echo [ERROR] Please run 'run.bat' first to initialize the project
    pause
    exit /b 1
)

echo [INFO] Using Python from virtual environment
"!VENV_PYTHON!" --version

echo.
echo [INFO] GPU availability:
"!VENV_PYTHON!" -c "import torch; print('  CUDA available:', torch.cuda.is_available())" 2>nul
echo.

echo [CONFIG]
echo  - WebSocket URL:  ws://localhost:8000/ws/tts
echo  - REST API:       http://localhost:8000/api/tts/generate
echo  - Voices API:     http://localhost:8000/api/voices/demo
echo  - Health check:   http://localhost:8000/health
echo  - Demo voices:    assets\czech voices
echo.

echo [INFO] Starting XTTS WebSocket Server...
echo [INFO] Model will be loaded lazily on first request
echo.
echo [NOTE] For Chrome Extension:
echo   1. Make sure this server is running
echo   2. Reload the extension in chrome://extensions
echo   3. Select text ^> Right click ^> "Precti nahlas"
echo.
echo Press CTRL+C to stop
echo ========================================================================
echo.

REM Launch the WebSocket server using venv Python directly
cd /d "!BACKEND_DIR!"
"!VENV_PYTHON!" -X utf8 main_xtts_ws.py

REM If we get here, the server stopped
echo.
echo [INFO] Server stopped
pause

endlocal
