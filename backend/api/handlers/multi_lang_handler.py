"""
Handler pro multi-lang/speaker generování
"""
import re
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Set
from fastapi import HTTPException

from backend.api.helpers import get_demo_voice_path

logger = logging.getLogger(__name__)

# Pattern pro detekci multi-lang anotací: [lang:speaker_id] nebo [lang]
MULTI_LANG_PATTERN = re.compile(r'\[(\w+)(?::([^\]]+))?\]')


def has_multi_lang_annotations(text: str) -> bool:
    """Zkontroluje, zda text obsahuje multi-lang/speaker anotace"""
    return bool(MULTI_LANG_PATTERN.search(text))


def extract_speaker_ids(text: str) -> Set[str]:
    """Extrahuje speaker IDs z textu"""
    speaker_ids = set()
    for match in MULTI_LANG_PATTERN.finditer(text):
        speaker_id = match.group(2)
        if speaker_id:
            speaker_ids.add(speaker_id)
    return speaker_ids


def build_speaker_map(
    speaker_ids: Set[str],
    default_speaker_wav: str,
    default_language: str = "cs",
    speaker_mapping_json: Optional[str] = None,
) -> Dict[str, str]:
    """
    Vytvoří speaker map z speaker IDs a volitelného JSON mappingu

    Args:
        speaker_ids: Set speaker IDs z textu
        default_speaker_wav: Cesta k default speaker WAV
        default_language: Výchozí jazyk
        speaker_mapping_json: Volitelný JSON string s explicitním mappingem

    Returns:
        Dictionary mapping speaker_id -> wav_path
    """
    speaker_map = {}

    # Auto-mapování z textu
    for sid in speaker_ids:
        demo_path = get_demo_voice_path(sid, lang=default_language)
        if demo_path:
            speaker_map[sid] = demo_path
            logger.info(f"Auto-mapování: Speaker '{sid}' -> demo hlas: {demo_path}")
        elif Path(sid).exists():
            speaker_map[sid] = sid
            logger.info(f"Auto-mapování: Speaker '{sid}' -> soubor: {sid}")
        else:
            speaker_map[sid] = default_speaker_wav

    # Explicitní mapping z JSON (má přednost)
    if speaker_mapping_json:
        try:
            mapping_data = json.loads(speaker_mapping_json)
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

    return speaker_map

