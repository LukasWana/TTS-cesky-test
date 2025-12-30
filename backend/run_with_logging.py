#!/usr/bin/env python3
"""
Wrapper script pro spuštění backendu s barevným výstupem a zápisem do log souboru
"""
import sys
import os
import subprocess
from pathlib import Path
from colorama import init, Fore, Style

# Inicializace colorama
init(autoreset=True, strip=False)

# Cesta k main.py
backend_dir = Path(__file__).parent
main_py = backend_dir / "main.py"

# Cesta k log souboru
root_dir = backend_dir.parent
log_file = root_dir / "logs" / "backend.log"

# Zajistit, že log adresář existuje
log_file.parent.mkdir(exist_ok=True)

# Otevřít log soubor pro append
try:
    log_fd = open(log_file, 'a', encoding='utf-8')
except (PermissionError, OSError) as e:
    print(f"{Fore.YELLOW}WARNING: Nelze otevřít log soubor {log_file}: {e}")
    print(f"{Fore.YELLOW}Logy budou zobrazovány pouze v konzoli.{Style.RESET_ALL}")
    log_fd = None

# Spustit main.py a zachytit výstup
try:
    process = subprocess.Popen(
        [sys.executable, "-X", "utf8", str(main_py)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
        encoding='utf-8',
        errors='replace',
        cwd=str(backend_dir)
    )

    # Import regex pro odstranění ANSI escape sekvencí
    import re
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    # Číst výstup řádek po řádku
    for line in process.stdout:
        # Zobrazit v konzoli s barvami (colorama je inicializováno)
        print(line, end='', flush=True)

        # Zapsat do souboru bez barev (odstranit ANSI escape sekvence)
        if log_fd:
            clean_line = ansi_escape.sub('', line)
            log_fd.write(clean_line)
            log_fd.flush()

    # Čekat na ukončení procesu
    return_code = process.wait()

    if log_fd:
        log_fd.close()

    sys.exit(return_code)

except KeyboardInterrupt:
    if log_fd:
        log_fd.close()
    sys.exit(0)
except Exception as e:
    print(f"{Fore.RED}ERROR: Chyba při spuštění backendu: {e}{Style.RESET_ALL}")
    if log_fd:
        log_fd.close()
    sys.exit(1)

