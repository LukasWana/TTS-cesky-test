"""
Bark engine – generování řeči, hudby a zvuků pomocí Suno AI Bark modelu.

Implementace používá oficiální bark knihovnu (suno-ai/bark).

- Lazy import bark (backend se spustí i bez toho; chyba až při použití).
- Ukládá WAV do outputs/ (OUTPUTS_DIR), takže se dá přehrát přes existující /api/audio/{filename}.
"""

from __future__ import annotations

import os
import threading
import uuid
from pathlib import Path
from typing import Optional
import numpy as np

# REMOVED: import torch
import soundfile as sf

from backend.config import OUTPUTS_DIR, OUTPUT_HEADROOM_DB, get_device
from backend.progress_manager import ProgressManager


class BarkEngine:
    def __init__(self):
        self._lock = threading.Lock()
        self._model_loaded = False
        self._model_size: Optional[str] = None
        self._model_mode: Optional[str] = None
        self._offload_cpu: Optional[bool] = None
        self._device: Optional[str] = None
        self._sample_rate: int = 24000  # Bark používá 24 kHz

    def _resolve_model_size(self, model_size: str) -> str:
        size = (model_size or "small").strip().lower()
        if size not in ("small", "large"):
            size = "small"
        return size

    def _resolve_model_mode(self, model_mode: Optional[str]) -> str:
        """
        Režim načtení Bark submodelů:
        - auto: zachová staré chování (small => vše small, large => vše large)
        - full: vše large
        - mixed: text large, ostatní small (šetří VRAM)
        - small: vše small
        """
        mm = (
            (model_mode or os.getenv("BARK_MODEL_MODE", "auto") or "auto")
            .strip()
            .lower()
        )
        if mm not in ("auto", "full", "mixed", "small"):
            mm = "auto"
        return mm

    def _ensure_loaded(
        self,
        model_size: str,
        *,
        model_mode: Optional[str] = None,
        offload_cpu: Optional[bool] = None,
        job_id: Optional[str] = None,
    ) -> None:
        target = self._resolve_model_size(model_size)
        mode = self._resolve_model_mode(model_mode)
        # offload_cpu: explicitní parametr má přednost, jinak env SUNO_OFFLOAD_CPU
        eff_offload = (
            bool(offload_cpu)
            if offload_cpu is not None
            else (os.getenv("SUNO_OFFLOAD_CPU", "False").lower() == "true")
        )
        with self._lock:
            if (
                self._model_loaded
                and self._model_size == target
                and self._model_mode == mode
                and self._offload_cpu == eff_offload
            ):
                if job_id:
                    ProgressManager.update(
                        job_id,
                        percent=10,
                        stage="bark",
                        message="Model je již v paměti, začínám generovat…",
                    )
                return

            if job_id:
                ProgressManager.update(
                    job_id,
                    percent=5,
                    stage="bark",
                    message=f"Načítám Bark model ({target}, mode={mode}, offload_cpu={eff_offload})…",
                )

            try:
                from bark import SAMPLE_RATE, preload_models
                # Bark používá preload_models() místo explicitního modelu
                # Podporuje text_use_small=True/False pro small/large model
                #
                # Pozn.: API Bark se mezi verzemi mění, proto voláme opatrně:
                # - nejprve zkusíme "novější" signature s coarse/fine/codec + offload_cpu
                # - pak fallback jen na text_use_small

                # Nastav env pro kompatibilitu (některé verze Bark čtou env místo kwargs)
                os.environ["SUNO_OFFLOAD_CPU"] = "True" if eff_offload else "False"

                if mode == "small":
                    text_use_small = True
                    coarse_use_small = True
                    fine_use_small = True
                    codec_use_small = True
                elif mode == "full":
                    text_use_small = False
                    coarse_use_small = False
                    fine_use_small = False
                    codec_use_small = False
                elif mode == "mixed":
                    # když uživatel chce small model_size, drž vše small
                    if target == "small":
                        text_use_small = True
                        coarse_use_small = True
                        fine_use_small = True
                        codec_use_small = True
                    else:
                        # text large, zbytek small (šetří VRAM, kvalita často téměř jako full)
                        text_use_small = False
                        coarse_use_small = True
                        fine_use_small = True
                        codec_use_small = True
                else:
                    # auto: zachovej původní chování podle model_size
                    text_use_small = target == "small"
                    coarse_use_small = target == "small"
                    fine_use_small = target == "small"
                    codec_use_small = target == "small"

                try:
                    preload_models(
                        text_use_small=text_use_small,
                        coarse_use_small=coarse_use_small,
                        fine_use_small=fine_use_small,
                        codec_use_small=codec_use_small,
                        offload_cpu=eff_offload,
                    )
                except TypeError:
                    # starší bark: typicky jen text_use_small
                    preload_models(text_use_small=text_use_small)
                self._sample_rate = SAMPLE_RATE
            except ImportError as e:
                raise RuntimeError(
                    "Bark závislosti nejsou nainstalované. Nainstalujte: pip install git+https://github.com/suno-ai/bark.git"
                ) from e
            except Exception as e:
                raise RuntimeError(f"Chyba při načítání Bark modelu: {e}") from e

            import torch  # Defer import

            device = (
                get_device()
                if get_device() in ("cpu", "cuda")
                else ("cuda" if torch.cuda.is_available() else "cpu")
            )
            self._model_loaded = True
            self._model_size = target
            self._model_mode = mode
            self._offload_cpu = eff_offload
            self._device = device

    def generate(
        self,
        text: str,
        *,
        model_size: str = "small",
        model_mode: Optional[str] = None,
        offload_cpu: Optional[bool] = None,
        temperature: float = 0.7,
        seed: Optional[int] = None,
        duration_s: Optional[float] = None,
        job_id: Optional[str] = None,
        target_headroom_db: Optional[float] = None,
        history_prompt: Optional[str] = None,
    ) -> str:
        """
        Generuje audio z textu pomocí Bark modelu.

        Args:
            text: Textový prompt (může obsahovat speciální tokeny jako [smích], [hudba], [pláč])
            model_size: Velikost modelu ("small" nebo "large")
            temperature: Teplota pro generování (vyšší = kreativnější)
            seed: Seed pro reprodukovatelnost
            duration_s: Požadovaná délka v sekundách (None = použít výchozí ~14s, pokud je delší, segment se zacyklí)
            history_prompt: Cesta k referenčnímu WAV souboru pro klonování hlasu (None = výchozí hlas)

        Returns:
            Cesta k vygenerovanému WAV souboru
        """
        if not text or not text.strip():
            raise ValueError("Textový prompt je prázdný")

        self._ensure_loaded(
            model_size, model_mode=model_mode, offload_cpu=offload_cpu, job_id=job_id
        )

        if seed is not None:
            s = int(seed)
            torch.manual_seed(s)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(s)

        if job_id:
            ProgressManager.update(
                job_id, percent=15, stage="bark", message="Generuji audio…"
            )

        try:
            from bark import generate_audio, SAMPLE_RATE
        except ImportError:
            raise RuntimeError("Bark knihovna není nainstalovaná")

        print(
            f"[Bark] Start generování: text='{text[:50]}...', model={model_size}, device={self._device}"
        )

        npz_history_prompt = None
        temp_npz_path = None

        if history_prompt and Path(history_prompt).exists():
            file_ext = Path(history_prompt).suffix.lower()
            if file_ext == ".npz":
                npz_history_prompt = str(history_prompt)
                print(
                    f"[Bark] Používám existující NPZ voice prompt: {npz_history_prompt}"
                )
            else:
                try:
                    from backend.bark_voice_cloner import generate_voice_clone_path

                    print(f"[Bark] Extrakce voice features z: {history_prompt}")
                    npz_history_prompt = generate_voice_clone_path(
                        str(history_prompt),
                        temp=True,
                        device=self._device,
                        verbose=True,
                    )
                    if npz_history_prompt:
                        temp_npz_path = npz_history_prompt
                        print(f"[Bark] Voice NPZ vytvořen: {npz_history_prompt}")
                    else:
                        print(
                            f"[Bark] ⚠️ Nepodařilo se extrahovat voice features, použije se výchozí hlas"
                        )
                except ImportError as e:
                    print(f"[Bark] ⚠️ Voice cloner není dostupný: {e}")
                except Exception as e:
                    import traceback

                    print(f"[Bark] ⚠️ Chyba při voice cloningu: {e}")
                    print(traceback.format_exc())

        # Generování audia
        audio_array = generate_audio(
            text,
            history_prompt=npz_history_prompt,
            text_temp=temperature,
            waveform_temp=temperature,
            output_full=False,
        )

        print("[Bark] Audio data vygenerována (v RAM).")

        if job_id:
            ProgressManager.update(
                job_id, percent=92, stage="bark", message="Ukládám WAV…"
            )

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
                    ProgressManager.update(
                        job_id,
                        percent=90,
                        stage="bark",
                        message="Upravuji délku (zacyklení)…",
                    )

                from backend.audio_mix_utils import (
                    LoadedAudio,
                    match_length_and_channels,
                )

                # Vytvoříme LoadedAudio objekt pro použití match_length_and_channels
                audio_obj = LoadedAudio(y=audio_array, sr=SAMPLE_RATE)

                # Použijeme match_length_and_channels pro zacyklení (vrací np.ndarray)
                looped_audio = match_length_and_channels(
                    audio_obj,
                    target_len=target_samples,
                    target_channels=1,
                    loop=True,
                    crossfade_ms=500,  # 0.5s crossfade pro plynulé zacyklení
                )
                audio_array = looped_audio
                print(
                    f"[Bark] Audio zacykleno z {current_samples / SAMPLE_RATE:.1f}s na {target_samples / SAMPLE_RATE:.1f}s"
                )
            elif target_samples < current_samples:
                # Kratší než generované - oříznout
                audio_array = audio_array[:target_samples]
                print(
                    f"[Bark] Audio oříznuto z {current_samples / SAMPLE_RATE:.1f}s na {target_samples / SAMPLE_RATE:.1f}s"
                )

        # Aplikovat headroom (pokud je zadán)
        if target_headroom_db is not None:
            try:
                final_headroom_db = target_headroom_db
                if final_headroom_db is not None:
                    peak = (
                        float(np.max(np.abs(audio_array)))
                        if audio_array is not None and len(audio_array)
                        else 0.0
                    )
                    if peak > 0:
                        if float(final_headroom_db) < 0:
                            target_peak = 10 ** (float(final_headroom_db) / 20.0)
                        else:
                            target_peak = 0.999
                        # Headroom jako "ceiling": pouze ztlumit, nikdy nezesilovat
                        if peak > target_peak:
                            audio_array = audio_array * (target_peak / peak)
                    if not np.isfinite(audio_array).all():
                        audio_array = np.nan_to_num(
                            audio_array, nan=0.0, posinf=0.0, neginf=0.0
                        )
                    print(
                        f"[Bark] Headroom ceiling: {final_headroom_db} dB (aplikováno jen pokud peak přesáhl cíl)"
                    )
            except Exception as e:
                print(f"[Bark] ⚠️ Headroom selhal: {e}")

        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"bark_{uuid.uuid4().hex[:10]}.wav"
        out_path = OUTPUTS_DIR / filename

        sf.write(str(out_path), audio_array, SAMPLE_RATE)

        if temp_npz_path and Path(temp_npz_path).exists():
            try:
                Path(temp_npz_path).unlink()
                print(f"[Bark] Smazán dočasný voice NPZ: {temp_npz_path}")
            except Exception as e:
                print(f"[Bark] ⚠️ Nepodařilo se smazat dočasný NPZ: {e}")

        # Cleanup VRAM
        if torch.cuda.is_available():
            try:
                torch.cuda.empty_cache()
            except Exception:
                pass

        return str(out_path)
