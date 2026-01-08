@echo off
echo ============================================
echo  Applio Integration Test
echo ============================================
echo.

REM Test 1: Check files exist
echo [1/5] Checking files...

set "ERRORS=0"

if not exist "backend\applio\gradio_client.py" (
  echo   [FAIL] backend\applio\gradio_client.py not found
  set /a ERRORS+=1
) else echo   [OK] gradio_client.py

if not exist "backend\applio\start-applio.bat" (
  echo   [FAIL] backend\applio\start-applio.bat not found
  set /a ERRORS+=1
) else echo   [OK] start-applio.bat

if not exist "backend\api\routers\applio.py" (
  echo   [FAIL] backend\api\routers\applio.py not found
  set /a ERRORS+=1
) else echo   [OK] applio.py router

if not exist "frontend\src\services\applio.js" (
  echo   [FAIL] frontend\src\services\applio.js not found
  set /a ERRORS+=1
) else echo   [OK] applio.js service

if not exist "frontend\src\components\ApplioPanel.jsx" (
  echo   [FAIL] frontend\src\components\ApplioPanel.jsx not found
  set /a ERRORS+=1
) else echo   [OK] ApplioPanel.jsx

if not exist "frontend\src\components\ApplioPanel.css" (
  echo   [FAIL] frontend\src\components\ApplioPanel.css not found
  set /a ERRORS+=1
) else echo   [OK] ApplioPanel.css

echo.

REM Test 2: Check start_all.bat modification
echo [2/5] Checking start_all.bat modification...
findstr /c:"start-applio.bat" "start_all.bat" >nul
if errorlevel 1 (
  echo   [FAIL] start_all.bat not modified for Applio
  set /a ERRORS+=1
) else echo   [OK] start_all.bat includes Applio startup

echo.

REM Test 3: Check requirements.txt
echo [3/5] Checking requirements.txt...
findstr /c:"gradio" "requirements.txt" >nul
if errorlevel 1 (
  echo   [FAIL] gradio not in requirements.txt
  set /a ERRORS+=1
) else echo   [OK] gradio in requirements.txt

echo.

REM Test 4: Check App.jsx modification
echo [4/5] Checking App.jsx modification...
findstr /c:"ApplioPanel" "frontend\src\App.jsx" >nul
if errorlevel 1 (
  echo   [FAIL] ApplioPanel not imported in App.jsx
  set /a ERRORS+=1
) else echo   [OK] ApplioPanel imported in App.jsx

echo.

REM Test 5: Check CSS modification
echo [5/5] Checking App.css modification...
findstr /c:".slovak-subtabs" "frontend\src\App.css" >nul
if errorlevel 1 (
  echo   [FAIL] Sub-tabs CSS not in App.css
  set /a ERRORS+=1
) else echo   [OK] Sub-tabs CSS in App.css

echo.

REM Summary
echo ============================================
if %ERRORS% equ 0 (
  echo  ALL TESTS PASSED!
  echo ============================================
  echo.
  echo  Next steps:
  echo  1. Install gradio: pip install gradio
  echo  2. Run: start_all.bat
  echo  3. Applio should start in separate window
  echo  4. Go to "slovenské slovo" tab
  echo  5. Switch to "Applio" sub-tab
  echo.
) else (
  echo  TESTS FAILED: %ERRORS% errors found
  echo ============================================
  echo.
  echo  Please check the errors above.
)

pause
