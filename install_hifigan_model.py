"""
Skript pro automatické stahování HiFi-GAN modelu z Hugging Face
"""
import sys
import warnings
from pathlib import Path
import shutil

# Potlačení FutureWarning z huggingface_hub o resume_download
warnings.filterwarnings("ignore", message=".*resume_download.*", category=FutureWarning)

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
    from backend.config import MODELS_DIR
    from huggingface_hub import snapshot_download
except ImportError as e:
    print(f"ERROR: Chybí závislosti: {e}")
    print("Nainstalujte: pip install huggingface-hub")
    sys.exit(1)

# Modely k vyzkoušení (v pořadí priority)
MODELS_TO_TRY = [
    "espnet/kan-bayashi_ljspeech_joint_finetune_conformer_fastspeech2_hifigan",
    "espnet/kan-bayashi_ljspeech_hifigan",
    "kan-bayashi/ljspeech_hifigan.v1"
]

# Cílový adresář pro lokální model
TARGET_DIR = Path(MODELS_DIR) / "hifigan"


def check_model_exists():
    """Zkontroluje, zda model již existuje v lokálním adresáři"""
    config_path = TARGET_DIR / "config.yaml"
    checkpoint_pkl = TARGET_DIR / "checkpoint.pkl"
    checkpoint_pth = TARGET_DIR / "checkpoint.pth"

    return (config_path.exists() and (checkpoint_pkl.exists() or checkpoint_pth.exists()))


def find_checkpoint_in_snapshot(snapshot_dir: Path):
    """
    Najde config.yaml a checkpoint v HuggingFace snapshot adresáři

    Returns:
        tuple (config_path, checkpoint_path) nebo (None, None) pokud nenalezeno
    """
    # Hledej v exp/*hifigan* adresářích
    exp_dirs = list(snapshot_dir.glob("exp/*hifigan*"))
    if not exp_dirs:
        # Zkus najít config.yaml a checkpoint přímo v rootu nebo kdekoliv
        config_files = list(snapshot_dir.rglob("config.yaml"))
        checkpoint_files = list(snapshot_dir.rglob("*.pth")) + list(snapshot_dir.rglob("*.pkl"))

        if config_files and checkpoint_files:
            return config_files[0], checkpoint_files[0]
        return None, None

    exp_dir = exp_dirs[0]
    config_path = exp_dir / "config.yaml"

    # Zkus různé názvy checkpointů
    checkpoint_names = [
        "train.total_count.ave_5best.pth",
        "checkpoint.pth",
        "checkpoint.pkl",
        "*.pth",
        "*.pkl"
    ]

    checkpoint_path = None
    for name in checkpoint_names:
        if name.startswith("*"):
            # Glob pattern
            matches = list(exp_dir.glob(name))
            if matches:
                checkpoint_path = matches[0]
                break
        else:
            candidate = exp_dir / name
            if candidate.exists():
                checkpoint_path = candidate
                break

    if config_path.exists() and checkpoint_path:
        return config_path, checkpoint_path

    return None, None


def download_model():
    """Stáhne HiFi-GAN model z Hugging Face a zkopíruje do lokálního adresáře"""
    print("=" * 60)
    print("HiFi-GAN Model Download")
    print("=" * 60)
    print()

    # Vytvoř cílový adresář
    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    # Zkontroluj, zda model již existuje
    if check_model_exists():
        print(f"[OK] Model už je stažen v: {TARGET_DIR}")
        print("Přeskakuji stahování.")
        return True

    print("Stahuji HiFi-GAN model z Hugging Face...")
    print(f"Cílový adresář: {TARGET_DIR}")
    print()
    print("POZNÁMKA: Model může být velký (~50-100 MB), stahování může trvat několik minut.")
    print()

    # Zkus stáhnout jeden z modelů
    downloaded_path = None
    model_used = None

    for model_id in MODELS_TO_TRY:
        try:
            print(f"Zkouším stáhnout: {model_id}...")
            downloaded_path = snapshot_download(
                repo_id=model_id,
                local_files_only=False,
                resume_download=True
            )
            model_used = model_id
            print(f"✅ Model stažen: {downloaded_path}")
            break
        except Exception as e:
            print(f"❌ Selhalo: {e}")
            continue

    if not downloaded_path:
        print()
        print("=" * 60)
        print("[ERROR] Nepodařilo se stáhnout žádný z modelů!")
        print("=" * 60)
        print()
        print("Zkuste:")
        print("  1. Zkontrolovat internetové připojení")
        print("  2. Zkontrolovat dostupné místo na disku")
        print("  3. Spustit skript znovu")
        return False

    # Najdi config a checkpoint v staženém modelu
    snapshot_path = Path(downloaded_path)
    config_path, checkpoint_path = find_checkpoint_in_snapshot(snapshot_path)

    if not config_path or not checkpoint_path:
        print()
        print("[WARN] Nepodařilo se najít config.yaml nebo checkpoint v staženém modelu.")
        print(f"Hledám v: {snapshot_path}")
        print()
        print("Zkusím najít soubory ručně...")

        # Zkus najít soubory kdekoliv v adresáři
        all_configs = list(snapshot_path.rglob("config.yaml"))
        all_checkpoints = list(snapshot_path.rglob("*.pth")) + list(snapshot_path.rglob("*.pkl"))

        if all_configs:
            config_path = all_configs[0]
            print(f"Nalezen config: {config_path}")
        if all_checkpoints:
            checkpoint_path = all_checkpoints[0]
            print(f"Nalezen checkpoint: {checkpoint_path}")

    if not config_path or not checkpoint_path:
        print()
        print("=" * 60)
        print("[ERROR] Nepodařilo se najít potřebné soubory v modelu!")
        print("=" * 60)
        print(f"Stažený model: {downloaded_path}")
        print("Zkuste stáhnout model ručně nebo zkontrolujte Hugging Face repozitář.")
        return False

    # Zkopíruj soubory do cílového adresáře
    try:
        print()
        print("Kopíruji soubory do lokálního adresáře...")
        target_config = TARGET_DIR / "config.yaml"
        target_checkpoint = TARGET_DIR / checkpoint_path.name

        shutil.copy2(config_path, target_config)
        print(f"✅ Zkopírován: {target_config}")

        shutil.copy2(checkpoint_path, target_checkpoint)
        print(f"✅ Zkopírován: {target_checkpoint}")

        # Pokud je checkpoint .pth, vytvoř také checkpoint.pth (pro kompatibilitu)
        if checkpoint_path.suffix == ".pth" and target_checkpoint.name != "checkpoint.pth":
            checkpoint_pth = TARGET_DIR / "checkpoint.pth"
            shutil.copy2(checkpoint_path, checkpoint_pth)
            print(f"✅ Zkopírován (alias): {checkpoint_pth}")

        print()
        print("=" * 60)
        print("[OK] Model úspěšně stažen a zkopírován!")
        print("=" * 60)
        print(f"Model je uložen v: {TARGET_DIR}")
        print(f"Použitý model: {model_used}")
        print()
        print("Soubory:")
        print(f"  - {target_config.name}")
        print(f"  - {target_checkpoint.name}")

        return True

    except Exception as e:
        print()
        print("=" * 60)
        print("[ERROR] CHYBA při kopírování souborů")
        print("=" * 60)
        print(f"Chyba: {e}")
        return False


if __name__ == "__main__":
    success = download_model()
    sys.exit(0 if success else 1)
