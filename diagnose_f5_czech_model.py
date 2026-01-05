"""
Diagnostický skript pro kontrolu kompatibility českého finetunovaného F5TTS modelu
Kontroluje vocab size, checkpoint kompatibilitu a model config
"""
import sys
import os
from pathlib import Path
import torch

# Fix pro Windows encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Přidat kořenový adresář projektu do sys.path
sys.path.append(os.getcwd())

import backend.config as config

def check_vocab_size(vocab_path: Path) -> int:
    """Zkontroluje počet tokenů v vocab souboru"""
    if not vocab_path.exists():
        return -1
    
    with open(vocab_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    
    # Odstranit duplikáty, ale zachovat pořadí
    seen = set()
    unique_tokens = []
    for token in lines:
        if token not in seen:
            seen.add(token)
            unique_tokens.append(token)
    
    return len(unique_tokens)

def check_checkpoint_vocab_size(ckpt_path: Path) -> int:
    """Zkontroluje vocab size v checkpointu"""
    if not ckpt_path.exists():
        return -1
    
    try:
        checkpoint = torch.load(ckpt_path, map_location='cpu')
        
        # Zkusit najít vocab size v různých možných klíčích
        vocab_size = None
        
        # Zkusit ema_model_state_dict
        if 'ema_model_state_dict' in checkpoint:
            state_dict = checkpoint['ema_model_state_dict']
            embed_key = 'transformer.text_embed.text_embed.weight'
            if embed_key in state_dict:
                vocab_size = state_dict[embed_key].shape[0]
        
        # Zkusit model_state_dict
        if vocab_size is None and 'model_state_dict' in checkpoint:
            state_dict = checkpoint['model_state_dict']
            embed_key = 'transformer.text_embed.text_embed.weight'
            if embed_key in state_dict:
                vocab_size = state_dict[embed_key].shape[0]
        
        # Zkusit přímo v root
        if vocab_size is None:
            embed_key = 'transformer.text_embed.text_embed.weight'
            if embed_key in checkpoint:
                vocab_size = checkpoint[embed_key].shape[0]
        
        return vocab_size if vocab_size is not None else -1
        
    except Exception as e:
        print(f"❌ Chyba při načítání checkpointu: {e}")
        return -1

def check_model_config(model_dir: Path) -> tuple[bool, Path]:
    """Zkontroluje, zda existuje model config"""
    local_config = model_dir / "F5TTS_Czech.yaml"
    if local_config.exists():
        return True, local_config
    
    # Zkusit najít base config
    try:
        import importlib.util
        spec = importlib.util.find_spec("f5_tts")
        if spec and spec.submodule_search_locations:
            f5_base = Path(list(spec.submodule_search_locations)[0]).resolve()
            base_config = f5_base / "configs" / "F5TTS_v1_Base.yaml"
            if base_config.exists():
                return False, base_config
            base_config = f5_base / "configs" / "F5TTS_Base.yaml"
            if base_config.exists():
                return False, base_config
    except Exception:
        pass
    
    return False, None

def main():
    print("=" * 70)
    print("DIAGNOSTIKA F5TTS ČESKÉHO FINETUNOVANÉHO MODELU")
    print("=" * 70)
    print()
    
    model_dir = config.F5_CZECH_MODEL_DIR
    ckpt_name = config.F5_CZECH_CKPT_NAME
    vocab_name = config.F5_CZECH_VOCAB_NAME
    
    ckpt_path = model_dir / ckpt_name
    vocab_path = model_dir / vocab_name
    
    print(f"📁 Model directory: {model_dir}")
    print(f"📄 Checkpoint: {ckpt_name}")
    print(f"📄 Vocab: {vocab_name}")
    print()
    
    # Kontrola 1: Existence souborů
    print("1️⃣ KONTROLA EXISTENCE SOUBORŮ")
    print("-" * 70)
    
    ckpt_exists = ckpt_path.exists()
    vocab_exists = vocab_path.exists()
    
    print(f"Checkpoint: {'✅ Existuje' if ckpt_exists else '❌ Nenalezen'} ({ckpt_path})")
    print(f"Vocab: {'✅ Existuje' if vocab_exists else '❌ Nenalezen'} ({vocab_path})")
    print()
    
    if not ckpt_exists or not vocab_exists:
        print("⚠️  Některé soubory chybí. Zkontrolujte konfiguraci.")
        return
    
    # Kontrola 2: Vocab size kompatibilita
    print("2️⃣ KONTROLA KOMPATIBILITY VOCAB SIZE")
    print("-" * 70)
    
    vocab_size = check_vocab_size(vocab_path)
    ckpt_vocab_size = check_checkpoint_vocab_size(ckpt_path)
    
    print(f"Vocab soubor: {vocab_size} tokenů")
    print(f"Checkpoint: {ckpt_vocab_size} tokenů")
    
    if vocab_size == -1:
        print("❌ Nepodařilo se načíst vocab soubor")
    elif ckpt_vocab_size == -1:
        print("❌ Nepodařilo se načíst vocab size z checkpointu")
    elif vocab_size == ckpt_vocab_size:
        print(f"✅ KOMPATIBILNÍ - oba mají {vocab_size} tokenů")
    elif ckpt_vocab_size == vocab_size + 1:
        # Checkpoint má o 1 token více (padding token) - to je správně pro F5-TTS CLI
        print(f"✅ KOMPATIBILNÍ - checkpoint má {ckpt_vocab_size} tokenů (vocab {vocab_size} + padding)")
        print("   → F5-TTS CLI očekává checkpoint s padding tokenem")
    elif vocab_size == ckpt_vocab_size + 1:
        print(f"✅ KOMPATIBILNÍ - vocab má {vocab_size} tokenů (checkpoint {ckpt_vocab_size} + padding v vocab)")
    else:
        print(f"❌ NEKOMPATIBILNÍ - rozdíl {abs(vocab_size - ckpt_vocab_size)} tokenů!")
        print()
        print("🔧 OPRAVA:")
        print(f"   - Vocab soubor má {vocab_size} tokenů")
        print(f"   - Checkpoint má {ckpt_vocab_size} tokenů")
        print()
        if vocab_size < ckpt_vocab_size:
            diff = ckpt_vocab_size - vocab_size
            if diff == 1:
                print(f"   → Checkpoint má o 1 token více (pravděpodobně padding) - to je správně!")
                print(f"   → F5-TTS CLI očekává checkpoint s {ckpt_vocab_size} tokeny")
            else:
                print(f"   → Musíte přidat {diff} tokenů do vocab souboru")
                print(f"   → Nebo použít patch_checkpoint_vocab_to_103.py pro úpravu checkpointu")
        else:
            print(f"   → Musíte odebrat {vocab_size - ckpt_vocab_size} tokenů z vocab souboru")
            print(f"   → Nebo použít patch_checkpoint_vocab_to_103.py pro úpravu checkpointu")
    print()
    
    # Kontrola 3: Model config
    print("3️⃣ KONTROLA MODEL CONFIG")
    print("-" * 70)
    
    has_local_config, config_path = check_model_config(model_dir)
    
    if has_local_config:
        print(f"✅ Lokální model config nalezen: {config_path}")
        print("   → Model bude používat vlastní konfiguraci")
    elif config_path:
        print(f"⚠️  Lokální config neexistuje, použije se base config: {config_path}")
        print("   → Může způsobit problémy pokud finetunovaný model má jinou architekturu")
        print()
        print("🔧 DOPORUČENÍ:")
        print(f"   → Vytvořte {model_dir / 'F5TTS_Czech.yaml'}")
        print(f"   → Zkopírujte base config a upravte podle finetunovaného modelu")
    else:
        print("❌ Model config nenalezen ani lokálně, ani v balíčku f5_tts")
    print()
    
    # Kontrola 4: NFE nastavení
    print("4️⃣ KONTROLA NFE NASTAVENÍ")
    print("-" * 70)
    
    nfe = config.F5_CZECH_DEFAULT_NFE
    print(f"Aktuální NFE: {nfe}")
    
    if nfe < 16:
        print("⚠️  NFE je příliš nízké (< 16) - může způsobit horší kvalitu")
        print("   → Doporučeno: 16-32")
    elif nfe > 32:
        print("⚠️  NFE je příliš vysoké (> 32) - může být pomalé")
        print("   → Doporučeno: 16-32")
    else:
        print(f"✅ NFE je v rozumném rozsahu")
    
    print()
    print("🔧 DOPORUČENÍ PRO NFE:")
    print("   → Pro finetunované modely zkuste: 20-24")
    print("   → Nastavte pomocí: export F5_CZECH_DEFAULT_NFE=20")
    print()
    
    # Shrnutí
    print("=" * 70)
    print("SHRNUTÍ")
    print("=" * 70)
    
    issues = []
    # Kontrola kompatibility - akceptujeme i variantu s padding tokenem
    if vocab_size > 0 and ckpt_vocab_size > 0:
        if vocab_size != ckpt_vocab_size and ckpt_vocab_size != vocab_size + 1 and vocab_size != ckpt_vocab_size + 1:
            issues.append("Vocab size mismatch")
    if not has_local_config:
        issues.append("Chybí lokální model config")
    if nfe < 16 or nfe > 32:
        issues.append("NFE mimo doporučený rozsah")
    
    if issues:
        print("❌ Nalezeny problémy:")
        for issue in issues:
            print(f"   - {issue}")
        print()
        print("🔧 Postupujte podle doporučení výše pro opravu.")
    else:
        print("✅ Všechny kontroly prošly úspěšně!")
        print("   Pokud stále máte problémy s nesrozumitelnou řečí,")
        print("   zkuste:")
        print("   1. Zkontrolovat kvalitu trénovacích dat")
        print("   2. Zkontrolovat, zda checkpoint není poškozený")
        print("   3. Zkusit jiné NFE hodnoty (20-24)")
        print("   4. Zkontrolovat, zda text preprocessing je správný")

if __name__ == "__main__":
    main()
