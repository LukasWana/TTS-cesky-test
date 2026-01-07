"""
Applio Integration Helper
Pomocné funkce pro integraci Applio do stávajícího pipeline
"""

import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
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


class ApplioIntegration:
    """
    Helper class pro integraci Applio do stávajícího voice assistant pipeline

    Umožňuje:
    - Voice conversion existujícího audia
    - TTS s voice cloning
    - Fallback na stávající TTS (XTTS, F5, Bark)
    """

    def __init__(self):
        self.engine = None
        self.manager = None
        self.is_available = False

    async def initialize(self) -> bool:
        """Inicializace Applio engine a manager"""
        try:
            from backend.applio.config import (
                APPLIO_ENABLED,
                APPLIO_BASE_URL,
                APPLIO_DIR,
            )

            if not APPLIO_ENABLED:
                logger.info(
                    f"{COLOR_WARN}Applio je zakázáno v konfiguraci{COLOR_RESET}"
                )
                return False

            # Kontrola Applio adresáře
            applio_path = Path(APPLIO_DIR)
            if not applio_path.exists():
                logger.warning(
                    f"{COLOR_WARN}Applio adresář neexistuje: {APPLIO_DIR}{COLOR_RESET}\n"
                    f"Stáhněte Applio z https://applio.org a rozbalte do tohoto adresáře."
                )
                return False

            # Inicializace engine a manager
            from backend.applio.engine import ApplioEngine
            from backend.applio.subprocess_manager import ApplioSubprocessManager

            self.engine = ApplioEngine(base_url=APPLIO_BASE_URL)
            self.manager = ApplioSubprocessManager(
                applio_dir=applio_path, config={"base_url": APPLIO_BASE_URL}
            )

            # Kontrola zdraví
            if await self.engine.check_health():
                self.is_available = True
                logger.info(f"{COLOR_OK}✅ Applio je dostupné{COLOR_RESET}")
                return True
            else:
                logger.warning(
                    f"{COLOR_WARN}Applio server neběží.{COLOR_RESET}\n"
                    f"Spusťte Applio manuálně nebo použijte /api/applio/server/start"
                )
                return False

        except ImportError as e:
            logger.error(f"{COLOR_ERROR}Nelze načíst Applio moduly: {e}{COLOR_RESET}")
            return False
        except Exception as e:
            logger.error(
                f"{COLOR_ERROR}Chyba při inicializaci Applio: {e}{COLOR_RESET}"
            )
            return False

    async def start_server(self, timeout: int = 120) -> bool:
        """Spustí Applio server"""
        if self.manager is None:
            await self.initialize()

        if self.manager and not self.manager.is_running:
            return await self.manager.start(timeout=timeout)
        return True

    async def stop_server(self):
        """Zastaví Applio server"""
        if self.manager:
            await self.manager.stop()

    # ==================== Voice Conversion ====================

    async def convert_voice(
        self,
        input_audio: str,
        voice_model: str,
        pitch_shift: int = 0,
        index_ratio: float = 0.75,
        output_dir: str = "outputs",
    ) -> Optional[str]:
        """
        Převod hlasu na cílový hlas pomocí RVC

        Args:
            input_audio: Cesta k vstupnímu audiu
            voice_model: Název RVC modelu
            pitch_shift: Pitch shift (-12 až +12)
            index_ratio: Poměr podobnosti (0-1)
            output_dir: Výstupní adresář

        Returns:
            Cesta k výstupnímu souboru nebo None při chybě
        """
        if not self.is_available:
            logger.error(f"{COLOR_ERROR}Applio není dostupné{COLOR_RESET}")
            return None

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        output_path = Path(output_dir) / f"applio_vc_{Path(input_audio).stem}.wav"

        try:
            result = await self.engine.voice_conversion(
                input_audio=input_audio,
                output_path=str(output_path),
                voice_model=voice_model,
                pitch_shift=pitch_shift,
                index_ratio=index_ratio,
            )
            return result
        except Exception as e:
            logger.error(f"{COLOR_ERROR}Voice conversion selhala: {e}{COLOR_RESET}")
            return None

    # ==================== TTS with Voice Cloning ====================

    async def tts_clone(
        self,
        text: str,
        voice_reference: str,
        language: str = "cs",
        voice_name: str = None,
        speed: float = 1.0,
        output_dir: str = "outputs",
    ) -> Optional[str]:
        """
        TTS s voice cloning

        Args:
            text: Text k syntéze
            voice_reference: Cesta k referenčnímu audiu
            language: Jazyk
            voice_name: Název hlasu (volitelné)
            speed: Rychlost řeči
            output_dir: Výstupní adresář

        Returns:
            Cesta k výstupnímu souboru nebo None při chybě
        """
        if not self.is_available:
            logger.error(f"{COLOR_ERROR}Applio není dostupné{COLOR_RESET}")
            return None

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        output_path = (
            Path(output_dir)
            / f"applio_tts_{language}_{int(__import__('time').time())}.wav"
        )

        try:
            result = await self.engine.tts_with_voice_clone(
                text=text,
                voice_reference=voice_reference,
                language=language,
                voice_name=voice_name,
                speed=speed,
                output_path=str(output_path),
            )
            return result
        except Exception as e:
            logger.error(f"{COLOR_ERROR}TTS clone selhal: {e}{COLOR_RESET}")
            return None

    # ==================== Utility Methods ====================

    async def list_models(self) -> list:
        """Vrátí seznam dostupných modelů"""
        if self.engine:
            return await self.engine.list_models()
        return []

    async def get_status(self) -> Dict[str, Any]:
        """Vrátí status"""
        if self.manager and self.engine:
            return {
                "running": self.manager.is_running,
                "available": self.is_available,
                "uptime": self.manager.uptime,
                "models_count": len(await self.list_models()),
            }
        return {"running": False, "available": False}

    def get_supported_languages(self) -> list:
        """Vrátí podporované jazyky"""
        if self.engine:
            return self.engine.get_available_voices()
        return []


# Global instance
_applio_integration = None


def get_applio_integration() -> ApplioIntegration:
    """Vrátí global instanci ApplioIntegration"""
    global _applio_integration
    if _applio_integration is None:
        _applio_integration = ApplioIntegration()
    return _applio_integration


async def init_applio() -> bool:
    """Inicializuje Applio integration"""
    integration = get_applio_integration()
    return await integration.initialize()


async def ensure_applio_running(timeout: int = 120) -> bool:
    """Zajistí, že Applio běží"""
    integration = get_applio_integration()

    # Inicializace
    if not integration.is_available:
        if not await integration.initialize():
            return False

    # Spuštění serveru pokud neběží
    if not integration.manager or not integration.manager.is_running:
        return await integration.start_server(timeout=timeout)

    return True
