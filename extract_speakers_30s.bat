@echo off
chcp 65001 >nul 2>&1
echo ========================================
echo ParCzech4Speech - Extrakce 30s audio od mluvcich
echo ========================================
echo.

cd /d "%~dp0"

echo Kontroluji a instaluji potrebne zavislosti...
echo.

REM Kontrola a instalace pydub
python -c "import pydub" >nul 2>&1
if errorlevel 1 (
    echo [1/5] Instaluji pydub...
    pip install pydub==0.25.1 >nul 2>&1
    python -c "import pydub" >nul 2>&1
    if errorlevel 1 (
        echo [CHYBA] Chyba pri instalaci pydub!
        pause
        exit /b 1
    )
    echo     [OK] pydub nainstalovan
) else (
    echo [1/5] [OK] pydub je nainstalovan
)

REM Kontrola a instalace requests
python -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo [2/5] Instaluji requests...
    pip install requests>=2.31.0 >nul 2>&1
    python -c "import requests" >nul 2>&1
    if errorlevel 1 (
        echo [CHYBA] Chyba pri instalaci requests!
        pause
        exit /b 1
    )
    echo     [OK] requests nainstalovan
) else (
    echo [2/5] [OK] requests je nainstalovan
)

REM Kontrola a instalace tqdm
python -c "import tqdm" >nul 2>&1
if errorlevel 1 (
    echo [3/5] Instaluji tqdm...
    pip install tqdm>=4.66.0 >nul 2>&1
    python -c "import tqdm" >nul 2>&1
    if errorlevel 1 (
        echo [CHYBA] Chyba pri instalaci tqdm!
        pause
        exit /b 1
    )
    echo     [OK] tqdm nainstalovan
) else (
    echo [3/5] [OK] tqdm je nainstalovan
)

REM Kontrola a instalace numpy
python -c "import numpy" >nul 2>&1
if errorlevel 1 (
    echo [4/5] Instaluji numpy...
    pip install numpy >nul 2>&1
    python -c "import numpy" >nul 2>&1
    if errorlevel 1 (
        echo [CHYBA] Chyba pri instalaci numpy!
        pause
        exit /b 1
    )
    echo     [OK] numpy nainstalovan
) else (
    echo [4/5] [OK] numpy je nainstalovan
)

REM Kontrola a instalace librosa
python -c "import librosa" >nul 2>&1
if errorlevel 1 (
    echo [5/5] Instaluji librosa...
    pip install librosa==0.10.0 >nul 2>&1
    python -c "import librosa" >nul 2>&1
    if errorlevel 1 (
        echo [CHYBA] Chyba pri instalaci librosa!
        pause
        exit /b 1
    )
    echo     [OK] librosa nainstalovan
) else (
    echo [5/5] [OK] librosa je nainstalovan
)

echo.
echo [OK] Vsechny zavislosti jsou nainstalovany!
echo.
echo Spoustim extrakci...
echo.

python scripts\extract_speakers_30s.py

if errorlevel 1 (
    echo.
    echo [CHYBA] Chyba pri spusteni scriptu!
    pause
    exit /b 1
)

pause


