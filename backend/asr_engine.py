"""
ASR (automatic speech recognition) pomocí Whisper přes Transformers.

- Nepřidáváme nové závislosti: používáme už existující `transformers` + `torch` + `librosa`.
- Optimalizace pro slovenštinu: vynucení decoder promptu pro jazyk "slovak".
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import torch
import librosa

from backend.config import DEVICE


_lock = threading.Lock()
_singleton = None


def _clean_ref_text(text: str) -> str:
    # Odstranit typické časové značky typu "(0:03)" na začátku řádků
    text = re.sub(r"(?m)^\s*\(\d{1,2}:\d{2}\)\s*", "", text)
    # Normalizace whitespace
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


@dataclass
class TranscribeResult:
    text: str
    cleaned_text: str
    language: str
    segments: List[Dict[str, Any]]


class ASREngine:
    """
    Lazy-loaded Whisper ASR přes HF Transformers pipeline.
    """

    def __init__(self, model_id: str = "openai/whisper-small"):
        self.model_id = model_id
        self._pipe = None
        self._processor = None
        self._device_index = 0 if (DEVICE == "cuda" and torch.cuda.is_available()) else -1

    def _ensure_loaded(self) -> None:
        if self._pipe is not None:
            return

        with _lock:
            if self._pipe is not None:
                return

            from transformers import (
                AutoModelForSpeechSeq2Seq,
                AutoProcessor,
                pipeline,
            )

            torch_dtype = torch.float16 if self._device_index >= 0 else torch.float32
            model = AutoModelForSpeechSeq2Seq.from_pretrained(
                self.model_id,
                torch_dtype=torch_dtype,
                low_cpu_mem_usage=True,
                use_safetensors=True,
            )

            processor = AutoProcessor.from_pretrained(self.model_id)

            self._pipe = pipeline(
                "automatic-speech-recognition",
                model=model,
                tokenizer=processor.tokenizer,
                feature_extractor=processor.feature_extractor,
                device=self._device_index,
            )
            self._processor = processor

    def transcribe_file(
        self,
        audio_path: str,
        *,
        language: str = "sk",
        task: str = "transcribe",
        return_timestamps: bool = True,
    ) -> TranscribeResult:
        """
        Přepis audia -> text + segmenty.

        language:
          - "sk" / "slovak" (optimalizace pro slovenštinu)
          - fallback: když je neznámý, necháme auto-detect
        """
        self._ensure_loaded()

        # Převést na 16 kHz mono (Whisper standard)
        audio, sr = librosa.load(audio_path, sr=16000, mono=True)

        generate_kwargs: Dict[str, Any] = {}
        lang = (language or "").strip().lower()
        if lang in ("sk", "slovak", "slovenstina", "slovenčina"):
            # Whisper HF používá jméno jazyka, ne kód
            forced = self._processor.get_decoder_prompt_ids(language="slovak", task=task)
            generate_kwargs["forced_decoder_ids"] = forced

        # Chunking pro delší audio
        result = self._pipe(
            {"array": audio, "sampling_rate": 16000},
            return_timestamps="chunk" if return_timestamps else False,
            chunk_length_s=30,
            stride_length_s=(5, 5),
            generate_kwargs=generate_kwargs,
        )

        text = str(result.get("text", "")).strip()
        cleaned = _clean_ref_text(text)

        segments: List[Dict[str, Any]] = []
        for ch in (result.get("chunks") or []):
            ts = ch.get("timestamp")
            segments.append(
                {
                    "start": ts[0] if isinstance(ts, (list, tuple)) and len(ts) > 0 else None,
                    "end": ts[1] if isinstance(ts, (list, tuple)) and len(ts) > 1 else None,
                    "text": _clean_ref_text(str(ch.get("text", ""))),
                }
            )

        return TranscribeResult(
            text=text,
            cleaned_text=cleaned,
            language=language,
            segments=segments,
        )


def get_asr_engine() -> ASREngine:
    global _singleton
    if _singleton is None:
        _singleton = ASREngine()
    return _singleton


