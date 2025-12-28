"""
Audio post-processing pro TTS výstupy
"""
import os
import subprocess
import logging
from pathlib import Path
from typing import Optional, Callable
import numpy as np

import librosa
import soundfile as sf

from backend.audio_enhancer import AudioEnhancer
from backend.vocoder_hifigan import get_hifigan_vocoder
from backend.audio_processor import AudioProcessor
from backend.config import (
    ENABLE_AUDIO_ENHANCEMENT,
    AUDIO_ENHANCEMENT_PRESET,
    OUTPUT_SAMPLE_RATE,
    OUTPUT_HEADROOM_DB,
)

logger = logging.getLogger(__name__)


class AudioPostProcessor:
    """Třída pro post-processing TTS audio výstupů"""

    @staticmethod
    def apply_enhancement(
        output_path: str,
        enhancement_preset: Optional[str],
        enable_enhancement: Optional[bool],
        enable_eq: bool,
        enable_denoiser: bool,
        enable_compressor: bool,
        enable_deesser: bool,
        enable_normalization: bool,
        enable_trim: bool,
        enable_whisper: Optional[bool],
        whisper_intensity: Optional[float],
        enable_vad: Optional[bool],
        target_headroom_db: Optional[float],
        progress_callback: Optional[Callable[[float, str, str], None]] = None,
    ):
        """
        Aplikuje audio enhancement

        Args:
            output_path: Cesta k audio souboru
            enhancement_preset: Preset pro enhancement
            enable_enhancement: Zapnout enhancement
            enable_eq: Zapnout EQ
            enable_denoiser: Zapnout denoiser
            enable_compressor: Zapnout compressor
            enable_deesser: Zapnout deesser
            enable_normalization: Zapnout normalizaci
            enable_trim: Zapnout trim
            enable_whisper: Zapnout whisper efekt
            whisper_intensity: Intenzita whisper efektu
            enable_vad: Zapnout VAD
            target_headroom_db: Cílový headroom
            progress_callback: Callback pro progress
        """
        if not ENABLE_AUDIO_ENHANCEMENT or (enable_enhancement is not None and not enable_enhancement):
            return

        try:
            preset_to_use = enhancement_preset if enhancement_preset else AUDIO_ENHANCEMENT_PRESET

            # Progress callback wrapper
            def enhance_progress(percent: float, stage: str, message: str):
                if progress_callback:
                    mapped_percent = 68.0 + (percent / 100.0) * 20.0  # 68-88%
                    progress_callback(mapped_percent, "enhance", message)

            AudioEnhancer.enhance_output(
                audio_path=str(output_path),
                preset=preset_to_use,
                enable_eq=enable_eq,
                enable_noise_reduction=enable_denoiser,
                enable_compression=enable_compressor,
                enable_deesser=enable_deesser,
                enable_normalization=enable_normalization,
                enable_trim=enable_trim,
                enable_whisper=enable_whisper,
                whisper_intensity=whisper_intensity,
                enable_vad=enable_vad,
                target_headroom_db=target_headroom_db,
                progress_callback=enhance_progress,
            )
        except Exception as e:
            logger.warning(f"Audio enhancement failed: {e}, continuing with original audio")
            if progress_callback:
                progress_callback(88, "enhance", "Enhancement přeskočen (chyba)")

    @staticmethod
    def apply_hifigan_refinement(
        output_path: str,
        use_hifigan: bool,
        vocoder,
        hifigan_refinement_intensity: Optional[float],
        hifigan_normalize_output: Optional[bool],
        hifigan_normalize_gain: Optional[float],
        progress_callback: Optional[Callable[[float, str, str], None]] = None,
    ):
        """
        Aplikuje HiFi-GAN vocoder refinement

        Args:
            output_path: Cesta k audio souboru
            use_hifigan: Zapnout HiFi-GAN
            vocoder: HiFi-GAN vocoder instance
            hifigan_refinement_intensity: Intenzita refinement
            hifigan_normalize_output: Normalizovat výstup
            hifigan_normalize_gain: Gain pro normalizaci
            progress_callback: Callback pro progress
        """
        if not use_hifigan or not vocoder or not vocoder.is_available():
            return

        try:
            if progress_callback:
                progress_callback(93, "hifigan", "HiFi-GAN refinement…")

            logger.info("🚀 Aplikuji HiFi-GAN vocoder refinement...")
            audio, sr = librosa.load(output_path, sr=None)
            original_audio = audio.copy()

            # Výpočet mel-spectrogramu
            mel_params = vocoder.mel_params
            mel = librosa.feature.melspectrogram(
                y=audio,
                sr=sr,
                n_fft=mel_params["n_fft"],
                hop_length=mel_params["hop_length"],
                win_length=mel_params["win_length"],
                n_mels=mel_params["n_mels"],
                fmin=mel_params["fmin"],
                fmax=mel_params["fmax"]
            )

            # Log-mel transformace
            mel_log = np.log10(np.maximum(mel, 1e-5))

            # Resyntéza pomocí HiFi-GAN
            refined_audio = vocoder.vocode(
                mel_log,
                sample_rate=sr,
                original_audio=original_audio,
                refinement_intensity=hifigan_refinement_intensity,
                normalize_output=hifigan_normalize_output,
                normalize_gain=hifigan_normalize_gain
            )

            if refined_audio is not None:
                sf.write(output_path, refined_audio, sr)
                used_intensity = hifigan_refinement_intensity if hifigan_refinement_intensity is not None else 1.0
                intensity_str = f" (intensity: {used_intensity:.2f})" if used_intensity < 1.0 else ""
                logger.info(f"✅ HiFi-GAN refinement dokončen{intensity_str}")
            else:
                logger.warning("⚠️ HiFi-GAN vocoding vrátil None, refinement přeskočen")

        except Exception as e:
            logger.warning(f"⚠️ Warning: HiFi-GAN refinement selhal: {e}")

    @staticmethod
    def apply_speed_adjustment(
        output_path: str,
        speed: float,
        progress_callback: Optional[Callable[[float, str, str], None]] = None,
    ):
        """
        Aplikuje změnu rychlosti pomocí FFmpeg atempo nebo fallback

        Args:
            output_path: Cesta k audio souboru
            speed: Rychlost (0.5-2.0)
            progress_callback: Callback pro progress
        """
        speed_float = float(speed) if speed is not None else 1.0

        if abs(speed_float - 1.0) <= 0.001:
            return

        try:
            if progress_callback:
                progress_callback(95, "speed", f"Úprava rychlosti na {speed_float}x…")

            # Preferujeme FFmpeg atempo
            if AudioProcessor._check_ffmpeg():
                logger.info(f"🎚️  Aplikuji změnu rychlosti (tempo) přes FFmpeg atempo: {speed_float}x")
                tmp_path = f"{output_path}.tmp_speed.wav"
                cmd = [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(output_path),
                    "-filter:a",
                    f"atempo={speed_float}",
                    "-ar",
                    str(OUTPUT_SAMPLE_RATE),
                    tmp_path,
                ]
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                os.replace(tmp_path, str(output_path))
                logger.info("✅ Rychlost změněna (FFmpeg atempo)")
            else:
                raise FileNotFoundError("FFmpeg není dostupný")

        except Exception as e:
            # Fallback: resample (změní i výšku hlasu)
            try:
                logger.warning(
                    f"⚠️  FFmpeg atempo nelze použít ({e}). "
                    f"Použiji fallback přes resampling (změní i výšku): {speed_float}x"
                )
                audio, sr = librosa.load(output_path, sr=None)
                target_sr = max(8000, int(sr / speed_float))
                audio_rs = librosa.resample(audio, orig_sr=sr, target_sr=target_sr)
                sf.write(output_path, audio_rs, sr)
                logger.info("✅ Rychlost změněna (fallback resampling)")
            except Exception as e2:
                logger.warning(f"⚠️ Warning: Změna rychlosti selhala i ve fallbacku: {e2}, pokračuji bez změny rychlosti")

    @staticmethod
    def apply_headroom(
        output_path: str,
        target_headroom_db: Optional[float],
        progress_callback: Optional[Callable[[float, str, str], None]] = None,
    ):
        """
        Aplikuje finální headroom ceiling

        Args:
            output_path: Cesta k audio souboru
            target_headroom_db: Cílový headroom v dB
            progress_callback: Callback pro progress
        """
        try:
            if progress_callback:
                progress_callback(97, "final", "Finální úpravy (headroom)…")

            audio, sr = librosa.load(output_path, sr=None)
            final_headroom_db = target_headroom_db if target_headroom_db is not None else OUTPUT_HEADROOM_DB

            if final_headroom_db is not None:
                # Headroom funguje jako "ceiling" (strop)
                peak = float(np.max(np.abs(audio))) if audio is not None and len(audio) else 0.0
                if peak > 0:
                    if float(final_headroom_db) < 0:
                        target_peak = 10 ** (float(final_headroom_db) / 20.0)
                    else:
                        target_peak = 0.999

                    if peak > target_peak:
                        scale = target_peak / peak
                        audio = audio * scale
                        peak_after = float(np.max(np.abs(audio))) if audio is not None and len(audio) else 0.0
                        logger.debug(
                            f"🔉 Headroom ceiling detail: headroom_db={float(final_headroom_db):.1f} dB, "
                            f"peak_before={peak:.4f}, target_peak={target_peak:.4f}, scale={scale:.4f}, peak_after={peak_after:.4f}"
                        )
                    else:
                        logger.debug(
                            f"🔉 Headroom ceiling: headroom_db={float(final_headroom_db):.1f} dB, "
                            f"peak_before={peak:.4f} <= target_peak={target_peak:.4f} (bez změny)"
                        )

                if not np.isfinite(audio).all():
                    audio = np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0)
                else:
                    audio = np.clip(audio, -0.999, 0.999)

                sf.write(output_path, audio, sr)
                logger.info(f"🔉 Finální headroom ceiling: {final_headroom_db} dB (aplikováno jen pokud peak přesáhl cíl)")

        except Exception as e:
            logger.warning(f"⚠️ Warning: Finální headroom selhal: {e}")

    @staticmethod
    def process_audio(
        output_path: str,
        speed: float,
        enhancement_preset: Optional[str],
        enable_enhancement: Optional[bool],
        enable_vad: Optional[bool],
        use_hifigan: bool,
        vocoder,
        enable_normalization: bool,
        enable_denoiser: bool,
        enable_compressor: bool,
        enable_deesser: bool,
        enable_eq: bool,
        enable_trim: bool,
        enable_whisper: Optional[bool],
        whisper_intensity: Optional[float],
        target_headroom_db: Optional[float],
        hifigan_refinement_intensity: Optional[float],
        hifigan_normalize_output: Optional[bool],
        hifigan_normalize_gain: Optional[float],
        progress_callback: Optional[Callable[[float, str, str], None]] = None,
    ):
        """
        Kompletní audio post-processing pipeline

        Args:
            output_path: Cesta k audio souboru
            speed: Rychlost řeči
            enhancement_preset: Preset pro enhancement
            enable_enhancement: Zapnout enhancement
            enable_vad: Zapnout VAD
            use_hifigan: Použít HiFi-GAN
            vocoder: HiFi-GAN vocoder instance
            enable_normalization: Zapnout normalizaci
            enable_denoiser: Zapnout denoiser
            enable_compressor: Zapnout compressor
            enable_deesser: Zapnout deesser
            enable_eq: Zapnout EQ
            enable_trim: Zapnout trim
            enable_whisper: Zapnout whisper efekt
            whisper_intensity: Intenzita whisper efektu
            target_headroom_db: Cílový headroom
            hifigan_refinement_intensity: Intenzita HiFi-GAN refinement
            hifigan_normalize_output: Normalizovat HiFi-GAN výstup
            hifigan_normalize_gain: Gain pro HiFi-GAN normalizaci
            progress_callback: Callback pro progress
        """
        # 1. Audio enhancement
        AudioPostProcessor.apply_enhancement(
            output_path=output_path,
            enhancement_preset=enhancement_preset,
            enable_enhancement=enable_enhancement,
            enable_eq=enable_eq,
            enable_denoiser=enable_denoiser,
            enable_compressor=enable_compressor,
            enable_deesser=enable_deesser,
            enable_normalization=enable_normalization,
            enable_trim=enable_trim,
            enable_whisper=enable_whisper,
            whisper_intensity=whisper_intensity,
            enable_vad=enable_vad,
            target_headroom_db=target_headroom_db,
            progress_callback=progress_callback,
        )

        # 2. HiFi-GAN refinement (před změnou rychlosti)
        AudioPostProcessor.apply_hifigan_refinement(
            output_path=output_path,
            use_hifigan=use_hifigan,
            vocoder=vocoder,
            hifigan_refinement_intensity=hifigan_refinement_intensity,
            hifigan_normalize_output=hifigan_normalize_output,
            hifigan_normalize_gain=hifigan_normalize_gain,
            progress_callback=progress_callback,
        )

        # 3. Speed adjustment (po HiFi-GAN)
        AudioPostProcessor.apply_speed_adjustment(
            output_path=output_path,
            speed=speed,
            progress_callback=progress_callback,
        )

        # 4. Finální headroom (po všem)
        AudioPostProcessor.apply_headroom(
            output_path=output_path,
            target_headroom_db=target_headroom_db,
            progress_callback=progress_callback,
        )

        if progress_callback:
            progress_callback(96, "final", "Dokončuji…")

