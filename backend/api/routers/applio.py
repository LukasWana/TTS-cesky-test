"""
Applio API Router
FastAPI endpoints pro Applio voice conversion a TTS
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Query, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from pathlib import Path
import aiofiles
import uuid
import time
import logging

from backend.config import (
    OUTPUTS_DIR,
)

from backend.applio.config import (
    APPLIO_VOICES_DIR,
    APPLIO_OUTPUT_SAMPLE_RATE,
)

try:
    from colorama import Fore, Style

    COLOR_OK = Fore.GREEN
    COLOR_WARN = Fore.YELLOW
    COLOR_ERROR = Fore.RED
    COLOR_RESET = Style.RESET_ALL
except ImportError:
    COLOR_OK = COLOR_WARN = COLOR_ERROR = COLOR_RESET = ""

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/applio", tags=["Applio"])

# Global engine instance (lazy initialization)
_applio_engine = None
_applio_manager = None


def get_engine():
    """Lazy getter pro Applio engine"""
    global _applio_engine
    if _applio_engine is None:
        try:
            from backend.applio.engine import ApplioEngine
            from backend.applio.config import APPLIO_BASE_URL

            _applio_engine = ApplioEngine(base_url=APPLIO_BASE_URL)
        except ImportError as e:
            logger.error(f"Cannot import Applio: {e}")
            raise HTTPException(status_code=500, detail="Applio module not available")
    return _applio_engine


def get_manager():
    """Lazy getter pro Applio subprocess manager"""
    global _applio_manager
    if _applio_manager is None:
        try:
            from backend.applio.subprocess_manager import ApplioSubprocessManager
            from backend.applio.config import APPLIO_DIR, APPLIO_BASE_URL

            _applio_manager = ApplioSubprocessManager(
                applio_dir=Path(APPLIO_DIR), config={"base_url": APPLIO_BASE_URL}
            )
        except ImportError as e:
            logger.error(f"Cannot import Applio manager: {e}")
            raise HTTPException(status_code=500, detail="Applio manager not available")
    return _applio_manager


# ==================== Pydantic Models ====================


class VoiceConversionRequest(BaseModel):
    """Request pro voice conversion"""

    voice_model: str = Field(..., description="Název RVC modelu")
    pitch_shift: int = Field(
        default=0, ge=-12, le=12, description="Pitch shift v půltónech"
    )
    index_ratio: float = Field(
        default=0.75, ge=0, le=1, description="Poměr podobnosti hlasu"
    )
    filter_radius: int = Field(default=7, ge=0, description="Filtr pro vyhlazení")
    output_format: str = Field(default="wav", description="Výstupní formát")


class TTSCloneRequest(BaseModel):
    """Request pro TTS s voice cloning"""

    text: str = Field(..., max_length=500, description="Text k syntéze")
    language: str = Field(default="cs", description="Jazyk textu")
    voice_name: Optional[str] = Field(None, description="Název EdgeTTS hlasu")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Rychlost řeči")


class ModelUploadRequest(BaseModel):
    """Request pro upload modelu"""

    model_name: str = Field(..., description="Název modelu")
    is_private: bool = Field(default=False, description="Privátní model")


# ==================== Health & Status Endpoints ====================


@router.get("/health")
async def health_check():
    """Kontrola zdraví Applio"""
    engine = get_engine()
    is_healthy = await engine.check_health()

    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "service": "applio",
        "version": "1.0.0",
    }


@router.get("/status")
async def get_status():
    """Vrátí detailní status Applio"""
    manager = get_manager()
    engine = get_engine()

    manager_status = manager.get_status()
    engine_status = await engine.get_status()

    return {
        "manager": manager_status,
        "engine": engine_status,
        "is_ready": manager.is_running and await engine.check_health(),
    }


# ==================== Voice Conversion Endpoints ====================


@router.post("/convert/{filename}")
async def voice_conversion(
    filename: str, request: VoiceConversionRequest, file: UploadFile = File(...)
):
    """
    Převod hlasu pomocí RVC modelu

    Upload audio souboru a převod na cílový hlas
    """
    # Validace souboru
    upload_dir = Path(OUTPUTS_DIR) / "applio_input"
    upload_dir.mkdir(parents=True, exist_ok=True)

    input_path = upload_dir / f"{uuid.uuid4().hex}_{filename}"

    # Uložení uploadu
    content = await file.read()
    async with aiofiles.open(input_path, "wb") as f:
        await f.write(content)

    # Výstupní cesta
    output_filename = (
        f"applio_vc_{Path(filename).stem}_{int(time.time())}.{request.output_format}"
    )
    output_path = Path(OUTPUTS_DIR) / output_filename

    try:
        engine = get_engine()

        result = await engine.voice_conversion(
            input_audio=str(input_path),
            output_path=str(output_path),
            voice_model=request.voice_model,
            pitch_shift=request.pitch_shift,
            index_ratio=request.index_ratio,
            filter_radius=request.filter_radius,
            output_format=request.output_format,
        )

        # Úklid vstupního souboru
        input_path.unlink(missing_ok=True)

        return {
            "status": "success",
            "audio_url": f"/api/audio/{Path(result).name}",
            "model": request.voice_model,
            "pitch_shift": request.pitch_shift,
            "index_ratio": request.index_ratio,
        }

    except Exception as e:
        logger.error(f"{COLOR_ERROR}Voice conversion failed: {e}{COLOR_RESET}")
        # Úklid
        input_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== TTS with Voice Cloning Endpoints ====================


@router.post("/tts-clone")
async def tts_clone(request: TTSCloneRequest, reference_file: UploadFile = File(...)):
    """
    TTS s voice cloning

    Generování řeči s klonováním hlasu z referenčního audia
    """
    # Uložení referenčního audia
    ref_dir = APPLIO_VOICES_DIR
    ref_dir.mkdir(parents=True, exist_ok=True)

    ref_path = (
        ref_dir / f"ref_{uuid.uuid4().hex}_{reference_file.filename or 'reference.wav'}"
    )

    content = await reference_file.read()
    async with aiofiles.open(ref_path, "wb") as f:
        await f.write(content)

    # Výstupní cesta
    output_filename = f"applio_tts_{request.language}_{int(time.time())}.wav"
    output_path = Path(OUTPUTS_DIR) / output_filename

    try:
        engine = get_engine()

        result = await engine.tts_with_voice_clone(
            text=request.text,
            voice_reference=str(ref_path),
            language=request.language,
            voice_name=request.voice_name,
            speed=request.speed,
            output_path=str(output_path),
        )

        # Úklid reference
        ref_path.unlink(missing_ok=True)

        return {
            "status": "success",
            "audio_url": f"/api/audio/{Path(result).name}",
            "language": request.language,
            "voice": request.voice_name or engine.get_default_voice(request.language),
            "speed": request.speed,
        }

    except Exception as e:
        logger.error(f"{COLOR_ERROR}TTS clone failed: {e}{COLOR_RESET}")
        ref_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Model Management Endpoints ====================


@router.get("/models")
async def list_models():
    """Vrátí seznam dostupných RVC modelů"""
    engine = get_engine()
    models = await engine.list_models()

    return {"models": models, "count": len(models)}


@router.get("/models/{model_name}")
async def get_model_info(model_name: str):
    """Vrátí informace o modelu"""
    engine = get_engine()
    info = await engine.get_model_info(model_name)

    if not info:
        raise HTTPException(status_code=404, detail="Model not found")

    return info


@router.post("/models/upload")
async def upload_model(
    model_name: str,
    model_file: UploadFile = File(...),
    index_file: Optional[UploadFile] = File(None),
):
    """Upload nového RVC modelu"""
    from backend.applio.config import APPLIO_MODELS_DIR

    models_dir = Path(APPLIO_MODELS_DIR)
    models_dir.mkdir(parents=True, exist_ok=True)

    # Uložení model souboru
    model_path = models_dir / f"{model_name}.pth"
    content = await model_file.read()
    async with aiofiles.open(model_path, "wb") as f:
        await f.write(content)

    # Uložení index souboru pokud existuje
    index_path = None
    if index_file:
        index_path = models_dir / f"{model_name}.index"
        content = await index_file.read()
        async with aiofiles.open(index_path, "wb") as f:
            await f.write(content)

    return {
        "status": "uploaded",
        "model": model_name,
        "model_path": str(model_path),
        "index_path": str(index_path) if index_path else None,
    }


@router.delete("/models/{model_name}")
async def delete_model(model_name: str):
    """Smaže RVC model"""
    engine = get_engine()
    success = await engine.delete_model(model_name)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete model")

    return {"status": "deleted", "model": model_name}


# ==================== Voice/peaker Endpoints ====================


@router.get("/voices")
async def list_voices(language: Optional[str] = None):
    """Vrátí seznam dostupných hlasů"""
    engine = get_engine()
    voices = await engine.get_available_voices(language)

    return {"voices": voices, "language_filter": language}


@router.get("/voices/default/{language}")
async def get_default_voice(language: str):
    """Vrátí výchozí hlas pro jazyk"""
    engine = get_engine()
    default_voice = engine.get_default_voice(language)

    return {"language": language, "default_voice": default_voice}


# ==================== Server Management Endpoints ====================


@router.post("/server/start")
async def start_server(background_tasks: BackgroundTasks):
    """Spustí Applio server"""
    manager = get_manager()

    if manager.is_running:
        return {"status": "already_running", "url": manager.config.get("base_url")}

    # Spustíme v background
    success = await manager.start(timeout=120)

    if success:
        return {
            "status": "started",
            "url": manager.config.get("base_url"),
            "uptime": manager.uptime,
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to start Applio server")


@router.post("/server/stop")
async def stop_server():
    """Zastaví Applio server"""
    manager = get_manager()

    await manager.stop()

    return {"status": "stopped"}


@router.get("/server/info")
async def get_server_info():
    """Vrátí info o serveru"""
    manager = get_manager()

    return {
        "running": manager.is_running,
        "uptime_seconds": manager.uptime,
        "config": manager.config,
    }
