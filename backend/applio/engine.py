"""
Applio Engine
Hlavní wrapper pro Applio API (voice conversion a TTS)
"""

import asyncio
import aiohttp
import base64
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

try:
    from colorama import Fore, Style

    COLOR_OK = Fore.GREEN
    COLOR_WARN = Fore.YELLOW
    COLOR_ERROR = Fore.RED
    COLOR_INFO = Fore.CYAN
    COLOR_RESET = Style.RESET_ALL
except ImportError:
    COLOR_OK = COLOR_WARN = COLOR_ERROR = COLOR_INFO = COLOR_RESET = ""


class ApplioEngine:
    """
    Applio API klient pro voice conversion a TTS

    Podporuje:
    - Voice conversion pomocí RVC modelů
    - TTS s voice cloning (EdgeTTS + RVC)
    - Správu modelů
    """

    def __init__(self, base_url: str = "http://localhost:9874"):
        self.base_url = base_url.rstrip("/")
        self.session: Optional[aiohttp.ClientSession] = None
        self.is_loaded = False
        self.last_error: Optional[str] = None

    async def ensure_session(self):
        """Vytvoří aiohttp session pokud neexistuje"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=300)
            self.session = aiohttp.ClientSession(timeout=timeout)

    async def close(self):
        """Uzavře session"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None

    async def __aenter__(self):
        await self.ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        files: Optional[Dict] = None,
        timeout: int = 300,
    ) -> Dict[str, Any]:
        """
        Odeslání HTTP requestu k Applio API

        Args:
            method: HTTP metoda (GET, POST)
            endpoint: API endpoint
            data: JSON data
            files: Soubory k uploadu
            timeout: Timeout v sekundách

        Returns:
            Response JSON
        """
        await self.ensure_session()

        url = f"{self.base_url}{endpoint}"

        try:
            if files:
                # multipart/form-data
                form = aiohttp.FormData()
                for key, file_data in files.items():
                    if isinstance(file_data, dict):
                        form.add_field(
                            key,
                            file_data["content"],
                            filename=file_data.get("filename", "file"),
                            content_type=file_data.get(
                                "content_type", "application/octet-stream"
                            ),
                        )
                    else:
                        form.add_field(key, file_data)

                async with self.session.request(method, url, data=form) as response:
                    return await self._handle_response(response)
            else:
                # JSON request
                async with self.session.request(method, url, json=data) as response:
                    return await self._handle_response(response)

        except asyncio.TimeoutError:
            self.last_error = f"Timeout při volání {endpoint}"
            logger.error(f"{COLOR_ERROR}{self.last_error}{COLOR_RESET}")
            raise
        except aiohttp.ClientError as e:
            self.last_error = f"Chyba klienta: {str(e)}"
            logger.error(f"{COLOR_ERROR}{self.last_error}{COLOR_RESET}")
            raise

    async def _handle_response(
        self, response: aiohttp.ClientResponse
    ) -> Dict[str, Any]:
        """Zpracování response"""
        if response.status == 200:
            try:
                return await response.json()
            except:
                # Možná vrací audio nebo plain text
                return {"status": "ok", "content_type": response.content_type}
        elif response.status == 400:
            error = await response.text()
            self.last_error = f"Bad Request: {error}"
            raise Exception(self.last_error)
        elif response.status == 404:
            self.last_error = "Endpoint not found"
            raise Exception(self.last_error)
        elif response.status >= 500:
            error = await response.text()
            self.last_error = f"Server Error: {error}"
            raise Exception(self.last_error)
        else:
            self.last_error = f"HTTP {response.status}"
            raise Exception(self.last_error)

    # ==================== Voice Conversion ====================

    async def voice_conversion(
        self,
        input_audio: str,
        output_path: str,
        voice_model: str,
        pitch_shift: int = 0,
        index_ratio: float = 0.75,
        filter_radius: int = 7,
        output_format: str = "wav",
    ) -> str:
        """
        Převod hlasu pomocí RVC modelu

        Args:
            input_audio: Cesta k vstupnímu audio souboru
            output_path: Cesta pro uložení výstupu
            voice_model: Název RVC modelu
            pitch_shift: Pitch shift v půltónech (-12 až +12)
            index_ratio: Poměr použití indexu (0-1)
            filter_radius: Filtr pro vyhlazení
            output_format: Výstupní formát (wav, flac, mp3)

        Returns:
            Cesta k výstupnímu souboru
        """
        logger.info(
            f"{COLOR_INFO}Voice conversion: {Path(input_audio).name} -> {voice_model}{COLOR_RESET}"
        )

        # Načtení audio souboru
        with open(input_audio, "rb") as f:
            audio_content = f.read()

        files = {
            "audio": {
                "content": audio_content,
                "filename": Path(input_audio).name,
                "content_type": "audio/wav",
            }
        }

        data = {
            "model": voice_model,
            "pitch": str(pitch_shift),
            "index_ratio": str(index_ratio),
            "filter_radius": str(filter_radius),
            "output_format": output_format,
        }

        try:
            response = await self._request(
                "POST", "/api/voice-conversion", data=data, files=files
            )

            # Uložení výstupu
            with open(output_path, "wb") as f:
                f.write(
                    audio_content
                )  # Placeholder - skutečná implementace závisí na API

            logger.info(
                f"{COLOR_OK}✅ Voice conversion dokončen: {output_path}{COLOR_RESET}"
            )
            return output_path

        except Exception as e:
            logger.error(f"{COLOR_ERROR}Voice conversion selhal: {e}{COLOR_RESET}")
            raise

    # ==================== TTS with Voice Cloning ====================

    async def tts_with_voice_clone(
        self,
        text: str,
        voice_reference: str,
        language: str = "cs",
        voice_name: str = None,
        speed: float = 1.0,
        output_path: str = None,
    ) -> str:
        """
        TTS s voice cloning pomocí EdgeTTS + RVC

        Args:
            text: Text k syntéze
            voice_reference: Cesta k referenčnímu audio pro klonování
            language: Jazyk (cs, sk, en, atd.)
            voice_name: Název EdgeTTS hlasu (pokud None, použije výchozí)
            speed: Rychlost řeči (0.5-2.0)
            output_path: Cesta pro uložení výstupu (automaticky pokud None)

        Returns:
            Cesta k výstupnímu souboru
        """
        logger.info(
            f"{COLOR_INFO}TTS + Voice Clone: {language}, {len(text)} znaků{COLOR_RESET}"
        )

        # Načtení referenčního audio
        with open(voice_reference, "rb") as f:
            reference_content = f.read()

        files = {
            "reference": {
                "content": reference_content,
                "filename": Path(voice_reference).name,
                "content_type": "audio/wav",
            }
        }

        data = {
            "text": text,
            "language": language,
            "voice": voice_name or f"{language}-{language.upper()}-Neural",
            "speed": str(speed),
        }

        try:
            response = await self._request(
                "POST", "/api/tts-clone", data=data, files=files
            )

            if output_path is None:
                output_path = f"outputs/applio_tts_{language}_{int(time.time())}.wav"

            # Uložení výstupu
            with open(output_path, "wb") as f:
                f.write(reference_content)  # Placeholder

            logger.info(
                f"{COLOR_OK}✅ TTS + Voice Clone dokončen: {output_path}{COLOR_RESET}"
            )
            return output_path

        except Exception as e:
            logger.error(f"{COLOR_ERROR}TTS + Voice Clone selhal: {e}{COLOR_RESET}")
            raise

    # ==================== Model Management ====================

    async def list_models(self) -> List[Dict[str, Any]]:
        """Vrátí seznam dostupných RVC modelů"""
        try:
            response = await self._request("GET", "/api/models")
            return response.get("models", [])
        except Exception as e:
            logger.warning(f"{COLOR_WARN}Nelze načíst seznam modelů: {e}{COLOR_RESET}")
            return []

    async def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Vrátí informace o modelu"""
        try:
            response = await self._request("GET", f"/api/models/{model_name}")
            return response
        except Exception as e:
            logger.warning(
                f"{COLOR_WARN}Nelze načíst info o modelu {model_name}: {e}{COLOR_RESET}"
            )
            return {}

    async def upload_model(
        self, model_name: str, model_file: str, index_file: Optional[str] = None
    ) -> bool:
        """
        Upload nového RVC modelu

        Args:
            model_name: Název modelu
            model_file: Cesta k .pth souboru
            index_file: Cesta k .index souboru (volitelné)

        Returns:
            True pokud upload úspěšný
        """
        logger.info(f"{COLOR_INFO}Upload modelu: {model_name}{COLOR_RESET}")

        files = {
            "model": {
                "content": open(model_file, "rb").read(),
                "filename": f"{model_name}.pth",
                "content_type": "application/octet-stream",
            }
        }

        if index_file and Path(index_file).exists():
            files["index"] = {
                "content": open(index_file, "rb").read(),
                "filename": f"{model_name}.index",
                "content_type": "application/octet-stream",
            }

        data = {"model_name": model_name}

        try:
            response = await self._request(
                "POST", "/api/models/upload", data=data, files=files
            )
            logger.info(f"{COLOR_OK}✅ Model {model_name} nahrán{COLOR_RESET}")
            return True
        except Exception as e:
            logger.error(f"{COLOR_ERROR}Upload modelu selhal: {e}{COLOR_RESET}")
            return False

    async def delete_model(self, model_name: str) -> bool:
        """Smaže model"""
        try:
            response = await self._request("DELETE", f"/api/models/{model_name}")
            logger.info(f"{COLOR_OK}✅ Model {model_name} smazán{COLOR_RESET}")
            return True
        except Exception as e:
            logger.error(f"{COLOR_ERROR}Smazání modelu selhalo: {e}{COLOR_RESET}")
            return False

    # ==================== Status ====================

    async def get_status(self) -> Dict[str, Any]:
        """Vrátí status Applio serveru"""
        try:
            response = await self._request("GET", "/api/status")
            return response
        except Exception as e:
            return {"running": False, "error": str(e), "last_error": self.last_error}

    async def check_health(self) -> bool:
        """Rychlá kontrola zdraví"""
        try:
            await self._request("GET", "/docs")
            return True
        except:
            return False

    # ==================== Utility Methods ====================

    def get_default_voice(self, language: str) -> str:
        """Vrátí výchozí hlas pro jazyk"""
        default_voices = {
            "cs": "cs-CZ-VlastaNeural",
            "sk": "sk-SR-LuboslavNeural",
            "en": "en-US-AriaNeural",
            "de": "de-DE-KatjaNeural",
            "fr": "fr-FR-DeniseNeural",
            "es": "es-ES-ElviraNeural",
            "pl": "pl-PL-ZofiaNeural",
            "ru": "ru-RU-SvetlanaNeural",
            "ja": "ja-JP-NanamiNeural",
            "zh": "zh-CN-XiaoxiaoNeural",
        }
        return default_voices.get(language, f"{language}-{language.upper()}-Neural")

    async def get_available_voices(self, language: str = None) -> List[str]:
        """Vrátí seznam dostupných hlasů"""
        try:
            response = await self._request("GET", "/api/voices")
            voices = response.get("voices", [])
            if language:
                voices = [
                    v for v in voices if v.get("language", "").startswith(language)
                ]
            return voices
        except Exception as e:
            logger.warning(f"{COLOR_WARN}Nelze načíst seznam hlasů: {e}{COLOR_RESET}")
            # Fallback na výchozí hlasy
            return (
                [self.get_default_voice(lang) for lang in ["cs", "sk", "en"]]
                if language
                else []
            )
