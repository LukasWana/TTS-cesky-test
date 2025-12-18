@echo off
setlocal EnableExtensions

echo XTTS-v2 Demo - STOP ALL (project processes)
echo ==========================================

REM Root projektu = slozka, kde lezi tento .bat
set "ROOT=%~dp0"
if not "%ROOT:~-1%"=="\" set "ROOT=%ROOT%\"

REM 1) Primarne ukoncime procesy, ktere maji v CommandLine cestu k projektu
echo.
echo [1/2] Killing processes started from this project folder:
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root = (Resolve-Path '%ROOT%').Path.TrimEnd('\');" ^
  "$rx = [Regex]::Escape($root);" ^
  "$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and ($_.CommandLine -match $rx) -and ($_.ProcessId -ne $PID) };" ^
  "if(-not $procs){ Write-Host 'No matching processes found.'; exit 0 }" ^
  "Write-Host ('Found {0} process(es):' -f $procs.Count);" ^
  "$procs | Select-Object ProcessId, Name, CommandLine | ForEach-Object { Write-Host ('- PID {0}  {1}`n  {2}' -f $_.ProcessId,$_.Name,$_.CommandLine) };" ^
  "$pids = $procs | Select-Object -ExpandProperty ProcessId -Unique;" ^
  "foreach($id in $pids){ try{ Stop-Process -Id $id -Force -ErrorAction Stop; Write-Host ('Killed PID ' + $id) } catch { Write-Host ('Failed PID ' + $id + ': ' + $_.Exception.Message) } }"

REM Kill process listening on :8000 (backend)
echo.
echo [2/2] Fallback: Killing processes listening on ports 8000/3000 (if any)
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


