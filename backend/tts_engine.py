"""
XTTS-v2 TTS Engine wrapper
"""
import uuid
import asyncio
from pathlib import Path
from typing import Optional, List
from TTS.api import TTS
import torch
import numpy as np
from num2words import num2words
from TTS.tts.layers.xtts import tokenizer as xtts_tokenizer
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
    ENABLE_MULTI_PASS,
    MULTI_PASS_COUNT,
    ENABLE_BATCH_PROCESSING,
    MAX_CHUNK_LENGTH,
    ENABLE_PROSODY_CONTROL
)
from backend.audio_enhancer import AudioEnhancer

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
        use_hifigan: bool = False
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

        Returns:
            Cesta k vygenerovanému audio souboru nebo seznam variant při multi-pass
        """
        if not self.is_loaded:
            await self.load_model()

        if not self.model:
            raise Exception("Model není načten")

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
                use_hifigan=use_hifigan
            )

        # Batch processing pro dlouhé texty
        use_batch = enable_batch if enable_batch is not None else (ENABLE_BATCH_PROCESSING and len(text) > MAX_CHUNK_LENGTH)
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
                use_hifigan=use_hifigan
            )

        # Aplikace quality preset pokud je zadán
        if quality_mode:
            preset_params = self._apply_quality_preset(quality_mode)
            speed = preset_params["speed"]
            temperature = preset_params["temperature"]
            length_penalty = preset_params["length_penalty"]
            repetition_penalty = preset_params["repetition_penalty"]
            top_k = preset_params["top_k"]
            top_p = preset_params["top_p"]

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
            use_hifigan
        )

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
        use_hifigan: bool = False
    ):
        """Synchronní generování řeči"""
        try:
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

            # Zkontroluj, jestli soubor byl vytvořen
            if not Path(output_path).exists():
                raise Exception(f"Output file was not created: {output_path}")

            # Post-processing: upsampling
            # XTTS-v2 generuje na 22050 Hz, ale chceme CD kvalitu (44100 Hz)
            try:
                import librosa
                import soundfile as sf

                # Načtení audio s původní sample rate
                audio, sr = librosa.load(output_path, sr=None)

                # Upsampling na cílovou sample rate (pokud je jiná)
                if sr != OUTPUT_SAMPLE_RATE:
                    print(f"🎵 Upsampling audio z {sr} Hz na {OUTPUT_SAMPLE_RATE} Hz (CD kvalita)...")
                    audio = librosa.resample(audio, orig_sr=sr, target_sr=OUTPUT_SAMPLE_RATE)
                    sr = OUTPUT_SAMPLE_RATE
                    print(f"✅ Audio upsamplováno na {OUTPUT_SAMPLE_RATE} Hz")

                # Uložení s upsamplovaným audio (před enhancement)
                sf.write(output_path, audio, sr)

            except Exception as e:
                print(f"⚠️ Warning: Post-processing (upsampling) failed: {e}, continuing with original audio")
                # Pokračujeme s původním audio

            # Post-processing audio enhancement (pokud je zapnuto)
            if ENABLE_AUDIO_ENHANCEMENT:
                try:
                    # Použít předaný enhancement_preset, nebo výchozí z configu
                    preset_to_use = enhancement_preset if enhancement_preset else AUDIO_ENHANCEMENT_PRESET
                    # Předat enable_vad do enhancement
                    AudioEnhancer.enhance_output(output_path, preset=preset_to_use)
                except Exception as e:
                    print(f"Warning: Audio enhancement failed: {e}, continuing with original audio")

            # Změna rychlosti pomocí time_stretch (pokud speed != 1.0) - APLIKUJE SE PO ENHANCEMENT
            # XTTS může nepodporovat parametr speed, takže použijeme post-processing
            if speed != 1.0:
                try:
                    import librosa
                    import soundfile as sf

                    print(f"🎚️  Aplikuji změnu rychlosti: {speed}x pomocí post-processing...")
                    # Načtení audio po enhancement
                    audio, sr = librosa.load(output_path, sr=None)
                    # time_stretch používá rate (1.0 = normální rychlost, 2.0 = 2x rychlejší, 0.5 = 2x pomalejší)
                    # speed parametr je přímo rate
                    audio = librosa.effects.time_stretch(audio, rate=speed)
                    print(f"✅ Rychlost změněna na {speed}x")
                    # Uložení s upravenou rychlostí
                    sf.write(output_path, audio, sr)
                except Exception as e:
                    print(f"⚠️ Warning: Změna rychlosti selhala: {e}, pokračuji s původní rychlostí")

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
            "m/s": "metrů za sekundu"
        }
        for abbr, full in abbreviations.items():
            # Nahradit pouze celá slova (s mezerami nebo interpunkcí)
            pattern = r'\b' + re.escape(abbr) + r'\b'
            text = re.sub(pattern, full, text, flags=re.IGNORECASE)

        # 3. Normalizace mezer
        text = re.sub(r'\s+', ' ', text)  # Více mezer na jednu
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)  # Mezera před interpunkcí
        text = text.strip()

        # 4. Rozšířený převod čísel na slova
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

        # Najdi čísla v textu a převeď je
        # Pattern pro celá čísla (1-3 cifry, aby se nechytly roky, telefony atd.)
        pattern = r'\b([0-9]{1,3})\b'

        def replace_number(match):
            num_str = match.group(1)
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
        use_hifigan: bool = False
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
                use_hifigan=use_hifigan
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
        use_hifigan: bool = False
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
        from backend.text_splitter import TextSplitter
        from backend.audio_concatenator import AudioConcatenator

        # Rozděl text na části
        chunks = TextSplitter.split_text(text)

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
                use_hifigan=use_hifigan
            )

        print(f"📦 Batch processing: rozděleno na {len(chunks)} částí")

        # Generuj každou část
        audio_files = []
        for i, chunk in enumerate(chunks):
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
                use_hifigan=use_hifigan
            )
            audio_files.append(chunk_output)

        # Spoj audio části
        output_filename = f"{uuid.uuid4()}.wav"
        output_path = OUTPUTS_DIR / output_filename

        print(f"🔗 Spojuji {len(audio_files)} audio částí...")
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
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
        }

