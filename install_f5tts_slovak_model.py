"""
Skript pro automatické stahování slovenského F5-TTS modelu z Hugging Face
"""
import sys
from pathlib import Path
import shutil

# Windows terminál může běžet v cp1252 (bez české diakritiky) -> zabraň UnicodeEncodeError
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Přidat backend do path pro import config
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

try:
    from backend.config import F5_SLOVAK_MODEL_NAME, F5_SLOVAK_MODEL_DIR
    from huggingface_hub import snapshot_download
except ImportError as e:
    print(f"ERROR: Chybí závislosti: {e}")
    print("Nainstalujte: pip install huggingface-hub")
    sys.exit(1)


def check_model_exists():
    """Zkontroluje, zda model již existuje v lokální cache"""
    # Zkontroluj, zda existují klíčové soubory modelu
    model_files = [
        "model_30000.safetensors",
        "model_30000.txt"
    ]

    for file in model_files:
        if (F5_SLOVAK_MODEL_DIR / file).exists():
            return True
    return False


def check_config_exists():
    """Zkontroluje, zda konfigurační soubor existuje v modelu"""
    config_files = [
        "F5_TTS_Slovak.yaml",
        "config.yaml",
        "*.yaml"
    ]

    for pattern in config_files:
        if pattern.startswith("*"):
            # Glob pattern
            if list(F5_SLOVAK_MODEL_DIR.glob(pattern)):
                return True
        else:
            if (F5_SLOVAK_MODEL_DIR / pattern).exists():
                return True
    return False


def download_model():
    """Stáhne slovenský F5-TTS model z Hugging Face"""
    print("=" * 60)
    print("F5-TTS Slovak Model Download")
    print("=" * 60)
    print()

    # Zkontroluj, zda model již existuje
    if check_model_exists():
        print(f"[OK] Model už je stažen v: {F5_SLOVAK_MODEL_DIR}")
        print("Přeskakuji stahování.")
        return True

    print(f"Stahuji model: {F5_SLOVAK_MODEL_NAME}")
    print(f"Cílový adresář: {F5_SLOVAK_MODEL_DIR}")
    print()
    print("POZNÁMKA: Model může být velký (~1.35 GB), stahování může trvat několik minut.")
    print()

    try:
        # Stáhni model z Hugging Face
        print("Začínám stahování...")
        snapshot_download(
            repo_id=F5_SLOVAK_MODEL_NAME,
            local_dir=str(F5_SLOVAK_MODEL_DIR),
            local_dir_use_symlinks=False,  # Použít kopii místo symlinků
            resume_download=True  # Pokračovat v přerušeném stahování
        )

        # Ověř, že model byl stažen správně
        if check_model_exists():
            print()
            print("=" * 60)
            print("[OK] Model úspěšně stažen!")
            print("=" * 60)
            print(f"Model je uložen v: {F5_SLOVAK_MODEL_DIR}")

            return True
        else:
            print()
            print("[WARN] Model byl stažen, ale některé soubory chybí.")
            print("Zkuste stáhnout znovu nebo zkontrolujte Hugging Face repozitář.")
            return False

    except Exception as e:
        print()
        print("=" * 60)
        print("[ERROR] CHYBA při stahování modelu")
        print("=" * 60)
        print(f"Chyba: {e}")
        print()
        print("Možné příčiny:")
        print("  - Problém s internetovým připojením")
        print("  - Nedostatek místa na disku")
        print("  - Problém s Hugging Face API")
        print()
        print("Zkuste:")
        print("  1. Zkontrolovat internetové připojení")
        print("  2. Zkontrolovat dostupné místo na disku")
        print("  3. Spustit skript znovu (resume_download=True pokračuje v přerušeném stahování)")
        return False


if __name__ == "__main__":
    success = download_model()
    sys.exit(0 if success else 1)

