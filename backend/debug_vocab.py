
import torch
from pathlib import Path
import os
import sys

# Config paths
MODEL_DIR = Path("c:/work/projects/2025-voice-assistent/models/f5-tts-slovak")
CKPT_PATH = MODEL_DIR / "model_30000.safetensors"
VOCAB_PATH = MODEL_DIR / "model_30000.txt"
VOCAB_BACKUP_PATH = MODEL_DIR / "vocab.txt.backup"

def validate_model(ckpt_path: Path, vocab_path: Path):
    print(f"Checking {ckpt_path} vs {vocab_path}")

    if not ckpt_path.exists():
        print("Ckpt not found")
        return
    if not vocab_path.exists():
        print("Vocab not found")
        return

    # 1. Check vocab file size
    with open(vocab_path, "r", encoding="utf-8") as f:
        vocab_lines = [l.strip('\n').strip('\r') for l in f.readlines() if l.strip()]

    vocab_file_size = len(vocab_lines)
    print(f"Vocab file size: {vocab_file_size}")

    # 2. Check checkpoint embedding size
    try:
        if str(ckpt_path).endswith(".safetensors"):
            from safetensors.torch import load_file
            checkpoint = load_file(ckpt_path)
            state_dict = checkpoint
        else:
            checkpoint = torch.load(ckpt_path, map_location='cpu', weights_only=False)
            state_dict = checkpoint
            if isinstance(checkpoint, dict):
                 state_dict = checkpoint.get("ema_model_state_dict", checkpoint.get("model_state_dict", checkpoint))

        embed_key = "transformer.text_embed.text_embed.weight"
        # Check for ema_model prefix
        if embed_key not in state_dict and f"ema_model.{embed_key}" in state_dict:
            embed_key = f"ema_model.{embed_key}"

        if isinstance(state_dict, dict) and embed_key in state_dict:
            ckpt_vocab_size = state_dict[embed_key].shape[0]
            print(f"Checkpoint embedding size: {ckpt_vocab_size}")

            diff = ckpt_vocab_size - vocab_file_size
            print(f"Difference (Ckpt - Vocab): {diff}")

            if diff == 0:
                print("MATCH")
            elif diff == 1:
                print("MATCH (+1 padding)")
            elif diff == -1:
                print("MATCH (-1 padding)")
            else:
                print("MISMATCH")
        else:
            print("Embedding key not found in state_dict")
            if isinstance(state_dict, dict):
                print(f"Keys (first 10): {list(state_dict.keys())[:10]}")
            else:
                print("state_dict is not dict")

    except Exception as e:
        print(f"Error loading ckpt: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    validate_model(CKPT_PATH, VOCAB_PATH)
