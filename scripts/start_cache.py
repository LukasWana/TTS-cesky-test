#!/usr/bin/env python3
"""
Cache mechanismus pro optimalizaci startu aplikace (Windows only)
Ukládá výsledky kontrol do .start_cache.json pro rychlejší následné spuštění
"""
import json
import hashlib
import os
import sys
from pathlib import Path
from datetime import datetime
import subprocess

CACHE_FILE = ".start_cache.json"


def get_file_hash(filepath: Path) -> str:
    """Vypočítá SHA256 hash souboru"""
    if not filepath.exists():
        return ""
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def load_cache(root_dir: Path) -> dict:
    """Načte cache ze souboru"""
    cache_path = root_dir / CACHE_FILE
    if cache_path.exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_cache(root_dir: Path, cache: dict):
    """Uloží cache do souboru"""
    cache_path = root_dir / CACHE_FILE
    cache["timestamp"] = datetime.now().isoformat()
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"WARNING: Failed to save cache: {e}", file=sys.stderr)


def check_python_version() -> tuple[str, str]:
    """Zkontroluje Python verzi a vrátí (cmd, version)"""
    for version in ["3.11", "3.10", "3.9"]:
        try:
            result = subprocess.run(
                ["py", f"-{version}", "--version"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                version_str = result.stdout.strip()
                return f"py -{version}", version_str
        except Exception:
            continue
    return None, None


def check_node_version() -> str:
    """Zkontroluje Node.js verzi"""
    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def check_dependencies_installed(venv_python: Path) -> bool:
    """Zkontroluje zda jsou nainstalované základní závislosti"""
    required_imports = [
        "fastapi",
        "TTS",
        "librosa",
        "soundfile",
        "transformers",
        "scipy",
        "yt_dlp"
    ]

    for module in required_imports:
        try:
            result = subprocess.run(
                [str(venv_python), "-c", f"import {module}"],
                capture_output=True,
                timeout=5
            )
            if result.returncode != 0:
                return False
        except Exception:
            return False
    return True


def check_optional_packages(venv_python: Path) -> dict:
    """Zkontroluje volitelné balíčky"""
    optional = {
        "demucs": False,
        "bark": False,
        "f5_tts": False
    }

    # Demucs
    try:
        result = subprocess.run(
            [str(venv_python), "-c", "import demucs"],
            capture_output=True,
            timeout=5
        )
        optional["demucs"] = (result.returncode == 0)
    except Exception:
        pass

    # Bark
    try:
        result = subprocess.run(
            [str(venv_python), "-c", "from bark import generate_audio, preload_models, SAMPLE_RATE"],
            capture_output=True,
            timeout=5
        )
        optional["bark"] = (result.returncode == 0)
    except Exception:
        pass

    # F5-TTS (kontrola existence CLI)
    f5_cli = venv_python.parent / "f5-tts_infer-cli.exe"
    optional["f5_tts"] = f5_cli.exists()

    return optional


def check_f5_slovak_model(root_dir: Path, venv_python: Path) -> bool:
    """Zkontroluje zda je stažený F5-TTS Slovak model"""
    try:
        # Import backend.config vyžaduje aktivní venv
        result = subprocess.run(
            [str(venv_python), "-c",
             "import sys; sys.path.insert(0, '.'); "
             "from backend.config import F5_SLOVAK_MODEL_DIR; "
             "from pathlib import Path; "
             "model_files = ['model_30000.safetensors', 'model_30000.txt']; "
             "exists = any((F5_SLOVAK_MODEL_DIR / f).exists() for f in model_files); "
             "sys.exit(0 if exists else 1)"],
            cwd=str(root_dir),
            capture_output=True,
            timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False


def is_cache_valid(cache: dict, root_dir: Path) -> bool:
    """Zkontroluje zda je cache platná"""
    if not cache:
        return False

    # Zkontrolovat hash requirements.txt
    req_hash = get_file_hash(root_dir / "requirements.txt")
    if cache.get("dependencies_hash") != req_hash:
        return False

    # Zkontrolovat hash package.json
    pkg_hash = get_file_hash(root_dir / "frontend" / "package.json")
    if cache.get("frontend_deps_hash") != pkg_hash:
        return False

    # Zkontrolovat zda venv stále existuje
    venv_exists = (root_dir / "venv" / "Scripts" / "python.exe").exists()
    if cache.get("venv_exists") != venv_exists:
        return False

    return True


def main():
    """Hlavní funkce pro cache operace"""
    if len(sys.argv) < 2:
        print("Usage: start_cache.py <command> [args...]")
        print("Commands: check, update, invalidate, get <key>")
        sys.exit(1)

    command = sys.argv[1]
    root_dir = Path.cwd()

    if command == "check":
        # Zkontrolovat cache a vrátit výsledek
        cache = load_cache(root_dir)
        if is_cache_valid(cache, root_dir):
            print("CACHE_VALID")
            sys.exit(0)
        else:
            print("CACHE_INVALID")
            sys.exit(1)

    elif command == "get":
        # Získat hodnotu z cache
        if len(sys.argv) < 3:
            print("Usage: start_cache.py get <key>")
            sys.exit(1)
        key = sys.argv[2]
        cache = load_cache(root_dir)
        value = cache.get(key, "")
        if value:
            print(value)
        sys.exit(0)

    elif command == "update":
        # Aktualizovat cache s aktuálními hodnotami
        cache = {}

        # Python
        python_cmd, python_version = check_python_version()
        if python_cmd:
            cache["python_cmd"] = python_cmd
            cache["python_version"] = python_version

        # Node.js
        node_version = check_node_version()
        if node_version:
            cache["node_version"] = node_version

        # Venv
        venv_path = root_dir / "venv" / "Scripts" / "python.exe"
        cache["venv_exists"] = venv_path.exists()

        # Dependencies hash
        cache["dependencies_hash"] = get_file_hash(root_dir / "requirements.txt")
        cache["frontend_deps_hash"] = get_file_hash(root_dir / "frontend" / "package.json")

        # Backend dependencies
        if venv_path.exists():
            cache["dependencies_installed"] = check_dependencies_installed(venv_path)
            optional = check_optional_packages(venv_path)
            cache.update(optional)
            cache["f5_slovak_model"] = check_f5_slovak_model(root_dir, venv_path)
        else:
            cache["dependencies_installed"] = False

        # Frontend dependencies
        frontend_node_modules = root_dir / "frontend" / "node_modules"
        cache["frontend_deps_installed"] = frontend_node_modules.exists()

        save_cache(root_dir, cache)
        print("Cache updated")

    elif command == "invalidate":
        # Smazat cache
        cache_path = root_dir / CACHE_FILE
        if cache_path.exists():
            cache_path.unlink()
            print("Cache invalidated")
        else:
            print("Cache does not exist")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
