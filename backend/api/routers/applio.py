"""
Applio API Router
FastAPI endpoints pro Applio TTS s voice cloning pres Gradio
"""

import os
import shutil
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from pathlib import Path
import logging

from backend.config import OUTPUTS_DIR, BASE_DIR
from backend.history_manager import HistoryManager

logger = logging.getLogger(__name__)

# Applio output directory - separate subfolder in central outputs
APPLIO_OUTPUT_DIR = OUTPUTS_DIR / "applio"
APPLIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

try:
    from colorama import Fore, Style

    COLOR_OK = Fore.GREEN
    COLOR_WARN = Fore.YELLOW
    COLOR_ERROR = Fore.RED
    COLOR_RESET = Style.RESET_ALL
except ImportError:
    COLOR_OK = COLOR_WARN = COLOR_ERROR = COLOR_RESET = ""

router = APIRouter(prefix="/api/applio", tags=["Applio"])

# Globalni instance klienta
_applio_client = None


def get_applio_client():
    """Ziska Applio Gradio klienta"""
    global _applio_client
    if _applio_client is None:
        try:
            from backend.applio.applio_client import ApplioGradioClient

            _applio_client = ApplioGradioClient()
        except ImportError as e:
            logger.error(f"Cannot import Applio client: {e}")
            raise HTTPException(status_code=500, detail="Applio module not available")
    return _applio_client


# ==================== Pydantic Models ====================


class ApplioTTSRequest(BaseModel):
    """Request pro Applio TTS"""

    text: str = Field(..., max_length=5000, description="Text k synteze")
    voice: str = Field(..., description="EdgeTTS voice (napr. cs-CZ-VlastaNeural)")
    speed: int = Field(default=0, ge=-100, le=100, description="Rychlost TTS")
    pitch: int = Field(default=0, ge=-24, le=24, description="Pitch shift")
    model: Optional[str] = Field(None, description="RVC model soubor")
    index_file: Optional[str] = Field(None, description="Index soubor")
    index_rate: float = Field(default=0.75, ge=0, le=1, description="Podobnost hlasu")
    f0_method: str = Field(default="rmvpe", description="Metoda extrakce pitch")
    export_format: str = Field(default="WAV", description="Format exportu")
    autotune: bool = Field(default=False, description="Pouzit autotune")
    clean_audio: bool = Field(default=False, description="Cistit audio od sumu")


# ==================== Health & Status Endpoints ====================


@router.get("/health")
async def health_check():
    """Kontrola dostupnosti Applio"""
    try:
        client = get_applio_client()
        available = client.is_available()
        return {
            "status": "healthy" if available else "unhealthy",
            "service": "applio",
            "available": available,
            "url": client.applio_url,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "applio",
            "available": False,
            "error": str(e),
        }


@router.get("/status")
async def get_status():
    """Vrati status Applio"""
    try:
        client = get_applio_client()
        available = client.is_available()

        # Ziskat seznam hlasu
        applio_voices = client.get_applio_voices() if available else []
        tts_voices = client.get_available_tts_voices() if available else []

        return {
            "available": available,
            "url": client.applio_url,
            "applio_voices_count": len(applio_voices),
            "tts_voices_count": len(tts_voices),
        }
    except Exception as e:
        return {
            "available": False,
            "error": str(e),
        }


# ==================== TTS Endpoints ====================


@router.post("/tts-clone")
async def applio_tts_clone(request: ApplioTTSRequest):
    """
    TTS s voice cloning pres Applio

    Generuje rěc z textu s aplikaci RVC voice conversion
    Vystupy se ukladaji do centralni slozky outputs/applio/
    """
    try:
        client = get_applio_client()

        if not client.is_available():
            raise HTTPException(
                status_code=503,
                detail="Applio neni dostupny. Spustte Applio na portu 6969.",
            )

        logger.info(
            f"{COLOR_OK}Generating TTS with Applio: voice={request.voice}, text={len(request.text)} chars{COLOR_RESET}"
        )

        result = client.tts_with_voice(
            tts_text=request.text,
            tts_voice=request.voice,
            tts_rate=request.speed,
            pitch=request.pitch,
            index_rate=request.index_rate,
            model_file=request.model,
            index_file=request.index_file,
            f0_method=request.f0_method,
            export_format=request.export_format,
            autotune=request.autotune,
            clean_audio=request.clean_audio,
        )

        info_msg, output_path = result
        output_filename = Path(output_path).name

        central_output_path = APPLIO_OUTPUT_DIR / output_filename
        if Path(output_path) != central_output_path:
            shutil.copy(output_path, central_output_path)
            logger.info(
                f"{COLOR_OK}Copied output to central outputs: {central_output_path}{COLOR_RESET}"
            )

        audio_url = f"/api/audio/{output_filename}"

        voice_name = f"{request.voice}"
        if request.model:
            voice_name += f" + {Path(request.model).stem}"

        tts_params = {
            "engine": "applio",
            "tts_voice": request.voice,
            "model": request.model,
            "index_file": request.index_file,
            "pitch": request.pitch,
            "speed": request.speed,
            "index_rate": request.index_rate,
            "f0_method": request.f0_method,
            "autotune": request.autotune,
            "clean_audio": request.clean_audio,
        }

        HistoryManager.add_entry(
            audio_url=audio_url,
            filename=output_filename,
            text=request.text,
            voice_type="applio",
            voice_name=voice_name,
            tts_params=tts_params,
        )

        logger.info(f"{COLOR_OK}Applio TTS completed: {output_filename}{COLOR_RESET}")

        return {
            "status": "success",
            "info": info_msg,
            "audio_url": audio_url,
            "filename": output_filename,
            "voice": request.voice,
            "speed": request.speed,
            "pitch": request.pitch,
            "model": request.model,
            "index_file": request.index_file,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{COLOR_ERROR}Applio TTS failed: {e}{COLOR_RESET}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Voice/Model Management Endpoints ====================


@router.get("/voices")
async def list_applio_voices(language: Optional[str] = None):
    """
    Vrati seznam Applio hlasu z assets/Aplio-voices/

    Formats response for UI voice cards grid
    """
    try:
        client = get_applio_client()
        voices = client.get_applio_voices()

        # Format for UI
        formatted_voices = []
        for v in voices:
            formatted_voices.append(
                {
                    "id": v["name"],
                    "name": v["name"],
                    "model": v["model"],
                    "index": v["index"],
                    "model_filename": v.get("model_filename", Path(v["model"]).stem),
                }
            )

        return {
            "voices": formatted_voices,
            "count": len(formatted_voices),
            "language_filter": language,
        }
    except Exception as e:
        logger.error(f"{COLOR_ERROR}Failed to list voices: {e}{COLOR_RESET}")
        return {"voices": [], "count": 0, "error": str(e)}


@router.get("/tts-voices")
async def list_tts_voices(language: Optional[str] = None):
    """
    Vrati seznam dostupnych EdgeTTS hlasu

    Args:
        language: Volitelny filtr podle jazyka (cs, sk, en, atd.)
    """
    try:
        client = get_applio_client()
        voices = client.get_available_tts_voices(language)

        return {
            "voices": voices,
            "count": len(voices),
            "language_filter": language,
        }
    except Exception as e:
        logger.error(f"{COLOR_ERROR}Failed to list TTS voices: {e}{COLOR_RESET}")
        return {"voices": [], "count": 0, "error": str(e)}


@router.get("/models")
async def list_models():
    """
    Vrati seznam RVC modelu z Applio models adresare
    """
    try:
        client = get_applio_client()
        models = client.get_applio_voices()

        return {
            "models": [v["name"] for v in models],
            "count": len(models),
        }
    except Exception as e:
        logger.error(f"{COLOR_ERROR}Failed to list models: {e}{COLOR_RESET}")
        return {"models": [], "count": 0, "error": str(e)}


@router.get("/models/{voice_name}")
async def get_model_info(voice_name: str):
    """Vrati informace o konkretnim hlasu"""
    try:
        client = get_applio_client()
        voices = client.get_applio_voices()

        for v in voices:
            if v["name"] == voice_name:
                return v

        raise HTTPException(status_code=404, detail=f"Voice '{voice_name}' not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{COLOR_ERROR}Failed to get model info: {e}{COLOR_RESET}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Server Management Endpoints ====================


@router.get("/server/info")
async def get_server_info():
    """Vrati info o Applio serveru"""
    try:
        client = get_applio_client()
        return {
            "url": client.applio_url,
            "available": client.is_available(),
            "voices_dir": str(client.voices_dir),
        }
    except Exception as e:
        return {
            "url": "http://localhost:6969",
            "available": False,
            "error": str(e),
        }
