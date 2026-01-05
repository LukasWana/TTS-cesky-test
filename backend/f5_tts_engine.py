"""
F5-TTS Engine wrapper
Používá CLI f5-tts_infer-cli pro inference (v1 implementace)
"""
import uuid
import asyncio
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict
import shutil
import os
import torch

import backend.config as config
from backend.config import (
    DEVICE,
    OUTPUTS_DIR,
    F5_MODEL_NAME,
    F5_DEFAULT_NFE,
    F5_DEVICE,
    F5_OUTPUT_SAMPLE_RATE,
    F5_CZECH_MODEL_DIR,
    F5_CZECH_DEFAULT_NFE,
    USE_CZECH_FINETUNED_MODEL
)


class F5TTSEngine:
    """Wrapper pro F5-TTS engine (v1: přes CLI)"""

    def __init__(self):
        self.device = F5_DEVICE
        self.is_loaded = False  # CLI nepotřebuje předběžné načtení modelu
        self.model_name = F5_MODEL_NAME
        self.model_dir = F5_CZECH_MODEL_DIR
        self.use_finetuned = USE_CZECH_FINETUNED_MODEL
        print(f"[INIT] F5TTSEngine initialized. Use finetuned Czech model: {self.use_finetuned}")

    def _validate_model(self, ckpt_path: Path, vocab_path: Path) -> bool:
        """
        Validates compatibility between checkpoint and vocabulary file.
        Returns True if compatible, False otherwise.
        """
        try:
            import torch

            # 1. Check vocab file size
            with open(vocab_path, "r", encoding="utf-8") as f:
                vocab_lines = [l.strip('\n').strip('\r') for l in f.readlines() if l.strip()]

            vocab_file_size = len(vocab_lines)
            print(f"[VALIDATION] Vocab file has {vocab_file_size} lines")

            # 2. Check checkpoint embedding size
            print(f"[VALIDATION] Loading checkpoint header: {ckpt_path}")
            # Load only map_location to avoid full load if possible, or just load
            checkpoint = torch.load(ckpt_path, map_location='cpu')

            # Identify state_dict
            if isinstance(checkpoint, dict):
                state_dict = checkpoint.get("ema_model_state_dict", checkpoint.get("model_state_dict"))
                if state_dict is None:
                    # Checkpoint might be the state_dict itself or contain it under other keys
                    if any(k.startswith("transformer.") for k in checkpoint.keys()):
                        state_dict = checkpoint
                    else:
                        print(f"[VALIDATION] ⚠️  Checkpoint structure unknown, searching for state_dict...")
                        # Fallback: find first key that looks like a state_dict
                        state_dict = checkpoint
            else:
                state_dict = checkpoint

            embed_key = "transformer.text_embed.text_embed.weight"
            if not isinstance(state_dict, dict) or embed_key not in state_dict:
                print(f"[VALIDATION] ⚠️  Embedding key {embed_key} not found in checkpoint.")
                print(f"[VALIDATION] Available keys (first 5): {list(state_dict.keys())[:5] if isinstance(state_dict, dict) else 'Not a dict'}")
                print(f"[VALIDATION] Podporujeme i tak - necháme F5TTS knihovnu, ať si s tím poradí.")
                return True

            ckpt_vocab_size = state_dict[embed_key].shape[0]
            print(f"[VALIDATION] Checkpoint embedding size: {ckpt_vocab_size}")

            # 3. Compare - checkpoint vocab size by měl odpovídat vocab file size
            if ckpt_vocab_size == vocab_file_size:
                print(f"[VALIDATION] ✅ Kompatibilní - checkpoint a vocab mají stejnou velikost ({vocab_file_size})")
                return True
            elif ckpt_vocab_size == vocab_file_size + 1:
                print(f"[VALIDATION] ✅ Kompatibilní - checkpoint má o 1 token více (padding token): {ckpt_vocab_size} = {vocab_file_size} + 1")
                return True
            elif ckpt_vocab_size + 1 == vocab_file_size:
                print(f"[VALIDATION] ⚠️  Vocab soubor má o 1 token více než checkpoint")
                print(f"[VALIDATION] ✅ Kompatibilní (vocab obsahuje padding token)")
                return True
            else:
                print(f"[VALIDATION] ❌ MISMATCH: Checkpoint ({ckpt_vocab_size}) != Vocab file ({vocab_file_size})")
                print(f"[VALIDATION] Hint: Check if vocab.txt has correct number of lines or if checkpoint needs patching.")
                return False

            print(f"[VALIDATION] ✅ Model and vocabulary are compatible.")
            return True

        except Exception as e:
            print(f"[VALIDATION] Error during validation: {e}")
            return False

    def _check_vocab_size(self, vocab_path: Path) -> int:
        """Zkontroluje počet tokenů v vocab souboru"""
        if not vocab_path.exists():
            return -1

        try:
            with open(vocab_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]

            # Odstranit duplikáty, ale zachovat pořadí
            seen = set()
            unique_tokens = []
            for token in lines:
                if token not in seen:
                    seen.add(token)
                    unique_tokens.append(token)

            return len(unique_tokens)
        except Exception:
            return -1

    def _check_checkpoint_vocab_size(self, ckpt_path: Path) -> int:
        """Zkontroluje vocab size v checkpointu"""
        if not ckpt_path.exists():
            return -1

        try:
            checkpoint = torch.load(ckpt_path, map_location='cpu')

            # Zkusit najít vocab size v různých možných klíčích
            vocab_size = None

            # Zkusit ema_model_state_dict
            if 'ema_model_state_dict' in checkpoint:
                state_dict = checkpoint['ema_model_state_dict']
                embed_key = 'transformer.text_embed.text_embed.weight'
                if embed_key in state_dict:
                    vocab_size = state_dict[embed_key].shape[0]

            # Zkusit model_state_dict
            if vocab_size is None and 'model_state_dict' in checkpoint:
                state_dict = checkpoint['model_state_dict']
                embed_key = 'transformer.text_embed.text_embed.weight'
                if embed_key in state_dict:
                    vocab_size = state_dict[embed_key].shape[0]

            # Zkusit přímo v root
            if vocab_size is None:
                embed_key = 'transformer.text_embed.text_embed.weight'
                if embed_key in checkpoint:
                    vocab_size = checkpoint[embed_key].shape[0]

            return vocab_size if vocab_size is not None else -1

        except Exception:
            return -1

    async def load_model(self):
        """Načte model do paměti (pro API inference)"""
        if self.is_loaded:
            return

        try:
            # Importujeme F5TTS zde, aby to nezpomalovalo start backendu
            from f5_tts.api import F5TTS

            # Zkontrolovat, zda máme finetunovaný český model
            from backend.config import F5_CZECH_CKPT_NAME, F5_CZECH_VOCAB_NAME

            ckpt_path = self.model_dir / F5_CZECH_CKPT_NAME
            vocab_path = self.model_dir / F5_CZECH_VOCAB_NAME

            # Pokud neexistuje finetunovaný, načteme výchozí (nebo necháme is_loaded=False pro CLI fallback)
            if ckpt_path.exists() and vocab_path.exists() and self.use_finetuned:
                print(f"[INIT] Loading F5-TTS Czech model for API: {ckpt_path}")

                # Validace kompatibility
                if not self._validate_model(ckpt_path, vocab_path):
                    print("[WARN] Model validation failed. Falling back to CLI mode for safety.")
                    self.tts_instance = None
                else:
                    self.tts_instance = F5TTS(
                        ckpt_file=str(ckpt_path),
                        vocab_file=str(vocab_path),
                        device=self.device
                    )
                    print("[OK] F5-TTS Czech model loaded successfully via API.")
            else:
                print("[INFO] No specific Czech model found for API loading, will use CLI mode if needed.")
                self.tts_instance = None

        except Exception as e:
            print(f"[ERROR] Failed to load F5-TTS via API: {e}")
            self.tts_instance = None

        self.is_loaded = True

    async def generate(
        self,
        text: str,
        speaker_wav: str,
        language: str = "cs",
        speed: float = 1.0,
        temperature: float = 0.7,
        length_penalty: float = 1.0,
        repetition_penalty: float = 2.0,
        top_k: int = 50,
        top_p: float = 0.85,
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
        Generuje řeč pomocí F5-TTS (API nebo CLI fallback)
        """
        # Ověření existence reference audio
        if not Path(speaker_wav).exists():
            raise Exception(f"Reference audio file not found: {speaker_wav}")

        # Vytvoření výstupní cesty
        output_filename = f"{uuid.uuid4()}.wav"
        output_path = OUTPUTS_DIR / output_filename

        # Předzpracování textu (český preprocessing)
        from backend.cs_pipeline import preprocess_czech_text
        processed_text = preprocess_czech_text(
            text,
            language,
            enable_dialect_conversion=enable_dialect_conversion,
            dialect_code=dialect_code,
            dialect_intensity=dialect_intensity,
            apply_voicing=False,  # Deaktivované - způsobuje "drmolení" v F5-TTS
            apply_glottal_stop=False  # Deaktivované - model matí ráz/apostrof
        )

        # Načíst model pokud ještě není (lazy load)
        if not self.is_loaded:
            await self.load_model()

        # Generování
        loop = asyncio.get_event_loop()

        # Pokud máme instanci TTS (API), použijeme ji
        if hasattr(self, 'tts_instance') and self.tts_instance is not None:
            await loop.run_in_executor(
                None,
                self._generate_sync_api,
                processed_text,
                speaker_wav,
                str(output_path),
                ref_text,
                job_id
            )
        else:
            # Jinak fallback na CLI
            await loop.run_in_executor(
                None,
                self._generate_sync_cli,
                processed_text,
                speaker_wav,
                str(output_path),
                ref_text,
                job_id
            )

        # Post-processing (stejné jako XTTS)
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

    def _generate_sync_api(
        self,
        text: str,
        ref_audio: str,
        output_path: str,
        ref_text: Optional[str],
        job_id: Optional[str]
    ):
        """Synchronní generování přes F5-TTS API (v paměti)"""
        def _progress(pct: float, stage: str, msg: str):
            if not job_id:
                return
            try:
                from backend.progress_manager import ProgressManager
                ProgressManager.update(job_id, percent=pct, stage=stage, message=msg)
            except Exception:
                pass

        try:
            _progress(15, "f5_tts", "Generuji řeč (F5-TTS Czech API)…")

            # Detekce ref_text (přepis reference)
            # Pokud není zadán, F5TTS API ho může zkusit odhadnout nebo vyžaduje
            # Ale v uživatelském příkladu byl zadán.
            reference_text = ref_text if ref_text else ""

            # API volání
            # tts.infer(ref_file, ref_text, gen_text, file_wave)
            self.tts_instance.infer(
                ref_file=ref_audio,
                ref_text=reference_text,
                gen_text=text,
                file_wave=output_path
            )

            _progress(55, "f5_tts", "F5-TTS API inference dokončena")

        except Exception as e:
            print(f"[ERROR] API inference failed: {e}")
            raise Exception(f"F5-TTS API inference selhala: {e}")

    def _generate_sync_cli(
        self,
        text: str,
        ref_audio: str,
        output_path: str,
        ref_text: Optional[str],
        job_id: Optional[str]
    ):
        """Synchronní generování přes F5-TTS CLI (fallback)"""
        def _progress(pct: float, stage: str, msg: str):
            if not job_id:
                return
            try:
                from backend.progress_manager import ProgressManager
                ProgressManager.update(job_id, percent=pct, stage=stage, message=msg)
            except Exception:
                pass

        try:
            _progress(15, "f5_tts", "Generuji řeč (F5-TTS Czech CLI)…")

            # Příprava CLI příkazu
            out_p = Path(output_path)

            import sys
            cli_exe = shutil.which("f5-tts_infer-cli")
            if not cli_exe or not Path(cli_exe).exists():
                venv_scripts = Path(sys.executable).parent / "f5-tts_infer-cli.exe"
                if venv_scripts.exists():
                    cli_exe = str(venv_scripts)
                else:
                    raise FileNotFoundError("f5-tts_infer-cli nebyl nalezen.")

            # Zkontrolovat, zda máme finetunovaný český model
            use_local_model = self.use_finetuned
            ckpt_path = None
            vocab_path = None

            if use_local_model:
                from backend.config import F5_CZECH_CKPT_NAME, F5_CZECH_VOCAB_NAME
                ckpt_path = self.model_dir / F5_CZECH_CKPT_NAME
                vocab_path = self.model_dir / F5_CZECH_VOCAB_NAME

                if not ckpt_path.exists() or not vocab_path.exists():
                    print(f"[INFO] Czech model from config not found, searching in {self.model_dir}")
                    # ... (původní vyhledávací logika by tu mohla být, ale pro stručnost ji zachováme jen v CLI mode)
                    possible_ckpt_names = ["model_last.pt", "model.pt"]
                    possible_vocab_names = ["vocab.txt"]

                    for name in possible_ckpt_names:
                        if (self.model_dir / name).exists():
                            ckpt_path = self.model_dir / name
                            break
                    for name in possible_vocab_names:
                        if (self.model_dir / name).exists():
                            vocab_path = self.model_dir / name
                            break

                if not ckpt_path or not ckpt_path.exists() or not vocab_path or not vocab_path.exists():
                    use_local_model = False

            # Sestavit CLI příkaz
            if use_local_model and ckpt_path and vocab_path:
                model_cfg_path = self.model_dir / "F5TTS_Czech.yaml"
                if not model_cfg_path.exists():
                    import importlib.util
                    spec = importlib.util.find_spec("f5_tts")
                    f5_base = Path(list(spec.submodule_search_locations)[0]).resolve()
                    model_cfg_path = f5_base / "configs" / "F5TTS_v1_Base.yaml"

                cmd = [
                    cli_exe,
                    "-m", "F5TTS_Czech" if (self.model_dir / "F5TTS_Czech.yaml").exists() else "F5TTS_v1_Base",
                    "-r", ref_audio,
                    "-t", text,
                    "-o", str(out_p.parent),
                    "-w", out_p.name,
                    "--ckpt_file", str(ckpt_path),
                    "--vocab_file", str(vocab_path),
                    "--model_cfg", str(model_cfg_path),
                    "--device", str(self.device),
                    "--nfe_step", str(F5_CZECH_DEFAULT_NFE),
                ]
            else:
                cmd = [
                    cli_exe,
                    "-m", self.model_name,
                    "-r", ref_audio,
                    "-t", text,
                    "-o", str(out_p.parent),
                    "-w", out_p.name,
                    "--device", str(self.device),
                    "--nfe_step", str(F5_DEFAULT_NFE),
                ]

            if ref_text:
                cmd.extend(["-s", ref_text])

            print(f"🔊 F5-TTS CLI: {' '.join(cmd)}")
            env = os.environ.copy()
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
            env["WANDB_MODE"] = "disabled"

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(out_p.parent), timeout=300, env=env)

            if result.returncode != 0:
                raise Exception(f"F5-TTS CLI selhal: {result.stderr or result.stdout}")

            if not out_p.exists():
                raise Exception(f"F5-TTS CLI nevytvořil výstupní soubor: {out_p}")

            _progress(55, "f5_tts", "F5-TTS CLI inference dokončena")

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
            print(f"F5-TTS generování selhalo: {e}")
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

