"""
Sdílený modul pro slovenský text preprocessing pipeline
Používá se pro F5-TTS slovenský engine
"""
from typing import Optional
from backend.config import (
    ENABLE_PHONETIC_TRANSLATION,
    ENABLE_SLOVAK_TEXT_PROCESSING
)
from backend.phonetic_translator import get_phonetic_translator


def preprocess_slovak_text(
    text: str,
    language: str,
    enable_dialect_conversion: Optional[bool] = None,
    dialect_code: Optional[str] = None,
    dialect_intensity: float = 1.0
) -> str:
    """
    Předzpracuje text pre slovenčinu - prevedie čísla na slová, normalizuje interpunkciu,
    prevedie skratky a opraví formátovanie.

    Táto funkcia je určená pre F5-TTS slovenský engine.

    Args:
        text: Text k predspracovaniu
        language: Jazyk textu (iba "sk" aktivuje slovenské spracovanie)
        enable_dialect_conversion: Či povoliť prevod na nárečie (None = nepoužiť, slovenština nemá nárečia v systéme)
        dialect_code: Kód nárečia (None = nepoužiť)
        dialect_intensity: Intenzita prevodu (0.0-1.0)

    Returns:
        Predspracovaný text
    """
    if language != "sk":
        return text

    # 0. Fonetický prepis cudzích slov (pred ostatným predspracovaním)
    if ENABLE_PHONETIC_TRANSLATION:
        try:
            translator = get_phonetic_translator()
            text = translator.translate_foreign_words(text, target_language="sk")
        except Exception as e:
            print(f"[WARN] Phonetic translation selhal: {e}")

    # 0.5. Pokročilé slovenské text processing pomocí SlovakTextProcessor
    if ENABLE_SLOVAK_TEXT_PROCESSING:
        try:
            from backend.slovak_text_processor import get_slovak_text_processor
            slovak_processor = get_slovak_text_processor()
            text = slovak_processor.process_text(
                text,
                apply_voicing=True,  # Aktivované pre lepšiu výslovnosť
                apply_glottal_stop=True,  # Aktivované pre lepšiu zrozumiteľnosť
                apply_consonant_groups=False,  # Pre slovenštinu zatiaľ neimplementované
                expand_abbreviations=True,
                expand_numbers=True
            )
        except Exception as e:
            print(f"[WARN] Varovanie: Slovak text processing selhal: {e}")

    # Poznámka: Dialect conversion není pro slovenštinu implementována
    # (slovenština má jiné nářečí než čeština a systém je zaměřen na česká nářečí)

    return text

