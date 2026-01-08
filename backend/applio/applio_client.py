"""
Applio Gradio Client Wrapper
Komunikuje s Applio na portu 6969 pres Gradio API
"""

import os
import sys
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

try:
    import gradio as gr

    HAS_GRADIO = True
except ImportError:
    logger.warning("Gradio not installed. Applio features will not be available.")
    HAS_GRADIO = False
    gr = None


class ApplioGradioClient:
    """
    Klient pro komunikaci s Applio pres Gradio API

    Applio bezi na http://localhost:6969 a poskytuje TTS funkcionalitu
    pres EdgeTTS + RVC voice conversion.
    """

    def __init__(self, applio_url="http://127.0.0.1:6969"):
        self.applio_url = applio_url
        self.client = None
        self._tts_voices = None

        # Cesta k Applio hlasum
        self.voices_dir = Path("assets/Aplio-voices")

    def connect(self):
        """Pripojeni k Applio"""
        if not HAS_GRADIO:
            raise RuntimeError(
                "Gradio is not installed. Install with: pip install gradio"
            )

        if self.client is None:
            try:
                self.client = gr.Client(self.applio_url)
                logger.info(f"Connected to Applio at {self.applio_url}")
            except Exception as e:
                logger.error(f"Failed to connect to Applio: {e}")
                raise
        return self.client

    def _load_tts_voices(self):
        """Nacte seznam dostupnych TTS hlasu z Applio"""
        if self._tts_voices is not None:
            return self._tts_voices

        voices_path = (
            Path(__file__).parent / "rvc" / "lib" / "tools" / "tts_voices.json"
        )

        if voices_path.exists():
            try:
                with open(voices_path, "r", encoding="utf-8") as f:
                    voices = json.load(f)
                    self._tts_voices = [v["ShortName"] for v in voices]
                    logger.info(f"Loaded {len(self._tts_voices)} TTS voices")
            except Exception as e:
                logger.warning(f"Failed to load TTS voices: {e}")
                self._tts_voices = []
        else:
            logger.warning(f"TTS voices file not found: {voices_path}")
            self._tts_voices = []

        return self._tts_voices

    def get_available_tts_voices(self, language=None):
        """Vrati dostupne TTS hlasy, filtruje podle jazyka pokud je zadano"""
        voices = self._load_tts_voices()

        if language:
            prefix = f"{language}-"
            voices = [v for v in voices if v.startswith(prefix)]

        return voices

    def get_applio_voices(self):
        """
        Nacte dostupne Applio hlasy z assets/Aplio-voices/

        Returns:
            list: Seznam slovniku s 'name', 'model', 'index' klici
        """
        voices = []

        if not self.voices_dir.exists():
            logger.warning(f"Applio voices directory not found: {self.voices_dir}")
            return voices

        for folder in self.voices_dir.iterdir():
            if folder.is_dir():
                pth_file = None
                index_file = None

                # Najit .pth soubor
                for f in folder.glob("*.pth"):
                    pth_file = str(f)
                    break

                # Najit .index soubor
                for f in folder.glob("*.index"):
                    index_file = str(f)
                    break

                if pth_file:
                    voices.append(
                        {
                            "name": folder.name,
                            "model": pth_file,
                            "index": index_file,
                            "model_filename": Path(pth_file).stem,
                            "index_filename": Path(index_file).stem
                            if index_file
                            else None,
                        }
                    )

        logger.info(f"Found {len(voices)} Applio voices")
        return voices

    def tts_with_voice(
        self,
        tts_text: str,
        tts_voice: str,
        tts_rate: int = 0,
        pitch: int = 0,
        index_rate: float = 0.75,
        model_file: str = None,
        index_file: str = None,
        f0_method: str = "rmvpe",
        export_format: str = "WAV",
        split_audio: bool = False,
        autotune: bool = False,
        autotune_strength: float = 1.0,
        clean_audio: bool = False,
        clean_strength: float = 0.5,
        rms_mix_rate: float = 1.0,
        protect: float = 0.5,
        **kwargs,
    ):
        """
        TTS s voice cloning pres Applio

        Args:
            tts_text: Text k synteze
            tts_voice: EdgeTTS voice (napr. cs-CZ-VlastaNeural)
            tts_rate: Rychlost TTS (-100 az 100)
            pitch: Pitch shift pro RVC (-24 az 24)
            index_rate: Poměr pouziti indexu (0-1)
            model_file: Cesta k RVC modelu (.pth)
            index_file: Cesta k index souboru (.index)
            f0_method: Metoda extrakce pitch (rmvpe, crepe, fcpe)
            export_format: Format exportu (WAV, MP3, FLAC, OGG, M4A)
            split_audio: Rozdelit audio na chunks
            autotune: Pouzit autotune
            autotune_strength: Silautotune
            clean_audio: Vyčistit audio od sumu
            clean_strength: Silacisteni (0-1)
            rms_mix_rate: Pomer hlasitosti (0-1)
            protect: Ochrana bezdychnych souhlasek (0-0.5)

        Returns:
            tuple: (info_message, output_file_path)
        """
        client = self.connect()

        # Nastavit vychozi hodnoty
        if model_file is None:
            model_file = ""
        if index_file is None:
            index_file = ""

        # Vstupni soubor pro TTS (prazdny text file)
        input_tts_path = ""

        try:
            result = client.predict(
                input_tts_path=input_tts_path,
                tts_text=tts_text,
                tts_voice=tts_voice,
                tts_rate=tts_rate,
                pitch=pitch,
                index_rate=index_rate,
                rms_mix_rate=rms_mix_rate,
                protect=protect,
                f0_method=f0_method,
                output_tts_path=os.path.join(
                    os.getcwd(), "assets", "audios", "tts_output.wav"
                ),
                output_rvc_path=os.path.join(
                    os.getcwd(), "assets", "audios", "tts_rvc_output.wav"
                ),
                model_file=model_file,
                index_file=index_file,
                split_audio=split_audio,
                autotune=autotune,
                autotune_strength=autotune_strength,
                proposed_pitch=False,
                proposed_pitch_threshold=155.0,
                clean_audio=clean_audio,
                clean_strength=clean_strength,
                export_format=export_format,
                embedder_model="contentvec",
                embedder_model_custom="",
                sid=0,
                terms_accepted=True,
            )

            return result

        except Exception as e:
            logger.error(f"TTS failed: {e}")
            raise

    def is_available(self):
        """Kontrola dostupnosti Applio"""
        try:
            client = self.connect()
            # Zkusit jednoduchy dotaz
            return True
        except:
            return False


# Globalni instance
_applio_client = None


def get_applio_client():
    """Vrati globalni instanci Applio klienta"""
    global _applio_client
    if _applio_client is None:
        _applio_client = ApplioGradioClient()
    return _applio_client


def check_applio_available():
    """Rychla kontrola dostupnosti Applio"""
    try:
        client = get_applio_client()
        return client.is_available()
    except:
        return False


def get_applio_voices_for_api():
    """Nacte Applio hlasy pro API endpoint"""
    try:
        client = get_applio_client()
        return client.get_applio_voices()
    except Exception as e:
        logger.error(f"Failed to get Applio voices: {e}")
        return []


def get_tts_voices_for_api(language=None):
    """Nacte TTS hlasy pro API endpoint"""
    try:
        client = get_applio_client()
        return client.get_available_tts_voices(language)
    except Exception as e:
        logger.error(f"Failed to get TTS voices: {e}")
        return []


# Pro testovani
if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)

    client = get_applio_client()

    print("Testing Applio connection...")
    print(f"Available: {client.is_available()}")

    print("\nApplio voices:")
    for v in client.get_applio_voices():
        print(f"  - {v['name']}: {v['model']}")

    print("\nTTS voices (CS):")
    for v in client.get_available_tts_voices("cs")[:5]:
        print(f"  - {v}")
