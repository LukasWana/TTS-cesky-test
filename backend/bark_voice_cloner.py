"""
Bark Voice Cloner - Utility for extracting voice features from audio files.

This module provides functions to extract semantic, coarse, and fine voice prompts
from reference audio files and save them in the NPZ format that Bark expects.

The NPZ file contains:
- semantic_prompt: HuBERT semantic tokens
- coarse_prompt: Encodec coarse audio codes (2 codebooks)
- fine_prompt: Encodec fine audio codes (all codebooks)
"""

import os
import uuid
from pathlib import Path
from typing import Optional, Tuple
import numpy as np
import soundfile as sf
import torch

from backend.config import BASE_DIR

TEMP_DIR = BASE_DIR / "temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

BARK_VOICES_DIR = BASE_DIR / "bark_voices"
BARK_VOICES_DIR.mkdir(parents=True, exist_ok=True)


def load_audio_for_bark(
    audio_path: str, target_sample_rate: int = 24000
) -> Tuple[np.ndarray, int]:
    """
    Load and preprocess audio file for Bark voice cloning.

    Args:
        audio_path: Path to the audio file
        target_sample_rate: Target sample rate (Bark uses 24kHz)

    Returns:
        Tuple of (audio_data, sample_rate)
    """
    audio_data, sample_rate = sf.read(str(audio_path))

    if audio_data.ndim > 1:
        audio_data = np.mean(audio_data, axis=1)

    if audio_data.dtype != np.float32:
        if audio_data.dtype == np.int16:
            audio_data = audio_data.astype(np.float32) / 32768.0
        elif audio_data.dtype == np.int32:
            audio_data = audio_data.astype(np.float32) / 2147483648.0
        else:
            audio_data = audio_data.astype(np.float32)

    audio_data = np.clip(audio_data, -1.0, 1.0)

    if sample_rate != target_sample_rate:
        try:
            from scipy import signal

            num_samples = int(len(audio_data) * target_sample_rate / sample_rate)
            audio_data = signal.resample(audio_data, num_samples)
        except ImportError:
            old_length = len(audio_data)
            new_length = int(old_length * target_sample_rate / sample_rate)
            old_indices = np.arange(old_length)
            new_indices = np.linspace(0, old_length - 1, new_length)
            audio_data = np.interp(new_indices, old_indices, audio_data)

    return audio_data, target_sample_rate


def extract_voice_features(
    audio_path: str, device: str = "cpu", verbose: bool = True
) -> Optional[dict]:
    """
    Extract voice features from audio file for Bark voice cloning.

    This function:
    1. Loads the audio file
    2. Encodes it using Encodec to get coarse and fine codes
    3. Uses HuBERT to get semantic tokens
    4. Saves everything to an NPZ file

    Args:
        audio_path: Path to the reference audio file
        device: Device to use for inference ('cpu' or 'cuda')
        verbose: Whether to print progress messages

    Returns:
        Dictionary with semantic_prompt, coarse_prompt, fine_prompt, or None on error
    """
    try:
        if verbose:
            print(f"[BarkVoiceCloner] Načítám audio: {audio_path}")

        audio_data, sample_rate = load_audio_for_bark(audio_path)

        if verbose:
            print(
                f"[BarkVoiceCloner] Audio načteno: {len(audio_data) / sample_rate:.2f}s, {sample_rate}Hz"
            )

        audio_tensor = torch.from_numpy(audio_data).float().unsqueeze(0)

        if device == "cuda" and torch.cuda.is_available():
            audio_tensor = audio_tensor.cuda()

        try:
            from encodec import EncodecModel

            encodec = EncodecModel.encodec_model_24khz()
            if device == "cuda" and torch.cuda.is_available():
                encodec = encodec.cuda()
            encodec.eval()

            with torch.inference_mode():
                encoded_frames = encodec.encode(audio_tensor.unsqueeze(0))

                coarse_codes = encoded_frames[0][0]
                fine_codes = encoded_frames[0][1]

                coarse_prompt = coarse_codes.cpu().numpy().squeeze()
                fine_prompt = fine_codes.cpu().numpy().squeeze()

                if verbose:
                    print(
                        f"[BarkVoiceCloner] Encodec kódy: coarse={coarse_prompt.shape}, fine={fine_prompt.shape}"
                    )

        except ImportError as e:
            if verbose:
                print(f"[BarkVoiceCloner] Encodec není dostupný: {e}")
            return None
        except Exception as e:
            if verbose:
                print(f"[BarkVoiceCloner] Chyba při Encodec: {e}")
            import traceback

            if verbose:
                print(traceback.format_exc())
            return None

        try:
            from huggingface_hub import hf_hub_download
            from transformers import AutoModel

            if verbose:
                print(f"[BarkVoiceCloner] Načítám HuBERT model...")

            hubert_model = AutoModel.from_pretrained("facebook/hubert-base-ls960")
            if device == "cuda" and torch.cuda.is_available():
                hubert_model = hubert_model.cuda()
            hubert_model.eval()

            if audio_data.ndim == 1:
                audio_data_2d = audio_data[np.newaxis, :]
            else:
                audio_data_2d = audio_data

            with torch.inference_mode():
                hubert_outputs = hubert_model(audio_data_2d)
                semantic_prompt = (
                    hubert_outputs.last_hidden_state.cpu().numpy().squeeze()
                )

            semantic_prompt = semantic_prompt.astype(np.int64)
            if semantic_prompt.ndim > 1:
                semantic_prompt = semantic_prompt.ravel()
            else:
                semantic_prompt = semantic_prompt[:512].astype(np.int64)

            if verbose:
                print(f"[BarkVoiceCloner] HuBERT tokeny: {semantic_prompt.shape}")

        except ImportError as e:
            if verbose:
                print(f"[BarkVoiceCloner] HuBERT není dostupný: {e}")
            return None
        except Exception as e:
            if verbose:
                print(f"[BarkVoiceCloner] Chyba při HuBERT: {e}")
            import traceback

            if verbose:
                print(traceback.format_exc())
            return None

        return {
            "semantic_prompt": semantic_prompt,
            "coarse_prompt": coarse_prompt,
            "fine_prompt": fine_prompt,
        }

    except Exception as e:
        if verbose:
            print(f"[BarkVoiceCloner] ⚠️ Obecná chyba: {e}")
        import traceback

        if verbose:
            print(traceback.format_exc())
        return None


def create_voice_npz(
    audio_path: str,
    voice_id: Optional[str] = None,
    output_dir: Path = None,
    device: str = "cpu",
    verbose: bool = True,
) -> Optional[str]:
    """
    Create an NPZ file with voice features for Bark.

    Args:
        audio_path: Path to the reference audio file
        voice_id: Optional custom ID for the voice (auto-generated if not provided)
        output_dir: Directory to save the NPZ file (default: BARK_VOICES_DIR)
        device: Device for inference
        verbose: Whether to print progress

    Returns:
        Path to the created NPZ file, or None on error
    """
    if output_dir is None:
        output_dir = BARK_VOICES_DIR

    if voice_id is None:
        voice_id = uuid.uuid4().hex[:8]

    output_path = output_dir / f"voice_{voice_id}.npz"

    try:
        voice_features = extract_voice_features(
            audio_path, device=device, verbose=verbose
        )

        if voice_features is None:
            if verbose:
                print(f"[BarkVoiceCloner] ⚠️ Nepodařilo se extrahovat voice features")
            return None

        np.savez(
            str(output_path),
            semantic_prompt=voice_features["semantic_prompt"],
            coarse_prompt=voice_features["coarse_prompt"],
            fine_prompt=voice_features["fine_prompt"],
        )

        if verbose:
            print(f"[BarkVoiceCloner] Uloženo: {output_path}")

        return str(output_path)

    except Exception as e:
        if verbose:
            print(f"[BarkVoiceCloner] ⚠️ Chyba při vytváření NPZ: {e}")
        return None


def generate_voice_clone_path(
    audio_path: str, temp: bool = True, device: str = "cpu", verbose: bool = True
) -> Optional[str]:
    """
    Generate a path to use as history_prompt for Bark voice cloning.

    This is the main function to call from bark_engine.py.
    It will:
    1. Extract voice features from the audio
    2. Save them to a temporary NPZ file
    3. Return the path to use as history_prompt

    Args:
        audio_path: Path to the reference audio file
        temp: Whether to use temporary directory (auto-cleanup) or persistent storage
        device: Device for inference
        verbose: Whether to print progress

    Returns:
        Path to NPZ file for use as history_prompt, or None on error
    """
    if temp:
        output_dir = TEMP_DIR
    else:
        output_dir = BARK_VOICES_DIR

    return create_voice_npz(
        audio_path=audio_path, output_dir=output_dir, device=device, verbose=verbose
    )


def cleanup_temp_voices(max_age_hours: int = 24) -> int:
    """
    Clean up temporary voice NPZ files older than max_age_hours.

    Args:
        max_age_hours: Maximum age in hours

    Returns:
        Number of files deleted
    """
    import time

    deleted = 0
    current_time = time.time()

    if not TEMP_DIR.exists():
        return 0

    for npz_file in TEMP_DIR.glob("voice_*.npz"):
        file_age_hours = (current_time - npz_file.stat().st_mtime) / 3600
        if file_age_hours > max_age_hours:
            try:
                npz_file.unlink()
                deleted += 1
            except Exception:
                pass

    if deleted > 0:
        print(f"[BarkVoiceCloner] Smazáno {deleted} starých voice souborů")

    return deleted


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python bark_voice_cloner.py <audio_file>")
        sys.exit(1)

    audio_file = sys.argv[1]
    if not Path(audio_file).exists():
        print(f"Soubor neexistuje: {audio_file}")
        sys.exit(1)

    npz_path = generate_voice_clone_path(audio_file, verbose=True)
    if npz_path:
        print(f"✅ Voice NPZ vytvořen: {npz_path}")
    else:
        print("❌ Nepodařilo se vytvořit voice NPZ")
        sys.exit(1)
