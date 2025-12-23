"""
Bark engine – generování řeči, hudby a zvuků pomocí Suno AI Bark modelu.

Implementace používá oficiální bark knihovnu (suno-ai/bark).

- Lazy import bark (backend se spustí i bez toho; chyba až při použití).
- Ukládá WAV do outputs/ (OUTPUTS_DIR), takže se dá přehrát přes existující /api/audio/{filename}.
"""

from __future__ import annotations

import threading
import uuid
from pathlib import Path
from typing import Optional
import numpy as np

import torch
import soundfile as sf

from backend.config import OUTPUTS_DIR, DEVICE
from backend.progress_manager import ProgressManager


class BarkEngine:
    def __init__(self):
        self._lock = threading.Lock()
        self._model_loaded = False
        self._model_size: Optional[str] = None
        self._device: Optional[str] = None
        self._sample_rate: int = 24000  # Bark používá 24 kHz

    def _resolve_model_size(self, model_size: str) -> str:
        size = (model_size or "small").strip().lower()
        if size not in ("small", "large"):
            size = "small"
        return size

    def _ensure_loaded(self, model_size: str, job_id: Optional[str] = None) -> None:
        target = self._resolve_model_size(model_size)
        with self._lock:
            if self._model_loaded and self._model_size == target:
                if job_id:
                    ProgressManager.update(job_id, percent=10, stage="bark", message="Model je již v paměti, začínám generovat…")
                return

            if job_id:
                ProgressManager.update(job_id, percent=5, stage="bark", message=f"Načítám Bark model ({target})…")

            try:
                from bark import SAMPLE_RATE, preload_models
                # Bark používá preload_models() místo explicitního modelu
                # Podporuje text_use_small=True/False pro small/large model
                preload_models(text_use_small=(target == "small"))
                self._sample_rate = SAMPLE_RATE
            except ImportError as e:
                raise RuntimeError(
                    "Bark závislosti nejsou nainstalované. Nainstalujte: pip install git+https://github.com/suno-ai/bark.git"
                ) from e
            except Exception as e:
                raise RuntimeError(f"Chyba při načítání Bark modelu: {e}") from e

            device = DEVICE if DEVICE in ("cpu", "cuda") else ("cuda" if torch.cuda.is_available() else "cpu")
            self._model_loaded = True
            self._model_size = target
            self._device = device

    def generate(
        self,
        text: str,
        *,
        model_size: str = "small",
        temperature: float = 0.7,
        seed: Optional[int] = None,
        duration_s: Optional[float] = None,
        job_id: Optional[str] = None,
    ) -> str:
        """
        Generuje audio z textu pomocí Bark modelu.

        Args:
            text: Textový prompt (může obsahovat speciální tokeny jako [smích], [hudba], [pláč])
            model_size: Velikost modelu ("small" nebo "large")
            temperature: Teplota pro generování (vyšší = kreativnější)
            seed: Seed pro reprodukovatelnost
            duration_s: Požadovaná délka v sekundách (None = použít výchozí ~14s, pokud je delší, segment se zacyklí)

        Returns:
            Cesta k vygenerovanému WAV souboru
        """
        if not text or not text.strip():
            raise ValueError("Textový prompt je prázdný")

        self._ensure_loaded(model_size, job_id=job_id)

        if seed is not None:
            s = int(seed)
            torch.manual_seed(s)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(s)

        if job_id:
            ProgressManager.update(job_id, percent=15, stage="bark", message="Generuji audio…")

        try:
            from bark import generate_audio, SAMPLE_RATE
        except ImportError:
            raise RuntimeError("Bark knihovna není nainstalovaná")

        print(f"[Bark] Start generování: text='{text[:50]}...', model={model_size}, device={self._device}")

        # Generování audia
        audio_array = generate_audio(
            text,
            history_prompt=None,  # Můžete přidat podporu pro history prompt
            text_temp=temperature,
            waveform_temp=temperature,
            output_full=False,  # Vrací pouze audio array
        )

        print("[Bark] Audio data vygenerována (v RAM).")

        if job_id:
            ProgressManager.update(job_id, percent=92, stage="bark", message="Ukládám WAV…")

        # Převedení na numpy array a normalizace
        if isinstance(audio_array, torch.Tensor):
            audio_array = audio_array.detach().cpu().numpy()

        # Zajištění správného formátu (mono, float32)
        if audio_array.ndim == 1:
            audio_array = audio_array[:, None]  # (T,) -> (T, 1)
        elif audio_array.ndim == 2 and audio_array.shape[0] < audio_array.shape[1]:
            audio_array = audio_array.T  # (C, T) -> (T, C)

        # Normalizace do rozsahu [-1, 1]
        audio_array = np.clip(audio_array, -1.0, 1.0)

        # Upravit délku pokud je požadováno
        if duration_s is not None and duration_s > 0:
            target_samples = int(duration_s * SAMPLE_RATE)
            current_samples = audio_array.shape[0]

            if target_samples > current_samples:
                # Delší než generované - zacyklit
                if job_id:
                    ProgressManager.update(job_id, percent=90, stage="bark", message="Upravuji délku (zacyklení)…")

                from backend.audio_mix_utils import LoadedAudio, match_length_and_channels
                # Vytvoříme LoadedAudio objekt pro použití match_length_and_channels
                audio_obj = LoadedAudio(y=audio_array, sr=SAMPLE_RATE)

                # Použijeme match_length_and_channels pro zacyklení (vrací np.ndarray)
                looped_audio = match_length_and_channels(
                    audio_obj,
                    target_len=target_samples,
                    target_channels=1,
                    loop=True,
                    crossfade_ms=500  # 0.5s crossfade pro plynulé zacyklení
                )
                audio_array = looped_audio
                print(f"[Bark] Audio zacykleno z {current_samples/SAMPLE_RATE:.1f}s na {target_samples/SAMPLE_RATE:.1f}s")
            elif target_samples < current_samples:
                # Kratší než generované - oříznout
                audio_array = audio_array[:target_samples]
                print(f"[Bark] Audio oříznuto z {current_samples/SAMPLE_RATE:.1f}s na {target_samples/SAMPLE_RATE:.1f}s")

        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"bark_{uuid.uuid4().hex[:10]}.wav"
        out_path = OUTPUTS_DIR / filename

        sf.write(str(out_path), audio_array, SAMPLE_RATE)

        # Cleanup VRAM
        if torch.cuda.is_available():
            try:
                torch.cuda.empty_cache()
            except Exception:
                pass

        return str(out_path)


