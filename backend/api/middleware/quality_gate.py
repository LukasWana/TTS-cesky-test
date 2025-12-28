"""
Quality gate middleware pro kontrolu kvality referenčního audia
"""
import uuid
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from fastapi import HTTPException

from backend.audio_processor import AudioProcessor
from backend.config import (
    UPLOADS_DIR,
    DEMO_VOICES_CS_DIR,
    DEMO_VOICES_SK_DIR,
    ENABLE_REFERENCE_QUALITY_GATE,
    ENABLE_REFERENCE_AUTO_ENHANCE,
    REFERENCE_ALLOW_POOR_BY_DEFAULT,
)

logger = logging.getLogger(__name__)


def is_demo_voice(speaker_wav: str) -> bool:
    """Zkontroluje, zda je speaker_wav demo voice"""
    try:
        speaker_resolved = Path(speaker_wav).resolve()
        is_demo = (
            speaker_resolved.is_relative_to(DEMO_VOICES_CS_DIR.resolve())
            or speaker_resolved.is_relative_to(DEMO_VOICES_SK_DIR.resolve())
        )
        return is_demo
    except Exception:
        try:
            speaker_resolved_str = str(Path(speaker_wav).resolve())
            is_demo = (
                speaker_resolved_str.startswith(str(DEMO_VOICES_CS_DIR.resolve()))
                or speaker_resolved_str.startswith(str(DEMO_VOICES_SK_DIR.resolve()))
            )
            return is_demo
        except Exception:
            return False


async def check_reference_quality(
    speaker_wav: str,
    auto_enhance_voice: Optional[str] = None,
    allow_poor_voice: Optional[str] = None,
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Zkontroluje kvalitu referenčního audia a případně provede auto-enhance

    Returns:
        Tuple[final_speaker_wav_path, reference_quality_dict]
    """
    if not ENABLE_REFERENCE_QUALITY_GATE:
        return speaker_wav, None

    try:
        reference_quality = AudioProcessor.analyze_audio_quality(speaker_wav) if speaker_wav else None

        if not reference_quality or reference_quality.get("score") != "poor":
            return speaker_wav, reference_quality

        # Kvalita je poor - zpracujeme request parametry
        request_auto = (auto_enhance_voice.lower() == "true") if isinstance(auto_enhance_voice, str) else None
        request_allow = (allow_poor_voice.lower() == "true") if isinstance(allow_poor_voice, str) else None

        do_auto = request_auto if request_auto is not None else ENABLE_REFERENCE_AUTO_ENHANCE

        # Demo hlasy mají automaticky povolené poor quality
        is_demo = is_demo_voice(speaker_wav)
        if request_allow is None and is_demo:
            do_allow = True
        else:
            do_allow = request_allow if request_allow is not None else REFERENCE_ALLOW_POOR_BY_DEFAULT

        # Auto-enhance
        if do_auto:
            enhanced_path = UPLOADS_DIR / f"enhanced_{uuid.uuid4().hex[:10]}.wav"
            ok, enh_err = AudioProcessor.enhance_voice_sample(speaker_wav, str(enhanced_path))
            if ok:
                speaker_wav = str(enhanced_path)
                reference_quality = AudioProcessor.analyze_audio_quality(speaker_wav)
            else:
                logger.warning(f"Auto-enhance referenčního hlasu selhal: {enh_err}")

        # Kontrola po enhance (pokud se kvalita nezlepšila)
        if reference_quality and reference_quality.get("score") == "poor" and not do_allow:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Referenční audio má nízkou kvalitu pro klonování (šum/clipping/krátká délka). Nahrajte čistší vzorek (10–30s řeči bez hudby) nebo použijte allow_poor_voice=true.",
                    "quality": reference_quality,
                },
            )

        return speaker_wav, reference_quality

    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Quality gate selhal (ignorováno): {e}")
        return speaker_wav, None

