@echo off
REM Spustí aplikaci s vynuceným GPU device
echo ========================================
echo Spouštím aplikaci s GPU device
echo ========================================
echo.
set FORCE_DEVICE=cuda
set PYTHONUTF8=
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set WANDB_MODE=disabled
set WANDB_SILENT=true
REM Default CUDA wheel index for PyTorch (cu121 / cu118)
if "%CUDA_URL%"=="" set CUDA_URL=cu121
call start_all.bat INTERNAL














