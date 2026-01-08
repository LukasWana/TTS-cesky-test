@echo off
REM Sync Applio Voices: copies from voices/ to logs/
setlocal enabledelayedexpansion

set "SCRIPT_DIR=C:\work\projects\2025-voice-assistent\backend\applio"
set "SOURCE=%SCRIPT_DIR%\voices"
set "TARGET=%SCRIPT_DIR%\logs"

if not exist "%SOURCE%" exit /b 1
if not exist "%TARGET%" mkdir "%TARGET%"

for /d %%F in ("%SOURCE%\*") do (
    if not exist "%TARGET%\%%~nxF" mkdir "%TARGET%\%%~nxF" 2>nul
    for %%P in ("%%F\*.pth") do (
        if not exist "%TARGET%\%%~nxF\%%~nxP" copy "%%P" "%TARGET%\%%~nxF\" >nul
    )
    for %%I in ("%%F\*.index") do (
        if not exist "%TARGET%\%%~nxF\%%~nxI" copy "%%I" "%TARGET%\%%~nxF\" >nul
    )
)
endlocal
