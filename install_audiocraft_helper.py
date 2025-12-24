#!/usr/bin/env python3
"""
Helper script pro instalaci audiocraft s alternativními metodami
"""
import subprocess
import sys
import os

def run_cmd(cmd, description):
    """Spustí příkaz a vrátí True pokud uspěl"""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    print(f"Spouštím: {cmd}")
    print()

    result = subprocess.run(cmd, shell=True, capture_output=False)
    return result.returncode == 0

def check_audiocraft():
    """Zkontroluje, jestli audiocraft funguje"""
    try:
        from audiocraft.models import AudioGen
        print("\n✅ AudioGen lze importovat - instalace je funkční!")
        return True
    except ImportError as e:
        print(f"\n❌ AudioGen nelze importovat: {e}")
        return False

def main():
    print("="*60)
    print("Instalace audiocraft - alternativní metody")
    print("="*60)

    # Metoda 1: Zkusit pre-built wheels
    print("\n📦 Metoda 1: Pre-built wheels (--no-build-isolation)")
    if run_cmd("pip install audiocraft --no-build-isolation", "Instalace s pre-built wheels"):
        if check_audiocraft():
            print("\n✅ ÚSPĚCH! audiocraft je nainstalováno a funkční.")
            return 0

    # Metoda 2: Zkusit bez cache
    print("\n📦 Metoda 2: Bez cache (--no-cache-dir)")
    if run_cmd("pip install audiocraft --no-cache-dir", "Instalace bez cache"):
        if check_audiocraft():
            print("\n✅ ÚSPĚCH! audiocraft je nainstalováno a funkční.")
            return 0

    # Metoda 3: Zkusit upgrade pip a pak instalaci
    print("\n📦 Metoda 3: Upgrade pip a pak instalace")
    run_cmd("python -m pip install --upgrade pip", "Upgrade pip")
    if run_cmd("pip install audiocraft", "Standardní instalace po upgrade pip"):
        if check_audiocraft():
            print("\n✅ ÚSPĚCH! audiocraft je nainstalováno a funkční.")
            return 0

    print("\n" + "="*60)
    print("❌ Všechny metody selhaly")
    print("="*60)
    print("\nDoporučení:")
    print("1. Nainstalujte conda/miniconda a použijte install_audiocraft_conda.bat")
    print("2. Nebo použijte WSL (Windows Subsystem for Linux)")
    print("3. Nebo použijte MusicGen pro SFX generování (funguje bez audiocraft)")
    print("\nSFX generování je volitelné - aplikace funguje i bez toho.")

    return 1

if __name__ == "__main__":
    sys.exit(main())

