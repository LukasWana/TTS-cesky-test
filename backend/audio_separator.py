"""
Modul pro separaci hlasu od pozadí pomocí Demucs
"""
import logging
from pathlib import Path
from typing import Tuple, Optional
import soundfile as sf
import torch
import numpy as np

from backend.config import DEVICE, TARGET_SAMPLE_RATE

logger = logging.getLogger(__name__)


def separate_vocals(
    input_path: str,
    output_path: str,
    model_name: str = "mdx_extra"
) -> Tuple[bool, Optional[str]]:
    """
    Separuje vokály od instrumentálu pomocí Demucs

    Args:
        input_path: Cesta k vstupnímu audio souboru
        output_path: Cesta k výstupnímu souboru (pouze vokály)
        model_name: Název Demucs modelu
            - mdx_extra: Nejlepší kvalita (~1.5 GB, pomalejší, doporučeno pro 6GB+ VRAM)
            - htdemucs_ft: Dobrá kvalita (~1 GB, rychlý)
            - htdemucs: Základní kvalita (~1 GB, nejrychlejší)

    Returns:
        (success, error_message)
    """
    try:
        from demucs.pretrained import get_model
        from demucs.apply import apply_model
        from demucs.audio import convert_audio

        logger.info(f"Začínám separaci vokálů pomocí Demucs (model: {model_name}, device: {DEVICE})")

        # Načtení modelu
        model = get_model(model_name)
        model.eval()

        # Přesunout model na správné zařízení
        device = torch.device(DEVICE)
        model = model.to(device)

        # Načtení audio pomocí soundfile
        wav, sr = sf.read(input_path, always_2d=False)
        logger.info(f"Načteno audio: shape={wav.shape if hasattr(wav, 'shape') else len(wav)}, sample rate: {sr} Hz")

        # Konverze na numpy array pokud není
        if not isinstance(wav, np.ndarray):
            wav = np.array(wav)

        # Zpracování stereo/mono - soundfile vrací:
        # - 1D array pro mono
        # - 2D array (channels, samples) pro stereo/multi-channel
        if wav.ndim == 1:
            # Mono - převést na (1, samples)
            wav = wav[np.newaxis, :]
        elif wav.ndim == 2:
            # Stereo/multi-channel - soundfile vrací (samples, channels)
            # Musíme transponovat na (channels, samples)
            if wav.shape[0] < wav.shape[1]:
                # Pokud máme více samples než channels, transponovat
                wav = wav.T

        # Omezit na maximálně 2 kanály (stereo)
        if wav.shape[0] > 2:
            wav = wav[:2]
        elif wav.shape[0] == 1:
            # Duplikovat mono na stereo
            wav = np.vstack([wav, wav])

        # Konverze na tensor
        wav = torch.from_numpy(wav).float()

        # Konverze na správný sample rate pro model
        wav = convert_audio(wav, sr, model.sample_rate, model.chin)
        logger.info(f"Audio konvertováno na {model.sample_rate} Hz pro model")

        # Přesunout na správné zařízení
        wav = wav.to(device)

        # Separace
        logger.info("Provádím separaci...")
        with torch.no_grad():
            # apply_model očekává tensor shape (batch, channels, samples)
            # wav má shape (channels, samples), přidáme batch dimenzi
            wav_batch = wav.unsqueeze(0)  # (1, channels, samples)

            # Volání apply_model
            sources = apply_model(model, wav_batch, device=device, shifts=1, split=True, overlap=0.25, progress=False)
            # sources shape: [batch, num_sources, channels, samples]
            # Pro htdemucs: [1, 4, channels, samples] - vocals, drums, bass, other

            # Odstranit batch dimenzi
            sources = sources[0]  # (num_sources, channels, samples)

        logger.info(f"Separace dokončena, shape: {sources.shape}")

        # Extrahovat vokály (první zdroj)
        vocals = sources[0].cpu().numpy()

        # Konverze stereo na mono pokud je potřeba
        if vocals.ndim == 2:
            if vocals.shape[0] == 2:
                # Stereo - převést na mono
                vocals = vocals.mean(axis=0)
            elif vocals.shape[1] == 2:
                vocals = vocals.mean(axis=1)

        # Normalizace - zabránit clippingu
        max_val = abs(vocals).max()
        if max_val > 0:
            # Normalizovat na 95% max hodnoty pro bezpečnost
            vocals = vocals / max_val * 0.95
            logger.info(f"Audio normalizováno, max hodnota: {max_val:.4f}")

        # Konverze sample rate na TARGET_SAMPLE_RATE pokud je potřeba
        if model.sample_rate != TARGET_SAMPLE_RATE:
            import librosa
            vocals = librosa.resample(vocals, orig_sr=model.sample_rate, target_sr=TARGET_SAMPLE_RATE)
            logger.info(f"Sample rate konvertován z {model.sample_rate} na {TARGET_SAMPLE_RATE} Hz")

        # Uložení
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
        sf.write(output_path, vocals, TARGET_SAMPLE_RATE)

        logger.info(f"Separované vokály uloženy do: {output_path}")
        return True, None

    except ImportError as e:
        error_msg = "Demucs není nainstalován. Nainstalujte pomocí: pip install demucs"
        logger.error(f"{error_msg}: {str(e)}")
        return False, error_msg
    except Exception as e:
        error_msg = f"Chyba při separaci vokálů: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg

