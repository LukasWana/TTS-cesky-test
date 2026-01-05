"""
Upraví checkpoint, aby měl 103 tokenů (102 + padding) pro kompatibilitu s F5-TTS CLI
"""
import sys
import os

# Fix pro Windows encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import torch
from pathlib import Path

# Load checkpoint
ckpt_path = Path("models/f5-tts-czech/model_1200000_vocab102.pt")
print(f"Loading checkpoint: {ckpt_path}")

if not ckpt_path.exists():
    print(f"❌ Checkpoint nenalezen: {ckpt_path}")
    sys.exit(1)

checkpoint = torch.load(ckpt_path, map_location='cpu')

# Check current vocab embedding size
if 'ema_model_state_dict' in checkpoint:
    state_dict = checkpoint['ema_model_state_dict']
elif 'model_state_dict' in checkpoint:
    state_dict = checkpoint['model_state_dict']
else:
    print("❌ Error: No state_dict found in checkpoint")
    sys.exit(1)

embed_key = 'transformer.text_embed.text_embed.weight'
if embed_key not in state_dict:
    print(f"❌ Error: {embed_key} not found in checkpoint")
    sys.exit(1)

current_embed = state_dict[embed_key]
current_size = current_embed.shape[0]
print(f"Current vocab size in checkpoint: {current_size}")

# F5-TTS CLI očekává 103 tokenů (102 + 1 padding)
target_size = 103
if current_size < target_size:
    print(f"🔧 Rozšiřuji vocab z {current_size} na {target_size} (přidávám padding token)")
    
    # Přidat 1 embedding pro padding token
    # Inicializovat malými náhodnými hodnotami (bude finetunováno)
    extra_embed = torch.randn(1, current_embed.shape[1]) * 0.02
    new_embed = torch.cat([current_embed, extra_embed], dim=0)
    state_dict[embed_key] = new_embed
    
    # Aktualizovat oba state_dict pokud existují
    if 'ema_model_state_dict' in checkpoint:
        checkpoint['ema_model_state_dict'] = state_dict
    if 'model_state_dict' in checkpoint:
        checkpoint['model_state_dict'] = state_dict
    
    # Vytvořit zálohu
    backup_path = ckpt_path.with_suffix('.pt.backup')
    import shutil
    shutil.copy2(ckpt_path, backup_path)
    print(f"✅ Záloha vytvořena: {backup_path}")
    
    # Uložit upravený checkpoint
    torch.save(checkpoint, ckpt_path)
    print(f"✅ Checkpoint upraven a uložen: {ckpt_path}")
    print(f"   → Nová vocab size: {target_size}")
    print()
    print("⚠️  POZNÁMKA:")
    print("   → Checkpoint nyní má 103 tokenů (102 + padding)")
    print("   → Vocab soubor má 102 tokenů")
    print("   → F5-TTS CLI by měl nyní fungovat správně")
elif current_size == target_size:
    print(f"✅ Checkpoint už má správnou velikost ({target_size})")
else:
    print(f"⚠️  Checkpoint má {current_size} tokenů, očekáváno {target_size}")
    print("   → Checkpoint má více tokenů než očekáváno")
