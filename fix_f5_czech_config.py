"""
Opraví F5TTS_Czech.yaml config - nastaví správnou vocab size
"""
import sys
import os
from pathlib import Path
import yaml

# Fix pro Windows encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Přidat kořenový adresář projektu do sys.path
sys.path.append(os.getcwd())

import backend.config as config
import torch

def fix_config():
    """Opraví config soubor nastavením správné vocab size"""
    model_dir = config.F5_CZECH_MODEL_DIR
    ckpt_name = config.F5_CZECH_CKPT_NAME
    vocab_name = config.F5_CZECH_VOCAB_NAME
    config_name = "F5TTS_Czech.yaml"

    ckpt_path = model_dir / ckpt_name
    vocab_path = model_dir / vocab_name
    config_path = model_dir / config_name

    print("=" * 70)
    print("OPRAVA F5TTS_Czech.yaml CONFIG")
    print("=" * 70)
    print()

    if not ckpt_path.exists():
        print(f"❌ Checkpoint nenalezen: {ckpt_path}")
        return False

    if not vocab_path.exists():
        print(f"❌ Vocab soubor nenalezen: {vocab_path}")
        return False

    if not config_path.exists():
        print(f"❌ Config soubor nenalezen: {config_path}")
        print("   → Vytvořím nový config založený na base configu")
        return create_new_config(model_dir, config_path, ckpt_path, vocab_path)

    # Načíst vocab size z checkpointu
    try:
        checkpoint = torch.load(ckpt_path, map_location='cpu')
        vocab_size = None

        if 'ema_model_state_dict' in checkpoint:
            state_dict = checkpoint['ema_model_state_dict']
            embed_key = 'transformer.text_embed.text_embed.weight'
            if embed_key in state_dict:
                vocab_size = state_dict[embed_key].shape[0]

        if vocab_size is None and 'model_state_dict' in checkpoint:
            state_dict = checkpoint['model_state_dict']
            embed_key = 'transformer.text_embed.text_embed.weight'
            if embed_key in state_dict:
                vocab_size = state_dict[embed_key].shape[0]

        if vocab_size is None:
            print("❌ Nepodařilo se najít vocab size v checkpointu")
            return False

        print(f"Checkpoint vocab size: {vocab_size}")

    except Exception as e:
        print(f"❌ Chyba při načítání checkpointu: {e}")
        return False

    # Načíst config
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        # Vytvořit zálohu
        backup_path = config_path.with_suffix('.yaml.backup')
        with open(backup_path, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
        print(f"✅ Záloha vytvořena: {backup_path}")

        # F5-TTS model config obvykle nemá explicitní vocab size v architektuře
        # Vocab size se načítá z vocab souboru při inicializaci modelu
        # Problém může být v tom, že model architektura má hardcoded hodnotu

        # Zkusit najít, kde se vocab size nastavuje
        # Obvykle je to v model.arch nebo model.tokenizer

        modified = False

        # Pokud existuje model.arch.vocab_size, upravit ho
        if 'model' in config_data and 'arch' in config_data['model']:
            if 'vocab_size' in config_data['model']['arch']:
                old_size = config_data['model']['arch']['vocab_size']
                if old_size != vocab_size:
                    config_data['model']['arch']['vocab_size'] = vocab_size
                    modified = True
                    print(f"   → Opraveno vocab_size v model.arch: {old_size} → {vocab_size}")

        # Pokud existuje model.vocab_size, upravit ho
        if 'model' in config_data:
            if 'vocab_size' in config_data['model']:
                old_size = config_data['model']['vocab_size']
                if old_size != vocab_size:
                    config_data['model']['vocab_size'] = vocab_size
                    modified = True
                    print(f"   → Opraveno vocab_size v model: {old_size} → {vocab_size}")

        if not modified:
            print("⚠️  Config neobsahuje explicitní vocab_size nastavení")
            print("   → F5-TTS by měl načítat vocab size z vocab souboru automaticky")
            print("   → Problém může být v tom, že model architektura má hardcoded hodnotu")
            print()
            print("🔧 DOPORUČENÍ:")
            print("   → Zkontrolujte, zda base config (F5TTS_v1_Base.yaml) má správnou hodnotu")
            print("   → Nebo zkuste použít base config místo lokálního")

        # Uložit config
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        print()
        print(f"✅ Config soubor aktualizován: {config_path}")
        return True

    except Exception as e:
        print(f"❌ Chyba při úpravě configu: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_new_config(model_dir: Path, config_path: Path, ckpt_path: Path, vocab_path: Path):
    """Vytvoří nový config založený na base configu"""
    try:
        import importlib.util
        spec = importlib.util.find_spec("f5_tts")
        if not spec or not spec.submodule_search_locations:
            print("❌ Nelze najít balíček f5_tts")
            return False

        f5_base = Path(list(spec.submodule_search_locations)[0]).resolve()
        base_config_path = f5_base / "configs" / "F5TTS_v1_Base.yaml"
        if not base_config_path.exists():
            base_config_path = f5_base / "configs" / "F5TTS_Base.yaml"

        if not base_config_path.exists():
            print(f"❌ Base config nenalezen: {base_config_path}")
            return False

        # Načíst base config
        with open(base_config_path, "r", encoding="utf-8") as f:
            base_config = yaml.safe_load(f)

        # Upravit pro český model
        if 'model' in base_config:
            base_config['model']['name'] = 'F5TTS_Czech'
            base_config['model']['tokenizer'] = 'custom'
            base_config['model']['tokenizer_path'] = str(vocab_path.name)  # Pouze název souboru

        # Uložit
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(base_config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        print(f"✅ Nový config vytvořen: {config_path}")
        return True

    except Exception as e:
        print(f"❌ Chyba při vytváření configu: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = fix_config()
        if success:
            print()
            print("=" * 70)
            print("✅ OPRAVA DOKONČENA")
            print("=" * 70)
            print()
            print("Nyní restartujte backend server a zkuste znovu.")
        else:
            print()
            print("=" * 70)
            print("❌ OPRAVA SELHALA")
            print("=" * 70)
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n❌ Přerušeno uživatelem")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Chyba: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
