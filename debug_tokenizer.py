import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(os.getcwd())

try:
    from f5_tts.infer.utils_infer import get_tokenizer
except ImportError:
    print("Could not import f5_tts. Ensure it is installed.")
    sys.exit(1)

model_cfg = {
    "model": {
        "tokenizer": "custom",
        "tokenizer_path": "models/f5-tts-czech/vocab.txt"
    }
}

print("Initializing tokenizer with custom vocab...")
# Simulate how the library loads it.
# Note: get_tokenizer might require more arguments or a specific config object structure.
# Let's try to inspect the source if possible, or just instantiate it.

# Actually, utils_infer.py uses:
# tokenizer = "custom"
# tokenizer_path = model_cfg.model.tokenizer_path
# vocab_char_map, vocab_size = get_tokenizer(model_cfg)

class MockConfig:
    def __init__(self, data):
        self.model = type('obj', (object,), data['model'])

cfg = MockConfig(model_cfg)
vocab_char_map, vocab_size = get_tokenizer("custom", "checkpoint_file", "vocab_file", cfg)

print(f"Vocab size: {vocab_size}")
print(f"Char map preview (first 10): {list(vocab_char_map.items())[:10]}")

# Test encoding a simple Czech sentence
text = "Ahoj světe"
print(f"\nTesting text: '{text}'")
# We need to find the encoding function. It is likely inside the tokenizer or utils.
# In F5-TTS, it often uses a simple char lookup.

encoded = [vocab_char_map.get(c, 0) for c in text] # Assuming 0 is UNK or PAD?
print(f"Encoded ids: {encoded}")

# Check what ID ' ' (space) maps to
if ' ' in vocab_char_map:
    print(f"Space ' ' maps to: {vocab_char_map[' ']}" )
else:
    print("Space ' ' NOT found in vocab map")

# Check what ID 'a' maps to
if 'a' in vocab_char_map:
    print(f"'a' maps to: {vocab_char_map['a']}")
