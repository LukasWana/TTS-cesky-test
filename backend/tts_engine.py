"""
XTTS-v2 TTS Engine wrapper
"""
import uuid
import asyncio
import threading
import warnings
from pathlib import Path
from typing import Optional, List, Dict
import re
import time
# REMOVED: from TTS.api import TTS
# REMOVED: import torch
import numpy as np
import backend.config as config
from num2words import num2words
from TTS.tts.layers.xtts import tokenizer as xtts_tokenizer

from backend.tts.text_processor import TextProcessor
from backend.tts.model_manager import ModelManager
from backend.tts.quality_control import QualityControl

# Potlačení deprecation warning z librosa (pkg_resources je zastaralé, ale knihovna ho ještě používá)
warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated.*", category=UserWarning)
from backend.config import (
    get_device,
    XTTS_MODEL_NAME,
    MODEL_CACHE_DIR,
    OUTPUTS_DIR,
    USE_SMALL_MODELS,
    ENABLE_CPU_OFFLOAD,
    FORCE_DEVICE,
    DEVICE_FORCED,
    ENABLE_AUDIO_ENHANCEMENT,
    AUDIO_ENHANCEMENT_PRESET,
    QUALITY_PRESETS,
    TARGET_SAMPLE_RATE,
    OUTPUT_SAMPLE_RATE,
    OUTPUT_HEADROOM_DB,
    ENABLE_MULTI_PASS,
    MULTI_PASS_COUNT,
    ENABLE_BATCH_PROCESSING,
    MAX_CHUNK_LENGTH,
    ENABLE_PROSODY_CONTROL,
    ENABLE_INTONATION_PROCESSING,
    ENABLE_PHONETIC_TRANSLATION,
    ENABLE_CZECH_TEXT_PROCESSING,
    ENABLE_DIALECT_CONVERSION,
    DIALECT_CODE,
    DIALECT_INTENSITY
)
from backend.audio_enhancer import AudioEnhancer
from backend.vocoder_hifigan import get_hifigan_vocoder
from backend.phonetic_translator import get_phonetic_translator

# Monkey patch pro správnou podporu češtiny v num2words (TTS upstream používá kód "cz")
try:
    def _expand_number_cs(m, lang="en"):
        lang_code = "cs" if lang.split("-")[0] == "cs" else lang
        return num2words(int(m.group(0)), lang=lang_code)

    def _expand_ordinal_cs(m, lang="en"):
        lang_code = "cs" if lang.split("-")[0] == "cs" else lang
        return num2words(int(m.group(1)), ordinal=True, lang=lang_code)

    xtts_tokenizer._expand_number = _expand_number_cs
    xtts_tokenizer._expand_ordinal = _expand_ordinal_cs
except Exception as patch_err:
    # Nechceme spadnout při importu – jen zalogujeme
    print(f"Warning: Czech number expansion patch not applied: {patch_err}")


class XTTSEngine:
    """Wrapper pro XTTS-v2 TTS engine"""

    def __init__(self):
        self._device = None
        self._vocoder = None  # Lazy loading - načte se až při prvním použití

        # Komponenty
        self.model_manager = ModelManager(device=None) # Lazy resolve inside ModelManager
        self.text_processor = TextProcessor(model=None)  # Model se nastaví po načtení
        self.quality_control = QualityControl()

        # Backward compatibility properties
        self.model = None  # Bude nastaveno z model_manager
        self.is_loading = False  # Bude nastaveno z model_manager
        self.is_loaded = False  # Bude nastaveno z model_manager
        self._bpe_tokenizer = None  # Bude nastaveno z text_processor

    @property
    def device(self):
        """Lazy access to device"""
        if self._device is None:
            self._device = get_device()
        return self._device

    @property
    def vocoder(self):
        """Lazy loading vocoder - načte se až při prvním použití"""
        if self._vocoder is None:
            self._vocoder = get_hifigan_vocoder()
        return self._vocoder

    @property
    def model(self):
        """Backward compatibility property"""
        return self.model_manager.model

    @model.setter
    def model(self, value):
        """Backward compatibility setter"""
        self.model_manager.model = value
        self.text_processor.model = value

    @property
    def is_loading(self):
        """Backward compatibility property"""
        return self.model_manager.is_loading

    @is_loading.setter
    def is_loading(self, value):
        """Backward compatibility setter"""
        self.model_manager.is_loading = value

    @property
    def is_loaded(self):
        """Backward compatibility property"""
        return self.model_manager.is_loaded

    @is_loaded.setter
    def is_loaded(self, value):
        """Backward compatibility setter"""
        self.model_manager.is_loaded = value

    def _get_bpe_tokenizer(self):
        """Backward compatibility wrapper"""
        return self.text_processor._get_bpe_tokenizer()

    def _count_xtts_tokens(self, text: str, language: str = "cs") -> Optional[int]:
        """Backward compatibility wrapper"""
        return self.text_processor.count_xtts_tokens(text, language)

    def _split_text_by_xtts_tokens(self, text: str, language: str = "cs") -> List[str]:
        """
        Rozseká text tak, aby žádný chunk nepřekročil config.XTTS_TARGET_MAX_TOKENS.
        Preferuje dělení na koncích vět, pak na slovech, a nakonec nouzově po znacích.
        """
        """Backward compatibility wrapper"""
        return self.text_processor.split_text_by_xtts_tokens(text, language)

    async def load_model(self):
        """Načte XTTS-v2 model asynchronně"""
        await self.model_manager.load_model()
        # Aktualizuj text_processor s načteným modelem
        self.text_processor.model = self.model_manager.model

    def _load_model_sync(self):
        """Backward compatibility wrapper"""
        return self.model_manager._load_model_sync()

    def _apply_quality_preset(self, preset: str) -> dict:
        """Backward compatibility wrapper"""
        return self.quality_control.apply_quality_preset(preset)

    def _compute_effective_settings(
        self,
        quality_mode: Optional[str] = None,
        enhancement_preset: Optional[str] = None,
        speed: Optional[float] = None,
        temperature: Optional[float] = None,
        length_penalty: Optional[float] = None,
        repetition_penalty: Optional[float] = None,
        top_k: Optional[int] = None,
        top_p: Optional[float] = None,
        enable_eq: Optional[bool] = None,
        enable_denoiser: Optional[bool] = None,
        enable_compressor: Optional[bool] = None,
        enable_deesser: Optional[bool] = None,
        enable_normalization: Optional[bool] = None,
        enable_trim: Optional[bool] = None,
        enable_whisper: Optional[bool] = None,
        whisper_intensity: Optional[float] = None,
        target_headroom_db: Optional[float] = None,
    ) -> dict:
        """
        Vypočítá efektivní nastavení kombinací quality_mode presetu, enhancement_preset a explicitních parametrů.

        Pravidla priority:
        1. Explicitní parametry (pokud zadány) mají přednost před presety
        2. quality_mode určuje TTS parametry a enhancement (pokud je quality preset)
        3. enhancement_preset určuje enhancement (pokud není quality_mode nebo quality_mode není quality preset)
        4. Výchozí hodnoty z configu pro neexplicitní parametry

        Pro speed: Pokud je quality_mode in {meditative, whisper} a speed není explicitně zadán,
        použije se speed z presetu. Jinak se zachová explicitní speed nebo výchozí.

        Returns:
            Dictionary s efektivními nastaveními:
            - tts: {speed, temperature, length_penalty, repetition_penalty, top_k, top_p}
            - enhancement: {enable_eq, enable_denoiser, enable_compressor, enable_deesser, enable_trim, enable_normalization}
            - whisper: {enable_whisper, whisper_intensity}
            - headroom: {target_headroom_db}
        """
        from backend.config import (
            TTS_SPEED, TTS_TEMPERATURE, TTS_LENGTH_PENALTY, TTS_REPETITION_PENALTY, TTS_TOP_K, TTS_TOP_P,
            OUTPUT_HEADROOM_DB, ENABLE_AUDIO_ENHANCEMENT
        )

        # Výchozí hodnoty z configu
        defaults = {
            "speed": TTS_SPEED,
            "temperature": TTS_TEMPERATURE,
            "length_penalty": TTS_LENGTH_PENALTY,
            "repetition_penalty": TTS_REPETITION_PENALTY,
            "top_k": TTS_TOP_K,
            "top_p": TTS_TOP_P,
            "enable_eq": True,
            "enable_denoiser": True,
            "enable_compressor": True,
            "enable_deesser": True,
            "enable_trim": True,
            "enable_normalization": True,
            "enable_whisper": False,
            "whisper_intensity": 1.0,
            "target_headroom_db": OUTPUT_HEADROOM_DB,
        }

        """Backward compatibility wrapper"""
        return self.quality_control.compute_effective_settings(
            quality_mode=quality_mode,
            enhancement_preset=enhancement_preset,
            speed=speed,
            temperature=temperature,
            length_penalty=length_penalty,
            repetition_penalty=repetition_penalty,
            top_k=top_k,
            top_p=top_p,
            enable_eq=enable_eq,
            enable_denoiser=enable_denoiser,
            enable_compressor=enable_compressor,
            enable_deesser=enable_deesser,
            enable_normalization=enable_normalization,
            enable_trim=enable_trim,
            enable_whisper=enable_whisper,
            whisper_intensity=whisper_intensity,
            target_headroom_db=target_headroom_db,
        )

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
        enable_enhancement: Optional[bool] = None,
        multi_pass: bool = False,
        multi_pass_count: int = 3,
        enable_batch: Optional[bool] = None,
        enable_vad: Optional[bool] = None,
        use_hifigan: bool = False,
        enable_normalization: bool = True,
        enable_denoiser: bool = True,
        enable_compressor: bool = True,
        enable_deesser: bool = True,
        enable_eq: bool = True,
        enable_trim: bool = True,
        handle_pauses: bool = True,
        enable_dialect_conversion: Optional[bool] = None,
        dialect_code: Optional[str] = None,
        dialect_intensity: float = 1.0,
        enable_whisper: Optional[bool] = None,
        whisper_intensity: Optional[float] = None,
        target_headroom_db: Optional[float] = None,
        hifigan_refinement_intensity: Optional[float] = None,
        hifigan_normalize_output: Optional[bool] = None,
        hifigan_normalize_gain: Optional[float] = None,
        job_id: Optional[str] = None
    ):
        """
        Generuje řeč z textu

        Args:
            text: Text k syntéze
            speaker_wav: Cesta k audio souboru s hlasem
            language: Jazyk (cs pro češtinu)
            speed: Rychlost řeči (0.5-2.0, výchozí: 1.0)
            temperature: Teplota pro sampling (0.0-1.0, výchozí: 0.7)
            length_penalty: Length penalty (výchozí: 1.0)
            repetition_penalty: Repetition penalty (výchozí: 2.0)
            top_k: Top-k sampling (výchozí: 50)
            top_p: Top-p sampling (výchozí: 0.85)
            quality_mode: Quality preset (high_quality, natural, fast) - přepíše jednotlivé parametry
            seed: Seed pro reprodukovatelnost generování (volitelné)
            enhancement_preset: Preset pro audio enhancement (high_quality, natural, fast)
            multi_pass: Zapnout multi-pass generování (výchozí: False)
            multi_pass_count: Počet variant při multi-pass (výchozí: 3)
            enable_batch: Zapnout batch processing pro dlouhé texty (None = auto)
            enable_vad: Zapnout VAD pro lepší trim (None = použít config)
            use_hifigan: Použít HiFi-GAN vocoder (výchozí: False)
            enable_normalization: Zapnout normalizaci (výchozí: True)
            enable_denoiser: Zapnout redukci šumu (výchozí: True)
            enable_compressor: Zapnout kompresi (výchozí: True)
            enable_deesser: Zapnout de-esser (výchozí: True)
            enable_eq: Zapnout EQ (výchozí: True)
            enable_trim: Zapnout ořez ticha (výchozí: True)

        Returns:
            Cesta k vygenerovanému audio souboru nebo seznam variant při multi-pass
        """
        if not self.is_loaded:
            await self.load_model()

        if not self.model:
            raise Exception("Model není načten")

        # Progress (pokud používáme job_id z frontendu)
        if job_id:
            try:
                from backend.progress_manager import ProgressManager
                ProgressManager.update(job_id, percent=2, stage="prepare", message="Připravuji generování…")
            except Exception:
                pass

        # Vypočítej efektivní nastavení (kombinace quality_mode, enhancement_preset a explicitních parametrů)
        effective = self._compute_effective_settings(
            quality_mode=quality_mode,
            enhancement_preset=enhancement_preset,
            speed=speed,
            temperature=temperature,
            length_penalty=length_penalty,
            repetition_penalty=repetition_penalty,
            top_k=top_k,
            top_p=top_p,
            enable_eq=enable_eq,
            enable_denoiser=enable_denoiser,
            enable_compressor=enable_compressor,
            enable_deesser=enable_deesser,
            enable_normalization=enable_normalization,
            enable_trim=enable_trim,
            enable_whisper=enable_whisper,
            whisper_intensity=whisper_intensity,
            target_headroom_db=target_headroom_db,
        )

        # Extrahuj efektivní hodnoty
        speed = effective["tts"]["speed"]
        temperature = effective["tts"]["temperature"]
        length_penalty = effective["tts"]["length_penalty"]
        repetition_penalty = effective["tts"]["repetition_penalty"]
        top_k = effective["tts"]["top_k"]
        top_p = effective["tts"]["top_p"]
        enable_eq = effective["enhancement"]["enable_eq"]
        enable_denoiser = effective["enhancement"]["enable_denoiser"]
        enable_compressor = effective["enhancement"]["enable_compressor"]
        enable_deesser = effective["enhancement"]["enable_deesser"]
        enable_normalization = effective["enhancement"]["enable_normalization"]
        enable_trim = effective["enhancement"]["enable_trim"]
        enable_whisper = effective["whisper"]["enable_whisper"]
        whisper_intensity = effective["whisper"]["whisper_intensity"]
        target_headroom_db = effective["headroom"]["target_headroom_db"]

        if quality_mode:
            print(f"🎯 Quality mode '{quality_mode}' aplikován - efektivní nastavení vypočítáno z presetu (speed={speed:.2f}x)")

        # Multi-pass generování
        if multi_pass or (ENABLE_MULTI_PASS and not multi_pass):
            return await self.generate_multi_pass(
                text=text,
                speaker_wav=speaker_wav,
                language=language,
                speed=speed,
                temperature=temperature,
                length_penalty=length_penalty,
                repetition_penalty=repetition_penalty,
                top_k=top_k,
                top_p=top_p,
                quality_mode=quality_mode,
                enhancement_preset=enhancement_preset,
                variant_count=multi_pass_count if multi_pass else MULTI_PASS_COUNT,
                enable_batch=enable_batch,
                enable_vad=enable_vad,
                use_hifigan=use_hifigan,
                enable_normalization=enable_normalization,
                enable_denoiser=enable_denoiser,
                enable_compressor=enable_compressor,
                enable_deesser=enable_deesser,
                enable_eq=enable_eq,
                enable_trim=enable_trim,
                enable_whisper=enable_whisper,
                whisper_intensity=whisper_intensity,
                target_headroom_db=target_headroom_db,
                hifigan_refinement_intensity=hifigan_refinement_intensity,
                hifigan_normalize_output=hifigan_normalize_output,
                hifigan_normalize_gain=hifigan_normalize_gain,
                enable_enhancement=enable_enhancement,
                job_id=job_id
            )

        # Skutečné pauzy: [PAUSE] / [pause] a [PAUSE:ms] / [pause:ms]
        # Pozn.: ProsodyProcessor historicky převáděl pauzy jen na mezery (a při batch splitu se ztratí).
        # Tady to řešíme správně: vygenerujeme úseky zvlášť a mezi ně vložíme ticho v milisekundách.
        if handle_pauses:
            import re
            # Najdi všechny pauzy a rozsekej text (case-insensitive).
            # Podporované formy:
            # - [pause]
            # - [pause:500], [pause=500]
            # - [pause:500ms], [pause = 500 ms]
            pause_re = re.compile(r"\[pause(?:\s*[:=]\s*(\d+)\s*(?:ms)?)?\]", re.IGNORECASE)
            matches = list(pause_re.finditer(text))
            if matches:
                segments: List[str] = []
                pauses_ms: List[int] = []
                leading_pause_ms = 0
                last = 0
                pending_pause = 0

                for m in matches:
                    seg = text[last:m.start()]
                    dur_raw = m.group(1)
                    try:
                        dur = int(dur_raw) if dur_raw is not None else 500
                    except Exception:
                        dur = 500
                    dur = max(0, min(dur, 10000))  # 0–10s safety

                    # Přidej segment (i prázdný zatím), pauzy slučujeme pokud jsou za sebou
                    if seg.strip():
                        is_first_segment = len(segments) == 0
                        segments.append(seg.strip())
                        if pending_pause > 0:
                            # Pokud ještě nemáme žádný segment, jde o pauzu NA ZAČÁTKU
                            if is_first_segment:
                                leading_pause_ms += pending_pause
                            else:
                                pauses_ms.append(pending_pause)
                            pending_pause = 0
                        pending_pause += dur
                    else:
                        pending_pause += dur

                    last = m.end()

                tail = text[last:]
                if tail.strip():
                    is_first_segment = len(segments) == 0
                    segments.append(tail.strip())
                    if pending_pause > 0:
                        if is_first_segment:
                            leading_pause_ms += pending_pause
                        else:
                            pauses_ms.append(pending_pause)
                        pending_pause = 0
                else:
                    # trailing pause bez dalšího textu: zachovej jako pauzu na konci
                    if pending_pause > 0 and segments:
                        pauses_ms.append(pending_pause)
                    pending_pause = 0

                # Pokud máme aspoň 2 segmenty, vygeneruj a spoj se skutečným tichem
                if len(segments) >= 2:
                    print(
                        f"⏸️  Detekovány pauzy v textu: {len(segments)} segmentů, "
                        f"{len(pauses_ms)} pauz (včetně případné pauzy na konci), "
                        f"leading_pause={leading_pause_ms}ms"
                    )
                    part_paths: List[str] = []
                    for idx, seg in enumerate(segments):
                        if job_id:
                            try:
                                from backend.progress_manager import ProgressManager
                                ProgressManager.update(
                                    job_id,
                                    percent=5 + (80.0 * idx / max(1, len(segments))),
                                    stage="pause_segments",
                                    message=f"Generuji segment {idx+1}/{len(segments)}…",
                                    meta_update={"segment": idx + 1, "segments_total": len(segments)},
                                )
                            except Exception:
                                pass
                        part_path = await self.generate(
                            text=seg,
                            speaker_wav=speaker_wav,
                            language=language,
                            speed=speed,
                            temperature=temperature,
                            length_penalty=length_penalty,
                            repetition_penalty=repetition_penalty,
                            top_k=top_k,
                            top_p=top_p,
                            quality_mode=quality_mode,
                            seed=seed,
                            enhancement_preset=enhancement_preset,
                            multi_pass=False,
                            # Batch uvnitř segmentu je OK (segment sám neobsahuje [PAUSE]),
                            # a zároveň to chrání před XTTS limitem 400 tokenů.
                            enable_batch=enable_batch,
                            enable_vad=enable_vad,
                            use_hifigan=use_hifigan,
                            enable_normalization=enable_normalization,
                            enable_denoiser=enable_denoiser,
                            enable_compressor=enable_compressor,
                            enable_deesser=enable_deesser,
                            enable_eq=enable_eq,
                            enable_trim=enable_trim,
                            handle_pauses=False,  # zabraň rekurzivnímu parsování
                            job_id=job_id,
                        )
                        part_paths.append(part_path)

                    # Spoj WAVy + vlož ticho přesně podle ms
                    final_output = OUTPUTS_DIR / f"{uuid.uuid4()}.wav"
                    try:
                        if job_id:
                            try:
                                from backend.progress_manager import ProgressManager
                                ProgressManager.update(job_id, percent=90, stage="concat", message="Skládám segmenty…")
                            except Exception:
                                pass
                        import librosa
                        import soundfile as sf

                        sr = OUTPUT_SAMPLE_RATE
                        # Krátký fade proti "klikům". 8ms je u krátkých pauz (10–50ms) moc a vizuálně je to může "srovnat".
                        # Držíme to malé, aby délka pauz odpovídala zadaným hodnotám.
                        fade_samples = int(0.001 * sr)  # 1 ms

                        out_parts: List[np.ndarray] = []
                        if leading_pause_ms > 0:
                            leading_samps = int(leading_pause_ms * sr / 1000)
                            print(f"⏱️  Leading pause: {leading_pause_ms} ms => {leading_samps} samples @ {sr} Hz")
                            out_parts.append(np.zeros(leading_samps, dtype=np.float32))
                        for i, p in enumerate(part_paths):
                            audio, _sr = librosa.load(p, sr=sr, mono=True)
                            # DŮLEŽITÉ: při segmentaci na jednotlivá slova model často přidá vlastní dlouhé ticho
                            # na začátek/konec každého segmentu, takže pak všechny pauzy zní stejně dlouhé.
                            # Proto každý segment před spojením ořízneme na řeč a necháme jen malý padding.
                            try:
                                from backend.vad_processor import get_vad_processor
                                vadp = get_vad_processor()
                                trimmed = vadp.trim_silence_vad(audio, sample_rate=sr, padding_ms=30.0)
                                if trimmed is not None and len(trimmed) > 0:
                                    audio = trimmed
                            except Exception:
                                # Fallback: energetický trim (může být méně přesný než VAD)
                                try:
                                    audio, _ = librosa.effects.trim(audio, top_db=35)
                                except Exception:
                                    pass
                            # jemný fade in/out
                            if len(audio) > fade_samples * 2:
                                audio[:fade_samples] *= np.linspace(0.0, 1.0, fade_samples)
                                audio[-fade_samples:] *= np.linspace(1.0, 0.0, fade_samples)
                            out_parts.append(audio)

                            if i < len(pauses_ms):
                                pause_ms = pauses_ms[i]
                                pause_samps = int(pause_ms * sr / 1000)
                                if pause_samps > 0:
                                    print(f"⏱️  Pause[{i}]: {pause_ms} ms => {pause_samps} samples @ {sr} Hz")
                                    out_parts.append(np.zeros(pause_samps, dtype=np.float32))

                        final_audio = np.concatenate(out_parts) if out_parts else np.array([], dtype=np.float32)
                        sf.write(str(final_output), final_audio, sr)
                    finally:
                        # uklidit dočasné segmenty
                        for p in part_paths:
                            try:
                                Path(p).unlink(missing_ok=True)
                            except Exception:
                                pass

                    return str(final_output)

        # Batch processing pro dlouhé texty
        hard_limit = getattr(config, "XTTS_MAX_TOKENS", 400)
        target_limit = getattr(config, "XTTS_TARGET_MAX_TOKENS", 380)
        token_count = self._count_xtts_tokens(text, language)

        # Pokud hrozí/už nastal token overflow, batch je povinný (jinak XTTS spadne).
        if token_count is not None and token_count > hard_limit:
            enable_batch = True

        use_batch = enable_batch if enable_batch is not None else (
            ENABLE_BATCH_PROCESSING and (
                (token_count is not None and token_count > target_limit) or (len(text) > MAX_CHUNK_LENGTH)
            )
        )
        if use_batch:
            return await self.generate_batch(
                text=text,
                speaker_wav=speaker_wav,
                language=language,
                speed=speed,
                temperature=temperature,
                length_penalty=length_penalty,
                repetition_penalty=repetition_penalty,
                top_k=top_k,
                top_p=top_p,
                quality_mode=quality_mode,
                seed=seed,
                enhancement_preset=enhancement_preset,
                enable_vad=enable_vad,
                use_hifigan=use_hifigan,
                enable_normalization=enable_normalization,
                enable_denoiser=enable_denoiser,
                enable_compressor=enable_compressor,
                enable_deesser=enable_deesser,
                enable_eq=enable_eq,
                enable_trim=enable_trim,
                enable_dialect_conversion=enable_dialect_conversion,
                dialect_code=dialect_code,
                dialect_intensity=dialect_intensity,
                job_id=job_id
            )

        # Prosody preprocessing
        prosody_metadata = {}
        try:
            from backend.prosody_processor import ProsodyProcessor
            if ENABLE_PROSODY_CONTROL:
                text, prosody_metadata = ProsodyProcessor.process_text(text)
        except Exception as e:
            print(f"Warning: Prosody processing failed: {e}")

        # Vytvoření výstupní cesty
        output_filename = f"{uuid.uuid4()}.wav"
        output_path = OUTPUTS_DIR / output_filename

        # Generování v thread poolu
        if job_id:
            try:
                from backend.progress_manager import ProgressManager
                ProgressManager.update(job_id, percent=10, stage="synth", message="Syntetizuji…")
            except Exception:
                pass
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._generate_sync,
            text,
            speaker_wav,
            language,
            str(output_path),
            speed,
            temperature,
            length_penalty,
            repetition_penalty,
            top_k,
            top_p,
            quality_mode,
            seed,
            enhancement_preset,
            enable_vad,
            use_hifigan,
            enable_normalization,
            enable_denoiser,
            enable_compressor,
            enable_deesser,
            enable_eq,
            enable_trim,
            enable_dialect_conversion,
            dialect_code,
            dialect_intensity,
            enable_whisper,
            whisper_intensity,
            target_headroom_db,
            hifigan_refinement_intensity,
            hifigan_normalize_output,
            hifigan_normalize_gain,
            job_id,
            enable_enhancement,
            prosody_metadata,
        )

        # finální 100% řeší backend/main.py (ProgressManager.done(job_id))
        return str(output_path)

    def _generate_sync(
        self,
        text: str,
        speaker_wav: str,
        language: str,
        output_path: str,
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
        enable_enhancement: Optional[bool] = None,
        prosody_metadata: Optional[Dict] = None
    ):
        # DEBUG: Ověření, že speed parametr skutečně přichází
        print(f"🔍 DEBUG _generate_sync START: speed={speed}, type={type(speed)}, output_path={output_path}")
        """Synchronní generování řeči"""
        def _progress(pct: float, stage: str, msg: str):
            if not job_id:
                return
            try:
                from backend.progress_manager import ProgressManager
                ProgressManager.update(job_id, percent=pct, stage=stage, message=msg)
            except Exception:
                pass

        try:
            import torch
            _progress(12, "prep", "Připravuji vstup…")
            # Nastavení seedu pro reprodukovatelnost
            if seed is not None:
                torch.manual_seed(seed)
                if torch.cuda.is_available():
                    torch.cuda.manual_seed_all(seed)
                np.random.seed(seed)
                print(f"🌱 Seed nastaven na: {seed}")
            else:
                # Pokud není seed zadán, použijeme fixní seed pro konzistenci
                fixed_seed = 42
                torch.manual_seed(fixed_seed)
                if torch.cuda.is_available():
                    torch.cuda.manual_seed_all(fixed_seed)
                np.random.seed(fixed_seed)
                print(f"🌱 Použit fixní seed: {fixed_seed} (pro reprodukovatelnost)")

            # Zkontroluj, jestli speaker_wav existuje
            if not Path(speaker_wav).exists():
                raise Exception(f"Speaker audio file not found: {speaker_wav}")

            # Předzpracování textu pro češtinu - převod čísel na slova
            # TTS knihovna má problém s num2words pro češtinu, takže převedeme čísla ručně
            processed_text = self.text_processor.preprocess_text(
                text,
                language,
                enable_dialect_conversion=enable_dialect_conversion,
                dialect_code=dialect_code,
                dialect_intensity=dialect_intensity
            )

            # Úprava: Odstranit koncovou tečku jen pro XTTS model,
            # aby ji model nepřečetl jako slovo "tečka".
            # Intonace (FALL) je už zachycena v prosody_metadata z dřívější fáze.
            text_for_model = processed_text
            if language == "cs" and isinstance(text_for_model, str):
                # Odstraníme koncovou tečku/tečky a případné mezery za ní
                text_for_model = re.sub(r"\s*[.…]+(\s*)$", r"\1", text_for_model).rstrip()
                if not text_for_model.strip():
                    # Pokud by po odstranění tečky nic nezbylo (např. vstup "."),
                    # vrátíme původní text jako fallback
                    text_for_model = processed_text

            _progress(15, "tts", "Generuji řeč (XTTS)…")

            # Příprava parametrů pro tts_to_file
            # Vždy předáváme všechny parametry, ne jen když se liší od výchozích hodnot
            # POZNÁMKA: XTTS-v2 nemusí podporovat parametr "speed" přímo v tts_to_file,
            # takže změnu rychlosti provádíme pomocí post-processing (viz níže)

            # Validace a korekce extrémních parametrů, které mohou způsobovat problémy
            # Extrémně nízká temperature (< 0.2) může způsobovat chrčení a dlouhé ticho
            safe_temperature = max(0.3, min(1.0, temperature)) if temperature < 0.3 else temperature
            if safe_temperature != temperature:
                print(f"⚠️ Temperature {temperature} je příliš nízká, upravuji na {safe_temperature} (min: 0.3)")

            # Extrémně vysoká length_penalty (> 1.5) může způsobovat velmi dlouhé generování
            safe_length_penalty = min(1.3, max(0.5, length_penalty)) if length_penalty > 1.3 else length_penalty
            if safe_length_penalty != length_penalty:
                print(f"⚠️ Length penalty {length_penalty} je příliš vysoká, upravuji na {safe_length_penalty} (max: 1.3)")

            # Extrémně nízká repetition_penalty (< 1.3) může způsobovat opakování
            safe_repetition_penalty = max(1.5, min(3.0, repetition_penalty)) if repetition_penalty < 1.5 else repetition_penalty
            if safe_repetition_penalty != repetition_penalty:
                print(f"⚠️ Repetition penalty {repetition_penalty} je příliš nízká, upravuji na {safe_repetition_penalty} (min: 1.5)")

            # Extrémně nízká top_p (< 0.3) může způsobovat problémy
            safe_top_p = max(0.5, min(0.95, top_p)) if top_p < 0.5 else top_p
            if safe_top_p != top_p:
                print(f"⚠️ Top-p {top_p} je příliš nízká, upravuji na {safe_top_p} (min: 0.5)")

            tts_params = {
                "text": text_for_model,
                "speaker_wav": speaker_wav,
                "language": language,
                "file_path": output_path,
                # speed se nepředává - použijeme post-processing místo toho
                "temperature": safe_temperature,
                "length_penalty": safe_length_penalty,
                "repetition_penalty": safe_repetition_penalty,
                "top_k": top_k,
                "top_p": safe_top_p
            }

            # Volitelné: použít caching conditioning latents (pokud to verze TTS podporuje)
            # Cíl: rychlejší opakované generování + stabilnější conditioning u stejného referenčního hlasu.
            try:
                from backend.config import ENABLE_SPEAKER_CACHE
                if ENABLE_SPEAKER_CACHE and self.model is not None:
                    import inspect
                    from backend.speaker_adapter import get_speaker_adapter

                    sig = None
                    try:
                        sig = inspect.signature(self.model.tts_to_file)
                    except Exception:
                        sig = None

                    if sig is not None:
                        param_names = set(sig.parameters.keys())
                        supports_embed = ("speaker_embeddings" in param_names) or ("speaker_embedding" in param_names)
                        supports_gpt = ("gpt_cond_latent" in param_names) or ("gpt_cond_latents" in param_names)

                        if supports_embed:
                            adapter = get_speaker_adapter()
                            latents = adapter.get_conditioning_latents(speaker_wav, self.model)
                            if latents is not None:
                                gpt_cond_latent, speaker_embedding = latents
                                # Přesuň na správný device, pokud je potřeba
                                try:
                                    device = self.device
                                    if hasattr(gpt_cond_latent, "to"):
                                        gpt_cond_latent = gpt_cond_latent.to(device)
                                    if hasattr(speaker_embedding, "to"):
                                        speaker_embedding = speaker_embedding.to(device)
                                except Exception:
                                    pass

                                # Preferuj embeddingy místo speaker_wav (aby se conditioning znovu nepočítal)
                                tts_params.pop("speaker_wav", None)
                                if "speaker_embeddings" in param_names:
                                    tts_params["speaker_embeddings"] = speaker_embedding
                                elif "speaker_embedding" in param_names:
                                    tts_params["speaker_embedding"] = speaker_embedding

                                if supports_gpt:
                                    if "gpt_cond_latent" in param_names:
                                        tts_params["gpt_cond_latent"] = gpt_cond_latent
                                    elif "gpt_cond_latents" in param_names:
                                        tts_params["gpt_cond_latents"] = gpt_cond_latent
            except Exception as e:
                print(f"⚠️ Conditioning cache nepoužit (ignorováno): {e}")

            # Logování parametrů pro debug
            print(f"🔊 TTS Generation Parameters:")
            print(f"   Speed: {speed}")
            print(f"   Temperature: {temperature}")
            print(f"   Length Penalty: {length_penalty}")
            print(f"   Repetition Penalty: {repetition_penalty}")
            print(f"   Top-K: {top_k}")
            print(f"   Top-P: {top_p}")
            print(f"   Quality Mode: {quality_mode if quality_mode else 'None (using individual params)'}")

            # Heartbeat mechanismus během XTTS inference (ukáže, že proces stále běží)
            heartbeat_stop = threading.Event()
            heartbeat_pct = [15.0]  # mutable pro thread

            def heartbeat_worker():
                """Aktualizuje progress pravidelně během inference"""
                import time
                # Odhad rychlosti: cca 15 znaků za sekundu na průměrném stroji
                # Pro 150 znaků (cca 10s) chceme dojít z 15% na 50% (+35%)
                char_count = len(text)
                estimated_seconds = max(3.0, char_count / 15.0)
                # Kolik procent přidat každých 0.5 sekundy
                increment = (35.0 / (estimated_seconds * 2.0))

                while not heartbeat_stop.is_set():
                    time.sleep(0.5)
                    if heartbeat_stop.is_set():
                        break
                    # Postupně zvyšuj progress (15% → 55% během inference)
                    # Častější malé updaty + CSS transition na FE vytvoří plynulý pohyb
                    heartbeat_pct[0] = min(55.0, heartbeat_pct[0] + increment)
                    _progress(heartbeat_pct[0], "tts", f"Generuji řeč… ({int(heartbeat_pct[0])}%)")

            heartbeat_thread = None
            if job_id:
                heartbeat_thread = threading.Thread(target=heartbeat_worker, daemon=True)
                heartbeat_thread.start()

            try:
                # Generování řeči
                # XTTS-v2 podporuje tyto parametry přímo v tts_to_file:
                # - temperature: Teplota pro sampling (0.0-1.0)
                # - length_penalty: Length penalty (0.5-2.0)
                # - repetition_penalty: Repetition penalty (1.0-5.0)
                # - top_k: Top-k sampling (1-100)
                # - top_p: Top-p sampling (0.0-1.0)
                # POZNÁMKA: speed se nepředává - použijeme post-processing místo toho
                # Pokud některý parametr není podporován, XTTS ho ignoruje nebo vyhodí TypeError
                try:
                    result = self.model.tts_to_file(**tts_params)
                except TypeError as e:
                    # Pokud některý parametr není podporován, zkusíme bez volitelných parametrů
                    error_msg = str(e)
                    print(f"⚠️ Warning: Some parameters may not be supported: {error_msg}")
                    print("   Attempting with basic parameters only (temperature)...")

                    # Základní parametry + pouze temperature (nejčastěji podporované)
                    basic_params = {
                        # Použij stejný text jako pro hlavní inference, aby se na konci nečetla "tečka"
                        "text": text_for_model,
                        "speaker_wav": speaker_wav,
                        "language": language,
                        "file_path": output_path,
                        "temperature": temperature
                    }

                    result = self.model.tts_to_file(**basic_params)
                    print("   ⚠️ Note: Some advanced parameters (length_penalty, repetition_penalty, top_k, top_p) may not be supported by this XTTS version")
            finally:
                # Zastav heartbeat
                if heartbeat_thread:
                    heartbeat_stop.set()
                    heartbeat_thread.join(timeout=1.0)

            # Zkontroluj, jestli soubor byl vytvořen
            if not Path(output_path).exists():
                raise Exception(f"Output file was not created: {output_path}")

            _progress(55, "tts", "XTTS inference dokončeno")

            _progress(58, "upsample", "Načítám audio…")
            # Post-processing: trimování PŘED upsamplingem (odstraní ticho a artefakty dříve)
            # XTTS-v2 generuje na 22050-24000 Hz, ale chceme CD kvalitu (44100 Hz)
            try:
                import librosa
                import soundfile as sf

                # Načtení audio s původní sample rate
                audio, sr = librosa.load(output_path, sr=None)
                original_length = len(audio) / sr

                # TRIMOVÁNÍ PŘED UPSAMPLINGEM - důležité pro odstranění ticha a artefaktů
                # Pro krátké texty použij agresivnější trim
                word_count = len(text.split())
                is_short_text = word_count <= 3

                if is_short_text or original_length > 10.0:
                    try:
                        from backend.vad_processor import get_vad_processor
                        from backend.config import ENABLE_VAD

                        if ENABLE_VAD:
                            vad_processor = get_vad_processor()
                            padding = 20.0 if is_short_text else 50.0
                            audio_trimmed = vad_processor.trim_silence_vad(
                                audio,
                                sample_rate=sr,
                                padding_ms=padding
                            )
                            if audio_trimmed is not None and len(audio_trimmed) > 0:
                                audio = audio_trimmed
                                print(f"✂️ VAD trim (před upsamplingem): {original_length:.1f}s → {len(audio)/sr:.1f}s")
                        else:
                            # Fallback: agresivnější librosa trim
                            top_db = 40 if is_short_text else 30
                            audio, _ = librosa.effects.trim(audio, top_db=top_db, frame_length=2048, hop_length=512)
                            print(f"✂️ Librosa trim (před upsamplingem): {original_length:.1f}s → {len(audio)/sr:.1f}s")
                    except Exception as e:
                        # Fallback: agresivnější librosa trim
                        top_db = 40 if is_short_text else 30
                        audio, _ = librosa.effects.trim(audio, top_db=top_db, frame_length=2048, hop_length=512)
                        print(f"✂️ Fallback trim (před upsamplingem): {original_length:.1f}s → {len(audio)/sr:.1f}s")

                # Maximální délka pro krátké texty (před upsamplingem)
                if is_short_text:
                    max_duration_samples = int(5.0 * sr)
                    if len(audio) > max_duration_samples:
                        print(f"⚠️ Krátký text ({word_count} slova) je příliš dlouhý ({len(audio)/sr:.1f}s), ořezávám na 5s")
                        audio = audio[:max_duration_samples]

                # Upsampling na cílovou sample rate (pokud je jiná)
                if sr != OUTPUT_SAMPLE_RATE:
                    _progress(62, "upsample", f"Převzorkování z {sr} Hz na {OUTPUT_SAMPLE_RATE} Hz…")
                    print(f"🎵 Upsampling audio z {sr} Hz na {OUTPUT_SAMPLE_RATE} Hz (CD kvalita)...")
                    audio = librosa.resample(audio, orig_sr=sr, target_sr=OUTPUT_SAMPLE_RATE)
                    sr = OUTPUT_SAMPLE_RATE
                    print(f"✅ Audio upsamplováno na {OUTPUT_SAMPLE_RATE} Hz")

                # Prosody post-processing (intonace a emphasis) - před enhancement
                if prosody_metadata:
                    try:
                        from backend.intonation_processor import IntonationProcessor
                        from backend.audio_enhancer import AudioEnhancer
                        from backend.config import ENABLE_INTONATION_PROCESSING, ENABLE_PROSODY_CONTROL

                        # Intonační post-processing
                        if ENABLE_INTONATION_PROCESSING and prosody_metadata.get('intonation'):
                            _progress(63, "intonation", "Aplikuji intonaci…")
                            intonation_metadata = prosody_metadata.get('intonation', [])

                            if intonation_metadata:
                                print(f"🎵 Aplikuji {len(intonation_metadata)} intonačních změn…")
                                applied_count = 0

                                for i, inton in enumerate(intonation_metadata):
                                    inton_type = inton.get('intonation_type')
                                    contour = inton.get('contour')
                                    content = inton.get('content', '')
                                    position = inton.get('position', 0)
                                    length = inton.get('length', len(content))
                                    intensity = inton.get('intensity', 1.0)
                                    auto_detected = inton.get('auto_detected', False)

                                    print(f"   Intonace {i+1}: type={inton_type}, auto={auto_detected}, content='{content[:50]}', pos={position}, len={length}")

                                    # Vypočítej pozice v audio (relativní k původnímu textu)
                                    text_length = len(text)
                                    if text_length > 0:
                                        start_ratio = position / text_length
                                        end_ratio = (position + length) / text_length

                                        start_sample = int(start_ratio * len(audio))
                                        end_sample = int(end_ratio * len(audio))

                                        print(f"      Audio: text_len={text_length}, audio_len={len(audio)}, start={start_sample}, end={end_sample}")

                                        if start_sample < end_sample and end_sample <= len(audio):
                                            if contour:
                                                # Aplikuj konturu
                                                segment = audio[start_sample:end_sample]
                                                modified_segment = IntonationProcessor.apply_contour(
                                                    segment, sr, contour
                                                )
                                                audio[start_sample:end_sample] = modified_segment
                                                applied_count += 1
                                                print(f"      ✅ Kontura aplikována na segment {start_sample}-{end_sample}")
                                            elif inton_type:
                                                # Pro automaticky detekovanou intonaci
                                                if auto_detected and inton_type in ['FALL', 'RISE', 'HALF_FALL']:
                                                    segment_length = end_sample - start_sample

                                                    # Pro FALL aplikuj na celou větu pro výraznější a přirozenější pokles
                                                    if inton_type == 'FALL':
                                                        # Aplikuj FALL na celou větu - profil už má pokles jen na konci
                                                        intonation_start = start_sample
                                                        intonation_end = end_sample

                                                        # Zkontroluj, jestli je to vykřičník (vyšší intenzita)
                                                        is_exclamation = inton.get('is_exclamation', False)
                                                        if is_exclamation:
                                                            # Pro vykřičník použij mírně vyšší intenzitu
                                                            fall_intensity = 1.2
                                                            print(f"      Auto-detekce FALL (vykřičník!): aplikuji na celou větu ({intonation_start}-{intonation_end}, 100% věty, intensity={fall_intensity})")
                                                        else:
                                                            # Přirozená intenzita pro běžný FALL
                                                            fall_intensity = 1.1
                                                            print(f"      Auto-detekce FALL: aplikuji na celou větu ({intonation_start}-{intonation_end}, 100% věty, intensity={fall_intensity})")
                                                    elif inton_type == 'RISE':
                                                        # Pro RISE stačí posledních 40% - stoupání je výraznější
                                                        intonation_start = start_sample + int(segment_length * 0.6)
                                                        intonation_end = end_sample
                                                        fall_intensity = intensity
                                                        print(f"      Auto-detekce RISE: aplikuji na konec ({intonation_start}-{intonation_end}, {100*(intonation_end-intonation_start)/segment_length:.0f}% věty)")
                                                    else:  # HALF_FALL
                                                        intonation_start = start_sample + int(segment_length * 0.7)
                                                        intonation_end = end_sample
                                                        fall_intensity = intensity
                                                        print(f"      Auto-detekce HALF_FALL: aplikuji na konec ({intonation_start}-{intonation_end}, {100*(intonation_end-intonation_start)/segment_length:.0f}% věty)")

                                                    if intonation_start < intonation_end:
                                                        audio = IntonationProcessor.apply_intonation_to_segment(
                                                            audio, sr, intonation_start, intonation_end,
                                                            inton_type, fall_intensity if inton_type == 'FALL' else intensity
                                                        )
                                                        applied_count += 1
                                                        print(f"      ✅ Intonace {inton_type} aplikována na segment {intonation_start}-{intonation_end}")
                                                    else:
                                                        # Pokud je segment příliš krátký, aplikuj na celý
                                                        audio = IntonationProcessor.apply_intonation_to_segment(
                                                            audio, sr, start_sample, end_sample,
                                                            inton_type, fall_intensity if inton_type == 'FALL' else intensity
                                                        )
                                                        applied_count += 1
                                                        print(f"      ✅ Intonace {inton_type} aplikována na celý segment {start_sample}-{end_sample} (segment příliš krátký)")
                                                else:
                                                    # Pro explicitní značky aplikuj na celý segment
                                                    audio = IntonationProcessor.apply_intonation_to_segment(
                                                        audio, sr, start_sample, end_sample,
                                                        inton_type, intensity
                                                    )
                                                    applied_count += 1
                                                    print(f"      ✅ Intonace {inton_type} aplikována na segment {start_sample}-{end_sample}")
                                        else:
                                            print(f"      ⚠️ Intonace NENÍ aplikována: start={start_sample}, end={end_sample}, audio_len={len(audio)}")

                                print(f"✅ Intonace aplikována: {applied_count}/{len(intonation_metadata)}")

                        # Emphasis post-processing
                        if ENABLE_PROSODY_CONTROL and prosody_metadata.get('emphasis'):
                            _progress(64, "emphasis", "Aplikuji důraz…")
                            emphasis_metadata = prosody_metadata.get('emphasis', [])

                            if emphasis_metadata:
                                print(f"💪 Aplikuji {len(emphasis_metadata)} důrazů…")
                                applied_count = 0

                                for i, emph in enumerate(emphasis_metadata):
                                    level = emph.get('level', 'MODERATE')
                                    # Použij zpracovaný obsah a pozici (pokud existuje), jinak původní
                                    processed_content = emph.get('processed_content', emph.get('content', ''))
                                    processed_position = emph.get('processed_position', emph.get('position', 0))
                                    processed_length = emph.get('processed_length', len(processed_content))
                                    auto_detected_emphasis = emph.get('auto_detected', False)

                                    print(f"   Emphasis {i+1}: level={level}, auto={auto_detected_emphasis}, content='{emph.get('content', '')[:30]}', processed='{processed_content[:30]}', pos={processed_position}, len={processed_length}")

                                    # Vypočítej pozice v audio (relativní k zpracovanému textu)
                                    text_length = len(text)
                                    if text_length > 0:
                                        # Odhad délky emphasis segmentu v audio
                                        if processed_length > 0:
                                            content_ratio = processed_length / text_length
                                            segment_length = int(content_ratio * len(audio))

                                            # Najdi pozici v audio
                                            position_ratio = processed_position / text_length
                                            start_sample = int(position_ratio * len(audio))
                                            end_sample = min(start_sample + segment_length, len(audio))

                                            print(f"      Audio: text_len={text_length}, audio_len={len(audio)}, start={start_sample}, end={end_sample}, segment_len={segment_length}")

                                            if start_sample < end_sample and end_sample <= len(audio):
                                                # Aplikuj emphasis efekt na segment
                                                segment = audio[start_sample:end_sample]
                                                # Pro STRONG použij jemnější intenzitu (0.5), pro MODERATE standardní (0.6)
                                                # Pro automaticky detekovaný emphasis z vykřičníku použij ještě vyšší intenzitu
                                                if auto_detected_emphasis and emph.get('source') == 'exclamation':
                                                    # Bezpečný důraz pro vykřičník (bez přebuzení)
                                                    emphasis_intensity = 0.7
                                                elif level == 'STRONG':
                                                    emphasis_intensity = 0.5  # Sníženo z 0.8 na 0.5 pro jemnější důraz
                                                else:
                                                    emphasis_intensity = 0.6  # Sníženo z 0.7 na 0.6
                                                modified_segment = AudioEnhancer.apply_emphasis_effect(
                                                    segment, sr, level=level, intensity=emphasis_intensity
                                                )

                                                # Vlož zpět s vyhlazením přechodů
                                                fade_samples = min(int(sr * 0.01), len(modified_segment) // 4)  # 10ms fade
                                                if fade_samples > 0:
                                                    fade_in = np.linspace(0.0, 1.0, fade_samples)
                                                    fade_out = np.linspace(1.0, 0.0, fade_samples)
                                                    modified_segment[:fade_samples] *= fade_in
                                                    modified_segment[-fade_samples:] *= fade_out

                                                audio[start_sample:end_sample] = modified_segment
                                                applied_count += 1
                                                print(f"      ✅ Emphasis aplikován na segment {start_sample}-{end_sample}")
                                            else:
                                                print(f"      ⚠️ Emphasis NENÍ aplikován: start={start_sample}, end={end_sample}, audio_len={len(audio)}")
                                        else:
                                            print(f"      ⚠️ Emphasis NENÍ aplikován: processed_length=0")
                                    else:
                                        print(f"      ⚠️ Emphasis NENÍ aplikován: text_length=0")

                                print(f"✅ Důraz aplikován: {applied_count}/{len(emphasis_metadata)}")

                        # Rate post-processing (rychlost řeči)
                        if ENABLE_PROSODY_CONTROL and prosody_metadata.get('rate_changes'):
                            _progress(65, "rate", "Aplikuji rychlost…")
                            rate_metadata = prosody_metadata.get('rate_changes', [])

                            if rate_metadata:
                                print(f"⚡ Aplikuji {len(rate_metadata)} změn rychlosti…")

                                for rate_info in rate_metadata:
                                    rate = rate_info.get('rate', 'NORMAL')
                                    content = rate_info.get('content', '')
                                    position = rate_info.get('position', 0)

                                    # Vypočítej pozice v audio
                                    text_length = len(text)
                                    if text_length > 0:
                                        content_length = len(content)
                                        if content_length > 0:
                                            content_ratio = content_length / text_length
                                            segment_length = int(content_ratio * len(audio))

                                            position_ratio = position / text_length
                                            start_sample = int(position_ratio * len(audio))
                                            end_sample = min(start_sample + segment_length, len(audio))

                                            if start_sample < end_sample and end_sample <= len(audio):
                                                # Aplikuj rate efekt na segment
                                                segment = audio[start_sample:end_sample]
                                                modified_segment = AudioEnhancer.apply_rate_effect(
                                                    segment, sr, rate=rate, intensity=1.0
                                                )

                                                # Vlož zpět s vyhlazením přechodů
                                                fade_samples = min(int(sr * 0.01), len(modified_segment) // 4)
                                                if fade_samples > 0:
                                                    fade_in = np.linspace(0.0, 1.0, fade_samples)
                                                    fade_out = np.linspace(1.0, 0.0, fade_samples)
                                                    modified_segment[:fade_samples] *= fade_in
                                                    modified_segment[-fade_samples:] *= fade_out

                                                # Pokud se délka změnila, musíme upravit audio
                                                length_diff = len(modified_segment) - len(segment)
                                                if length_diff != 0:
                                                    # Vytvoř nové audio s upravenou délkou
                                                    new_audio = np.zeros(len(audio) + length_diff, dtype=audio.dtype)
                                                    new_audio[:start_sample] = audio[:start_sample]
                                                    new_audio[start_sample:start_sample + len(modified_segment)] = modified_segment
                                                    new_audio[start_sample + len(modified_segment):] = audio[end_sample:]
                                                    audio = new_audio
                                                else:
                                                    audio[start_sample:end_sample] = modified_segment

                                print(f"✅ Rychlost aplikována")

                        # Pitch post-processing (výška hlasu)
                        if ENABLE_PROSODY_CONTROL and prosody_metadata.get('pitch_changes'):
                            _progress(66, "pitch", "Aplikuji výšku hlasu…")
                            pitch_metadata = prosody_metadata.get('pitch_changes', [])

                            if pitch_metadata:
                                print(f"🎵 Aplikuji {len(pitch_metadata)} změn výšky hlasu…")

                                for pitch_info in pitch_metadata:
                                    pitch = pitch_info.get('pitch', 'NORMAL')
                                    content = pitch_info.get('content', '')
                                    position = pitch_info.get('position', 0)

                                    # Vypočítej pozice v audio
                                    text_length = len(text)
                                    if text_length > 0:
                                        content_length = len(content)
                                        if content_length > 0:
                                            content_ratio = content_length / text_length
                                            segment_length = int(content_ratio * len(audio))

                                            position_ratio = position / text_length
                                            start_sample = int(position_ratio * len(audio))
                                            end_sample = min(start_sample + segment_length, len(audio))

                                            if start_sample < end_sample and end_sample <= len(audio):
                                                # Aplikuj pitch efekt na segment
                                                segment = audio[start_sample:end_sample]
                                                modified_segment = AudioEnhancer.apply_pitch_effect(
                                                    segment, sr, pitch=pitch, intensity=1.0
                                                )

                                                # Vlož zpět s vyhlazením přechodů
                                                fade_samples = min(int(sr * 0.01), len(modified_segment) // 4)
                                                if fade_samples > 0:
                                                    fade_in = np.linspace(0.0, 1.0, fade_samples)
                                                    fade_out = np.linspace(1.0, 0.0, fade_samples)
                                                    modified_segment[:fade_samples] *= fade_in
                                                    modified_segment[-fade_samples:] *= fade_out

                                                audio[start_sample:end_sample] = modified_segment

                                print(f"✅ Výška hlasu aplikována")
                    except Exception as e:
                        print(f"⚠️ Warning: Prosody post-processing selhal: {e}")

                # Uložení s upsamplovaným audio (před enhancement)
                sf.write(output_path, audio, sr)
                _progress(65, "upsample", "Upsampling dokončen")

            except Exception as e:
                print(f"⚠️ Warning: Post-processing (upsampling) failed: {e}, continuing with original audio")
                # Pokračujeme s původním audio

            # Post-processing audio enhancement (pokud je zapnuto)
            if ENABLE_AUDIO_ENHANCEMENT and (enable_enhancement is None or enable_enhancement):
                try:
                    # Použít předaný enhancement_preset, nebo výchozí z configu (pro kompatibilitu se starým kódem)
                    preset_to_use = enhancement_preset if enhancement_preset else AUDIO_ENHANCEMENT_PRESET

                    # Progress callback wrapper: mapuje 0-100 z AudioEnhancer na 68-88 v celkovém progressu
                    def enhance_progress(percent: float, stage: str, message: str):
                        mapped_percent = 68.0 + (percent / 100.0) * 20.0  # 68-88%
                        _progress(mapped_percent, "enhance", message)

                    # Volání jednotné enhancement metody
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
                    print(f"Warning: Audio enhancement failed: {e}, continuing with original audio")
                    _progress(88, "enhance", "Enhancement přeskočen (chyba)")

            # HiFi-GAN Vocoder refinement (pokud zapnuto)
            # POZNÁMKA: Musí být před změnou rychlosti, aby speed nebyl přepsán
            if use_hifigan and self.vocoder.is_available():
                try:
                    _progress(93, "hifigan", "HiFi-GAN refinement…")
                    import librosa
                    import soundfile as sf

                    print("🚀 Aplikuji HiFi-GAN vocoder refinement...")
                    # Načtení aktuálního audio
                    audio, sr = librosa.load(output_path, sr=None)
                    original_audio = audio.copy()  # Uložit pro případné blending

                    # 1. Výpočet mel-spectrogramu z vygenerovaného audio
                    # Použijeme parametry z configu
                    mel_params = self.vocoder.mel_params
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

                    # OPRAVA: HiFi-GAN očekává log-mel (v dB), ne power-mel
                    # Použijeme stabilnější logaritmickou transformaci
                    mel_log = np.log10(np.maximum(mel, 1e-5))

                    # 2. Resyntéza pomocí HiFi-GAN (s blending pokud je intensity < 1.0)
                    # Použij per-request parametry (předané z API)
                    refined_audio = self.vocoder.vocode(
                        mel_log,
                        sample_rate=sr,
                        original_audio=original_audio,
                        refinement_intensity=hifigan_refinement_intensity,
                        normalize_output=hifigan_normalize_output,
                        normalize_gain=hifigan_normalize_gain
                    )

                    if refined_audio is not None:
                        # Uložení vylepšeného audio
                        sf.write(output_path, refined_audio, sr)
                        used_intensity = hifigan_refinement_intensity if hifigan_refinement_intensity is not None else config.HIFIGAN_REFINEMENT_INTENSITY
                        intensity_str = f" (intensity: {used_intensity:.2f})" if used_intensity is not None and used_intensity < 1.0 else ""
                        print(f"✅ HiFi-GAN refinement dokončen{intensity_str}")
                    else:
                        print("⚠️ HiFi-GAN vocoding vrátil None, refinement přeskočen")

                except Exception as e:
                    print(f"⚠️ Warning: HiFi-GAN refinement selhal: {e}")

            # Změna rychlosti pomocí time_stretch (pokud speed != 1.0)
            # POZNÁMKA: Musí být až PO HiFi-GAN, aby se změna rychlosti nepřepsala
            # XTTS může nepodporovat parametr speed, takže použijeme post-processing
            speed_float = float(speed) if speed is not None else 1.0

            # Tolerance kvůli float porovnání
            if abs(speed_float - 1.0) > 0.001:
                # Preferujeme FFmpeg atempo: mění tempo bez změny výšky (pitch)
                try:
                    _progress(95, "speed", f"Úprava rychlosti na {speed_float}x…")
                    import os
                    import subprocess
                    from backend.audio_processor import AudioProcessor

                    if AudioProcessor._check_ffmpeg():
                        print(f"🎚️  Aplikuji změnu rychlosti (tempo) přes FFmpeg atempo: {speed_float}x")
                        tmp_path = f"{output_path}.tmp_speed.wav"
                        # atempo podporuje 0.5–2.0 (což odpovídá validaci v API)
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
                        print("✅ Rychlost změněna (FFmpeg atempo)")
                    else:
                        raise FileNotFoundError("FFmpeg není dostupný")
                except Exception as e:
                    # Fallback bez FFmpeg: resample (změní i výšku hlasu), ale rychlost bude fungovat
                    try:
                        import librosa
                        import soundfile as sf

                        print(
                            f"⚠️  FFmpeg atempo nelze použít ({e}). "
                            f"Použiji fallback přes resampling (změní i výšku): {speed_float}x"
                        )
                        audio, sr = librosa.load(output_path, sr=None)
                        # Pro rychlejší řeč potřebujeme méně samplů => target_sr = sr / speed
                        target_sr = max(8000, int(sr / speed_float))
                        audio_rs = librosa.resample(audio, orig_sr=sr, target_sr=target_sr)
                        # Zapíšeme při původním sr -> efekt rychlosti (s posunem pitch)
                        sf.write(output_path, audio_rs, sr)
                        print("✅ Rychlost změněna (fallback resampling)")
                    except Exception as e2:
                        print(f"⚠️ Warning: Změna rychlosti selhala i ve fallbacku: {e2}, pokračuji bez změny rychlosti")
            else:
                # Normální rychlost
                pass

            # Finální headroom (po VŠEM): vždy, aby UI headroom měl efekt i když enhancement neběží / selže,
            # a aby se headroom dorovnal po HiFi-GAN / změně rychlosti.
            try:
                _progress(97, "final", "Finální úpravy (headroom)…")
                import librosa
                import soundfile as sf

                audio, sr = librosa.load(output_path, sr=None)
                final_headroom_db = target_headroom_db if target_headroom_db is not None else OUTPUT_HEADROOM_DB
                if final_headroom_db is not None:
                    try:
                        # Headroom funguje jako "ceiling" (strop): pokud je peak nad cílem, ztlumíme.
                        # Nechceme nikdy zesilovat tiché výstupy, protože to působí, že posuvník "nefunguje".
                        peak = float(np.max(np.abs(audio))) if audio is not None and len(audio) else 0.0
                        if peak > 0:
                            if float(final_headroom_db) < 0:
                                target_peak = 10 ** (float(final_headroom_db) / 20.0)
                            else:
                                target_peak = 0.999

                            if peak > target_peak:
                                scale = target_peak / peak
                                audio = audio * scale
                                try:
                                    peak_after = float(np.max(np.abs(audio))) if audio is not None and len(audio) else 0.0
                                    print(
                                        f"🔉 Headroom ceiling detail: headroom_db={float(final_headroom_db):.1f} dB, "
                                        f"peak_before={peak:.4f}, target_peak={target_peak:.4f}, scale={scale:.4f}, peak_after={peak_after:.4f}"
                                    )
                                except Exception:
                                    pass
                            else:
                                # Pod cílem nic neděláme (nezesilujeme)
                                try:
                                    print(
                                        f"🔉 Headroom ceiling: headroom_db={float(final_headroom_db):.1f} dB, "
                                        f"peak_before={peak:.4f} <= target_peak={target_peak:.4f} (bez změny)"
                                    )
                                except Exception:
                                    pass

                        if not np.isfinite(audio).all():
                            audio = np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0)
                    except Exception:
                        audio = np.clip(audio, -0.999, 0.999)

                    sf.write(output_path, audio, sr)
                    print(f"🔉 Finální headroom ceiling: {final_headroom_db} dB (aplikováno jen pokud peak přesáhl cíl)")
            except Exception as e:
                print(f"⚠️ Warning: Finální headroom selhal: {e}")
            # 99% necháme až pro úplně poslední krok v backend/main.py (těsně před done=100),
            # ať to v UI nevypadá, že je to "hotové", ale ještě dlouho to stojí.
            _progress(96, "final", "Dokončuji…")

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Generate error details:\n{error_details}")
            raise Exception(f"Chyba při generování řeči: {str(e)}")



    async def warmup(self, demo_voice_path: Optional[str] = None):
        """
        Zahřeje model prvním inference

        Args:
            demo_voice_path: Cesta k demo hlasu pro warmup
        """
        await self.model_manager.warmup(demo_voice_path, generate_func=self.generate)

    async def generate_multi_pass(
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
        enhancement_preset: Optional[str] = None,
        variant_count: int = 3,
        enable_batch: Optional[bool] = None,
        enable_vad: Optional[bool] = None,
        use_hifigan: bool = False,
        enable_normalization: bool = True,
        enable_denoiser: bool = True,
        enable_compressor: bool = True,
        enable_deesser: bool = True,
        enable_eq: bool = True,
        enable_trim: bool = True,
        enable_whisper: Optional[bool] = None,
        whisper_intensity: Optional[float] = None,
        target_headroom_db: Optional[float] = None,
        hifigan_refinement_intensity: Optional[float] = None,
        hifigan_normalize_output: Optional[bool] = None,
        hifigan_normalize_gain: Optional[float] = None,
        enable_enhancement: Optional[bool] = None,
        enable_dialect_conversion: Optional[bool] = None,
        dialect_code: Optional[str] = None,
        dialect_intensity: float = 1.0,
        job_id: Optional[str] = None
    ) -> List[dict]:
        """
        Generuje více variant řeči s různými parametry

        Args:
            text: Text k syntéze
            speaker_wav: Cesta k audio souboru s hlasem
            language: Jazyk
            speed: Rychlost řeči
            temperature: Základní teplota
            length_penalty: Length penalty
            repetition_penalty: Repetition penalty
            top_k: Top-k sampling
            top_p: Top-p sampling
            quality_mode: Quality preset
            enhancement_preset: Enhancement preset
            variant_count: Počet variant k vygenerování
            enable_batch: Zapnout batch processing
            enable_vad: Zapnout VAD
            use_hifigan: Použít HiFi-GAN

        Returns:
            Seznam variant s metadaty
        """
        variants = []
        base_seed = 42

        # Variace teplot pro různé varianty
        temperature_variations = [
            temperature - 0.1,
            temperature,
            temperature + 0.1
        ]

        for i in range(variant_count):
            if job_id:
                try:
                    from backend.progress_manager import ProgressManager
                    ProgressManager.update(
                        job_id,
                        percent=2 + (90.0 * i / max(1, variant_count)),
                        stage="multi_pass",
                        message=f"Generuji variantu {i+1}/{variant_count}…",
                        meta_update={"variant": i + 1, "variants_total": variant_count},
                    )
                except Exception:
                    pass
            variant_seed = base_seed + i
            variant_temp = temperature_variations[i % len(temperature_variations)]

            # Generuj variantu
            output_path = await self.generate(
                text=text,
                speaker_wav=speaker_wav,
                language=language,
                speed=speed,
                temperature=variant_temp,
                length_penalty=length_penalty,
                repetition_penalty=repetition_penalty,
                top_k=top_k,
                top_p=top_p,
                quality_mode=quality_mode,
                seed=variant_seed,
                enhancement_preset=enhancement_preset,
                enable_enhancement=enable_enhancement,
                multi_pass=False,  # Zabrání rekurzi
                enable_batch=enable_batch,
                enable_vad=enable_vad,
                use_hifigan=use_hifigan,
                enable_normalization=enable_normalization,
                enable_denoiser=enable_denoiser,
                enable_compressor=enable_compressor,
                enable_deesser=enable_deesser,
                enable_eq=enable_eq,
                enable_trim=enable_trim,
                enable_whisper=enable_whisper,
                whisper_intensity=whisper_intensity,
                target_headroom_db=target_headroom_db,
                hifigan_refinement_intensity=hifigan_refinement_intensity,
                hifigan_normalize_output=hifigan_normalize_output,
                hifigan_normalize_gain=hifigan_normalize_gain,
                enable_dialect_conversion=enable_dialect_conversion,
                dialect_code=dialect_code,
                dialect_intensity=dialect_intensity,
                job_id=job_id
            )

            filename = Path(output_path).name
            audio_url = f"/api/audio/{filename}"

            variants.append({
                "audio_url": audio_url,
                "filename": filename,
                "seed": variant_seed,
                "temperature": variant_temp,
                "index": i + 1
            })

        return variants

    async def generate_batch(
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
        job_id: Optional[str] = None
    ) -> str:
        """
        Generuje řeč pro dlouhý text pomocí batch processing

        Args:
            text: Text k syntéze
            speaker_wav: Cesta k audio souboru s hlasem
            language: Jazyk
            speed: Rychlost řeči
            temperature: Teplota
            length_penalty: Length penalty
            repetition_penalty: Repetition penalty
            top_k: Top-k sampling
            top_p: Top-p sampling
            quality_mode: Quality preset
            seed: Seed
            enhancement_preset: Enhancement preset
            enable_vad: Zapnout VAD
            use_hifigan: Použít HiFi-GAN

        Returns:
            Cesta k finálnímu spojenému audio souboru
        """
        from backend.audio_concatenator import AudioConcatenator

        # Rozděl text na části podle XTTS tokenů (ochrana proti limitu 400 tokenů)
        chunks = self._split_text_by_xtts_tokens(text, language=language)
        token_counts = [self._count_xtts_tokens(c, language) for c in chunks]
        # fallback na délku v znacích, pokud tokenizer není k dispozici
        units = [(tc if tc is not None and tc > 0 else max(1, len(ch))) for tc, ch in zip(token_counts, chunks)]
        total_units = max(1, sum(units))
        done_units = 0

        if job_id:
            try:
                from backend.progress_manager import ProgressManager
                ProgressManager.update(
                    job_id,
                    percent=3,
                    stage="batch_prepare",
                    message=f"Rozděleno na {len(chunks)} částí…",
                    meta_update={"chunks_total": len(chunks), "total_units": total_units, "unit": "tokens_or_chars"},
                )
            except Exception:
                pass

        if len(chunks) == 1:
            # Pokud je jen jedna část, použij standardní generování
            return await self.generate(
                text=text,
                speaker_wav=speaker_wav,
                language=language,
                speed=speed,
                temperature=temperature,
                length_penalty=length_penalty,
                repetition_penalty=repetition_penalty,
                top_k=top_k,
                top_p=top_p,
                quality_mode=quality_mode,
                seed=seed,
                enhancement_preset=enhancement_preset,
                multi_pass=False,
                enable_batch=False,
                enable_vad=enable_vad,
                use_hifigan=use_hifigan,
                enable_normalization=enable_normalization,
                enable_denoiser=enable_denoiser,
                enable_compressor=enable_compressor,
                enable_deesser=enable_deesser,
                enable_eq=enable_eq,
                enable_trim=enable_trim,
                enable_dialect_conversion=enable_dialect_conversion,
                dialect_code=dialect_code,
                dialect_intensity=dialect_intensity,
                job_id=job_id
            )

        print(f"📦 Batch processing: rozděleno na {len(chunks)} částí")

        # Generuj každou část
        audio_files = []
        for i, chunk in enumerate(chunks):
            if job_id:
                try:
                    from backend.progress_manager import ProgressManager
                    # ETA: odhad z už hotových částí (sekundy / unit), po 1. části je to už celkem stabilní
                    now = time.time()
                    started_at = ProgressManager.get(job_id).get("started_at", now)  # type: ignore[union-attr]
                    elapsed = max(0.0, now - float(started_at))
                    rate = (elapsed / done_units) if done_units > 0 else None
                    remaining = max(0, total_units - done_units)
                    eta = int(rate * remaining) if rate is not None else None

                    percent = 5 + (85.0 * done_units / total_units)
                    ProgressManager.update(
                        job_id,
                        percent=percent,
                        eta_seconds=eta,
                        stage="batch",
                        message=f"Generuji část {i+1}/{len(chunks)}…",
                        meta_update={"chunk": i + 1, "chunks_total": len(chunks), "done_units": done_units},
                    )
                except Exception:
                    pass
            print(f"   Generuji část {i+1}/{len(chunks)}...")
            chunk_output = await self.generate(
                text=chunk,
                speaker_wav=speaker_wav,
                language=language,
                speed=speed,
                temperature=temperature,
                length_penalty=length_penalty,
                repetition_penalty=repetition_penalty,
                top_k=top_k,
                top_p=top_p,
                quality_mode=quality_mode,
                seed=seed,
                enhancement_preset=enhancement_preset,
                multi_pass=False,
                enable_batch=False,
                enable_vad=enable_vad,
                use_hifigan=use_hifigan,
                enable_normalization=enable_normalization,
                enable_denoiser=enable_denoiser,
                enable_compressor=enable_compressor,
                enable_deesser=enable_deesser,
                enable_eq=enable_eq,
                enable_trim=enable_trim,
                enable_dialect_conversion=enable_dialect_conversion,
                dialect_code=dialect_code,
                dialect_intensity=dialect_intensity,
                job_id=job_id
            )
            audio_files.append(chunk_output)
            done_units += units[i]

            if job_id:
                try:
                    from backend.progress_manager import ProgressManager
                    now = time.time()
                    started_at = ProgressManager.get(job_id).get("started_at", now)  # type: ignore[union-attr]
                    elapsed = max(0.0, now - float(started_at))
                    rate = elapsed / max(1, done_units)
                    remaining = max(0, total_units - done_units)
                    eta = int(rate * remaining)
                    percent = 5 + (85.0 * done_units / total_units)
                    ProgressManager.update(
                        job_id,
                        percent=percent,
                        eta_seconds=eta,
                        stage="batch",
                        message=f"Hotovo {i+1}/{len(chunks)} částí…",
                        meta_update={"done_units": done_units},
                    )
                except Exception:
                    pass

        # Spoj audio části
        output_filename = f"{uuid.uuid4()}.wav"
        output_path = OUTPUTS_DIR / output_filename

        print(f"🔗 Spojuji {len(audio_files)} audio částí...")
        if job_id:
            try:
                from backend.progress_manager import ProgressManager
                # concat + post tvoří posledních ~10–15%
                ProgressManager.update(job_id, percent=92, stage="concat", message="Spojuji části…", eta_seconds=5)
            except Exception:
                pass
        AudioConcatenator.concatenate_audio(
            audio_files,
            str(output_path),
            crossfade_ms=50
        )

        # Smazat dočasné části
        for audio_file in audio_files:
            try:
                Path(audio_file).unlink()
            except:
                pass

        print(f"✅ Batch processing dokončen: {output_path}")
        if job_id:
            try:
                from backend.progress_manager import ProgressManager
                ProgressManager.update(job_id, percent=95, stage="post", message="Dokončuji…")
            except Exception:
                pass
        return str(output_path)

    async def generate_multi_lang_speaker(
        self,
        text: str,
        default_speaker_wav: str,
        default_language: str = "cs",
        speaker_map: Optional[Dict[str, str]] = None,
        job_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generuje řeč pro text s více jazyky a mluvčími

        Podporuje syntaxi: [lang:speaker]text[/lang] nebo [lang]text[/lang]

        Args:
            text: Text s anotacemi [lang:speaker]text[/lang]
            default_speaker_wav: Výchozí mluvčí pro neanotované části
            default_language: Výchozí jazyk
            speaker_map: Mapování speaker_id -> speaker_wav_path
            job_id: ID jobu pro progress tracking
            **kwargs: Ostatní parametry (speed, temperature, atd.)

        Returns:
            Cesta k finálnímu audio souboru
        """
        from backend.multi_lang_speaker_processor import MultiLangSpeakerProcessor
        import re

        # Nejdříve zpracuj pauzy - rozsekej text podle [pause:ms] a pak parsuj každý kus
        # Podporované formy: [pause], [pause:200], [pause=200], [pause:200ms]
        pause_re = re.compile(r"\[pause(?:\s*[:=]\s*(\d+)\s*(?:ms)?)?\]", re.IGNORECASE)
        pause_matches = list(pause_re.finditer(text))

        # Pokud jsou v textu pauzy, rozsekej text a zpracuj každý kus zvlášť
        if pause_matches:
            print(f"⏸️  Detekovány pauzy v multi-lang textu: {len(pause_matches)} pauz")
            text_parts = []
            pauses_between = []
            last_pos = 0

            for m in pause_matches:
                # Text před pauzou
                part_before = text[last_pos:m.start()].strip()
                if part_before:
                    text_parts.append(part_before)

                # Délka pauzy
                dur_raw = m.group(1)
                try:
                    dur = int(dur_raw) if dur_raw is not None else 500
                except Exception:
                    dur = 500
                dur = max(0, min(dur, 10000))  # 0–10s safety
                pauses_between.append(dur)

                last_pos = m.end()

            # Zbytek textu po poslední pauze
            tail = text[last_pos:].strip()
            if tail:
                text_parts.append(tail)

            # Pokud máme části s pauzami, zpracuj každou část zvlášť a spoj s pauzami
            if len(text_parts) > 1:
                print(f"   Rozděleno na {len(text_parts)} částí s {len(pauses_between)} pauzami")
                audio_files = []

                # Vytvoř processor
                default_lang = default_language if default_language else "cs"
                processor = MultiLangSpeakerProcessor(
                    default_language=default_lang,
                    default_speaker=default_speaker_wav
                )

                # Registruj mluvčí
                if speaker_map:
                    for speaker_id, speaker_wav in speaker_map.items():
                        processor.register_speaker(speaker_id, speaker_wav)

                # Zpracuj každou část zvlášť
                for i, part_text in enumerate(text_parts):
                    part_segments = processor.parse_text(part_text)

                    # Pokud má část jen jeden segment, použij standardní generování
                    if len(part_segments) == 1:
                        seg = part_segments[0]
                        # Odstraň enable_batch z kwargs, protože ho explicitně nastavujeme
                        part_kwargs = {k: v for k, v in kwargs.items() if k != 'enable_batch'}
                        part_audio = await self.generate(
                            text=seg.text,
                            speaker_wav=seg.speaker_wav or default_speaker_wav,
                            language=seg.language,
                            enable_batch=False,
                            handle_pauses=False,  # Pauzy už jsme zpracovali
                            job_id=None,
                            **part_kwargs
                        )
                        audio_files.append(part_audio)
                    else:
                        # Více segmentů v části - generuj každý segment zvlášť a spoj
                        part_audio_files = []
                        for seg in part_segments:
                            # Odstraň enable_trim a enable_batch z kwargs, protože ho explicitně nastavujeme
                            seg_kwargs = {k: v for k, v in kwargs.items() if k not in ('enable_trim', 'enable_batch')}
                            seg_audio = await self.generate(
                                text=seg.text,
                                speaker_wav=seg.speaker_wav or default_speaker_wav,
                                language=seg.language,
                                enable_batch=False,
                                handle_pauses=False,
                                enable_trim=False,
                                job_id=None,
                                **seg_kwargs
                            )
                            part_audio_files.append(seg_audio)

                        # Spoj segmenty části
                        from backend.audio_concatenator import AudioConcatenator
                        temp_output = OUTPUTS_DIR / f"{uuid.uuid4()}.wav"
                        AudioConcatenator.concatenate_audio(
                            part_audio_files,
                            str(temp_output),
                            crossfade_ms=100
                        )
                        # Uklidit dočasné segmenty
                        for af in part_audio_files:
                            try:
                                Path(af).unlink()
                            except Exception:
                                pass
                        part_audio = str(temp_output)
                        audio_files.append(part_audio)

                    # Přidej pauzu po části (kromě poslední)
                    if i < len(pauses_between):
                        pause_ms = pauses_between[i]
                        # Pauza se přidá při spojování

                # Spoj všechny části s pauzami
                from backend.audio_concatenator import AudioConcatenator
                output_filename = f"{uuid.uuid4()}.wav"
                output_path = OUTPUTS_DIR / output_filename

                # Spoj s pauzami
                concatenated_audio = []
                import librosa
                import soundfile as sf
                import numpy as np
                sr = OUTPUT_SAMPLE_RATE

                for i, audio_file in enumerate(audio_files):
                    audio, _ = librosa.load(audio_file, sr=sr)
                    concatenated_audio.append(audio)

                    # Přidej pauzu po části (kromě poslední)
                    if i < len(pauses_between):
                        pause_ms = pauses_between[i]
                        pause_samples = int(pause_ms * sr / 1000)
                        if pause_samples > 0:
                            print(f"⏱️  Pause[{i}]: {pause_ms} ms => {pause_samples} samples")
                            concatenated_audio.append(np.zeros(pause_samples, dtype=np.float32))

                final_audio = np.concatenate(concatenated_audio) if concatenated_audio else np.array([], dtype=np.float32)
                sf.write(str(output_path), final_audio, sr)

                # Uklidit dočasné soubory
                for audio_file in audio_files:
                    try:
                        Path(audio_file).unlink()
                    except Exception:
                        pass

                print(f"✅ Multi-lang/speaker generování s pauzami dokončeno: {output_path}")
                return str(output_path)

        # Pokud nejsou pauzy, pokračuj normálně
        # Vytvoř processor
        # Výchozí jazyk je čeština, pokud není zadán
        default_lang = default_language if default_language else "cs"
        processor = MultiLangSpeakerProcessor(
            default_language=default_lang,
            default_speaker=default_speaker_wav
        )

        # Registruj mluvčí
        if speaker_map:
            for speaker_id, speaker_wav in speaker_map.items():
                processor.register_speaker(speaker_id, speaker_wav)

        # Parsuj text na segmenty
        segments = processor.parse_text(text)

        if job_id:
            try:
                from backend.progress_manager import ProgressManager
                ProgressManager.update(
                    job_id,
                    percent=2,
                    stage="parse",
                    message=f"Parsováno {len(segments)} segmentů…",
                    meta_update={"segments_total": len(segments)}
                )
            except Exception:
                pass

        print(f"📝 Multi-lang/speaker: parsováno {len(segments)} segmentů")
        if len(segments) > 1:
            print(processor.get_segments_summary(segments))

        if len(segments) == 1:
            # Jen jeden segment - použij standardní generování
            segment = segments[0]

            # Pro cross-language generování uprav parametry
            segment_kwargs = kwargs.copy()
            # Odstraň enable_batch z kwargs, protože ho explicitně nastavujeme
            segment_kwargs.pop('enable_batch', None)
            speaker_wav_path = segment.speaker_wav or default_speaker_wav
            is_cross_language = False

            # Detekce cross-language: pokud je jazyk jiný než cs a hlas je pravděpodobně český
            if segment.language != "cs" and speaker_wav_path:
                speaker_name = Path(speaker_wav_path).stem.lower()
                czech_indicators = ['buchty', 'klepl', 'bohumil', 'werich', 'pohadka', 'brodsky', 'speakato']
                if any(indicator in speaker_name for indicator in czech_indicators):
                    is_cross_language = True
                    print(f"⚠️ Cross-language detekce: používá se český hlas ({speaker_name}) pro jazyk {segment.language}")
                    print(f"   Pro lepší kvalitu doporučujeme použít hlas v jazyce {segment.language}")
                    # Uprav parametry pro cross-language
                    if 'temperature' not in segment_kwargs or segment_kwargs.get('temperature', 0.7) < 0.5:
                        segment_kwargs['temperature'] = 0.7
                    if 'length_penalty' not in segment_kwargs or segment_kwargs.get('length_penalty', 1.0) > 1.2:
                        segment_kwargs['length_penalty'] = 1.0
                    if 'repetition_penalty' not in segment_kwargs or segment_kwargs.get('repetition_penalty', 2.0) < 1.5:
                        segment_kwargs['repetition_penalty'] = 2.0
                    print(f"   Upravené parametry pro cross-language: temp={segment_kwargs.get('temperature', 0.7)}, length_penalty={segment_kwargs.get('length_penalty', 1.0)}")

            result = await self.generate(
                text=segment.text,
                speaker_wav=speaker_wav_path,
                language=segment.language,
                enable_batch=False,  # Batch už řešíme na úrovni segmentů
                job_id=job_id,
                **segment_kwargs
            )

            # Pro krátké texty (1-3 slova) použij agresivnější trimování
            # XTTS často generuje dlouhé ticho pro velmi krátké texty
            # POZNÁMKA: Trimování se provádí v _generate_sync PŘED upsamplingem,
            # takže tady jen kontrolujeme délku a případně omezíme
            word_count = len(segment.text.split())
            if word_count <= 3:
                try:
                    import librosa
                    import soundfile as sf
                    audio, sr = librosa.load(result, sr=None)
                    original_length = len(audio) / sr

                    # Maximální délka pro krátké texty (5 sekund)
                    max_duration_samples = int(5.0 * sr)
                    if len(audio) > max_duration_samples:
                        print(f"⚠️ Krátký segment ({word_count} slova) je příliš dlouhý ({len(audio)/sr:.1f}s), ořezávám na 5s")
                        audio = audio[:max_duration_samples]
                        sf.write(result, audio, sr)
                        print(f"✂️ Finální ořez krátkého segmentu: {original_length:.1f}s → {len(audio)/sr:.1f}s")
                except Exception as e:
                    print(f"⚠️ Warning: Finální ořez krátkého segmentu selhal: {e}")

            return result

        # Generuj každý segment zvlášť
        audio_files = []
        for i, segment in enumerate(segments):
            if job_id:
                try:
                    from backend.progress_manager import ProgressManager
                    ProgressManager.update(
                        job_id,
                        percent=5 + (85.0 * i / max(1, len(segments))),
                        stage="multi_segment",
                        message=f"Generuji segment {i+1}/{len(segments)} ({segment.language})…",
                        meta_update={"segment": i + 1, "segments_total": len(segments), "language": segment.language}
                    )
                except Exception:
                    pass

            print(f"🎤 Generuji segment {i+1}/{len(segments)}: lang={segment.language}, speaker={segment.speaker_id or 'default'}")

            # Odstraň enable_trim a enable_batch z kwargs, protože ho explicitně nastavujeme
            segment_kwargs = {k: v for k, v in kwargs.items() if k not in ('enable_trim', 'enable_batch')}

            # Pro cross-language generování (např. český hlas pro anglický text) použij lepší parametry
            # XTTS může mít problémy s cross-language cloning, takže upravíme parametry
            speaker_wav_path = segment.speaker_wav or default_speaker_wav
            is_cross_language = False

            # Detekce cross-language: pokud je jazyk jiný než cs a hlas je pravděpodobně český
            if segment.language != "cs" and speaker_wav_path:
                # Zkontroluj název souboru - pokud obsahuje české názvy, je to cross-language
                speaker_name = Path(speaker_wav_path).stem.lower()
                czech_indicators = ['buchty', 'klepl', 'bohumil', 'werich', 'pohadka', 'brodsky', 'speakato']
                if any(indicator in speaker_name for indicator in czech_indicators):
                    is_cross_language = True
                    print(f"⚠️ Cross-language detekce: používá se český hlas ({speaker_name}) pro jazyk {segment.language}")
                    print(f"   Pro lepší kvalitu doporučujeme použít hlas v jazyce {segment.language}")
                    # Uprav parametry pro cross-language - vyšší temperature, nižší length_penalty
                    if 'temperature' not in segment_kwargs or segment_kwargs.get('temperature', 0.7) < 0.5:
                        segment_kwargs['temperature'] = 0.7  # Vyšší temperature pro lepší cross-language
                    if 'length_penalty' not in segment_kwargs or segment_kwargs.get('length_penalty', 1.0) > 1.2:
                        segment_kwargs['length_penalty'] = 1.0  # Nižší length_penalty pro kratší generování
                    if 'repetition_penalty' not in segment_kwargs or segment_kwargs.get('repetition_penalty', 2.0) < 1.5:
                        segment_kwargs['repetition_penalty'] = 2.0  # Vyšší repetition_penalty pro lepší kvalitu
                    print(f"   Upravené parametry pro cross-language: temp={segment_kwargs.get('temperature', 0.7)}, length_penalty={segment_kwargs.get('length_penalty', 1.0)}")

            segment_audio = await self.generate(
                text=segment.text,
                speaker_wav=speaker_wav_path,
                language=segment.language,
                enable_batch=False,  # Batch už řešíme na úrovni segmentů
                handle_pauses=False,  # Pauzy řešíme na úrovni spojování
                enable_trim=False,  # Vypneme trim pro jednotlivé segmenty - trimneme až při spojování
                job_id=None,  # Nepředáváme job_id do jednotlivých segmentů
                **segment_kwargs
            )

            # Pro krátké texty (1-3 slova) použij kontrolu délky před spojením
            # POZNÁMKA: Trimování se provádí v _generate_sync PŘED upsamplingem,
            # takže tady jen kontrolujeme délku a případně omezíme
            word_count = len(segment.text.split())
            if word_count <= 3:
                try:
                    import librosa
                    import soundfile as sf
                    audio, sr = librosa.load(segment_audio, sr=None)
                    original_length = len(audio) / sr

                    # Maximální délka pro krátké texty (5 sekund)
                    max_duration_samples = int(5.0 * sr)
                    if len(audio) > max_duration_samples:
                        print(f"⚠️ Krátký segment {i+1} ({word_count} slova) je příliš dlouhý ({len(audio)/sr:.1f}s), ořezávám na 5s")
                        audio = audio[:max_duration_samples]
                        sf.write(segment_audio, audio, sr)
                        print(f"✂️ Finální ořez segmentu {i+1}: {original_length:.1f}s → {len(audio)/sr:.1f}s")
                except Exception as e:
                    print(f"⚠️ Warning: Finální ořez krátkého segmentu selhal: {e}")

            audio_files.append(segment_audio)

        # Spoj všechny segmenty
        from backend.audio_concatenator import AudioConcatenator

        output_filename = f"{uuid.uuid4()}.wav"
        output_path = OUTPUTS_DIR / output_filename

        if job_id:
            try:
                from backend.progress_manager import ProgressManager
                ProgressManager.update(job_id, percent=92, stage="concat", message="Spojuji segmenty…")
            except Exception:
                pass

        print(f"🔗 Spojuji {len(audio_files)} audio segmentů...")
        AudioConcatenator.concatenate_audio(
            audio_files,
            str(output_path),
            crossfade_ms=100  # Zvýšený crossfade pro plynulejší přechody (100ms místo 50ms)
        )

        # Uklidit dočasné soubory
        for audio_file in audio_files:
            try:
                Path(audio_file).unlink()
            except Exception:
                pass

        print(f"✅ Multi-lang/speaker generování dokončeno: {output_path}")
        return str(output_path)

    def get_status(self) -> dict:
        """Vrátí status modelu"""
        return self.model_manager.get_status(vocoder=self.vocoder)

