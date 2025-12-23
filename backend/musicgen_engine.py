"""
MusicGen engine – generování instrumentální hudby lokálně.

Implementace používá HuggingFace Transformers (facebook/musicgen-*) místo audiocraft,
aby to šlo instalovat na Windows bez kompilace PyAV/FFmpeg knihoven.

- Lazy import transformers (backend se spustí i bez toho; chyba až při použití).
- Ukládá WAV do outputs/ (OUTPUTS_DIR), takže se dá přehrát přes existující /api/audio/{filename}.
"""

from __future__ import annotations

import threading
import uuid
from pathlib import Path
from typing import Optional, Tuple

import torch
import soundfile as sf

from backend.config import OUTPUTS_DIR, DEVICE
from backend.progress_manager import ProgressManager


class MusicGenEngine:
    def __init__(self):
        self._lock = threading.Lock()
        self._model = None
        self._processor = None
        self._model_name: Optional[str] = None
        self._device: Optional[str] = None
        self._sample_rate: int = 32000

    def _resolve_model_name(self, model_size: str) -> str:
        size = (model_size or "small").strip().lower()
        if size not in ("small", "medium", "large"):
            size = "small"
        return f"facebook/musicgen-{size}"

    def _ensure_loaded(self, model_size: str, job_id: Optional[str] = None) -> None:
        target = self._resolve_model_name(model_size)
        with self._lock:
            if self._model is not None and self._model_name == target:
                if job_id:
                    ProgressManager.update(job_id, percent=10, stage="musicgen", message="Model je již v paměti, začínám generovat…")
                return

            if job_id:
                ProgressManager.update(job_id, percent=5, stage="musicgen", message=f"Načítám model {target}…")

            try:
                from transformers import AutoProcessor, MusicgenForConditionalGeneration  # type: ignore
            except Exception as e:
                raise RuntimeError(
                    "MusicGen závislosti nejsou nainstalované. Nainstalujte: pip install transformers accelerate sentencepiece"
                ) from e

            device = DEVICE if DEVICE in ("cpu", "cuda") else ("cuda" if torch.cuda.is_available() else "cpu")
            processor = AutoProcessor.from_pretrained(target)
            model = MusicgenForConditionalGeneration.from_pretrained(target)
            model.to(device)
            model.eval()

            sr = 32000
            try:
                sr = int(getattr(model.config, "audio_encoder", None).sampling_rate)  # type: ignore
            except Exception:
                try:
                    sr = int(getattr(model.config, "sampling_rate", 32000))
                except Exception:
                    sr = 32000

            self._model = model
            self._processor = processor
            self._model_name = target
            self._device = device
            self._sample_rate = sr

    def _duration_to_tokens(self, duration_s: float) -> int:
        """
        Transformers MusicGen typicky používá ~50 tokenů/s (viz HF example).
        """
        return max(1, int(round(float(duration_s) * 50)))

    def generate(
        self,
        prompt: str,
        *,
        duration_s: float = 12.0,
        temperature: float = 1.0,
        top_k: int = 250,
        top_p: float = 0.0,
        seed: Optional[int] = None,
        model_size: str = "small",
        job_id: Optional[str] = None,
    ) -> str:
        if not prompt or not prompt.strip():
            raise ValueError("Prompt je prázdný")

        duration_s = float(duration_s)
        if not (1.0 <= duration_s <= 30.0):
            raise ValueError("duration musí být 1–30 sekund")

        temperature = float(temperature)
        if not (0.0 <= temperature <= 2.0):
            raise ValueError("temperature musí být 0.0–2.0")

        top_k = int(top_k)
        if top_k < 0:
            raise ValueError("top_k musí být >= 0")

        top_p = float(top_p)
        if not (0.0 <= top_p <= 1.0):
            raise ValueError("top_p musí být 0.0–1.0")

        self._ensure_loaded(model_size, job_id=job_id)

        if seed is not None:
            s = int(seed)
            torch.manual_seed(s)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(s)

        if job_id:
            ProgressManager.update(job_id, percent=15, stage="musicgen", message="Nastavuji generování…")

        gen_top_k = top_k if top_k and top_k > 0 else None
        gen_top_p = top_p if top_p and top_p > 0 else None

        print(f"[MusicGen] Start generování: prompt='{prompt[:50]}...', trvání={duration_s}s, device={self._device}")
        with torch.inference_mode():
            if job_id:
                ProgressManager.update(job_id, percent=25, stage="musicgen", message="Generuji hudbu…")

            inputs = self._processor(text=[prompt], padding=True, return_tensors="pt")
            inputs = {k: v.to(self._device) for k, v in inputs.items()}

            # HF: délka je řízená max_new_tokens
            max_new_tokens = self._duration_to_tokens(duration_s)
            audio_values = self._model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                temperature=temperature,
                top_k=gen_top_k,
                top_p=gen_top_p,
            )
        print("[MusicGen] Audio data vygenerována (v RAM).")

        if job_id:
            ProgressManager.update(job_id, percent=92, stage="musicgen", message="Ukládám WAV…")

        # Transformers vrací (B, T) float waveform @ sample_rate
        wav0 = audio_values[0].detach().cpu().float().numpy()
        if wav0.ndim == 1:
            wav0 = wav0[:, None]  # (T, 1)
        elif wav0.ndim == 2:
            # (C, T) -> (T, C) (kdyby se někdy vrátilo multichannel)
            if wav0.shape[0] <= 2 and wav0.shape[1] > wav0.shape[0]:
                wav0 = wav0.T

        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"musicgen_{uuid.uuid4().hex[:10]}.wav"
        out_path = OUTPUTS_DIR / filename

        sf.write(str(out_path), wav0, self._sample_rate)

        # drobný cleanup VRAM
        if torch.cuda.is_available():
            try:
                torch.cuda.empty_cache()
            except Exception:
                pass

        return str(out_path)


