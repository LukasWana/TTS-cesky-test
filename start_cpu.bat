@echo off
REM Spustí aplikaci s vynuceným CPU device
echo ========================================
echo Spouštím aplikaci s CPU device
echo ========================================
echo.
set FORCE_DEVICE=cpu
set PYTHONUTF8=
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set WANDB_MODE=disabled
set WANDB_SILENT=true
call start_all.bat INTERNAL














