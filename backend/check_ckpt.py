
import torch
import sys

ckpt_path = "c:/work/projects/2025-voice-assistent/models/f5-tts-czech/model.pt"

try:
    print(f"Loading {ckpt_path}...")
    checkpoint = torch.load(ckpt_path, map_location='cpu')

    state_dict = checkpoint.get("ema_model_state_dict", checkpoint.get("model_state_dict", checkpoint))

    # Try different key prefixes
    keys_to_try = [
        "transformer.text_embed.text_embed.weight",
        "ema_model.transformer.text_embed.text_embed.weight",
        "model.transformer.text_embed.text_embed.weight"
    ]

    found = False
    for key in keys_to_try:
        if key in state_dict:
            weight = state_dict[key]
            print(f"Vocab size in checkpoint ({key}): {weight.shape[0]}")
            found = True
            break

    if not found:
        print(f"Embedding weights not found.")
        # Print more keys to help debug
        print("Keys snippet:", list(state_dict.keys())[:10])

except Exception as e:
    print(f"Error: {e}")
