"""
Helper funkce pro API routery
"""
import os
import re
from pathlib import Path
from typing import Optional
from backend.config import DEMO_VOICES_CS_DIR, DEMO_VOICES_SK_DIR


def _normalize_demo_lang(lang: Optional[str]) -> str:
    """Normalizuje jazyk pro výběr adresáře demo hlasů."""
    l = (lang or "cs").strip().lower()
    return "sk" if l.startswith("sk") else "cs"


def _get_demo_voices_dir(lang: Optional[str]) -> Path:
    """Vrátí adresář pro demo hlasy podle jazyka."""
    return DEMO_VOICES_SK_DIR if _normalize_demo_lang(lang) == "sk" else DEMO_VOICES_CS_DIR


def get_demo_voice_path(demo_voice_name: str, lang: Optional[str] = None) -> Optional[str]:
    """
    Vrátí cestu k demo hlasu nebo None pokud neexistuje

    Podporuje názvy s podtržítky, pomlčkami, velkými písmeny a mezerami.
    Vyhledávání je case-insensitive a ignoruje mezery na začátku/konci.

    Args:
        demo_voice_name: Název demo hlasu (např. "buchty01", "Pohadka_muz", "Klepl-Bolzakov-rusky")
        lang: Volitelně jazyk ("cs" / "sk"). Pokud není zadán, použije se default "cs".

    Returns:
        Cesta k WAV souboru nebo None
    """
    if not demo_voice_name:
        return None

    # Odstraň mezery na začátku/konci
    demo_voice_name = demo_voice_name.strip()

    # Podpora prefixu "cs:" / "sk:" nebo "cs/" / "sk/" (kvůli jednoznačnému mapování / preview_url)
    m = re.match(r"^(cs|sk)\s*[:/]\s*(.+)$", demo_voice_name, flags=re.IGNORECASE)
    if m:
        lang = m.group(1).lower()
        demo_voice_name = m.group(2).strip()

    # Pokud je to cesta, extrahuj pouze název souboru bez přípony
    if os.path.sep in demo_voice_name or '/' in demo_voice_name:
        demo_voice_name = Path(demo_voice_name).stem

    demo_dir = _get_demo_voices_dir(lang)

    # Nejdříve zkus přesný název (case-sensitive)
    demo_path = demo_dir / f"{demo_voice_name}.wav"
    if demo_path.exists():
        return str(demo_path)

    # Pak zkus case-insensitive vyhledávání
    # Projdeme všechny WAV soubory a porovnáme názvy (bez přípony)
    for wav_file in demo_dir.glob("*.wav"):
        file_stem = wav_file.stem.strip()  # Název bez přípony, bez mezer
        # Porovnej case-insensitive
        if file_stem.lower() == demo_voice_name.lower():
            return str(wav_file)

    # Pokud nic nenašlo, vrať None
    return None

