"""
TTS router - endpointy pro text-to-speech generování
"""
import re
import uuid
import json
import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
import aiofiles

from backend.api.dependencies import (
    tts_engine,
    f5_tts_engine,
    f5_tts_slovak_engine,
)
from backend.api.helpers import get_demo_voice_path, _get_demo_voices_dir
from backend.progress_manager import ProgressManager
from backend.audio_processor import AudioProcessor
from backend.history_manager import HistoryManager
from backend.config import (
    UPLOADS_DIR,
    DEMO_VOICES_CS_DIR,
    DEMO_VOICES_SK_DIR,
    MAX_TEXT_LENGTH,
    TTS_SPEED,
    TTS_TEMPERATURE,
    TTS_LENGTH_PENALTY,
    TTS_REPETITION_PENALTY,
    TTS_TOP_K,
    TTS_TOP_P,
    ENABLE_AUDIO_ENHANCEMENT,
    AUDIO_ENHANCEMENT_PRESET,
    ENABLE_BATCH_PROCESSING,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tts", tags=["tts"])


@router.post("/generate")
async def generate_speech(
    text: str = Form(...),
    job_id: str = Form(None),
    voice_file: UploadFile = File(None),
    demo_voice: str = Form(None),
    speed: str = Form(None),
    temperature: float = Form(None),
    length_penalty: float = Form(None),
    repetition_penalty: float = Form(None),
    top_k: int = Form(None),
    top_p: float = Form(None),
    quality_mode: str = Form(None),
    enhancement_preset: str = Form(None),
    enable_enhancement: str = Form(None),
    seed: int = Form(None),
    multi_pass: str = Form(None),
    multi_pass_count: int = Form(None),
    enable_vad: str = Form(None),
    enable_batch: str = Form(None),
    use_hifigan: str = Form(None),
    enable_normalization: str = Form(None),
    enable_denoiser: str = Form(None),
    enable_compressor: str = Form(None),
    enable_deesser: str = Form(None),
    enable_eq: str = Form(None),
    enable_trim: str = Form(None),
    enable_dialect_conversion: str = Form(None),
    dialect_code: str = Form(None),
    dialect_intensity: str = Form(None),
    hifigan_refinement_intensity: str = Form(None),
    hifigan_normalize_output: str = Form(None),
    hifigan_normalize_gain: str = Form(None),
    enable_whisper: str = Form(None),
    whisper_intensity: str = Form(None),
    target_headroom_db: str = Form(None),
    auto_enhance_voice: str = Form(None),
    allow_poor_voice: str = Form(None),
):
    """
    Generuje řeč z textu pomocí XTTS
    """
    try:
        if job_id:
            ProgressManager.start(
                job_id,
                meta={
                    "text_length": len(text or ""),
                    "endpoint": "/api/tts/generate",
                },
            )

        if not tts_engine.is_loaded:
            if job_id:
                ProgressManager.update(job_id, percent=5, stage="load", message="Načítám XTTS model do VRAM…")
            await tts_engine.load_model()
        else:
            if job_id:
                ProgressManager.update(job_id, percent=10, stage="load", message="Model je připraven, začínám syntézu…")

        # Zpracování parametrů
        if speed is not None:
            try:
                tts_speed = float(speed) if isinstance(speed, str) else float(speed)
            except (ValueError, TypeError):
                tts_speed = TTS_SPEED
        else:
            tts_speed = TTS_SPEED

        tts_temperature = float(temperature) if temperature is not None else TTS_TEMPERATURE
        tts_length_penalty = float(length_penalty) if length_penalty is not None else TTS_LENGTH_PENALTY
        tts_repetition_penalty = float(repetition_penalty) if repetition_penalty is not None else TTS_REPETITION_PENALTY
        tts_top_k = int(top_k) if top_k is not None else TTS_TOP_K
        tts_top_p = float(top_p) if top_p is not None else TTS_TOP_P

        use_multi_pass = (multi_pass.lower() == "true") if isinstance(multi_pass, str) else bool(multi_pass)
        multi_pass_count_value = int(multi_pass_count) if multi_pass_count is not None else 3

        enable_enh_flag = (enable_enhancement.lower() == "true") if isinstance(enable_enhancement, str) else ENABLE_AUDIO_ENHANCEMENT
        enable_vad_flag = (enable_vad.lower() == "true") if isinstance(enable_vad, str) else None
        use_batch_flag = (enable_batch.lower() == "true") if isinstance(enable_batch, str) else None
        use_hifigan_flag = (use_hifigan.lower() == "true") if isinstance(use_hifigan, str) else False

        enable_norm = (enable_normalization.lower() == "true") if isinstance(enable_normalization, str) else None
        enable_den = (enable_denoiser.lower() == "true") if isinstance(enable_denoiser, str) else None
        enable_comp = (enable_compressor.lower() == "true") if isinstance(enable_compressor, str) else None
        enable_deess = (enable_deesser.lower() == "true") if isinstance(enable_deesser, str) else None
        enable_eq_flag = (enable_eq.lower() == "true") if isinstance(enable_eq, str) else None
        enable_trim_flag = (enable_trim.lower() == "true") if isinstance(enable_trim, str) else None

        use_dialect = (enable_dialect_conversion.lower() == "true") if isinstance(enable_dialect_conversion, str) else False
        dialect_code_value = dialect_code if dialect_code and dialect_code != "standardni" else None
        try:
            dialect_intensity_value = float(dialect_intensity) if dialect_intensity else 1.0
        except (ValueError, TypeError):
            dialect_intensity_value = 1.0

        # Whisper a headroom parametry - musí být definovány dříve, protože se používají v multi-lang části
        enable_whisper_value = (enable_whisper.lower() == "true") if isinstance(enable_whisper, str) else None
        try:
            whisper_intensity_value = float(whisper_intensity) if whisper_intensity else None
            if whisper_intensity_value is not None and not (0.0 <= whisper_intensity_value <= 1.0):
                raise HTTPException(status_code=400, detail="whisper_intensity musí být mezi 0.0 a 1.0")
        except (ValueError, TypeError):
            whisper_intensity_value = None

        try:
            target_headroom_db_value = float(target_headroom_db) if target_headroom_db else None
            if target_headroom_db_value is not None and not (-128.0 <= target_headroom_db_value <= 0.0):
                raise HTTPException(status_code=400, detail="target_headroom_db musí být mezi -128.0 a 0.0 dB")
        except (ValueError, TypeError):
            target_headroom_db_value = None

        # HiFi-GAN parametry
        try:
            hifigan_refinement_intensity_value = float(hifigan_refinement_intensity) if hifigan_refinement_intensity else None
            if hifigan_refinement_intensity_value is not None and not (0.0 <= hifigan_refinement_intensity_value <= 1.0):
                raise HTTPException(status_code=400, detail="hifigan_refinement_intensity musí být mezi 0.0 a 1.0")
        except (ValueError, TypeError):
            hifigan_refinement_intensity_value = None

        hifigan_normalize_output_value = (hifigan_normalize_output.lower() == "true") if isinstance(hifigan_normalize_output, str) else None

        try:
            hifigan_normalize_gain_value = float(hifigan_normalize_gain) if hifigan_normalize_gain else None
            if hifigan_normalize_gain_value is not None and not (0.0 <= hifigan_normalize_gain_value <= 1.0):
                raise HTTPException(status_code=400, detail="hifigan_normalize_gain musí být mezi 0.0 a 1.0")
        except (ValueError, TypeError):
            hifigan_normalize_gain_value = None

        if not text or len(text.strip()) == 0:
            raise HTTPException(status_code=400, detail="Text je prázdný")

        multi_lang_pattern = re.compile(r'\[(\w+)(?::([^\]]+))?\]')
        has_multi_lang_annotations = bool(multi_lang_pattern.search(text))

        if has_multi_lang_annotations:
            logger.info(f"Detekovány multi-lang/speaker anotace v textu, používám multi-lang generování (multi_pass={use_multi_pass})")
            default_speaker_wav = None
            if voice_file:
                file_ext = Path(voice_file.filename).suffix
                temp_filename = f"{uuid.uuid4()}{file_ext}"
                temp_path = UPLOADS_DIR / temp_filename
                async with aiofiles.open(temp_path, 'wb') as f:
                    content = await voice_file.read()
                    await f.write(content)
                processed_path, error = AudioProcessor.process_uploaded_file(str(temp_path))
                if error:
                    raise HTTPException(status_code=400, detail=error)
                default_speaker_wav = processed_path
            elif demo_voice:
                demo_path = get_demo_voice_path(demo_voice, lang="cs")
                if demo_path:
                    default_speaker_wav = demo_path
                else:
                    available_voices = list(DEMO_VOICES_CS_DIR.glob("*.wav"))
                    if available_voices:
                        default_speaker_wav = str(available_voices[0])
                    else:
                        raise HTTPException(status_code=404, detail="Žádné demo hlasy nejsou k dispozici")
            else:
                available_voices = list(DEMO_VOICES_CS_DIR.glob("*.wav"))
                if available_voices:
                    default_speaker_wav = str(available_voices[0])
                else:
                    raise HTTPException(status_code=400, detail="Musí být zadán voice_file nebo demo_voice")

            speaker_ids = set()
            for match in multi_lang_pattern.finditer(text):
                speaker_id = match.group(2)
                if speaker_id:
                    speaker_ids.add(speaker_id)

            speaker_map = {}
            if speaker_ids:
                for sid in speaker_ids:
                    demo_path = get_demo_voice_path(sid, lang="cs")
                    if demo_path:
                        speaker_map[sid] = demo_path
                    elif Path(sid).exists():
                        speaker_map[sid] = sid
                    else:
                        speaker_map[sid] = default_speaker_wav

            if use_multi_pass:
                logger.info(f"Generuji {multi_pass_count_value} variant pro multi-lang")
                variants = []
                for i in range(multi_pass_count_value):
                    if job_id:
                        ProgressManager.update(job_id, percent=2 + (90 * i / multi_pass_count_value), message=f"Generuji variantu {i+1}/{multi_pass_count_value} (multi-lang)…")

                    v_seed = (seed or 42) + i
                    output_path = await tts_engine.generate_multi_lang_speaker(
                        text=text,
                        default_speaker_wav=default_speaker_wav,
                        default_language="cs",
                        speaker_map=speaker_map if speaker_map else None,
                        speed=tts_speed,
                        temperature=tts_temperature + (0.05 * (i % 3 - 1)),
                        length_penalty=tts_length_penalty,
                        repetition_penalty=tts_repetition_penalty,
                        top_k=tts_top_k,
                        top_p=tts_top_p,
                        quality_mode=quality_mode,
                        enhancement_preset=enhancement_preset,
                        seed=v_seed,
                        enable_vad=enable_vad_flag,
                        enable_batch=use_batch_flag,
                        enable_enhancement=enable_enh_flag,
                        enable_normalization=enable_norm,
                        enable_denoiser=enable_den,
                        enable_compressor=enable_comp,
                        enable_deesser=enable_deess,
                        enable_eq=enable_eq_flag,
                        enable_trim=enable_trim_flag,
                        enable_dialect_conversion=use_dialect,
                        dialect_code=dialect_code_value,
                        dialect_intensity=dialect_intensity_value,
                        enable_whisper=enable_whisper_value,
                        whisper_intensity=whisper_intensity_value,
                        target_headroom_db=target_headroom_db_value,
                        use_hifigan=use_hifigan_flag,
                        hifigan_refinement_intensity=hifigan_refinement_intensity_value,
                        hifigan_normalize_output=hifigan_normalize_output_value,
                        hifigan_normalize_gain=hifigan_normalize_gain_value,
                        job_id=job_id
                    )
                    filename = Path(output_path).name
                    variants.append({
                        "audio_url": f"/api/audio/{filename}",
                        "filename": filename,
                        "seed": v_seed,
                        "temperature": tts_temperature + (0.05 * (i % 3 - 1)),
                        "index": i + 1
                    })

                if job_id:
                    ProgressManager.done(job_id)

                return {
                    "variants": variants,
                    "success": True,
                    "multi_pass": True,
                    "multi_lang": True
                }

            output_path = await tts_engine.generate_multi_lang_speaker(
                text=text,
                default_speaker_wav=default_speaker_wav,
                default_language="cs",
                speaker_map=speaker_map if speaker_map else None,
                speed=tts_speed,
                temperature=tts_temperature,
                length_penalty=tts_length_penalty,
                repetition_penalty=tts_repetition_penalty,
                top_k=tts_top_k,
                top_p=tts_top_p,
                quality_mode=quality_mode,
                enhancement_preset=enhancement_preset,
                seed=seed,
                enable_vad=enable_vad_flag,
                enable_batch=use_batch_flag,
                enable_enhancement=enable_enh_flag,
                enable_normalization=enable_norm,
                enable_denoiser=enable_den,
                enable_compressor=enable_comp,
                enable_deesser=enable_deess,
                enable_eq=enable_eq_flag,
                enable_trim=enable_trim_flag,
                enable_dialect_conversion=use_dialect,
                dialect_code=dialect_code_value,
                dialect_intensity=dialect_intensity_value,
                enable_whisper=enable_whisper_value,
                whisper_intensity=whisper_intensity_value,
                target_headroom_db=target_headroom_db_value,
                use_hifigan=use_hifigan_flag,
                hifigan_refinement_intensity=hifigan_refinement_intensity_value,
                hifigan_normalize_output=hifigan_normalize_output_value,
                hifigan_normalize_gain=hifigan_normalize_gain_value,
                job_id=job_id
            )

            filename = Path(output_path).name
            audio_url = f"/api/audio/{filename}"

            if job_id:
                ProgressManager.done(job_id)

            return {
                "audio_url": audio_url,
                "filename": filename,
                "success": True,
                "job_id": job_id,
                "multi_lang": True,
            }

        text_length = len(text)
        if text_length > MAX_TEXT_LENGTH:
            logger.warning(f"Text je delší než {MAX_TEXT_LENGTH} znaků ({text_length} znaků), automaticky zapínám batch processing")
            if use_batch_flag is None or use_batch_flag is True:
                use_batch = True
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Text je příliš dlouhý ({text_length} znaků, max {MAX_TEXT_LENGTH}). Pro delší texty zapněte batch processing (enable_batch=true)."
                )
        elif text_length > 2000:
            logger.info(f"Text je dlouhý ({text_length} znaků), doporučuji zapnout batch processing pro lepší kvalitu")
            use_batch = use_batch_flag if use_batch_flag is not None else ENABLE_BATCH_PROCESSING
        else:
            use_batch = use_batch_flag if use_batch_flag is not None else False

        speaker_wav = None
        reference_quality = None

        if voice_file:
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
            demo_path = get_demo_voice_path(demo_voice, lang="cs")
            if not demo_path:
                available_voices = list(DEMO_VOICES_CS_DIR.glob("*.wav"))
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

        try:
            from backend.config import (
                ENABLE_REFERENCE_QUALITY_GATE,
                ENABLE_REFERENCE_AUTO_ENHANCE,
                REFERENCE_ALLOW_POOR_BY_DEFAULT,
                UPLOADS_DIR,
            )
            reference_quality = AudioProcessor.analyze_audio_quality(speaker_wav) if speaker_wav else None

            if ENABLE_REFERENCE_QUALITY_GATE and reference_quality and reference_quality.get("score") == "poor":
                request_auto = (auto_enhance_voice.lower() == "true") if isinstance(auto_enhance_voice, str) else None
                request_allow = (allow_poor_voice.lower() == "true") if isinstance(allow_poor_voice, str) else None

                do_auto = request_auto if request_auto is not None else ENABLE_REFERENCE_AUTO_ENHANCE

                is_demo_voice = False
                try:
                    speaker_resolved = Path(speaker_wav).resolve()
                    is_demo_voice = (
                        speaker_resolved.is_relative_to(DEMO_VOICES_CS_DIR.resolve())
                        or speaker_resolved.is_relative_to(DEMO_VOICES_SK_DIR.resolve())
                    )
                except Exception:
                    try:
                        speaker_resolved_str = str(Path(speaker_wav).resolve())
                        is_demo_voice = (
                            speaker_resolved_str.startswith(str(DEMO_VOICES_CS_DIR.resolve()))
                            or speaker_resolved_str.startswith(str(DEMO_VOICES_SK_DIR.resolve()))
                        )
                    except Exception:
                        is_demo_voice = False

                if request_allow is None and is_demo_voice:
                    do_allow = True
                else:
                    do_allow = request_allow if request_allow is not None else REFERENCE_ALLOW_POOR_BY_DEFAULT

                if do_auto:
                    enhanced_path = UPLOADS_DIR / f"enhanced_{uuid.uuid4().hex[:10]}.wav"
                    ok, enh_err = AudioProcessor.enhance_voice_sample(speaker_wav, str(enhanced_path))
                    if ok:
                        speaker_wav = str(enhanced_path)
                        reference_quality = AudioProcessor.analyze_audio_quality(speaker_wav)
                    else:
                        logger.warning(f"Auto-enhance referenčního hlasu selhal: {enh_err}")

                if reference_quality and reference_quality.get("score") == "poor" and not do_allow:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "message": "Referenční audio má nízkou kvalitu pro klonování (šum/clipping/krátká délka). Nahrajte čistší vzorek (10–30s řeči bez hudby) nebo použijte allow_poor_voice=true.",
                            "quality": reference_quality,
                        },
                    )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Quality gate selhal (ignorováno): {e}")

        if not (0.5 <= tts_speed <= 2.0):
            raise HTTPException(status_code=400, detail="Speed musí být mezi 0.5 a 2.0")
        if not (0.0 <= tts_temperature <= 1.0):
            raise HTTPException(status_code=400, detail="Temperature musí být mezi 0.0 a 1.0")
        if tts_top_k < 1:
            raise HTTPException(status_code=400, detail="top_k musí být >= 1")
        if not (0.0 <= tts_top_p <= 1.0):
            raise HTTPException(status_code=400, detail="top_p musí být mezi 0.0 a 1.0")

        tts_quality_mode = quality_mode if quality_mode else None
        enhancement_preset_value = enhancement_preset if enhancement_preset else (quality_mode if quality_mode else AUDIO_ENHANCEMENT_PRESET)

        if job_id:
            ProgressManager.update(job_id, percent=1, stage="tts", message="Generuji řeč…")
        logger.info(f"UI headroom: target_headroom_db={target_headroom_db_value} dB, enable_enhancement={enable_enh_flag}, enable_normalization={enable_norm}")
        result = await tts_engine.generate(
            text=text,
            speaker_wav=speaker_wav,
            language="cs",
            speed=tts_speed,
            temperature=tts_temperature,
            length_penalty=tts_length_penalty,
            repetition_penalty=tts_repetition_penalty,
            top_k=tts_top_k,
            top_p=tts_top_p,
            quality_mode=tts_quality_mode,
            seed=seed,
            enhancement_preset=enhancement_preset_value,
            enable_enhancement=enable_enh_flag,
            multi_pass=use_multi_pass,
            multi_pass_count=multi_pass_count_value,
            enable_batch=use_batch,
            enable_vad=enable_vad_flag,
            use_hifigan=use_hifigan_flag,
            enable_normalization=enable_norm,
            enable_denoiser=enable_den,
            enable_compressor=enable_comp,
            enable_deesser=enable_deess,
            enable_eq=enable_eq_flag,
            enable_trim=enable_trim_flag,
            enable_dialect_conversion=use_dialect,
            dialect_code=dialect_code_value,
            dialect_intensity=dialect_intensity_value,
            enable_whisper=enable_whisper_value,
            whisper_intensity=whisper_intensity_value,
            target_headroom_db=target_headroom_db_value,
            hifigan_refinement_intensity=hifigan_refinement_intensity_value,
            hifigan_normalize_output=hifigan_normalize_output_value,
            hifigan_normalize_gain=hifigan_normalize_gain_value,
            job_id=job_id
        )

        if isinstance(result, list):
            return {
                "variants": result,
                "success": True,
                "multi_pass": True,
                "reference_quality": reference_quality,
            }
        else:
            output_path = result
            filename = Path(output_path).name
            audio_url = f"/api/audio/{filename}"

            voice_type = "upload" if voice_file else "demo"
            voice_name = None
            if demo_voice:
                voice_name = demo_voice
            elif voice_file:
                voice_name = voice_file.filename

            tts_params_dict = {
                "speed": tts_speed,
                "temperature": tts_temperature,
                "length_penalty": tts_length_penalty,
                "repetition_penalty": tts_repetition_penalty,
                "top_k": tts_top_k,
                "top_p": tts_top_p
            }

            history_entry = HistoryManager.add_entry(
                audio_url=audio_url,
                filename=filename,
                text=text,
                voice_type=voice_type,
                voice_name=voice_name,
                tts_params=tts_params_dict
            )

            if job_id:
                ProgressManager.update(job_id, percent=99, stage="final", message="Ukládám do historie a odesílám…")
                ProgressManager.done(job_id)
            return {
                "audio_url": audio_url,
                "filename": filename,
                "success": True,
                "history_id": history_entry["id"],
                "job_id": job_id,
                "reference_quality": reference_quality,
            }

    except HTTPException:
        if job_id:
            ProgressManager.fail(job_id, "HTTPException")
        raise
    except Exception as e:
        msg = str(e)
        if job_id:
            ProgressManager.fail(job_id, msg)
        raise HTTPException(status_code=500, detail=f"Chyba při generování: {msg}")


@router.post("/generate-f5")
async def generate_speech_f5(
    text: str = Form(...),
    job_id: str = Form(None),
    voice_file: UploadFile = File(None),
    demo_voice: str = Form(None),
    ref_text: str = Form(None),
    speed: str = Form(None),
    temperature: float = Form(None),
    length_penalty: float = Form(None),
    repetition_penalty: float = Form(None),
    top_k: int = Form(None),
    top_p: float = Form(None),
    quality_mode: str = Form(None),
    enhancement_preset: str = Form(None),
    enable_enhancement: str = Form(None),
    seed: int = Form(None),
    enable_vad: str = Form(None),
    use_hifigan: str = Form(None),
    enable_normalization: str = Form(None),
    enable_denoiser: str = Form(None),
    enable_compressor: str = Form(None),
    enable_deesser: str = Form(None),
    enable_eq: str = Form(None),
    enable_trim: str = Form(None),
    enable_dialect_conversion: str = Form(None),
    dialect_code: str = Form(None),
    dialect_intensity: str = Form(None),
    hifigan_refinement_intensity: str = Form(None),
    hifigan_normalize_output: str = Form(None),
    hifigan_normalize_gain: str = Form(None),
    enable_whisper: str = Form(None),
    whisper_intensity: str = Form(None),
    target_headroom_db: str = Form(None),
    auto_enhance_voice: str = Form(None),
    allow_poor_voice: str = Form(None),
):
    """Generuje řeč z textu pomocí F5-TTS"""
    try:
        if job_id:
            ProgressManager.start(
                job_id,
                meta={
                    "text_length": len(text or ""),
                    "endpoint": "/api/tts/generate-f5",
                },
            )

        if not f5_tts_engine.is_loaded:
            if job_id:
                ProgressManager.update(job_id, percent=5, stage="load", message="Kontroluji F5-TTS CLI…")
            await f5_tts_engine.load_model()
        else:
            if job_id:
                ProgressManager.update(job_id, percent=10, stage="load", message="F5-TTS je připraven, začínám syntézu…")

        if speed is not None:
            try:
                tts_speed = float(speed) if isinstance(speed, str) else float(speed)
            except (ValueError, TypeError):
                tts_speed = TTS_SPEED
        else:
            tts_speed = TTS_SPEED

        enable_enh_flag = (enable_enhancement.lower() == "true") if isinstance(enable_enhancement, str) else ENABLE_AUDIO_ENHANCEMENT
        enhancement_preset_value = enhancement_preset if enhancement_preset else AUDIO_ENHANCEMENT_PRESET

        enable_vad_flag = (enable_vad.lower() == "true") if isinstance(enable_vad, str) else None
        use_hifigan_flag = (use_hifigan.lower() == "true") if isinstance(use_hifigan, str) else False
        enable_norm = (enable_normalization.lower() == "true") if isinstance(enable_normalization, str) else None
        enable_den = (enable_denoiser.lower() == "true") if isinstance(enable_denoiser, str) else None
        enable_comp = (enable_compressor.lower() == "true") if isinstance(enable_compressor, str) else None
        enable_deess = (enable_deesser.lower() == "true") if isinstance(enable_deesser, str) else None
        enable_eq_flag = (enable_eq.lower() == "true") if isinstance(enable_eq, str) else None
        enable_trim_flag = (enable_trim.lower() == "true") if isinstance(enable_trim, str) else None

        use_dialect = (enable_dialect_conversion.lower() == "true") if isinstance(enable_dialect_conversion, str) else False
        dialect_code_value = dialect_code if dialect_code and dialect_code != "standardni" else None
        try:
            dialect_intensity_value = float(dialect_intensity) if dialect_intensity else 1.0
        except (ValueError, TypeError):
            dialect_intensity_value = 1.0

        try:
            hifigan_refinement_intensity_value = float(hifigan_refinement_intensity) if hifigan_refinement_intensity else None
            if hifigan_refinement_intensity_value is not None and not (0.0 <= hifigan_refinement_intensity_value <= 1.0):
                raise HTTPException(status_code=400, detail="hifigan_refinement_intensity musí být mezi 0.0 a 1.0")
        except (ValueError, TypeError):
            hifigan_refinement_intensity_value = None

        hifigan_normalize_output_value = (hifigan_normalize_output.lower() == "true") if isinstance(hifigan_normalize_output, str) else None

        try:
            hifigan_normalize_gain_value = float(hifigan_normalize_gain) if hifigan_normalize_gain else None
            if hifigan_normalize_gain_value is not None and not (0.0 <= hifigan_normalize_gain_value <= 1.0):
                raise HTTPException(status_code=400, detail="hifigan_normalize_gain musí být mezi 0.0 a 1.0")
        except (ValueError, TypeError):
            hifigan_normalize_gain_value = None

        enable_whisper_value = (enable_whisper.lower() == "true") if isinstance(enable_whisper, str) else None
        try:
            whisper_intensity_value = float(whisper_intensity) if whisper_intensity else None
            if whisper_intensity_value is not None and not (0.0 <= whisper_intensity_value <= 1.0):
                raise HTTPException(status_code=400, detail="whisper_intensity musí být mezi 0.0 a 1.0")
        except (ValueError, TypeError):
            whisper_intensity_value = None

        try:
            target_headroom_db_value = float(target_headroom_db) if target_headroom_db else None
            if target_headroom_db_value is not None and not (-128.0 <= target_headroom_db_value <= 0.0):
                raise HTTPException(status_code=400, detail="target_headroom_db musí být mezi -128.0 a 0.0 dB")
        except (ValueError, TypeError):
            target_headroom_db_value = None

        speaker_wav = None
        reference_quality = None

        if voice_file:
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
            demo_path = get_demo_voice_path(demo_voice, lang="cs")
            if not demo_path:
                available_voices = list(DEMO_VOICES_CS_DIR.glob("*.wav"))
                if available_voices:
                    speaker_wav = str(available_voices[0])
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Demo hlas '{demo_voice}' neexistuje a žádné demo hlasy nejsou k dispozici."
                    )
            else:
                speaker_wav = demo_path
        else:
            raise HTTPException(
                status_code=400,
                detail="Musí být zadán buď voice_file nebo demo_voice"
            )

        try:
            from backend.config import (
                ENABLE_REFERENCE_QUALITY_GATE,
                ENABLE_REFERENCE_AUTO_ENHANCE,
                REFERENCE_ALLOW_POOR_BY_DEFAULT,
            )
            reference_quality = AudioProcessor.analyze_audio_quality(speaker_wav) if speaker_wav else None

            if ENABLE_REFERENCE_QUALITY_GATE and reference_quality and reference_quality.get("score") == "poor":
                request_auto = (auto_enhance_voice.lower() == "true") if isinstance(auto_enhance_voice, str) else None
                request_allow = (allow_poor_voice.lower() == "true") if isinstance(allow_poor_voice, str) else None

                do_auto = request_auto if request_auto is not None else ENABLE_REFERENCE_AUTO_ENHANCE

                is_demo_voice = False
                try:
                    speaker_resolved = Path(speaker_wav).resolve()
                    is_demo_voice = (
                        speaker_resolved.is_relative_to(DEMO_VOICES_CS_DIR.resolve())
                        or speaker_resolved.is_relative_to(DEMO_VOICES_SK_DIR.resolve())
                    )
                except Exception:
                    try:
                        speaker_resolved_str = str(Path(speaker_wav).resolve())
                        is_demo_voice = (
                            speaker_resolved_str.startswith(str(DEMO_VOICES_CS_DIR.resolve()))
                            or speaker_resolved_str.startswith(str(DEMO_VOICES_SK_DIR.resolve()))
                        )
                    except Exception:
                        is_demo_voice = False

                if request_allow is None and is_demo_voice:
                    do_allow = True
                else:
                    do_allow = request_allow if request_allow is not None else REFERENCE_ALLOW_POOR_BY_DEFAULT

                if do_auto:
                    enhanced_path = UPLOADS_DIR / f"enhanced_{uuid.uuid4().hex[:10]}.wav"
                    ok, enh_err = AudioProcessor.enhance_voice_sample(speaker_wav, str(enhanced_path))
                    if ok:
                        speaker_wav = str(enhanced_path)
                        reference_quality = AudioProcessor.analyze_audio_quality(speaker_wav)

                if reference_quality and reference_quality.get("score") == "poor" and not do_allow:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "message": "Referenční audio má nízkou kvalitu pro klonování. Nahrajte čistší vzorek nebo použijte allow_poor_voice=true.",
                            "quality": reference_quality,
                        },
                    )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Quality gate selhal (ignorováno): {e}")

        if not (0.5 <= tts_speed <= 2.0):
            raise HTTPException(status_code=400, detail="Speed musí být mezi 0.5 a 2.0")

        if job_id:
            ProgressManager.update(job_id, percent=1, stage="f5_tts", message="Generuji řeč (F5-TTS)…")

        logger.info(f"UI headroom (F5): target_headroom_db={target_headroom_db_value} dB, enable_enhancement={enable_enh_flag}, enable_normalization={enable_norm}")
        output_path = await f5_tts_engine.generate(
            text=text,
            speaker_wav=speaker_wav,
            language="cs",
            speed=tts_speed,
            temperature=0.7,
            length_penalty=1.0,
            repetition_penalty=2.0,
            top_k=50,
            top_p=0.85,
            quality_mode=quality_mode,
            seed=seed,
            enhancement_preset=enhancement_preset_value,
            enable_vad=enable_vad_flag,
            use_hifigan=use_hifigan_flag,
            enable_normalization=enable_norm,
            enable_denoiser=enable_den,
            enable_compressor=enable_comp,
            enable_deesser=enable_deess,
            enable_eq=enable_eq_flag,
            enable_trim=enable_trim_flag,
            enable_dialect_conversion=use_dialect,
            dialect_code=dialect_code_value,
            dialect_intensity=dialect_intensity_value,
            enable_whisper=enable_whisper_value,
            whisper_intensity=whisper_intensity_value,
            target_headroom_db=target_headroom_db_value,
            hifigan_refinement_intensity=hifigan_refinement_intensity_value,
            hifigan_normalize_output=hifigan_normalize_output_value,
            hifigan_normalize_gain=hifigan_normalize_gain_value,
            enable_enhancement=enable_enh_flag,
            job_id=job_id,
            ref_text=ref_text
        )

        filename = Path(output_path).name
        audio_url = f"/api/audio/{filename}"

        voice_type = "upload" if voice_file else "demo"
        voice_name = None
        if demo_voice:
            voice_name = demo_voice
        elif voice_file:
            voice_name = voice_file.filename

        tts_params_dict = {
            "speed": tts_speed,
            "engine": "f5-tts"
        }

        history_entry = HistoryManager.add_entry(
            audio_url=audio_url,
            filename=filename,
            text=text,
            voice_type=voice_type,
            voice_name=voice_name,
            tts_params=tts_params_dict
        )

        if job_id:
            ProgressManager.update(job_id, percent=99, stage="final", message="Ukládám do historie a odesílám…")
            ProgressManager.done(job_id)

        return {
            "audio_url": audio_url,
            "filename": filename,
            "success": True,
            "history_id": history_entry["id"],
            "job_id": job_id,
            "reference_quality": reference_quality,
        }

    except HTTPException:
        if job_id:
            ProgressManager.fail(job_id, "HTTPException")
        raise
    except Exception as e:
        msg = str(e)
        if job_id:
            ProgressManager.fail(job_id, msg)
        raise HTTPException(status_code=500, detail=f"Chyba při generování F5-TTS: {msg}")


@router.post("/generate-f5-sk")
async def generate_speech_f5_sk(
    text: str = Form(...),
    job_id: str = Form(None),
    voice_file: UploadFile = File(None),
    demo_voice: str = Form(None),
    ref_text: str = Form(None),
    speed: str = Form(None),
    temperature: float = Form(None),
    length_penalty: float = Form(None),
    repetition_penalty: float = Form(None),
    top_k: int = Form(None),
    top_p: float = Form(None),
    quality_mode: str = Form(None),
    enhancement_preset: str = Form(None),
    enable_enhancement: str = Form(None),
    seed: int = Form(None),
    enable_vad: str = Form(None),
    use_hifigan: str = Form(None),
    enable_normalization: str = Form(None),
    enable_denoiser: str = Form(None),
    enable_compressor: str = Form(None),
    enable_deesser: str = Form(None),
    enable_eq: str = Form(None),
    enable_trim: str = Form(None),
    enable_dialect_conversion: str = Form(None),
    dialect_code: str = Form(None),
    dialect_intensity: str = Form(None),
    hifigan_refinement_intensity: str = Form(None),
    hifigan_normalize_output: str = Form(None),
    hifigan_normalize_gain: str = Form(None),
    enable_whisper: str = Form(None),
    whisper_intensity: str = Form(None),
    target_headroom_db: str = Form(None),
    auto_enhance_voice: str = Form(None),
    allow_poor_voice: str = Form(None),
):
    """Generuje řeč z textu pomocí F5-TTS slovenského modelu"""
    try:
        if job_id:
            ProgressManager.start(
                job_id,
                meta={
                    "text_length": len(text or ""),
                    "endpoint": "/api/tts/generate-f5-sk",
                },
            )

        if not f5_tts_slovak_engine.is_loaded:
            if job_id:
                ProgressManager.update(job_id, percent=5, stage="load", message="Kontroluji F5-TTS Slovak CLI…")
            await f5_tts_slovak_engine.load_model()
        else:
            if job_id:
                ProgressManager.update(job_id, percent=10, stage="load", message="F5-TTS Slovak je připraven, začínám syntézu…")

        if speed is not None:
            try:
                tts_speed = float(speed) if isinstance(speed, str) else float(speed)
            except (ValueError, TypeError):
                tts_speed = TTS_SPEED
        else:
            tts_speed = TTS_SPEED

        enable_enh_flag = (enable_enhancement.lower() == "true") if isinstance(enable_enhancement, str) else ENABLE_AUDIO_ENHANCEMENT
        enhancement_preset_value = enhancement_preset if enhancement_preset else AUDIO_ENHANCEMENT_PRESET

        enable_vad_flag = (enable_vad.lower() == "true") if isinstance(enable_vad, str) else None
        use_hifigan_flag = (use_hifigan.lower() == "true") if isinstance(use_hifigan, str) else False
        enable_norm = (enable_normalization.lower() == "true") if isinstance(enable_normalization, str) else None
        enable_den = (enable_denoiser.lower() == "true") if isinstance(enable_denoiser, str) else None
        enable_comp = (enable_compressor.lower() == "true") if isinstance(enable_compressor, str) else None
        enable_deess = (enable_deesser.lower() == "true") if isinstance(enable_deesser, str) else None
        enable_eq_flag = (enable_eq.lower() == "true") if isinstance(enable_eq, str) else None
        enable_trim_flag = (enable_trim.lower() == "true") if isinstance(enable_trim, str) else None

        use_dialect = False
        dialect_code_value = None
        dialect_intensity_value = 1.0

        try:
            hifigan_refinement_intensity_value = float(hifigan_refinement_intensity) if hifigan_refinement_intensity else None
            if hifigan_refinement_intensity_value is not None and not (0.0 <= hifigan_refinement_intensity_value <= 1.0):
                raise HTTPException(status_code=400, detail="hifigan_refinement_intensity musí být mezi 0.0 a 1.0")
        except (ValueError, TypeError):
            hifigan_refinement_intensity_value = None

        hifigan_normalize_output_value = (hifigan_normalize_output.lower() == "true") if isinstance(hifigan_normalize_output, str) else None

        try:
            hifigan_normalize_gain_value = float(hifigan_normalize_gain) if hifigan_normalize_gain else None
            if hifigan_normalize_gain_value is not None and not (0.0 <= hifigan_normalize_gain_value <= 1.0):
                raise HTTPException(status_code=400, detail="hifigan_normalize_gain musí být mezi 0.0 a 1.0")
        except (ValueError, TypeError):
            hifigan_normalize_gain_value = None

        enable_whisper_value = (enable_whisper.lower() == "true") if isinstance(enable_whisper, str) else None
        try:
            whisper_intensity_value = float(whisper_intensity) if whisper_intensity else None
            if whisper_intensity_value is not None and not (0.0 <= whisper_intensity_value <= 1.0):
                raise HTTPException(status_code=400, detail="whisper_intensity musí být mezi 0.0 a 1.0")
        except (ValueError, TypeError):
            whisper_intensity_value = None

        try:
            target_headroom_db_value = float(target_headroom_db) if target_headroom_db else None
            if target_headroom_db_value is not None and not (-128.0 <= target_headroom_db_value <= 0.0):
                raise HTTPException(status_code=400, detail="target_headroom_db musí být mezi -128.0 a 0.0 dB")
        except (ValueError, TypeError):
            target_headroom_db_value = None

        speaker_wav = None
        reference_quality = None

        if voice_file:
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
            demo_path = get_demo_voice_path(demo_voice, lang="sk")
            if not demo_path:
                available_voices = list(DEMO_VOICES_SK_DIR.glob("*.wav"))
                if available_voices:
                    speaker_wav = str(available_voices[0])
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Demo hlas '{demo_voice}' neexistuje a žádné demo hlasy nejsou k dispozici."
                    )
            else:
                speaker_wav = demo_path
        else:
            raise HTTPException(
                status_code=400,
                detail="Musí být zadán buď voice_file nebo demo_voice"
            )

        try:
            from backend.config import (
                ENABLE_REFERENCE_QUALITY_GATE,
                ENABLE_REFERENCE_AUTO_ENHANCE,
                REFERENCE_ALLOW_POOR_BY_DEFAULT,
            )
            auto_enhance_flag = (auto_enhance_voice.lower() == "true") if isinstance(auto_enhance_voice, str) else ENABLE_REFERENCE_AUTO_ENHANCE
            allow_poor_flag = (allow_poor_voice.lower() == "true") if isinstance(allow_poor_voice, str) else REFERENCE_ALLOW_POOR_BY_DEFAULT

            if ENABLE_REFERENCE_QUALITY_GATE:
                reference_quality = AudioProcessor.analyze_audio_quality(speaker_wav)
                if reference_quality["score"] == "poor" and not allow_poor_flag:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Kvalita referenčního audia je příliš nízká (SNR: {reference_quality['snr']:.1f} dB). "
                               f"Použijte allow_poor_voice=true pro povolení."
                    )
                if auto_enhance_flag and reference_quality["score"] != "good":
                    enhanced_path = UPLOADS_DIR / f"enhanced_{uuid.uuid4().hex[:10]}.wav"
                    ok, enh_err = AudioProcessor.enhance_voice_sample(speaker_wav, str(enhanced_path))
                    if ok:
                        speaker_wav = str(enhanced_path)
                        reference_quality = AudioProcessor.analyze_audio_quality(speaker_wav)
                        logger.info("Referenční audio bylo automaticky vylepšeno")
                    else:
                        logger.warning(f"Auto-enhance referenčního hlasu selhal: {enh_err}")
        except Exception as e:
            logger.warning(f"Quality gate selhal: {e}")

        if not (0.5 <= tts_speed <= 2.0):
            raise HTTPException(status_code=400, detail="Speed musí být mezi 0.5 a 2.0")

        if job_id:
            ProgressManager.update(job_id, percent=1, stage="f5_tts_slovak", message="Generujem reč (F5-TTS Slovak)…")

        logger.info(f"UI headroom (F5-SK): target_headroom_db={target_headroom_db_value} dB, enable_enhancement={enable_enh_flag}, enable_normalization={enable_norm}")
        output_path = await f5_tts_slovak_engine.generate(
            text=text,
            speaker_wav=speaker_wav,
            language="sk",
            speed=tts_speed,
            temperature=0.7,
            length_penalty=1.0,
            repetition_penalty=2.0,
            top_k=50,
            top_p=0.85,
            quality_mode=quality_mode,
            seed=seed,
            enhancement_preset=enhancement_preset_value,
            enable_vad=enable_vad_flag,
            use_hifigan=use_hifigan_flag,
            enable_normalization=enable_norm,
            enable_denoiser=enable_den,
            enable_compressor=enable_comp,
            enable_deesser=enable_deess,
            enable_eq=enable_eq_flag,
            enable_trim=enable_trim_flag,
            enable_dialect_conversion=use_dialect,
            dialect_code=dialect_code_value,
            dialect_intensity=dialect_intensity_value,
            enable_whisper=enable_whisper_value,
            whisper_intensity=whisper_intensity_value,
            target_headroom_db=target_headroom_db_value,
            hifigan_refinement_intensity=hifigan_refinement_intensity_value,
            hifigan_normalize_output=hifigan_normalize_output_value,
            hifigan_normalize_gain=hifigan_normalize_gain_value,
            enable_enhancement=enable_enh_flag,
            job_id=job_id,
            ref_text=ref_text
        )

        filename = Path(output_path).name
        audio_url = f"/api/audio/{filename}"

        voice_type = "upload" if voice_file else "demo"
        voice_name = None
        if demo_voice:
            voice_name = demo_voice
        elif voice_file:
            voice_name = voice_file.filename

        tts_params_dict = {
            "speed": tts_speed,
            "engine": "f5-tts-slovak"
        }

        history_entry = HistoryManager.add_entry(
            audio_url=audio_url,
            filename=filename,
            text=text,
            voice_type=voice_type,
            voice_name=voice_name,
            tts_params=tts_params_dict
        )

        if job_id:
            ProgressManager.update(job_id, percent=100, stage="done", message="Hotovo!")
            ProgressManager.done(job_id)

        return {
            "success": True,
            "audio_url": audio_url,
            "filename": filename,
            "voice_type": voice_type,
            "voice_name": voice_name,
            "engine": "f5-tts-slovak",
            "reference_quality": reference_quality
        }

    except HTTPException:
        if job_id:
            ProgressManager.fail(job_id, "HTTPException")
        raise
    except Exception as e:
        msg = str(e)
        if job_id:
            ProgressManager.fail(job_id, msg)
        raise HTTPException(status_code=500, detail=f"Chyba při generování F5-TTS Slovak: {msg}")


@router.post("/generate-multi")
async def generate_speech_multi(
    text: str = Form(...),
    job_id: str = Form(None),
    default_voice_file: UploadFile = File(None),
    default_demo_voice: str = Form(None),
    default_language: str = Form("cs"),
    speaker_mapping: str = Form(None),
    speed: str = Form(None),
    temperature: float = Form(None),
    length_penalty: float = Form(None),
    repetition_penalty: float = Form(None),
    top_k: int = Form(None),
    top_p: float = Form(None),
    quality_mode: str = Form(None),
    enhancement_preset: str = Form(None),
    enable_enhancement: str = Form(None),
    seed: int = Form(None),
    enable_vad: str = Form(None),
    enable_normalization: str = Form(None),
    enable_denoiser: str = Form(None),
    enable_compressor: str = Form(None),
    enable_deesser: str = Form(None),
    enable_eq: str = Form(None),
    enable_trim: str = Form(None),
    target_headroom_db: str = Form(None),
):
    """Generuje řeč pro text s více jazyky a mluvčími"""
    try:
        if job_id:
            ProgressManager.start(
                job_id,
                meta={
                    "text_length": len(text or ""),
                    "endpoint": "/api/tts/generate-multi",
                },
            )

        if not tts_engine.is_loaded:
            if job_id:
                ProgressManager.update(job_id, percent=5, stage="load", message="Načítám XTTS model do VRAM…")
            await tts_engine.load_model()
        else:
            if job_id:
                ProgressManager.update(job_id, percent=10, stage="load", message="Model je připraven, začínám syntézu…")

        if not text or len(text.strip()) == 0:
            raise HTTPException(status_code=400, detail="Text je prázdný")

        default_speaker_wav = None

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
            default_speaker_wav = processed_path

        elif default_demo_voice:
            demo_path = get_demo_voice_path(default_demo_voice, lang=default_language)
            if demo_path:
                default_speaker_wav = demo_path
            else:
                available_voices = list(_get_demo_voices_dir(default_language).glob("*.wav"))
                if available_voices:
                    default_speaker_wav = str(available_voices[0])
                    logger.warning(f"Demo voice '{default_demo_voice}' not found, using: {default_speaker_wav}")
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Demo hlas '{default_demo_voice}' neexistuje a žádné demo hlasy nejsou k dispozici."
                    )
        else:
            available_voices = list(_get_demo_voices_dir(default_language).glob("*.wav"))
            if available_voices:
                default_speaker_wav = str(available_voices[0])
                logger.info(f"Žádný výchozí hlas zadán, používám: {default_speaker_wav}")
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Musí být zadán buď default_voice_file nebo default_demo_voice, nebo musí existovat demo hlasy"
                )

        speaker_map = {}
        multi_lang_pattern = re.compile(r'\[(\w+)(?::([^\]]+))?\]')
        speaker_ids_from_text = set()
        for match in multi_lang_pattern.finditer(text):
            speaker_id = match.group(2)
            if speaker_id:
                speaker_ids_from_text.add(speaker_id)

        for sid in speaker_ids_from_text:
            demo_path = get_demo_voice_path(sid, lang=default_language)
            if demo_path:
                speaker_map[sid] = demo_path
                logger.info(f"Auto-mapování: Speaker '{sid}' -> demo hlas: {demo_path}")
            elif Path(sid).exists():
                speaker_map[sid] = sid
                logger.info(f"Auto-mapování: Speaker '{sid}' -> soubor: {sid}")

        if speaker_mapping:
            try:
                mapping_data = json.loads(speaker_mapping)
                for speaker_id, voice_ref in mapping_data.items():
                    if Path(voice_ref).exists():
                        speaker_map[speaker_id] = voice_ref
                    else:
                        demo_path = get_demo_voice_path(voice_ref, lang=default_language)
                        if demo_path:
                            speaker_map[speaker_id] = demo_path
                        else:
                            logger.warning(f"Speaker '{speaker_id}': voice '{voice_ref}' neexistuje, použije se výchozí hlas")
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=400, detail=f"Neplatný speaker_mapping JSON: {str(e)}")

        if speed is not None:
            try:
                tts_speed = float(speed) if isinstance(speed, str) else float(speed)
            except (ValueError, TypeError):
                tts_speed = TTS_SPEED
        else:
            tts_speed = TTS_SPEED

        tts_temperature = temperature if temperature is not None else TTS_TEMPERATURE
        tts_length_penalty = length_penalty if length_penalty is not None else TTS_LENGTH_PENALTY
        tts_repetition_penalty = repetition_penalty if repetition_penalty is not None else TTS_REPETITION_PENALTY
        tts_top_k = top_k if top_k is not None else TTS_TOP_K
        tts_top_p = top_p if top_p is not None else TTS_TOP_P

        enable_enh = (enable_enhancement.lower() == "true") if isinstance(enable_enhancement, str) else ENABLE_AUDIO_ENHANCEMENT
        enable_vad_flag = (enable_vad.lower() == "true") if isinstance(enable_vad, str) else None
        enable_norm = (enable_normalization.lower() == "true") if isinstance(enable_normalization, str) else None
        enable_den = (enable_denoiser.lower() == "true") if isinstance(enable_denoiser, str) else None
        enable_comp = (enable_compressor.lower() == "true") if isinstance(enable_compressor, str) else None
        enable_deess = (enable_deesser.lower() == "true") if isinstance(enable_deesser, str) else None
        enable_eq_flag = (enable_eq.lower() == "true") if isinstance(enable_eq, str) else None
        enable_trim_flag = (enable_trim.lower() == "true") if isinstance(enable_trim, str) else None

        try:
            target_headroom_db_value = float(target_headroom_db) if target_headroom_db else None
            if target_headroom_db_value is not None and not (-128.0 <= target_headroom_db_value <= 0.0):
                raise HTTPException(status_code=400, detail="target_headroom_db musí být mezi -128.0 a 0.0 dB")
        except (ValueError, TypeError):
            target_headroom_db_value = None

        output_path = await tts_engine.generate_multi_lang_speaker(
            text=text,
            default_speaker_wav=default_speaker_wav,
            default_language=default_language if default_language else "cs",
            speaker_map=speaker_map if speaker_map else None,
            speed=tts_speed,
            temperature=tts_temperature,
            length_penalty=tts_length_penalty,
            repetition_penalty=tts_repetition_penalty,
            top_k=tts_top_k,
            top_p=tts_top_p,
            quality_mode=quality_mode,
            enhancement_preset=enhancement_preset,
            seed=seed,
            enable_vad=enable_vad_flag,
            enable_enhancement=enable_enh,
            enable_normalization=enable_norm,
            enable_denoiser=enable_den,
            enable_compressor=enable_comp,
            enable_deesser=enable_deess,
            enable_eq=enable_eq_flag,
            enable_trim=enable_trim_flag,
            target_headroom_db=target_headroom_db_value,
            job_id=job_id
        )

        filename = Path(output_path).name
        audio_url = f"/api/audio/{filename}"

        if job_id:
            ProgressManager.done(job_id)

        return {
            "audio_url": audio_url,
            "filename": filename,
            "success": True,
            "job_id": job_id,
        }

    except HTTPException:
        if job_id:
            ProgressManager.fail(job_id, "HTTPException")
        raise
    except Exception as e:
        msg = str(e)
        if job_id:
            ProgressManager.fail(job_id, msg)
        raise HTTPException(status_code=500, detail=f"Chyba při generování: {msg}")

