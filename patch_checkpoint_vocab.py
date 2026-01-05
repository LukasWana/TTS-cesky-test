import torch
import sys

# Load checkpoint
ckpt_path = "models/f5-tts-czech/model_1200000_standard.pt"
print(f"Loading checkpoint: {ckpt_path}")
checkpoint = torch.load(ckpt_path, map_location='cpu')

# Check current vocab embedding size
if 'ema_model_state_dict' in checkpoint:
    state_dict = checkpoint['ema_model_state_dict']
else:
    print("Error: No ema_model_state_dict found")
    sys.exit(1)

embed_key = 'transformer.text_embed.text_embed.weight'
if embed_key in state_dict:
    current_embed = state_dict[embed_key]
    current_size = current_embed.shape[0]
    print(f"Current vocab size in checkpoint: {current_size}")

    # We need 102 instead of 101 (vocab has 101 lines + 1 padding token)
    target_size = 102
    if current_size < target_size:
        print(f"Extending vocab from {current_size} to {target_size}")
        # Add 2 random embeddings (will be fine-tuned if needed)
        extra_rows = target_size - current_size
        extra_embed = torch.randn(extra_rows, current_embed.shape[1]) * 0.02
        new_embed = torch.cat([current_embed, extra_embed], dim=0)
        state_dict[embed_key] = new_embed

        # Save
        output_path = "models/f5-tts-czech/model_1200000_vocab102.pt"
        checkpoint['ema_model_state_dict'] = state_dict
        torch.save(checkpoint, output_path)
        print(f"Saved extended checkpoint to: {output_path}")
        print("Update F5_CZECH_CKPT_NAME in config.py to 'model_1200000_vocab102.pt'")
    else:
        print(f"Vocab size already >= {target_size}, no change needed")
else:
    print(f"Error: {embed_key} not found in checkpoint")
