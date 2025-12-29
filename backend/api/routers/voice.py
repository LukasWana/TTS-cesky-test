"""
Voice router - endpointy pro správu hlasů
"""
import base64
import uuid
import re
import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
import aiofiles

from backend.api.helpers import get_demo_voice_path, _get_demo_voices_dir, _normalize_demo_lang
from backend.audio_processor import AudioProcessor
from backend.config import UPLOADS_DIR, MIN_VOICE_DURATION
from backend.youtube_downloader import (
    download_youtube_audio,
    validate_youtube_url,
    sanitize_filename,
    extract_video_id,
    get_video_info,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["voice"])


@router.post("/voice/upload")
async def upload_voice(
    voice_file: UploadFile = File(...),
    remove_background: bool = Form(False)
):
    """Nahraje audio soubor pro voice cloning"""
    try:
        file_ext = Path(voice_file.filename).suffix
        voice_id = str(uuid.uuid4())
        temp_filename = f"{voice_id}{file_ext}"
        temp_path = UPLOADS_DIR / temp_filename

        async with aiofiles.open(temp_path, 'wb') as f:
            content = await voice_file.read()
            await f.write(content)

        processed_path, error = AudioProcessor.process_uploaded_file(
            str(temp_path),
            f"{voice_id}.wav",
            remove_background=remove_background
        )

        if error:
            raise HTTPException(status_code=400, detail=error)

        quality_info = AudioProcessor.analyze_audio_quality(processed_path)

        # Validace typu audia pomocí klasifikace
        try:
            from backend.config import ENABLE_AUDIO_CLASSIFICATION, AUDIO_CLASSIFICATION_MIN_SPEECH_RATIO

            if ENABLE_AUDIO_CLASSIFICATION and quality_info.get('classification_available'):
                audio_type = quality_info.get('audio_type', 'unknown')
                speech_ratio = quality_info.get('speech_ratio', 0.0)
                suitable_for_cloning = quality_info.get('suitable_for_cloning', True)

                # Pokud není řeč nebo málo řeči, vrátit chybu
                if audio_type == 'music':
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "message": "Nahraný soubor obsahuje převážně hudbu, ne řeč. Nahrajte audio s mluveným slovem.",
                            "audio_type": audio_type,
                            "speech_ratio": speech_ratio,
                            "quality": quality_info
                        }
                    )

                if speech_ratio < AUDIO_CLASSIFICATION_MIN_SPEECH_RATIO:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "message": f"Audio obsahuje málo řeči ({speech_ratio:.0%}). Pro voice cloning je potřeba alespoň {AUDIO_CLASSIFICATION_MIN_SPEECH_RATIO:.0%} řeči.",
                            "audio_type": audio_type,
                            "speech_ratio": speech_ratio,
                            "quality": quality_info
                        }
                    )

                if not suitable_for_cloning:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "message": "Audio není vhodné pro voice cloning. Nahrajte čistší vzorek řeči (10-30s bez hudby v pozadí).",
                            "audio_type": audio_type,
                            "speech_ratio": speech_ratio,
                            "has_music": quality_info.get('has_music', False),
                            "quality": quality_info
                        }
                    )
        except HTTPException:
            raise
        except Exception as e:
            # Pokud klasifikace selže, logovat ale nepřerušit upload
            logger.warning(f"Chyba při validaci typu audia: {e}")

        return {
            "voice_id": voice_id,
            "processed": True,
            "file_path": processed_path,
            "quality": quality_info
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při uploadu: {str(e)}")


@router.post("/voice/record")
async def record_voice(
    audio_blob: str = Form(...),
    filename: str = Form(None),
    lang: str = Form("cs"),
):
    """Uloží audio nahrané z mikrofonu jako demo hlas"""
    try:
        audio_data = base64.b64decode(audio_blob.split(',')[1])

        if filename:
            filename = sanitize_filename(filename)
        else:
            filename = f"record_{uuid.uuid4().hex[:8]}"

        if not filename.endswith('.wav'):
            filename = f"{filename}.wav"

        temp_path = UPLOADS_DIR / f"temp_{uuid.uuid4()}.wav"
        with open(temp_path, 'wb') as f:
            f.write(audio_data)

        demo_dir = _get_demo_voices_dir(lang)
        output_path = demo_dir / filename
        success, error = AudioProcessor.convert_audio(
            str(temp_path),
            str(output_path),
            apply_advanced_processing=True
        )

        temp_path.unlink(missing_ok=True)

        if not success:
            raise HTTPException(status_code=400, detail=error)

        try:
            import librosa
            duration = librosa.get_duration(path=str(output_path))
            if duration < 3.0:
                output_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=400,
                    detail=f"Audio je příliš krátké ({duration:.1f}s). Minimálně 3 sekundy pro nahrávání z mikrofonu, doporučeno 6+ sekund pro lepší kvalitu."
                )
            elif duration < MIN_VOICE_DURATION:
                logger.warning(f"Recorded audio is short ({duration:.1f}s), recommended minimum is {MIN_VOICE_DURATION}s")
        except Exception as e:
            output_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail=f"Chyba při validaci audio: {str(e)}")

        path = Path(output_path)
        if not path.exists():
            raise HTTPException(status_code=400, detail="Soubor neexistuje")

        if path.suffix.lower() != ".wav":
            raise HTTPException(status_code=400, detail="Nepodporovaný formát")

        audio_url = f"/api/audio/demo/{_normalize_demo_lang(lang)}/{filename}"

        quality_info = AudioProcessor.analyze_audio_quality(str(output_path))

        return {
            "success": True,
            "filename": filename,
            "audio_url": audio_url,
            "file_path": str(output_path),
            "quality": quality_info
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při ukládání nahrávky: {str(e)}")


@router.get("/voices/demo")
async def get_demo_voices(lang: str = Query("cs")):
    """Vrátí seznam dostupných demo hlasů"""
    demo_voices = []

    lang_norm = _normalize_demo_lang(lang)
    demo_dir = _get_demo_voices_dir(lang_norm)

    # Debug: zkontroluj, že adresář existuje
    if not demo_dir.exists():
        logger.warning(f"Demo voices directory does not exist: {demo_dir}")
        return {"voices": []}

    # Debug: zkontroluj, že adresář obsahuje soubory
    wav_files = list(demo_dir.glob("*.wav"))
    logger.info(f"Found {len(wav_files)} WAV files in {demo_dir} for lang={lang_norm}")

    for voice_file in wav_files:
        voice_id = voice_file.stem
        voice_id_lower = voice_id.lower()

        gender = "unknown"
        gender_keywords = []

        has_female = "female" in voice_id_lower or "žena" in voice_id_lower or "demo2" in voice_id_lower
        has_male = "male" in voice_id_lower or "muž" in voice_id_lower or "demo1" in voice_id_lower

        if has_female:
            gender = "female"
            if "female" in voice_id_lower:
                gender_keywords.append("female")
            if "žena" in voice_id_lower:
                gender_keywords.append("žena")
            if "demo2" in voice_id_lower:
                gender_keywords.append("demo2")
        elif has_male:
            gender = "male"
            if "male" in voice_id_lower:
                gender_keywords.append("male")
            if "muž" in voice_id_lower:
                gender_keywords.append("muž")
            if "demo1" in voice_id_lower:
                gender_keywords.append("demo1")

        clean_name = voice_id
        for keyword in gender_keywords:
            keyword_escaped = re.escape(keyword)
            pattern = rf"[-_]?{keyword_escaped}[-_]?"
            clean_name = re.sub(pattern, "", clean_name, flags=re.IGNORECASE)

        clean_name = re.sub(r"[-_]+", "_", clean_name)
        clean_name = clean_name.strip("_-")

        formatted_name = clean_name.replace("_", " ").title() if clean_name else voice_id.replace("_", " ").title()

        if gender == "male":
            display_name = f"Muž: {formatted_name}"
        elif gender == "female":
            display_name = f"Žena: {formatted_name}"
        else:
            display_name = formatted_name

        demo_voices.append({
            "id": voice_id,
            "name": formatted_name,
            "display_name": display_name,
            "gender": gender,
            "lang": lang_norm,
            "preview_url": f"/api/audio/demo/{lang_norm}/{voice_file.name}"
        })

    return {"voices": demo_voices}


@router.post("/voice/youtube")
async def download_youtube_voice(
    url: str = Form(...),
    start_time: float = Form(None),
    duration: float = Form(None),
    filename: str = Form(None),
    lang: str = Form("cs"),
    remove_background: bool = Form(False),
):
    """Stáhne audio z YouTube a uloží jako demo hlas"""
    try:
        is_valid, error = validate_youtube_url(url)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error)

        if start_time is not None and start_time < 0:
            raise HTTPException(status_code=400, detail="start_time musí být >= 0")

        if duration is not None:
            if duration < MIN_VOICE_DURATION:
                raise HTTPException(
                    status_code=400,
                    detail=f"duration musí být minimálně {MIN_VOICE_DURATION} sekund"
                )
            if duration > 600:
                raise HTTPException(
                    status_code=400,
                    detail="duration musí být maximálně 600 sekund (10 minut)"
                )

        video_id = extract_video_id(url)
        if not video_id:
            raise HTTPException(status_code=400, detail="Neplatné YouTube URL")

        if not filename:
            video_info, error = get_video_info(url)
            if video_info and video_info.get("title"):
                filename = sanitize_filename(video_info["title"])
            else:
                filename = f"youtube_{video_id}"

        if not filename.endswith('.wav'):
            filename = f"{filename}.wav"

        demo_dir = _get_demo_voices_dir(lang)
        output_path = demo_dir / filename

        success, error = download_youtube_audio(
            url,
            str(output_path),
            start_time=start_time,
            duration=duration,
            remove_background=remove_background,
        )

        if not success:
            raise HTTPException(status_code=400, detail=error)

        audio_url = f"/api/audio/demo/{_normalize_demo_lang(lang)}/{filename}"

        quality_info = AudioProcessor.analyze_audio_quality(str(output_path))

        return {
            "success": True,
            "filename": filename,
            "audio_url": audio_url,
            "file_path": str(output_path),
            "quality": quality_info
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při stahování YouTube audia: {str(e)}")

