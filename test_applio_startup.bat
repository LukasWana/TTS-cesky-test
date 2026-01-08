@echo off
echo ============================================
echo  Applio Integration Test
echo ============================================
echo.

REM Test the Applio section
echo Testing Applio startup section...
if exist "backend\applio\start-applio.bat" (
  echo [OK] Applio script found
  start "Applio Test" cmd /k "echo Applio would start here && pause"
  echo [OK] Start command executed
) else (
  echo [FAIL] Applio script not found
)

echo.
echo Test complete.
pause
