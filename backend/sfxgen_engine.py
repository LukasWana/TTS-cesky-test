"""
SFX engine – generování zvukových efektů (SFX) pomocí AudioGen z Meta AudioCraft.

Implementace používá audiocraft (volitelná závislost).
- Lazy import audiocraft (backend se spustí i bez toho; chyba až při použití).
- Ukládá WAV do outputs/ (OUTPUTS_DIR), takže se dá přehrát přes existující /api/audio/{filename}.
- Optimalizováno pro RTX 3060 6GB VRAM: doporučená délka 2-4 sekundy.
"""

from __future__ import annotations

import threading
import uuid
from pathlib import Path
from typing import Optional

import torch
import soundfile as sf

from backend.config import OUTPUTS_DIR, DEVICE
from backend.progress_manager import ProgressManager


class SfxGenEngine:
    def __init__(self):
        self._lock = threading.Lock()
        self._model = None
        self._model_name: Optional[str] = None
        self._device: Optional[str] = None
        self._sample_rate: int = 32000

    def _resolve_model_name(self, model_size: str) -> str:
        """
        AudioGen má modely: facebook/audiogen-medium, facebook/audiogen-small
        Pro 6GB VRAM doporučeno medium (pokud to jde) nebo small.
        """
        size = (model_size or "medium").strip().lower()
        if size not in ("small", "medium"):
            size = "medium"
        return f"facebook/audiogen-{size}"

    def _ensure_loaded(self, model_size: str, job_id: Optional[str] = None) -> None:
        target = self._resolve_model_name(model_size)
        with self._lock:
            if self._model is not None and self._model_name == target:
                if job_id:
                    ProgressManager.update(job_id, percent=10, stage="sfxgen", message="Model je již v paměti, začínám generovat…")
                return

            if job_id:
                ProgressManager.update(job_id, percent=5, stage="sfxgen", message=f"Načítám AudioGen model {target}…")

            try:
                # Zkus import kompletního AudioGen modulu
                from audiocraft.models import AudioGen  # type: ignore
            except ImportError as e:
                # Diagnostika - zkus různé scénáře
                error_msg = "AudioGen závislosti nejsou správně nainstalované.\n\n"

                try:
                    import audiocraft
                    audiocraft_version = getattr(audiocraft, '__version__', 'unknown')
                    error_msg += f"✓ audiocraft {audiocraft_version} je nainstalováno\n"
                    error_msg += "✗ ale chybí modul audiocraft.models.AudioGen\n"
                    error_msg += "\nŘešení:\n"
                    error_msg += "1. pip uninstall audiocraft\n"
                    error_msg += "2. pip install audiocraft\n"
                    error_msg += "3. Nebo zkuste: pip install audiocraft --no-deps\n"
                except ImportError:
                    error_msg += "✗ audiocraft není vůbec nainstalováno\n"
                    error_msg += "\nŘešení:\n"
                    error_msg += "pip install audiocraft\n"

                error_msg += "\nPozn.: TTS a MusicGen fungují i bez této závislosti."
                raise RuntimeError(error_msg) from e

            device = DEVICE if DEVICE in ("cpu", "cuda") else ("cuda" if torch.cuda.is_available() else "cpu")

            try:
                model = AudioGen.get_pretrained(target)
                model.set_generation_params(duration=4)  # Default 4s pro SFX
                model.to(device)
                model.eval()
            except Exception as e:
                raise RuntimeError(
                    f"Chyba při načítání AudioGen modelu {target}: {str(e)}\n"
                    "Zkontrolujte, že máte dostatek VRAM (pro medium doporučeno 6GB+)."
                ) from e

            # AudioGen typicky používá 32kHz sample rate
            sr = 32000
            try:
                # Zkus získat sample rate z modelu
                if hasattr(model, "sample_rate"):
                    sr = int(model.sample_rate)
                elif hasattr(model, "cfg") and hasattr(model.cfg, "sample_rate"):
                    sr = int(model.cfg.sample_rate)
            except Exception:
                sr = 32000

            self._model = model
            self._model_name = target
            self._device = device
            self._sample_rate = sr

    def generate(
        self,
        prompt: str,
        *,
        duration_s: float = 3.0,
        temperature: float = 1.0,
        top_k: int = 250,
        top_p: float = 0.0,
        cfg_coef: float = 3.0,
        seed: Optional[int] = None,
        model_size: str = "medium",
        job_id: Optional[str] = None,
    ) -> str:
        """
        Generuje SFX zvukový efekt na základě textového popisu.

        Args:
            prompt: Textový popis zvukového efektu (např. "laser zap sound, sci-fi, clean")
            duration_s: Délka v sekundách (1-8, doporučeno 2-4 pro 6GB VRAM)
            temperature: Teplota pro sampling (0.0-2.0)
            top_k: Top-k sampling
            top_p: Top-p sampling
            cfg_coef: Classifier-free guidance coefficient (1.0-10.0)
            seed: Seed pro reprodukovatelnost
            model_size: "small" nebo "medium" (pro 6GB VRAM doporučeno medium, pokud to jde)
            job_id: ID jobu pro progress tracking

        Returns:
            Cesta k vygenerovanému WAV souboru
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt je prázdný")

        duration_s = float(duration_s)
        if not (1.0 <= duration_s <= 8.0):
            raise ValueError("duration musí být 1–8 sekund (pro 6GB VRAM doporučeno 2–4s)")

        temperature = float(temperature)
        if not (0.0 <= temperature <= 2.0):
            raise ValueError("temperature musí být 0.0–2.0")

        top_k = int(top_k)
        if top_k < 0:
            raise ValueError("top_k musí být >= 0")

        top_p = float(top_p)
        if not (0.0 <= top_p <= 1.0):
            raise ValueError("top_p musí být 0.0–1.0")

        cfg_coef = float(cfg_coef)
        if not (1.0 <= cfg_coef <= 10.0):
            raise ValueError("cfg_coef musí být 1.0–10.0")

        self._ensure_loaded(model_size, job_id=job_id)

        if seed is not None:
            s = int(seed)
            torch.manual_seed(s)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(s)

        if job_id:
            ProgressManager.update(job_id, percent=15, stage="sfxgen", message="Nastavuji generování SFX…")

        # Nastavit parametry generování
        self._model.set_generation_params(
            duration=duration_s,
            temperature=temperature,
            top_k=top_k if top_k > 0 else None,
            top_p=top_p if top_p > 0 else None,
            cfg_coef=cfg_coef,
        )

        print(f"[SfxGen] Start generování: prompt='{prompt[:50]}...', trvání={duration_s}s, device={self._device}")
        with torch.inference_mode():
            if job_id:
                ProgressManager.update(job_id, percent=25, stage="sfxgen", message="Generuji SFX…")

            # AudioGen.generate vrací tensor (batch, channels, samples) @ sample_rate
            # generate() bere list promptů a vrací tensor
            wav = self._model.generate([prompt], progress=True if job_id else False)
        print("[SfxGen] Audio data vygenerována (v RAM).")

        if job_id:
            ProgressManager.update(job_id, percent=92, stage="sfxgen", message="Ukládám WAV…")

        # AudioGen vrací (B, C, T) nebo (B, T) tensor
        wav0 = wav[0].detach().cpu().float()
        if wav0.ndim == 1:
            wav0 = wav0[:, None]  # (T, 1)
        elif wav0.ndim == 2:
            # (C, T) -> (T, C)
            if wav0.shape[0] <= 2 and wav0.shape[1] > wav0.shape[0]:
                wav0 = wav0.T
        wav_numpy = wav0.numpy()

        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"sfxgen_{uuid.uuid4().hex[:10]}.wav"
        out_path = OUTPUTS_DIR / filename

        sf.write(str(out_path), wav_numpy, self._sample_rate)

        # Cleanup VRAM
        if torch.cuda.is_available():
            try:
                torch.cuda.empty_cache()
            except Exception:
                pass

        return str(out_path)

