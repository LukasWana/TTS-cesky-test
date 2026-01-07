"""
F5-TTS Slovak Engine wrapper
Používá CLI f5-tts_infer-cli pro inference s slovenským modelem
"""
import uuid
import asyncio
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict
import shutil
import os

import backend.config as config
from backend.config import (
    DEVICE,
    OUTPUTS_DIR,
    F5_SLOVAK_MODEL_NAME,
    F5_SLOVAK_MODEL_DIR,
    F5_SLOVAK_DEFAULT_NFE,
    # F5_DEVICE, # Removed to avoid early access
    F5_OUTPUT_SAMPLE_RATE
)


class F5TTSSlovakEngine:
    """Wrapper pro F5-TTS slovenský engine (v1: přes CLI)"""

    def __init__(self):
        self._device = None
        self.is_loaded = False  # CLI nepotřebuje předběžné načtení modelu

    @property
    def device(self):
        if self._device is None:
            # Lazy import config variables to avoid triggering __getattr__ too early
            from backend.config import get_f5_device
            self._device = get_f5_device()
        return self._device
        # F5-TTS CLI očekává Hugging Face identifikátor (např. "petercheben/F5_TTS_Slovak")
        # a hledá config v f5_tts/configs/petercheben/F5_TTS_Slovak.yaml
        # Pokud model existuje lokálně, CLI ho stáhne z Hugging Face cache nebo použije lokální
        # POZNÁMKA: Pro správné fungování musí existovat config v f5_tts/configs/petercheben/F5_TTS_Slovak.yaml
        # nebo musí být config v adresáři modelu a musíme použít jiný formát
        self.model_name = F5_SLOVAK_MODEL_NAME
        self.model_dir = F5_SLOVAK_MODEL_DIR

    async def load_model(self):
        """Placeholder pro kompatibilitu s XTTS interface (CLI nepotřebuje předběžné načtení)"""
        self.is_loaded = True
        # Rychlá kontrola existence CLI (místo pomalého --help volání s timeoutem)
        # Na Windows může --help trvat >5s kvůli importům/warningům, takže kontrolujeme jen existenci exe
        try:
            import sys
            cli_path = shutil.which("f5-tts_infer-cli")
            if cli_path and Path(cli_path).exists():
                # CLI je dostupné
                pass
            else:
                # Zkus najít v běžných umístěních (venv/Scripts)
                venv_scripts = Path(sys.executable).parent / "f5-tts_infer-cli.exe"
                if not venv_scripts.exists():
                    print("[WARN] f5-tts_infer-cli nebyl nalezen. Ujistěte se, že je f5-tts nainstalován: pip install f5-tts")
        except Exception as e:
            print(f"[WARN] Ověření F5-TTS CLI selhalo: {e}")

    async def generate(
        self,
        text: str,
        speaker_wav: str,
        language: str = "sk",
        speed: float = 1.0,
        nfe_step: Optional[int] = None,
        cfg_strength: float = 2.0,
        sway_sampling_coef: float = -1.0,
        quality_mode: Optional[str] = None,
        seed: Optional[int] = None,
        enhancement_preset: Optional[str] = None,
        enable_vad: Optional[bool] = None,
        use_hifigan: bool = False,
        enable_normalization: bool = True,
        enable_denoiser: bool = True,
        enable_compressor: bool = True,
        enable_deesser: bool = True,
        enable_eq: bool = True,
        enable_trim: bool = True,
        enable_dialect_conversion: Optional[bool] = None,
        dialect_code: Optional[str] = None,
        dialect_intensity: float = 1.0,
        enable_whisper: bool = False,
        whisper_intensity: float = 1.0,
        target_headroom_db: Optional[float] = None,
        hifigan_refinement_intensity: Optional[float] = None,
        hifigan_normalize_output: Optional[bool] = None,
        hifigan_normalize_gain: Optional[float] = None,
        job_id: Optional[str] = None,
        ref_text: Optional[str] = None,  # Volitelně: přepis reference audio pro lepší kvalitu
        enable_enhancement: Optional[bool] = None,
    ) -> str:
        """
        Generuje řeč pomocí F5-TTS slovenského modelu

        Args:
            text: Text k syntéze
            speaker_wav: Cesta k referenčnímu audio souboru
            language: Jazyk (pouze "sk" aktivuje slovenské zpracování)
            speed: Rychlost řeči (aplikuje se jako post-processing)
            nfe_step: Počet kroků pro odebrání šumu (diffusion)
            cfg_strength: Síla navádění (Classifier-Free Guidance)
            sway_sampling_coef: Koeficient vzorkování (dynamika)
            quality_mode: Mapuje se na nfe_step pokud není zadáno
            seed: Seed pro reprodukovatelnost (pokud F5 podporuje)
            enhancement_preset: Preset pro audio enhancement
            enable_vad: Zapnout VAD
            use_hifigan: Použít HiFi-GAN
            enable_normalization: Normalizace
            enable_denoiser: Denoiser
            enable_compressor: Komprese
            enable_deesser: De-esser
            enable_eq: Equalizer
            enable_trim: Trim ticha
            enable_dialect_conversion: Převod na nářečí (není podporováno pro slovenštinu)
            dialect_code: Kód nářečí (není podporováno)
            dialect_intensity: Intenzita převodu (není podporováno)
            enable_whisper: Whisper efekt
            whisper_intensity: Intenzita whisper efektu
            target_headroom_db: Headroom v dB
            hifigan_refinement_intensity: HiFi-GAN intenzita
            hifigan_normalize_output: HiFi-GAN normalizace
            hifigan_normalize_gain: HiFi-GAN gain
            job_id: Job ID pro progress tracking
            ref_text: Přepis reference audio (volitelné, pro lepší kvalitu)

        Returns:
            Cesta k vygenerovanému WAV souboru
        """
        # Ověření existence reference audio
        if not Path(speaker_wav).exists():
            raise Exception(f"Reference audio file not found: {speaker_wav}")

        # Vytvoření výstupní cesty
        output_filename = f"{uuid.uuid4()}.wav"
        output_path = OUTPUTS_DIR / output_filename

        # Předzpracování textu (slovenský preprocessing)
        from backend.sk_pipeline import preprocess_slovak_text
        processed_text = preprocess_slovak_text(
            text,
            language,
            enable_dialect_conversion=enable_dialect_conversion,
            dialect_code=dialect_code,
            dialect_intensity=dialect_intensity
        )

        # Generování pomocí CLI
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._generate_sync_cli,
            processed_text,
            speaker_wav,
            str(output_path),
            ref_text,
            nfe_step,
            cfg_strength,
            sway_sampling_coef,
            job_id
        )

        # Post-processing (stejné jako XTTS)
        # Použijeme stejnou logiku jako XTTS pro konzistenci
        await self._apply_post_processing(
            str(output_path),
            speed,
            enhancement_preset,
            enable_vad,
            use_hifigan,
            enable_normalization,
            enable_denoiser,
            enable_compressor,
            enable_deesser,
            enable_eq,
            enable_trim,
            enable_whisper,
            whisper_intensity,
            target_headroom_db,
            hifigan_refinement_intensity,
            hifigan_normalize_output,
            hifigan_normalize_gain,
            job_id,
            enable_enhancement
        )

        return str(output_path)

    def _generate_sync_cli(
        self,
        text: str,
        ref_audio: str,
        output_path: str,
        ref_text: Optional[str],
        nfe_step: Optional[int],
        cfg_strength: float,
        sway_sampling_coef: float,
        job_id: Optional[str]
    ):
        """Synchronní generování přes F5-TTS CLI"""
        def _progress(pct: float, stage: str, msg: str):
            if not job_id:
                return
            try:
                from backend.progress_manager import ProgressManager
                ProgressManager.update(job_id, percent=pct, stage=stage, message=msg)
            except Exception:
                pass

        try:
            _progress(15, "f5_tts_slovak", "Generujem reč (F5-TTS Slovak)…")

            # Příprava CLI příkazu (preferujeme explicitní output file, ať nemusíme hledat nejnovější WAV)
            # Pozn.: CLI podporuje -o/--output_dir a -w/--output_file + --device + --nfe_step
            out_p = Path(output_path)

            # Najít cestu k f5-tts_infer-cli exe (může být v PATH nebo v venv/Scripts)
            import sys
            cli_exe = shutil.which("f5-tts_infer-cli")
            if not cli_exe or not Path(cli_exe).exists():
                # Zkus najít v venv/Scripts (kde se typicky instaluje)
                venv_scripts = Path(sys.executable).parent / "f5-tts_infer-cli.exe"
                if venv_scripts.exists():
                    cli_exe = str(venv_scripts)
                else:
                    raise FileNotFoundError(
                        "f5-tts_infer-cli nebyl nalezen.\n\n"
                        "Pro instalaci F5-TTS spusťte:\n"
                        "  pip install f5-tts\n\n"
                        "Nebo pro lokální vývoj (editable install):\n"
                        "  git clone https://github.com/SWivid/F5-TTS.git\n"
                        "  cd F5-TTS\n"
                        "  pip install -e .\n\n"
                        "Po instalaci restartujte backend server."
                    )

            # Slovenský checkpoint je uložen lokálně (stáhnutý z HF) – CLI si umí vzít ckpt/vocab explicitně.
            # To je robustnější než používat -m petercheben/F5_TTS_Slovak (které by vyžadovalo YAML config v f5_tts/configs/petercheben/...).
            ckpt_path = self.model_dir / "model_30000.safetensors"
            vocab_path = self.model_dir / "model_30000.txt"
            if not ckpt_path.exists():
                raise FileNotFoundError(
                    f"Chybí slovenský checkpoint: {ckpt_path}\n"
                    "Spusťte prosím instalaci modelu: install_f5tts_slovak_model.bat"
                )
            if not vocab_path.exists():
                raise FileNotFoundError(
                    f"Chybí slovenský vocab soubor: {vocab_path}\n"
                    "Spusťte prosím instalaci modelu: install_f5tts_slovak_model.bat"
                )

            # Model config použijeme z balíčku f5_tts (F5TTS_v1_Base je kompatibilní s naším wrapperem)
            import importlib.util
            spec = importlib.util.find_spec("f5_tts")
            if not spec or not spec.submodule_search_locations:
                raise RuntimeError("Nelze najít balíček f5_tts (find_spec). Je f5-tts nainstalován?")
            f5_base = Path(list(spec.submodule_search_locations)[0]).resolve()
            model_cfg_path = f5_base / "configs" / "F5TTS_v1_Base.yaml"
            if not model_cfg_path.exists():
                # fallback pro jiné verze balíčku
                model_cfg_path = f5_base / "configs" / "F5TTS_Base.yaml"
            if not model_cfg_path.exists():
                raise FileNotFoundError(f"Nenalezen model config v balíčku f5_tts: {model_cfg_path}")

            cmd = [
                cli_exe,
                # Použijeme vestavěné jméno modelu + explicitní ckpt/vocab/model_cfg pro slovenštinu
                "-m", "F5TTS_v1_Base",
                "-r", ref_audio,
                "-t", text,
                "-o", str(out_p.parent),
                "-w", out_p.name,
                "--ckpt_file", str(ckpt_path),
                "--vocab_file", str(vocab_path),
                "--model_cfg", str(model_cfg_path),
                "--device", str(self.device),
            ]

            # Určení NFE kroků
            actual_nfe = nfe_step
            if actual_nfe is None:
                actual_nfe = F5_SLOVAK_DEFAULT_NFE

            cmd.extend(["--nfe_step", str(actual_nfe)])
            cmd.extend(["--cfg_strength", str(cfg_strength)])
            cmd.extend(["--sway_sampling_coef", str(sway_sampling_coef)])

            # Přidat ref_text pokud je zadán (zlepšuje kvalitu)
            if ref_text:
                cmd.extend(["-s", ref_text])

            # F5-TTS CLI vytvoří výstupní soubor (obvykle pojmenovaný podle modelu nebo timestamp)
            # CLI nepodporuje explicitní --output, takže musíme najít nejnovější WAV soubor
            # Zaznamenáme čas před spuštěním CLI
            import time
            before_time = time.time()

            # Spustit CLI v OUTPUTS_DIR, aby výstup byl tam
            print(f"🔊 F5-TTS Slovak CLI: {' '.join(cmd)}")
            env = os.environ.copy()
            # Fix pro Windows cp1252 -> UTF-8 (jinak spadne na diakritice při printu v CLI)
            # Pokud je globálně nastavený PYTHONUTF8 na neplatnou hodnotu, Python spadne už při preinit.
            # Proto nejdřív smažeme starou hodnotu, pak nastavíme správnou.
            if "PYTHONUTF8" in env:
                del env["PYTHONUTF8"]
            env["PYTHONUTF8"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"
            # Fix pro PYTHONHASHSEED - musí být "random" nebo integer v rozsahu [0; 4294967295]
            # Pokud je nastaveno na neplatnou hodnotu (prázdný string, neplatné číslo), Python spadne při preinit.
            if "PYTHONHASHSEED" in env:
                hashseed_val = env["PYTHONHASHSEED"].strip()
                if hashseed_val == "":
                    # Prázdný string je neplatný
                    del env["PYTHONHASHSEED"]
                elif hashseed_val.lower() != "random":
                    # Zkusit parsovat jako integer
                    try:
                        hashseed_int = int(hashseed_val)
                        if hashseed_int < 0 or hashseed_int > 4294967295:
                            # Mimo povolený rozsah
                            del env["PYTHONHASHSEED"]
                    except ValueError:
                        # Není to integer ani "random"
                        del env["PYTHONHASHSEED"]
            # Vypnout wandb console capture (častý zdroj UnicodeEncodeError)
            env["WANDB_MODE"] = "disabled"
            env["WANDB_SILENT"] = "true"
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(out_p.parent),
                timeout=300  # 5 minut timeout
                ,
                env=env,
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout

                # Detekce specifických chyb a poskytnutí lepších instrukcí
                if "libtorchcodec" in error_msg or "FFmpeg" in error_msg or "torchcodec" in error_msg or "Could not load libtorchcodec" in error_msg:
                    detailed_error = (
                        "F5-TTS vyžaduje FFmpeg s podporou TorchCodec.\n\n"
                        "ŘEŠENÍ:\n"
                        "1. Nainstalujte FFmpeg full-shared verzi (s DLL soubory):\n"
                        "   - Stáhněte z: https://www.gyan.dev/ffmpeg/builds/\n"
                        "   - Vyberte 'ffmpeg-release-full-shared.7z'\n"
                        "   - Rozbalte a přidejte 'bin' složku do PATH\n"
                        "   - Nebo použijte conda: conda install -c conda-forge ffmpeg\n\n"
                        "2. Ověřte kompatibilitu PyTorch s TorchCodec:\n"
                        "   - Zkuste: pip install torch torchaudio --upgrade\n"
                        "   - Nebo pro GPU: pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121\n\n"
                        "3. Po instalaci FFmpeg restartujte backend server.\n\n"
                        f"Původní chyba:\n{error_msg[:500]}"
                    )
                    raise Exception(detailed_error)
                else:
                    raise Exception(f"F5-TTS Slovak CLI selhal: {error_msg}")

            # Výstup má být přesně v output_path (nastavili jsme -o/-w)
            if not out_p.exists():
                # fallback diagnostika: pokud výstup chybí, vypiš aspoň seznam wavů po spuštění
                after_time = time.time()
                wav_files = [
                    f for f in out_p.parent.glob("*.wav")
                    if f.stat().st_mtime >= before_time and f.stat().st_mtime <= after_time + 5
                ]
                raise Exception(
                    "F5-TTS Slovak CLI nevytvořil očekávaný výstupní soubor.\n"
                    f"Očekáváno: {out_p}\n"
                    f"Nalezené nové WAVy: {[p.name for p in wav_files][:10]}"
                )
            print(f"✅ F5-TTS Slovak výstup: {out_p}")

            _progress(55, "f5_tts_slovak", "F5-TTS Slovak inference dokončeno")

        except FileNotFoundError:
            error_msg = (
                "f5-tts_infer-cli nebyl nalezen.\n\n"
                "Pro instalaci F5-TTS spusťte:\n"
                "  pip install f5-tts\n\n"
                "Nebo pro lokální vývoj (editable install):\n"
                "  git clone https://github.com/SWivid/F5-TTS.git\n"
                "  cd F5-TTS\n"
                "  pip install -e .\n\n"
                "Po instalaci restartujte backend server."
            )
            raise Exception(error_msg)
        except Exception as e:
            error_str = str(e)
            # Pokud už je to naše vlastní chybová zpráva, jen ji přepošleme
            if "F5-TTS vyžaduje FFmpeg" in error_str or "f5-tts_infer-cli nebyl nalezen" in error_str:
                raise
            # Jinak přidáme kontext
            print(f"F5-TTS Slovak generování selhalo: {e}")
            # Zkontroluj, jestli to není FFmpeg/torchcodec problém
            if "libtorchcodec" in error_str or "FFmpeg" in error_str or "torchcodec" in error_str:
                detailed_error = (
                    "F5-TTS vyžaduje FFmpeg s podporou TorchCodec.\n\n"
                    "ŘEŠENÍ:\n"
                    "1. Nainstalujte FFmpeg full-shared verzi (s DLL soubory):\n"
                    "   - Stáhněte z: https://www.gyan.dev/ffmpeg/builds/\n"
                    "   - Vyberte 'ffmpeg-release-full-shared.7z'\n"
                    "   - Rozbalte a přidejte 'bin' složku do PATH\n"
                    "   - Nebo použijte conda: conda install -c conda-forge ffmpeg\n\n"
                    "2. Ověřte kompatibilitu PyTorch s TorchCodec:\n"
                    "   - Zkuste: pip install torch torchaudio --upgrade\n"
                    "   - Nebo pro GPU: pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121\n\n"
                    "3. Po instalaci FFmpeg restartujte backend server.\n\n"
                    f"Původní chyba:\n{error_str[:500]}"
                )
                raise Exception(detailed_error)
            raise

    async def _apply_post_processing(
        self,
        output_path: str,
        speed: float,
        enhancement_preset: Optional[str],
        enable_vad: Optional[bool],
        use_hifigan: bool,
        enable_normalization: bool,
        enable_denoiser: bool,
        enable_compressor: bool,
        enable_deesser: bool,
        enable_eq: bool,
        enable_trim: bool,
        enable_whisper: bool,
        whisper_intensity: float,
        target_headroom_db: Optional[float],
        hifigan_refinement_intensity: Optional[float],
        hifigan_normalize_output: Optional[bool],
        hifigan_normalize_gain: Optional[float],
        job_id: Optional[str],
        enable_enhancement: Optional[bool] = None
    ):
        """
        Aplikuje stejný post-processing jako XTTS pro konzistenci
        Reuse logiku z XTTSEngine._generate_sync
        """
        # Importujeme potřebné moduly
        from backend.audio_enhancer import AudioEnhancer
        from backend.vocoder_hifigan import get_hifigan_vocoder
        from backend.config import (
            ENABLE_AUDIO_ENHANCEMENT,
            AUDIO_ENHANCEMENT_PRESET,
            OUTPUT_SAMPLE_RATE,
            OUTPUT_HEADROOM_DB,
            ENABLE_VAD
        )
        import librosa
        import soundfile as sf
        import numpy as np
        import os
        import subprocess
        from backend.audio_processor import AudioProcessor

        def _progress(pct: float, stage: str, msg: str):
            if not job_id:
                return
            try:
                from backend.progress_manager import ProgressManager
                ProgressManager.update(job_id, percent=pct, stage=stage, message=msg)
            except Exception:
                pass

        try:
            _progress(58, "post", "Načítám audio…")
            # Načtení audio
            audio, sr = librosa.load(output_path, sr=None)
            original_length = len(audio) / sr

            # Upsampling na cílovou sample rate (pokud je jiná)
            if sr != OUTPUT_SAMPLE_RATE:
                _progress(62, "upsample", f"Převzorkování z {sr} Hz na {OUTPUT_SAMPLE_RATE} Hz…")
                audio = librosa.resample(audio, orig_sr=sr, target_sr=OUTPUT_SAMPLE_RATE)
                sr = OUTPUT_SAMPLE_RATE

            # Trim ticha (VAD nebo librosa)
            if enable_trim:
                try:
                    if enable_vad and ENABLE_VAD:
                        from backend.vad_processor import get_vad_processor
                        vad_processor = get_vad_processor()
                        audio = vad_processor.trim_silence_vad(audio, sample_rate=sr, padding_ms=50.0)
                    else:
                        audio, _ = librosa.effects.trim(audio, top_db=30)
                except Exception as e:
                    print(f"⚠️ Trim selhal: {e}")

            # Uložení před enhancement
            sf.write(output_path, audio, sr)
            _progress(65, "post", "Upsampling dokončen")

            # Audio enhancement (globálně + per-request)
            if ENABLE_AUDIO_ENHANCEMENT and (enable_enhancement is None or enable_enhancement):
                try:
                    preset_to_use = enhancement_preset if enhancement_preset else AUDIO_ENHANCEMENT_PRESET
                    def enhance_progress(percent: float, stage: str, message: str):
                        mapped_percent = 68.0 + (percent / 100.0) * 20.0
                        _progress(mapped_percent, "enhance", message)

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
                        progress_callback=enhance_progress
                    )
                except Exception as e:
                    print(f"Warning: Audio enhancement failed: {e}")

            # HiFi-GAN refinement (pokud zapnuto)
            if use_hifigan:
                try:
                    _progress(93, "hifigan", "HiFi-GAN refinement…")
                    vocoder = get_hifigan_vocoder()
                    if vocoder.is_available():
                        audio, sr = librosa.load(output_path, sr=None)
                        original_audio = audio.copy()
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
                        mel_log = np.log10(np.maximum(mel, 1e-5))
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
                            print("✅ HiFi-GAN refinement dokončen")
                except Exception as e:
                    print(f"⚠️ HiFi-GAN refinement selhal: {e}")

            # Změna rychlosti (FFmpeg atempo)
            speed_float = float(speed) if speed is not None else 1.0
            if abs(speed_float - 1.0) > 0.001:
                try:
                    _progress(95, "speed", f"Úprava rychlosti na {speed_float}x…")
                    if AudioProcessor._check_ffmpeg():
                        tmp_path = f"{output_path}.tmp_speed.wav"
                        cmd = [
                            "ffmpeg",
                            "-hide_banner",
                            "-loglevel", "error",
                            "-y",
                            "-i", str(output_path),
                            "-filter:a", f"atempo={speed_float}",
                            "-ar", str(OUTPUT_SAMPLE_RATE),
                            tmp_path,
                        ]
                        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                        os.replace(tmp_path, str(output_path))
                        print("✅ Rychlost změněna (FFmpeg atempo)")
                except Exception as e:
                    print(f"⚠️ Změna rychlosti selhala: {e}")

            # Finální headroom (po VŠEM): aby UI headroom měl efekt i když enhancement neběží / selže,
            # a aby se headroom dorovnal po HiFi-GAN / změně rychlosti.
            try:
                _progress(97, "final", "Finální úpravy (headroom)…")
                audio, sr = librosa.load(output_path, sr=None)
                final_headroom_db = target_headroom_db if target_headroom_db is not None else OUTPUT_HEADROOM_DB
                if final_headroom_db is not None:
                    peak = float(np.max(np.abs(audio))) if audio is not None and len(audio) else 0.0
                    if peak > 0:
                        if float(final_headroom_db) < 0:
                            target_peak = 10 ** (float(final_headroom_db) / 20.0)
                        else:
                            target_peak = 0.999
                        # Headroom jako "ceiling": pouze ztlumit, nikdy nezesilovat (lepší UX pro posuvník)
                        if peak > target_peak:
                            audio = audio * (target_peak / peak)
                    if not np.isfinite(audio).all():
                        audio = np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0)
                    sf.write(output_path, audio, sr)
                    print(f"🔉 Finální headroom ceiling: {final_headroom_db} dB (aplikováno jen pokud peak přesáhl cíl)")
            except Exception as e:
                print(f"⚠️ Finální headroom selhal: {e}")

            _progress(96, "final", "Dokončuji…")

        except Exception as e:
            print(f"⚠️ Post-processing selhal: {e}")

