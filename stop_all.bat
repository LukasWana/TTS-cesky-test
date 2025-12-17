@echo off
setlocal EnableExtensions

echo XTTS-v2 Demo - STOP ALL
echo ======================

REM Kill process listening on :8000 (backend)
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
  echo Killing PID %%p on port 8000
  taskkill /PID %%p /F >nul 2>&1
)

REM Kill process listening on :3000 (frontend)
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":3000" ^| findstr "LISTENING"') do (
  echo Killing PID %%p on port 3000
  taskkill /PID %%p /F >nul 2>&1
)

echo Done.
exit /b 0


