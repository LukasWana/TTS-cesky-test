"""
Resolver pro voice soubory (upload/demo)
"""
import uuid
import logging
from pathlib import Path
from typing import Optional, Tuple
from fastapi import UploadFile, HTTPException
import aiofiles

from backend.api.helpers import get_demo_voice_path
from backend.audio_processor import AudioProcessor
from backend.config import UPLOADS_DIR, DEMO_VOICES_CS_DIR, DEMO_VOICES_SK_DIR

logger = logging.getLogger(__name__)


async def resolve_voice_file(
    voice_file: Optional[UploadFile] = None,
    demo_voice: Optional[str] = None,
    lang: str = "cs",
) -> Tuple[Optional[str], Optional[dict]]:
    """
    Vyřeší voice soubor z upload nebo demo voice

    Returns:
        Tuple[speaker_wav_path, reference_quality_dict]
    """
    speaker_wav = None
    reference_quality = None

    if voice_file:
        # Upload handling
        file_ext = Path(voice_file.filename).suffix
        temp_filename = f"{uuid.uuid4()}{file_ext}"
        temp_path = UPLOADS_DIR / temp_filename

        async with aiofiles.open(temp_path, 'wb') as f:
            content = await voice_file.read()
            await f.write(content)

        processed_path, error = AudioProcessor.process_uploaded_file(str(temp_path))
        if error:
            raise HTTPException(status_code=400, detail=error)
        speaker_wav = processed_path

    elif demo_voice:
        # Demo voice handling
        demo_path = get_demo_voice_path(demo_voice, lang=lang)
        if not demo_path:
            # Fallback na první dostupný demo voice
            demo_voices_dir = DEMO_VOICES_CS_DIR if lang == "cs" else DEMO_VOICES_SK_DIR
            available_voices = list(demo_voices_dir.glob("*.wav"))
            if available_voices:
                speaker_wav = str(available_voices[0])
                logger.warning(f"Demo voice '{demo_voice}' not found, using: {speaker_wav}")
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"Demo hlas '{demo_voice}' neexistuje a žádné demo hlasy nejsou k dispozici. Prosím nahrajte audio soubor."
                )
        else:
            speaker_wav = demo_path
    else:
        raise HTTPException(
            status_code=400,
            detail="Musí být zadán buď voice_file nebo demo_voice"
        )

    return speaker_wav, reference_quality


async def resolve_default_voice(
    default_voice_file: Optional[UploadFile] = None,
    default_demo_voice: Optional[str] = None,
    default_language: str = "cs",
) -> str:
    """
    Vyřeší default voice pro multi-lang generování

    Returns:
        Path k default speaker WAV souboru
    """
    from backend.api.helpers import _get_demo_voices_dir

    if default_voice_file:
        file_ext = Path(default_voice_file.filename).suffix
        temp_filename = f"{uuid.uuid4()}{file_ext}"
        temp_path = UPLOADS_DIR / temp_filename

        async with aiofiles.open(temp_path, 'wb') as f:
            content = await default_voice_file.read()
            await f.write(content)

        processed_path, error = AudioProcessor.process_uploaded_file(str(temp_path))
        if error:
            raise HTTPException(status_code=400, detail=error)
        return processed_path

    elif default_demo_voice:
        demo_path = get_demo_voice_path(default_demo_voice, lang=default_language)
        if demo_path:
            return demo_path
        else:
            available_voices = list(_get_demo_voices_dir(default_language).glob("*.wav"))
            if available_voices:
                result = str(available_voices[0])
                logger.warning(f"Demo voice '{default_demo_voice}' not found, using: {result}")
                return result
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"Demo hlas '{default_demo_voice}' neexistuje a žádné demo hlasy nejsou k dispozici."
                )
    else:
        # Fallback na první dostupný demo voice
        available_voices = list(_get_demo_voices_dir(default_language).glob("*.wav"))
        if available_voices:
            result = str(available_voices[0])
            logger.info(f"Žádný výchozí hlas zadán, používám: {result}")
            return result
        else:
            raise HTTPException(
                status_code=400,
                detail="Musí být zadán buď default_voice_file nebo default_demo_voice, nebo musí existovat demo hlasy"
            )

