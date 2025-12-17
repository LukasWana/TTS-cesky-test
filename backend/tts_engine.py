"""
XTTS-v2 TTS Engine wrapper
"""
import uuid
import asyncio
from pathlib import Path
from typing import Optional
from TTS.api import TTS
import torch
from backend.config import (
    DEVICE,
    XTTS_MODEL_NAME,
    MODEL_CACHE_DIR,
    OUTPUTS_DIR,
    USE_SMALL_MODELS,
    ENABLE_CPU_OFFLOAD,
    FORCE_DEVICE,
    DEVICE_FORCED
)


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
        top_p: float = 0.85
    ) -> str:
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

        Returns:
            Cesta k vygenerovanému audio souboru
        """
        if not self.is_loaded:
            await self.load_model()

        if not self.model:
            raise Exception("Model není načten")

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
            top_p
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
        top_p: float = 0.85
    ):
        """Synchronní generování řeči"""
        try:
            # Zkontroluj, jestli speaker_wav existuje
            if not Path(speaker_wav).exists():
                raise Exception(f"Speaker audio file not found: {speaker_wav}")

            # Předzpracování textu pro češtinu - převod čísel na slova
            # TTS knihovna má problém s num2words pro češtinu, takže převedeme čísla ručně
            processed_text = self._preprocess_text_for_czech(text, language)

            # Příprava parametrů pro tts_to_file
            tts_params = {
                "text": processed_text,
                "speaker_wav": speaker_wav,
                "language": language,
                "file_path": output_path
            }

            # Přidání volitelných parametrů (pokud jsou podporovány)
            # XTTS-v2 může podporovat různé parametry v závislosti na verzi
            if speed != 1.0:
                tts_params["speed"] = speed
            if temperature != 0.7:
                tts_params["temperature"] = temperature
            if length_penalty != 1.0:
                tts_params["length_penalty"] = length_penalty
            if repetition_penalty != 2.0:
                tts_params["repetition_penalty"] = repetition_penalty
            if top_k != 50:
                tts_params["top_k"] = top_k
            if top_p != 0.85:
                tts_params["top_p"] = top_p

            # Generování řeči
            # TTS API může vracet různé hodnoty v závislosti na verzi
            result = self.model.tts_to_file(**tts_params)

            # Zkontroluj, jestli soubor byl vytvořen
            if not Path(output_path).exists():
                raise Exception(f"Output file was not created: {output_path}")

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Generate error details:\n{error_details}")
            raise Exception(f"Chyba při generování řeči: {str(e)}")

    def _preprocess_text_for_czech(self, text: str, language: str) -> str:
        """
        Předzpracuje text pro češtinu - převede čísla na slova
        aby se předešlo chybě s num2words
        """
        if language != "cs":
            return text

        import re

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
                    TTS_TOP_P
                )
                await self.generate(
                    text="Zahřívací text pro optimalizaci modelu.",
                    speaker_wav=demo_voice_path,
                    language="cs",
                    speed=TTS_SPEED,
                    temperature=TTS_TEMPERATURE,
                    length_penalty=TTS_LENGTH_PENALTY,
                    repetition_penalty=TTS_REPETITION_PENALTY,
                    top_k=TTS_TOP_K,
                    top_p=TTS_TOP_P
                )
                print("Model warmup dokončen")
            except Exception as e:
                print(f"Warmup selhal: {str(e)}")

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

