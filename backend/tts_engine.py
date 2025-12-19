"""
XTTS-v2 TTS Engine wrapper
"""
import uuid
import asyncio
import threading
import warnings
from pathlib import Path
from typing import Optional, List
import re
import time
from TTS.api import TTS
import torch
import numpy as np
import backend.config as config
from num2words import num2words
from TTS.tts.layers.xtts import tokenizer as xtts_tokenizer

# Potlačení deprecation warning z librosa (pkg_resources je zastaralé, ale knihovna ho ještě používá)
warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated.*", category=UserWarning)
from backend.config import (
    DEVICE,
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
    ENABLE_PHONETIC_TRANSLATION
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
        self.model: Optional[TTS] = None
        self.device = DEVICE
        self.is_loading = False
        self.is_loaded = False
        self.vocoder = get_hifigan_vocoder()
        # None = ještě nezkoušeno, False = není dostupné, jinak tokenizer instance
        self._bpe_tokenizer = None

    def _get_bpe_tokenizer(self):
        """
        Vytvoří/vrátí XTTS BPE tokenizer (stejný tokenizer.json jako upstream XTTS).
        Používá se pro počítání tokenů a bezpečné dělení textu pod limit 400 tokenů.
        """
        if self._bpe_tokenizer is False:
            return None
        if self._bpe_tokenizer is not None:
            return self._bpe_tokenizer

        def _silence_len_warnings(tok_obj):
            # VoiceBpeTokenizer.encode() volá check_input_length(), která printuje warningy
            # při překročení char limitu (typicky 186 pro cs). To je pro nás při token-countingu
            # velmi hlučné a není to chyba, takže to ztišíme.
            try:
                if hasattr(tok_obj, "check_input_length"):
                    tok_obj.check_input_length = lambda *_args, **_kwargs: None
            except Exception:
                pass

        # 1) Zkus tokenizer přímo z modelu (nejspolehlivější)
        try:
            if self.model is not None and hasattr(self.model, "synthesizer"):
                tts_model = getattr(self.model.synthesizer, "tts_model", None)
                model_tokenizer = getattr(tts_model, "tokenizer", None)
                if model_tokenizer is not None:
                    _silence_len_warnings(model_tokenizer)
                    self._bpe_tokenizer = model_tokenizer
                    return self._bpe_tokenizer
        except Exception:
            pass

        # 2) Fallback: tokenizer.json z balíčku (ne všechny instalace ho bohužel obsahují)
        try:
            candidate = Path(getattr(xtts_tokenizer, "DEFAULT_VOCAB_FILE", "")).resolve()
            if not candidate.exists():
                # V některých build/instalacích je tokenizer.json uložen v assets (tortoise)
                base_tts_dir = Path(xtts_tokenizer.__file__).resolve().parents[2]  # .../TTS/tts
                alt = base_tts_dir / "utils" / "assets" / "tortoise" / "tokenizer.json"
                if alt.exists():
                    candidate = alt.resolve()

            if candidate.exists():
                tok = xtts_tokenizer.VoiceBpeTokenizer(str(candidate))
                _silence_len_warnings(tok)
                self._bpe_tokenizer = tok
                return self._bpe_tokenizer
        except Exception as e:
            print(f"Warning: XTTS tokenizer init failed: {e}")

        # 3) Nedostupné → necháme None a nebudeme znovu zkoušet (bez spamování warningů)
        self._bpe_tokenizer = False
        return None

    def _count_xtts_tokens(self, text: str, language: str = "cs") -> Optional[int]:
        """Vrátí počet XTTS tokenů pro daný text, nebo None pokud se to nepovede."""
        tok = self._get_bpe_tokenizer()
        if tok is None:
            return None
        try:
            # VoiceBpeTokenizer má encode(txt, lang) → ids
            if hasattr(tok, "encode"):
                return len(tok.encode(text, language))
        except Exception:
            return None
        return None

    def _split_text_by_xtts_tokens(self, text: str, language: str = "cs") -> List[str]:
        """
        Rozseká text tak, aby žádný chunk nepřekročil config.XTTS_TARGET_MAX_TOKENS.
        Preferuje dělení na koncích vět, pak na slovech, a nakonec nouzově po znacích.
        """
        max_tokens = getattr(config, "XTTS_TARGET_MAX_TOKENS", 380)
        text = re.sub(r"\s+", " ", (text or "").strip())
        if not text:
            return []

        # Pokud tokenizer není dostupný, drž se konzervativního char splitu (bez overlap = žádné opakování)
        if self._get_bpe_tokenizer() is None:
            try:
                from backend.text_splitter import TextSplitter
                return TextSplitter.split_text(text, max_length=MAX_CHUNK_LENGTH, overlap=0)
            except Exception:
                # úplný fallback: hrubé dělení po MAX_CHUNK_LENGTH znacích
                return [text[i:i + MAX_CHUNK_LENGTH].strip() for i in range(0, len(text), MAX_CHUNK_LENGTH) if text[i:i + MAX_CHUNK_LENGTH].strip()]

        n = self._count_xtts_tokens(text, language)
        if n is not None and n <= max_tokens:
            return [text]

        def split_hard_by_chars(s: str) -> List[str]:
            out: List[str] = []
            s = s.strip()
            if not s:
                return out
            start = 0
            while start < len(s):
                # binární vyhledání nejdelšího prefixu, který se vejde do token budgetu
                lo = start + 1
                hi = len(s)
                best = None
                while lo <= hi:
                    mid = (lo + hi) // 2
                    part = s[start:mid].strip()
                    if not part:
                        lo = mid + 1
                        continue
                    tn = self._count_xtts_tokens(part, language)
                    if tn is None:
                        # fallback: když selže tokenizer, řežeme po MAX_CHUNK_LENGTH znacích
                        best = min(start + MAX_CHUNK_LENGTH, len(s))
                        break
                    if tn <= max_tokens:
                        best = mid
                        lo = mid + 1
                    else:
                        hi = mid - 1

                if best is None:
                    best = start + 1
                chunk = s[start:best].strip()
                if chunk:
                    out.append(chunk)
                start = best
            return out

        def split_by_words(sentence: str) -> List[str]:
            words = [w for w in sentence.strip().split(" ") if w]
            out: List[str] = []
            cur = ""
            for w in words:
                cand = w if not cur else f"{cur} {w}"
                tn = self._count_xtts_tokens(cand, language)
                if tn is not None and tn <= max_tokens:
                    cur = cand
                    continue

                if cur:
                    out.append(cur)
                    cur = w
                    # Pokud i samotné slovo/fragment přetéká, řež tvrdě
                    if (self._count_xtts_tokens(cur, language) or (max_tokens + 1)) > max_tokens:
                        out.extend(split_hard_by_chars(cur))
                        cur = ""
                else:
                    out.extend(split_hard_by_chars(w))
                    cur = ""

            if cur:
                out.append(cur)
            return out

        # Primárně dělení na věty
        sentences = re.split(r"(?<=[.!?…])\s+", text)
        chunks: List[str] = []
        cur = ""
        for s in sentences:
            s = (s or "").strip()
            if not s:
                continue
            cand = s if not cur else f"{cur} {s}"
            tn = self._count_xtts_tokens(cand, language)
            if tn is not None and tn <= max_tokens:
                cur = cand
                continue

            if cur:
                chunks.append(cur)
                cur = ""

            # samotná věta je dlouhá → rozdělit podle slov / nouzově po znacích
            if (self._count_xtts_tokens(s, language) or (max_tokens + 1)) <= max_tokens:
                cur = s
            else:
                chunks.extend(split_by_words(s))

        if cur:
            chunks.append(cur)

        # Poslední pojistka: kdyby cokoli přeteklo (např. tokenizer None), dořež
        safe_chunks: List[str] = []
        for ch in chunks:
            tn = self._count_xtts_tokens(ch, language)
            if tn is None or tn <= max_tokens:
                safe_chunks.append(ch)
            else:
                safe_chunks.extend(split_hard_by_chars(ch))

        return [c for c in safe_chunks if c.strip()]

    async def load_model(self):
        """Načte XTTS-v2 model asynchronně"""
        if self.is_loaded:
            return

        if self.is_loading:
            # Počkej až se model načte
            while self.is_loading:
                await asyncio.sleep(0.5)
            return

        self.is_loading = True

        try:
            print(f"Loading XTTS-v2 on {self.device}...")

            # Načtení modelu v thread poolu (TTS není async)
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None,
                self._load_model_sync
            )

            self.is_loaded = True
            print("Model loaded successfully!")

        except Exception as e:
            print(f"Error loading model: {str(e)}")
            raise
        finally:
            self.is_loading = False

    def _load_model_sync(self) -> TTS:
        """Synchronní načtení modelu z Hugging Face nebo lokální cache"""
        print(f"Loading model: {XTTS_MODEL_NAME}")
        print("Model bude stažen z Hugging Face, pokud není v cache...")

        try:
            # Zkus nejprve TTS registry název (stabilnější)
            if XTTS_MODEL_NAME.startswith("coqui/"):
                # Převod z Hugging Face formátu na TTS registry
                model_name = "tts_models/multilingual/multi-dataset/xtts_v2"
                print(f"Trying TTS registry name: {model_name}")
            else:
                model_name = XTTS_MODEL_NAME

            # Načtení modelu s explicitním nastavením
            # Použijeme GPU pouze pokud je device nastaven na "cuda"
            use_gpu = (self.device == "cuda" and torch.cuda.is_available())
            model = TTS(
                model_name=model_name,
                progress_bar=True
            )

            # Optimalizace pro GPU s omezenou VRAM (6GB)
            if use_gpu and (USE_SMALL_MODELS or ENABLE_CPU_OFFLOAD):
                print("Applying GPU memory optimizations for 6GB VRAM...")
                if hasattr(model, 'synthesizer') and hasattr(model.synthesizer, 'tts_model'):
                    # Offload části modelu na CPU pokud je potřeba
                    if ENABLE_CPU_OFFLOAD:
                        print("CPU offload enabled - parts of model will be on CPU")

            # Explicitní přesun na device
            if hasattr(model, 'to'):
                model.to(self.device)
            elif hasattr(model, 'model') and hasattr(model.model, 'to'):
                model.model.to(self.device)

            return model

        except Exception as e1:
            print(f"First attempt failed: {str(e1)}")
            # Fallback: zkus přímo Hugging Face model
            try:
                print(f"Trying direct Hugging Face model: {XTTS_MODEL_NAME}")
                # Použijeme GPU pouze pokud je device nastaven na "cuda"
                use_gpu = (self.device == "cuda" and torch.cuda.is_available())
                model = TTS(
                    model_name=XTTS_MODEL_NAME,
                    progress_bar=True
                )
                if hasattr(model, 'to'):
                    model.to(self.device)
                elif hasattr(model, 'model') and hasattr(model.model, 'to'):
                    model.model.to(self.device)
                return model
            except Exception as e2:
                print(f"Both attempts failed. Error 1: {str(e1)}, Error 2: {str(e2)}")
                raise Exception(f"Failed to load model: {str(e2)}")

    def _apply_quality_preset(self, preset: str) -> dict:
        """
        Aplikuje quality preset na TTS parametry

        Args:
            preset: Název presetu (high_quality, natural, fast)

        Returns:
            Slovník s TTS parametry
        """
        preset_config = QUALITY_PRESETS.get(preset, QUALITY_PRESETS["natural"])

        # Vrátit pouze TTS parametry (bez enhancement)
        tts_params = {
            "speed": preset_config.get("speed", 1.0),
            "temperature": preset_config.get("temperature", 0.7),
            "length_penalty": preset_config.get("length_penalty", 1.0),
            "repetition_penalty": preset_config.get("repetition_penalty", 2.0),
            "top_k": preset_config.get("top_k", 50),
            "top_p": preset_config.get("top_p", 0.85)
        }

        return tts_params

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

        # Aplikace quality preset pokud je zadán - MUSÍ být PŘED kontrolou multi-pass a batch
        # aby se parametry správně aplikovaly ve všech případech
        if quality_mode:
            preset_params = self._apply_quality_preset(quality_mode)
            # Rychlost (speed) chceme zachovat z parametrů volání,
            # protože ji uživatel nastavuje v UI posuvníkem
            # speed = preset_params["speed"]
            temperature = preset_params["temperature"]
            length_penalty = preset_params["length_penalty"]
            repetition_penalty = preset_params["repetition_penalty"]
            top_k = preset_params["top_k"]
            top_p = preset_params["top_p"]
            print(f"🎯 Quality mode '{quality_mode}' aplikován - parametry přepsány z presetu")

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
                job_id=job_id
            )

        # Prosody preprocessing
        try:
            from backend.prosody_processor import ProsodyProcessor
            if ENABLE_PROSODY_CONTROL:
                text, _ = ProsodyProcessor.process_text(text)
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
            job_id
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
        job_id: Optional[str] = None
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
            processed_text = self._preprocess_text_for_czech(text, language)
            _progress(15, "tts", "Generuji řeč (XTTS)…")

            # Příprava parametrů pro tts_to_file
            # Vždy předáváme všechny parametry, ne jen když se liší od výchozích hodnot
            # POZNÁMKA: XTTS-v2 nemusí podporovat parametr "speed" přímo v tts_to_file,
            # takže změnu rychlosti provádíme pomocí post-processing (viz níže)
            tts_params = {
                "text": processed_text,
                "speaker_wav": speaker_wav,
                "language": language,
                "file_path": output_path,
                # speed se nepředává - použijeme post-processing místo toho
                "temperature": temperature,
                "length_penalty": length_penalty,
                "repetition_penalty": repetition_penalty,
                "top_k": top_k,
                "top_p": top_p
            }

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
                        "text": processed_text,
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
            # Post-processing: upsampling
            # XTTS-v2 generuje na 22050 Hz, ale chceme CD kvalitu (44100 Hz)
            try:
                import librosa
                import soundfile as sf

                # Načtení audio s původní sample rate
                audio, sr = librosa.load(output_path, sr=None)

                # Upsampling na cílovou sample rate (pokud je jiná)
                if sr != OUTPUT_SAMPLE_RATE:
                    _progress(62, "upsample", f"Převzorkování z {sr} Hz na {OUTPUT_SAMPLE_RATE} Hz…")
                    print(f"🎵 Upsampling audio z {sr} Hz na {OUTPUT_SAMPLE_RATE} Hz (CD kvalita)...")
                    audio = librosa.resample(audio, orig_sr=sr, target_sr=OUTPUT_SAMPLE_RATE)
                    sr = OUTPUT_SAMPLE_RATE
                    print(f"✅ Audio upsamplováno na {OUTPUT_SAMPLE_RATE} Hz")

                # Uložení s upsamplovaným audio (před enhancement)
                sf.write(output_path, audio, sr)
                _progress(65, "upsample", "Upsampling dokončen")

            except Exception as e:
                print(f"⚠️ Warning: Post-processing (upsampling) failed: {e}, continuing with original audio")
                # Pokračujeme s původním audio

            # Post-processing audio enhancement (pokud je zapnuto)
            if ENABLE_AUDIO_ENHANCEMENT:
                try:
                    # Rozděl enhancement na více kroků pro lepší progress feedback
                    _progress(68, "enhance", "Načítám audio pro enhancement…")
                    import librosa
                    import soundfile as sf
                    audio, sr = librosa.load(output_path, sr=OUTPUT_SAMPLE_RATE)

                    # Použít předaný enhancement_preset, nebo výchozí z configu
                    preset_to_use = enhancement_preset if enhancement_preset else AUDIO_ENHANCEMENT_PRESET

                    # Počítáme aktivní kroky pro správné rozložení procent
                    active_steps = []
                    if enable_trim:
                        active_steps.append("trim")
                    if enable_denoiser:
                        active_steps.append("denoiser")
                    if enable_eq:
                        active_steps.append("eq")
                    if enable_compressor:
                        active_steps.append("compressor")
                    if enable_deesser:
                        active_steps.append("deesser")
                    active_steps.append("final")  # fade + DC + normalizace

                    step_size = 20.0 / max(1, len(active_steps))  # 68-88% pro enhancement
                    current_pct = 68.0

                    # 1. Trim (pokud zapnuto)
                    if enable_trim:
                        current_pct += step_size
                        _progress(current_pct, "enhance", "Ořez ticha…")
                        try:
                            from backend.vad_processor import get_vad_processor
                            from backend.config import ENABLE_VAD
                            if ENABLE_VAD:
                                vad_processor = get_vad_processor()
                                audio = vad_processor.trim_silence_vad(audio, sr)
                            else:
                                audio, _ = librosa.effects.trim(audio, top_db=25)
                        except Exception:
                            audio, _ = librosa.effects.trim(audio, top_db=25)

                    # 2. Noise reduction (pokud zapnuto)
                    if enable_denoiser:
                        current_pct += step_size
                        _progress(current_pct, "enhance", "Redukce šumu…")
                        audio = AudioEnhancer.reduce_noise_advanced(audio, sr)

                    # 3. EQ (pokud zapnuto)
                    if enable_eq:
                        current_pct += step_size
                        _progress(current_pct, "enhance", "EQ korekce…")
                        audio = AudioEnhancer.apply_eq(audio, sr)

                    # 4. Komprese (pokud zapnuto)
                    if enable_compressor:
                        current_pct += step_size
                        _progress(current_pct, "enhance", "Komprese dynamiky…")
                        audio = AudioEnhancer.compress_dynamic_range(audio, ratio=2.5)

                    # 5. De-esser (pokud zapnuto)
                    if enable_deesser:
                        current_pct += step_size
                        _progress(current_pct, "enhance", "De-esser…")
                        audio = AudioEnhancer.apply_deesser(audio, sr)

                    # 6. Fade in/out + DC offset + normalizace
                    current_pct += step_size
                    _progress(current_pct, "enhance", "Finální úpravy enhancement…")
                    audio = AudioEnhancer.apply_fade(audio, sr, fade_ms=50)
                    audio = AudioEnhancer.remove_dc_offset(audio)

                    if enable_normalization:
                        audio = AudioEnhancer.normalize_audio(audio, peak_target_db=-3.0, rms_target_db=-18.0)

                    # Uložení
                    sf.write(output_path, audio, sr)
                    _progress(88, "enhance", "Enhancement dokončen")
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
                    refined_audio = self.vocoder.vocode(
                        mel_log,
                        sample_rate=sr,
                        # Vždy předáme originál; vocoder si podle aktuální intensity z configu rozhodne,
                        # jestli blendovat (UI → backend.main dočasně přepíše config hodnoty).
                        original_audio=original_audio
                    )

                    if refined_audio is not None:
                        # Uložení vylepšeného audio
                        sf.write(output_path, refined_audio, sr)
                        intensity = config.HIFIGAN_REFINEMENT_INTENSITY
                        intensity_str = f" (intensity: {intensity:.2f})" if intensity < 1.0 else ""
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

            # Finální headroom (po VŠEM): stáhne hlasitost, aby výstup nepůsobil "přebuzile"
            # Aplikuje se i když je normalizace/komprese vypnutá, protože samotný model může generovat hodně "hot" signál.
            try:
                _progress(97, "final", "Finální úpravy (headroom)…")
                import librosa
                import soundfile as sf

                audio, sr = librosa.load(output_path, sr=None)
                gain = 10 ** (float(OUTPUT_HEADROOM_DB) / 20.0)  # např. -6 dB => ~0.501
                audio = audio * gain
                # bezpečnostní clip (float WAV může jít mimo rozsah)
                audio = np.clip(audio, -1.0, 1.0)
                sf.write(output_path, audio, sr)
                print(f"🔉 Aplikuji finální headroom: {OUTPUT_HEADROOM_DB} dB")
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

    def _preprocess_text_for_czech(self, text: str, language: str) -> str:
        """
        Předzpracuje text pro češtinu - převede čísla na slova, normalizuje interpunkci,
        převede zkratky a opraví formátování
        """
        if language != "cs":
            return text

        import re

        # Normalizace typografických mezer (často se používají před % apod.)
        # NBSP (U+00A0) a NNBSP (U+202F) → obyčejná mezera
        text = (text or "").replace("\u00A0", " ").replace("\u202F", " ")
        # Normalizace různých unicode variant procenta na ASCII %
        text = text.replace("％", "%").replace("﹪", "%")

        # 0. Fonetický přepis cizích slov (před ostatním předzpracováním)
        if ENABLE_PHONETIC_TRANSLATION:
            translator = get_phonetic_translator()
            text = translator.translate_foreign_words(text, target_language="cs")

        # 1. Normalizace interpunkce
        text = text.replace("...", "…")
        text = text.replace("--", "—")
        text = text.replace("''", '"')
        text = text.replace("``", '"')

        # 2. Převod zkratek na plné formy
        abbreviations = {
            "např.": "například",
            "atd.": "a tak dále",
            "tj.": "to jest",
            "tzn.": "to znamená",
            "apod.": "a podobně",
            "př.": "příklad",
            "č.": "číslo",
            "str.": "strana",
            "s.": "strana",
            "r.": "rok",
            "m.": "měsíc",
            "min.": "minuta",
            "sek.": "sekunda",
            "km/h": "kilometrů za hodinu",
            "m/s": "metrů za sekundu",
            "cca": "přibližně",
            "atp.": "a tak podobně",
            "tzv.": "takzvaný",
            "vč.": "včetně",
            "vč": "včetně",
            "čes.": "český",
            "angl.": "anglický",
            "tel.": "telefon",
            "č.p.": "číslo popisné",
            "č.j.": "číslo jednací",
            "Kč": "korun českých",
            "mil.": "milionů",
            "mld.": "miliard",
            "tis.": "tisíc"
        }
        for abbr, full in abbreviations.items():
            # Nahradit pouze celá slova (s mezerami nebo interpunkcí)
            # Použijeme regex, který bere v úvahu i tečku na konci zkratky
            if abbr.endswith('.'):
                pattern = r'\b' + re.escape(abbr)
            else:
                pattern = r'\b' + re.escape(abbr) + r'\b'
            text = re.sub(pattern, full, text, flags=re.IGNORECASE)

        # 3. Zpracování interpunkce pro prosody (pauzy a intonace)
        # Tečka = delší pauza (2 mezery) - model automaticky klesne hlasem u konce věty
        # Otazník = delší pauza (2 mezery) - model automaticky stoupne hlasem
        # Vykřičník = delší pauza (2 mezery) - model automaticky zdůrazní
        # Čárka = kratší pauza (1 mezera)

        # Najdeme konce vět (tečka, otazník, vykřičník) následované mezerou nebo koncem textu
        # a přidáme více mezer pro delší pauzu
        # Pattern: písmeno + interpunkce + mezera/ konec (ne číslo před tečkou, to jsou zkratky jako "1.")
        text = re.sub(r'([a-záčďéěíňóřšťúůýžA-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ])([.!?])(\s|$)', r'\1\2  \3', text)

        # Čárky - zajistíme mezeru po čárce (pokud tam není),
        # ALE nesmíme rozbít desetinná čísla typu "0,13" → tam mezera být nemá.
        text = re.sub(r'(?<!\d),(?!\d)(\S)', r', \1', text)

        # Normalizace mezer
        # Nejdřív odstraníme mezery před interpunkcí
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)
        # Pak normalizujeme více mezer na jednu, ale zachováme 2 mezery po konci věty
        text = re.sub(r' {3,}', ' ', text)  # Více než 2 mezery na jednu
        # Zachováme 2 mezery po konci věty (tečka, otazník, vykřičník) pro delší pauzu
        text = re.sub(r'([.!?])(\s)', r'\1  \2', text)
        text = text.strip()

        # 4. Rozšířený převod čísel na slova
        # 4a. Převod řadových číslovek (70., 1., atd.) s kontextovým skloňováním
        # Slovník pro určení rodu a čísla podle následujícího slova
        context_words = {
            # Střední rod, množné číslo (sedmdesátá) - "70. let" = "sedmdesátá léta"
            'let': ('s', 'mn'), 'léta': ('s', 'mn'), 'letá': ('s', 'mn'),

            # Ženský rod, množné číslo (sedmdesátá)
            'minuty': ('ž', 'mn'), 'minut': ('ž', 'mn'),
            'sekundy': ('ž', 'mn'), 'sekund': ('ž', 'mn'),
            'hodiny': ('ž', 'mn'), 'hodin': ('ž', 'mn'),
            'strany': ('ž', 'mn'), 'stran': ('ž', 'mn'),
            'kapitoly': ('ž', 'mn'), 'kapitol': ('ž', 'mn'),
            'stránky': ('ž', 'mn'), 'stránek': ('ž', 'mn'),
            'strany': ('ž', 'mn'), 'stran': ('ž', 'mn'),
            'knihy': ('ž', 'mn'), 'knih': ('ž', 'mn'),
            'karty': ('ž', 'mn'), 'karet': ('ž', 'mn'),
            'řady': ('ž', 'mn'), 'řad': ('ž', 'mn'),

            # Mužský rod, jednotné číslo (sedmdesátý)
            'rok': ('m', 'j'), 'roku': ('m', 'j'), 'roce': ('m', 'j'),
            'den': ('m', 'j'), 'dne': ('m', 'j'), 'dni': ('m', 'j'),
            'měsíc': ('m', 'j'), 'měsíce': ('m', 'j'), 'měsíci': ('m', 'j'),
            'týden': ('m', 'j'), 'týdne': ('m', 'j'), 'týdnu': ('m', 'j'),
            'článek': ('m', 'j'), 'článku': ('m', 'j'), 'článkem': ('m', 'j'),
            'bod': ('m', 'j'), 'bodu': ('m', 'j'), 'bodem': ('m', 'j'),
            'paragraf': ('m', 'j'), 'paragrafu': ('m', 'j'), 'paragrafem': ('m', 'j'),
            'list': ('m', 'j'), 'listu': ('m', 'j'), 'listem': ('m', 'j'),
            'svazek': ('m', 'j'), 'svazku': ('m', 'j'), 'svazkem': ('m', 'j'),
            'díl': ('m', 'j'), 'dílu': ('m', 'j'), 'dílem': ('m', 'j'),
            'krok': ('m', 'j'), 'kroku': ('m', 'j'), 'krokem': ('m', 'j'),
            'úkol': ('m', 'j'), 'úkolu': ('m', 'j'), 'úkolem': ('m', 'j'),
            'projekt': ('m', 'j'), 'projektu': ('m', 'j'), 'projektem': ('m', 'j'),
            'závod': ('m', 'j'), 'závodu': ('m', 'j'), 'závodem': ('m', 'j'),
            'soutěž': ('ž', 'j'), 'soutěže': ('ž', 'j'), 'soutěží': ('ž', 'j'),

            # Střední rod, jednotné číslo (sedmdesáté)
            'výročí': ('s', 'j'), 'výročím': ('s', 'j'),
            'století': ('s', 'j'), 'stoletím': ('s', 'j'),
            'desetiletí': ('s', 'j'), 'desetiletím': ('s', 'j'),
            'pololetí': ('s', 'j'), 'pololetím': ('s', 'j'),
            'čtvrtletí': ('s', 'j'), 'čtvrtletím': ('s', 'j'),
        }

        def get_ordinal_form(num: int, gender: str = 'm', number: str = 'j') -> str:
            """Vrátí správnou formu řadové číslovky podle rodu a čísla"""
            try:
                # Speciální případy pro malá čísla
                if num == 1:
                    return 'první'
                elif num == 2:
                    if number == 'mn':
                        return 'druhá'
                    elif gender == 's':
                        return 'druhé'
                    elif gender == 'ž':
                        return 'druhá'
                    else:
                        return 'druhý'
                elif num == 3:
                    return 'třetí'
                elif num == 4:
                    if number == 'mn':
                        return 'čtvrtá'
                    elif gender == 's':
                        return 'čtvrté'
                    elif gender == 'ž':
                        return 'čtvrtá'
                    else:
                        return 'čtvrtý'

                # Základní tvar pomocí num2words
                base = num2words(num, ordinal=True, lang='cs')

                # Upravíme podle rodu a čísla
                if number == 'mn':
                    # Množné číslo: sedmdesátý -> sedmdesátá (pro střední i ženský rod)
                    if base.endswith('ý'):
                        return base[:-1] + 'á'
                    elif base.endswith('í'):
                        return base  # Třetí, pátý atd. zůstávají
                    elif base.endswith('é'):
                        return base  # Už je správně
                elif gender == 's' and number == 'j':
                    # Střední rod, jednotné číslo: sedmdesátý -> sedmdesáté
                    if base.endswith('ý'):
                        return base[:-1] + 'é'
                    elif base.endswith('í'):
                        return base  # Třetí zůstane
                elif gender == 'ž' and number == 'j':
                    # Ženský rod, jednotné číslo: sedmdesátý -> sedmdesátá
                    if base.endswith('ý'):
                        return base[:-1] + 'á'
                    elif base.endswith('í'):
                        return base
                # Mužský rod, jednotné číslo zůstane jako base (sedmdesátý)

                return base
            except:
                # Fallback na základní tvar
                return num2words(num, ordinal=True, lang='cs')

        # Pattern pro řadové číslovky s následujícím slovem
        ordinal_with_context_pattern = r'\b([0-9]{1,3})\.\s+([a-záčďéěíňóřšťúůýž]+)\b'

        def replace_ordinal_with_context(match):
            num_str = match.group(1)
            next_word = match.group(2).lower()

            try:
                num = int(num_str)
                # Zkontroluj, jestli následující slovo má definovaný kontext
                if next_word in context_words:
                    gender, number = context_words[next_word]
                    return get_ordinal_form(num, gender, number) + ' ' + match.group(2)
                else:
                    # Výchozí: mužský rod, jednotné číslo
                    ordinal = num2words(num, ordinal=True, lang='cs')
                    return ordinal + ' ' + match.group(2)
            except:
                return match.group(0)

        # Nejdřív zpracujeme řadové číslovky s kontextem
        text = re.sub(ordinal_with_context_pattern, replace_ordinal_with_context, text, flags=re.IGNORECASE)

        # Pak zpracujeme samostatné řadové číslovky (bez následujícího slova)
        ordinal_pattern = r'\b([0-9]{1,3})\.\b'
        def replace_ordinal(match):
            num_str = match.group(1)
            try:
                num = int(num_str)
                # Výchozí: mužský rod, jednotné číslo
                ordinal = num2words(num, ordinal=True, lang='cs')
                return ordinal
            except:
                return match.group(0)
        text = re.sub(ordinal_pattern, replace_ordinal, text)

        # Slovník pro základní čísla (0-100)
        number_words = {
            0: "nula", 1: "jedna", 2: "dva", 3: "tři", 4: "čtyři", 5: "pět",
            6: "šest", 7: "sedm", 8: "osm", 9: "devět", 10: "deset",
            11: "jedenáct", 12: "dvanáct", 13: "třináct", 14: "čtrnáct", 15: "patnáct",
            16: "šestnáct", 17: "sedmnáct", 18: "osmnáct", 19: "devatenáct", 20: "dvacet",
            30: "třicet", 40: "čtyřicet", 50: "padesát", 60: "šedesát",
            70: "sedmdesát", 80: "osmdesát", 90: "devadesát", 100: "sto"
        }

        def number_to_words(num_str: str) -> str:
            """Převede číslo na slovo (jednoduchá verze)"""
            try:
                num = int(num_str)
                if num in number_words:
                    return number_words[num]
                elif num < 100:
                    tens = (num // 10) * 10
                    ones = num % 10
                    if tens in number_words and ones in number_words:
                        return f"{number_words[tens]} {number_words[ones]}"
                # Pro větší čísla použijeme jednoduchý převod
                # nebo necháme číslo jako text
                return num_str
            except:
                return num_str

        # 4b. Převod desetinných čísel a procent
        def decimal_to_words(match, has_percent=False):
            """Převede desetinné číslo na slova"""
            whole_part = match.group(1)  # část před čárkou
            decimal_part = match.group(2)  # část za čárkou

            try:
                whole_num = int(whole_part) if whole_part else 0
                decimal_num = int(decimal_part)
                decimal_len = len(decimal_part)

                # Převod celé části
                if whole_num == 0:
                    whole_text = "nula"
                else:
                    whole_text = number_to_words(str(whole_num))

                # Převod desetinné části podle počtu desetinných míst
                if decimal_len == 1:
                    # Desetiny: 0,1 = "jedna desetina"
                    if decimal_num == 1:
                        decimal_text = "jedna desetina"
                    elif decimal_num == 2:
                        decimal_text = "dvě desetiny"
                    elif decimal_num in [3, 4]:
                        decimal_text = f"{number_to_words(str(decimal_num))} desetiny"
                    else:
                        decimal_text = f"{number_to_words(str(decimal_num))} desetin"
                elif decimal_len == 2:
                    # Setiny: 0,13 = "třináct setin"
                    if decimal_num < 20:
                        decimal_text = f"{number_to_words(str(decimal_num))} setin"
                    else:
                        tens = (decimal_num // 10) * 10
                        ones = decimal_num % 10
                        if ones == 0:
                            decimal_text = f"{number_to_words(str(tens))} setin"
                        else:
                            decimal_text = f"{number_to_words(str(tens))} {number_to_words(str(ones))} setin"
                elif decimal_len == 3:
                    # Tisíciny
                    if decimal_num == 1:
                        decimal_text = "jedna tisícina"
                    elif decimal_num == 2:
                        decimal_text = "dvě tisíciny"
                    elif decimal_num in [3, 4]:
                        decimal_text = f"{number_to_words(str(decimal_num))} tisíciny"
                    else:
                        decimal_text = f"{number_to_words(str(decimal_num))} tisícin"
                else:
                    # Pro více míst použijeme jednodušší formu
                    decimal_text = f"{number_to_words(str(decimal_num))}"

                # Správné skloňování "celý" podle celé části:
                # 0,13  → "nula celých třináct setin"
                # 1,13  → "jedna celá třináct setin"
                # 2,13  → "dva celé třináct setin" (běžněji "dvě celé", ale zde držíme základní převod)
                # 3,13  → "tři celé ..."
                # 5,13  → "pět celých ..."
                if whole_num == 1:
                    whole_suffix = "celá"
                elif whole_num in [2, 3, 4]:
                    whole_suffix = "celé"
                else:
                    whole_suffix = "celých"

                result = f"{whole_text} {whole_suffix} {decimal_text}"
                if has_percent:
                    # Pro TTS je nejstabilnější podstatné jméno ve tvaru "procent" (např. 0,13 procent).
                    result += " procent"

                return result
            except:
                return match.group(0)

        # 4b0. Procentní (adjektivní) zápis bez mezery: "10% sleva" → "desetiprocentní sleva"
        # Pozn.: Tady řešíme primárně případy s celými čísly 1–3 cifry.
        percent_adjective_pattern = r'\b([0-9]{1,3})[%％]\s*([a-záčďéěíňóřšťúůýžA-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ])'
        def replace_percent_adjective(match):
            num_str = match.group(1)
            next_char = match.group(2)
            num_word = number_to_words(num_str)
            # spojení do jednoho slova (TTS to čte lépe než "X procentní")
            compact = re.sub(r'\s+', '', num_word)
            return f"{compact}procentní {next_char}"
        text = re.sub(percent_adjective_pattern, replace_percent_adjective, text)

        # Pattern pro desetinná čísla:
        # - 0,13 % / 0,13%  (mezery okolo čárky a před % jsou povolené)
        # - 0,13           (mezery okolo čárky povolené)
        #
        # Nejdřív zpracujeme desetinná čísla s procentem, aby se zbytek ("%") nezpracoval jako celé procento.
        decimal_with_percent_pattern = r'\b(\d+)\s*,\s*(\d+)\s*[%％]'
        text = re.sub(decimal_with_percent_pattern, lambda m: decimal_to_words(m, has_percent=True), text)

        # Pak zpracujeme desetinná čísla bez procenta
        decimal_pattern = r'\b(\d+)\s*,\s*(\d+)\b'
        text = re.sub(decimal_pattern, lambda m: decimal_to_words(m, has_percent=False), text)

        # Také zpracujeme procenta u celých čísel (např. "13 %")
        # Ale nechytíme čísla, která jsou součástí desetinných čísel (už zpracovaná)
        # Negativní lookbehind zajistí, že před číslem není čárka
        percent_pattern = r'\b([0-9]{1,3})\s*[%％]'
        def replace_percent(match):
            num_str = match.group(1)
            try:
                num_word = number_to_words(num_str)
                # Pro TTS držíme stabilní tvar "procent" (např. o deset procent, o dvě procent).
                return f"{num_word} procent"
            except:
                return match.group(0)

        text = re.sub(percent_pattern, replace_percent, text)

        # Poslední pojistka: pokud by v textu přesto zůstalo "%" (např. kvůli exotickému formátu),
        # XTTS to často přečte jako "procento". Raději to odstraň a nahraď slovem.
        text = re.sub(r'[%％]', ' procent', text)

        # Najdi čísla v textu a převeď je
        # Pattern pro celá čísla (1-3 cifry, aby se nechytly roky, telefony atd.)
        # Ale nechytíme čísla, která jsou součástí desetinných čísel (0,13) nebo procent (13%)
        pattern = r'\b([0-9]{1,3})\b'

        def replace_number(match):
            num_str = match.group(1)
            start_pos = match.start()
            end_pos = match.end()

            # Zkontroluj, jestli to není součást desetinného čísla nebo procenta
            # Podívej se na kontext před a za číslem v aktuálním textu
            text_before = text[max(0, start_pos-10):start_pos]
            text_after = text[end_pos:min(len(text), end_pos+10)]

            # Pokud je za číslem čárka následovaná číslicí, je to desetinné číslo - přeskoč
            if re.search(r',\d', text_after):
                return num_str

            # Pokud je za číslem procento (s mezerou nebo bez), už jsme to zpracovali - přeskoč
            if re.search(r'\s*%', text_after):
                return num_str

            # Pokud je před číslem čárka a číslice, je to desetinné číslo - přeskoč
            if re.search(r'\d,', text_before):
                return num_str

            # Přeskoč pokud je to součást většího čísla nebo data
            if len(num_str) > 3:
                return num_str
            return number_to_words(num_str)

        processed_text = re.sub(pattern, replace_number, text)

        return processed_text

    async def warmup(self, demo_voice_path: Optional[str] = None):
        """
        Zahřeje model prvním inference

        Args:
            demo_voice_path: Cesta k demo hlasu pro warmup
        """
        if not self.is_loaded:
            await self.load_model()

        if demo_voice_path and Path(demo_voice_path).exists():
            try:
                # Použij výchozí parametry pro warmup
                from backend.config import (
                    TTS_SPEED,
                    TTS_TEMPERATURE,
                    TTS_LENGTH_PENALTY,
                    TTS_REPETITION_PENALTY,
                    TTS_TOP_K,
                    TTS_TOP_P,
                    OUTPUTS_DIR
                )
                # Generuj warmup audio s krátkým textem
                warmup_output = await self.generate(
                    text="Warmup.",
                    speaker_wav=demo_voice_path,
                    language="cs",
                    speed=TTS_SPEED,
                    temperature=TTS_TEMPERATURE,
                    length_penalty=TTS_LENGTH_PENALTY,
                    repetition_penalty=TTS_REPETITION_PENALTY,
                    top_k=TTS_TOP_K,
                    top_p=TTS_TOP_P
                )
                # Smazat warmup soubor, aby se neukládal do historie
                warmup_path = Path(warmup_output)
                if warmup_path.exists():
                    try:
                        warmup_path.unlink()
                    except Exception:
                        pass  # Ignoruj chyby při mazání
                print("Model warmup dokončen")
            except Exception as e:
                print(f"Warmup selhal: {str(e)}")

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

    def get_status(self) -> dict:
        """Vrátí status modelu"""
        return {
            "loaded": self.is_loaded,
            "loading": self.is_loading,
            "device": self.device,
            "cuda_available": torch.cuda.is_available(),
            "device_forced": DEVICE_FORCED,
            "force_device": FORCE_DEVICE,
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "hifigan_available": self.vocoder.available if hasattr(self, 'vocoder') else False
        }

