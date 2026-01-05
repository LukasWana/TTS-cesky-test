import sys
import os
from pathlib import Path
import asyncio

# Přidat kořenový adresář projektu do sys.path
sys.path.append(os.getcwd())

import backend.config as config

async def test_f5_czech_model():
    print("--- F5-TTS Czech Model Connection Test (Updated) ---")
    print(f"Configured ckpt: {config.F5_CZECH_CKPT_NAME}")

    ckpt_path = config.F5_CZECH_MODEL_DIR / config.F5_CZECH_CKPT_NAME

    print(f"Checking file:")
    print(f"Checkpoint exists: {ckpt_path.exists()} ({ckpt_path})")

    if ckpt_path.exists():
        print("\n✅ SUCCESS: Converted model file correctly identified.")
    else:
        print(f"\n❌ ERROR: Converted model file not found: {ckpt_path}")

if __name__ == "__main__":
    asyncio.run(test_f5_czech_model())
