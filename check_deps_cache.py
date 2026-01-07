#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pomocný skript pro kontrolu cache závislostí.
Vypočítá hash requirements.txt a porovná ho s uloženým hashem.
"""
import sys
import hashlib
import os
from pathlib import Path

def get_file_hash(filepath):
    """Vypočítá SHA-256 hash souboru."""
    try:
        with open(filepath, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception as e:
        return None

def main():
    if len(sys.argv) < 3:
        print("Usage: check_deps_cache.py <requirements_file> <cache_file>")
        sys.exit(1)

    requirements_file = Path(sys.argv[1])
    cache_file = Path(sys.argv[2])

    # Pokud requirements.txt neexistuje, vrať chybu
    if not requirements_file.exists():
        sys.exit(1)

    # Vypočítej aktuální hash
    current_hash = get_file_hash(requirements_file)
    if current_hash is None:
        sys.exit(1)

    # Pokud cache neexistuje, vytvoř ho a vrať "changed"
    if not cache_file.exists():
        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(current_hash, encoding='utf-8')
        except Exception:
            pass
        print("CHANGED")
        sys.exit(0)

    # Načti uložený hash
    try:
        cached_hash = cache_file.read_text(encoding='utf-8').strip()
    except Exception:
        cached_hash = None

    # Porovnej hashe
    if cached_hash == current_hash:
        print("OK")
        sys.exit(0)
    else:
        # Aktualizuj cache
        try:
            cache_file.write_text(current_hash, encoding='utf-8')
        except Exception:
            pass
        print("CHANGED")
        sys.exit(0)

if __name__ == "__main__":
    main()
