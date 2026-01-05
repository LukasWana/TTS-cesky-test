"""
Opraví vocab soubor pro český F5TTS model - přidá chybějící tokeny
"""
import sys
import os
from pathlib import Path

# Fix pro Windows encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Přidat kořenový adresář projektu do sys.path
sys.path.append(os.getcwd())

import backend.config as config
import torch

def fix_vocab():
    """Opraví vocab soubor přidáním chybějících tokenů"""
    model_dir = config.F5_CZECH_MODEL_DIR
    ckpt_name = config.F5_CZECH_CKPT_NAME
    vocab_name = config.F5_CZECH_VOCAB_NAME

    ckpt_path = model_dir / ckpt_name
    vocab_path = model_dir / vocab_name

    print("=" * 70)
    print("OPRAVA VOCAB SOUBORU PRO F5TTS ČESKÝ MODEL")
    print("=" * 70)
    print()

    if not ckpt_path.exists():
        print(f"❌ Checkpoint nenalezen: {ckpt_path}")
        return False

    if not vocab_path.exists():
        print(f"❌ Vocab soubor nenalezen: {vocab_path}")
        return False

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

        print(f"Checkpoint očekává: {vocab_size} tokenů")

    except Exception as e:
        print(f"❌ Chyba při načítání checkpointu: {e}")
        return False

    # Načíst aktuální vocab (odstranit prázdné řádky na začátku a konci)
    with open(vocab_path, "r", encoding="utf-8") as f:
        all_lines = f.readlines()

    # Odstranit prázdné řádky na začátku a konci, ale zachovat prázdné řádky uprostřed (pokud jsou významné)
    lines = []
    for line in all_lines:
        stripped = line.strip()
        if stripped:  # Ne-prázdný řádek
            lines.append(stripped)

    # Odstranit duplikáty, ale zachovat pořadí
    seen = set()
    unique_tokens = []
    for token in lines:
        if token not in seen:
            seen.add(token)
            unique_tokens.append(token)

    current_size = len(unique_tokens)
    print(f"Aktuální vocab: {current_size} tokenů (po odstranění prázdných řádků)")
    print()

    # F5-TTS checkpoint obvykle má o 1 token více než vocab (padding token)
    # Takže pokud checkpoint má vocab_size, vocab soubor by měl mít vocab_size - 1
    expected_vocab_size = vocab_size - 1  # Checkpoint má padding token navíc

    if current_size == expected_vocab_size:
        print(f"✅ Vocab soubor má správnou velikost ({current_size}), checkpoint má {vocab_size} (včetně padding)")
        return True
    elif current_size == vocab_size:
        print(f"✅ Vocab soubor má stejnou velikost jako checkpoint ({vocab_size})")
        return True

    if current_size > vocab_size:
        print(f"⚠️  Vocab soubor má více tokenů ({current_size}) než checkpoint ({vocab_size})")
        print("   → Zkontrolujte, zda je checkpoint správný")
        response = input("   → Chcete pokračovat a oříznout vocab? (ano/ne): ")
        if response.lower() != 'ano':
            return False
        unique_tokens = unique_tokens[:expected_vocab_size]
    else:
        # Přidat chybějící tokeny
        # Použijeme expected_vocab_size (vocab_size - 1) pro kompatibilitu s F5-TTS CLI
        missing = expected_vocab_size - current_size
        print(f"🔧 Přidávám {missing} chybějících tokenů...")
        print(f"   → Checkpoint má {vocab_size} tokenů (včetně padding)")
        print(f"   → Vocab soubor by měl mít {expected_vocab_size} tokenů")

        # Vytvořit zálohu
        backup_path = vocab_path.with_suffix('.txt.backup')
        with open(backup_path, "w", encoding="utf-8") as f:
            for token in unique_tokens:
                f.write(token + "\n")
        print(f"✅ Záloha vytvořena: {backup_path}")

        # Přidat placeholder tokeny (budou finetunovány při dalším trénování)
        # Použijeme jednoduché tokeny jako <pad>, <unk>, nebo číselné tokeny
        placeholder_tokens = []
        for i in range(missing):
            # Zkusit použít běžné placeholder tokeny
            if i == 0 and '<pad>' not in seen:
                placeholder_tokens.append('<pad>')
            elif i == 1 and '<unk>' not in seen:
                placeholder_tokens.append('<unk>')
            else:
                # Jinak použít číselný token
                placeholder_tokens.append(f'<token_{current_size + i}>')

        unique_tokens.extend(placeholder_tokens)
        print(f"   Přidané tokeny: {placeholder_tokens}")

    # Uložit opravený vocab
    with open(vocab_path, "w", encoding="utf-8") as f:
        for token in unique_tokens:
            f.write(token + "\n")

    print()
    print(f"✅ Vocab soubor opraven: {len(unique_tokens)} tokenů")
    print(f"   → Soubor: {vocab_path}")
    print()
    print("⚠️  POZNÁMKA:")
    print("   Pokud jste přidali placeholder tokeny, doporučuji:")
    print("   1. Zkontrolovat, zda model funguje správně")
    print("   2. Pokud ne, zvažte pře-trénování s kompletním vocab souborem")

    return True

if __name__ == "__main__":
    try:
        success = fix_vocab()
        if success:
            print()
            print("=" * 70)
            print("✅ OPRAVA DOKONČENA")
            print("=" * 70)
            print()
            print("Nyní můžete znovu spustit diagnostiku:")
            print("  python diagnose_f5_czech_model.py")
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
