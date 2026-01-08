"""
Audio router - endpointy pro serving audio souborů
"""

import logging
import time
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.api.helpers import _get_demo_voices_dir, _normalize_demo_lang
from backend.config import OUTPUTS_DIR

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audio", tags=["audio"])

# Cache pro varování o neexistujících souborech (aby se neopakovaly stále dokola)
_missing_file_warnings = {}  # {filename: timestamp}
_WARNING_CACHE_TTL = (
    60  # Logovat varování maximálně jednou za 60 sekund pro stejný soubor
)

# Mapa přípon na MIME typy
AUDIO_MIME_TYPES = {
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
}


def _get_audio_mime_type(filename: str) -> str:
    """Získá správný MIME typ pro audio soubor."""
    ext = Path(filename).suffix.lower()
    return AUDIO_MIME_TYPES.get(ext, "application/octet-stream")


def _normalize_audio_filename(filename: str) -> str:
    """Normalizuje název audio souboru - odstraní nebezpečné znaky."""
    norm = filename.strip().replace("\\", "/")
    if ".." in norm or "/" in norm:
        raise HTTPException(status_code=400, detail="Neplatný název souboru")
    return norm


@router.get("/{filename}")
async def get_audio(filename: str):
    """Vrátí audio soubor z outputs"""
    filename = _normalize_audio_filename(filename)

    try:
        file_path = (OUTPUTS_DIR / filename).resolve()
        outputs_dir_resolved = OUTPUTS_DIR.resolve()

        if not str(file_path).startswith(str(outputs_dir_resolved)):
            raise HTTPException(status_code=403, detail="Přístup zamítnut")
    except (ValueError, OSError) as e:
        raise HTTPException(status_code=400, detail=f"Neplatná cesta: {str(e)}")

    if not file_path.exists():
        current_time = time.time()
        last_warning_time = _missing_file_warnings.get(filename, 0)

        if current_time - last_warning_time > _WARNING_CACHE_TTL:
            logger.warning(
                f"Audio file not found: {file_path} (requested as {filename})"
            )
            _missing_file_warnings[filename] = current_time

            if len(_missing_file_warnings) > 1000:
                cutoff_time = current_time - 300
                _missing_file_warnings.clear()

        raise HTTPException(status_code=404, detail="Soubor nebyl nalezen")

    return FileResponse(
        str(file_path),
        media_type=_get_audio_mime_type(filename),
        filename=filename,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
    )


@router.get("/demo/{filename:path}")
async def get_demo_audio(filename: str):
    """Vrátí demo audio soubor"""
    norm = filename.replace("\\", "/").strip("/")
    if norm == "" or ".." in norm:
        raise HTTPException(status_code=400, detail="Neplatný název souboru")

    parts = norm.split("/", 1)
    if len(parts) == 2 and parts[0].lower() in ("cs", "sk"):
        lang_norm = _normalize_demo_lang(parts[0])
        fname = parts[1]
    else:
        lang_norm = "cs"
        fname = norm

    if "/" in fname or "\\" in fname or ".." in fname:
        raise HTTPException(status_code=400, detail="Neplatný název souboru")

    demo_dir = _get_demo_voices_dir(lang_norm)

    try:
        file_path = (demo_dir / fname).resolve()
        demo_dir_resolved = demo_dir.resolve()

        if not str(file_path).startswith(str(demo_dir_resolved)):
            raise HTTPException(status_code=403, detail="Přístup zamítnut")
    except (ValueError, OSError) as e:
        raise HTTPException(status_code=400, detail=f"Neplatná cesta: {str(e)}")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Demo audio neexistuje")

    return FileResponse(
        str(file_path),
        media_type=_get_audio_mime_type(fname),
        filename=filename,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
    )
