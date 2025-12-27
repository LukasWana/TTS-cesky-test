"""
ASR router - endpointy pro Automatic Speech Recognition
"""
import uuid
import logging
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import aiofiles

from backend.api.dependencies import asr_engine
from backend.api.helpers import get_demo_voice_path
from backend.audio_processor import AudioProcessor
from backend.config import UPLOADS_DIR

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/asr", tags=["asr"])


@router.post("/transcribe")
async def transcribe_reference_audio(
    voice_file: UploadFile = File(None),
    demo_voice: str = Form(None),
    language: str = Form("sk"),
):
    """
    Přepíše referenční audio na text (ref_text) pomocí Whisper.
    """
    try:
        if (voice_file is None) == (demo_voice is None):
            raise HTTPException(status_code=400, detail="Zadejte buď voice_file, nebo demo_voice.")

        audio_path = None

        if voice_file is not None:
            file_ext = Path(voice_file.filename).suffix
            temp_filename = f"{uuid.uuid4()}{file_ext}"
            temp_path = UPLOADS_DIR / temp_filename
            async with aiofiles.open(temp_path, "wb") as f:
                content = await voice_file.read()
                await f.write(content)

            processed_path, error = AudioProcessor.process_uploaded_file(str(temp_path))
            if error:
                raise HTTPException(status_code=400, detail=error)
            audio_path = processed_path
        else:
            demo_path = get_demo_voice_path(demo_voice, lang=language)
            if not demo_path:
                raise HTTPException(status_code=404, detail=f"Demo hlas '{demo_voice}' nebyl nalezen.")
            audio_path = demo_path

        res = asr_engine.transcribe_file(
            audio_path,
            language=language or "sk",
            task="transcribe",
            return_timestamps=True,
        )

        return {
            "success": True,
            "text": res.text,
            "cleaned_text": res.cleaned_text,
            "language": res.language,
            "segments": res.segments,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při přepisu audia: {str(e)}")

