"""
Sdílený modul pro český text preprocessing pipeline
Používá se pro F5-TTS český engine a XTTS engine
"""
from typing import Optional
from backend.config import (
    ENABLE_PHONETIC_TRANSLATION,
    ENABLE_CZECH_TEXT_PROCESSING,
    ENABLE_DIALECT_CONVERSION,
    DIALECT_CODE,
    DIALECT_INTENSITY
)
from backend.phonetic_translator import get_phonetic_translator


def preprocess_czech_text(
    text: str,
    language: str,
    enable_dialect_conversion: Optional[bool] = None,
    dialect_code: Optional[str] = None,
    dialect_intensity: float = 1.0,
    apply_voicing: Optional[bool] = None,
    apply_glottal_stop: Optional[bool] = None
) -> str:
    """
    Předzpracuje text pro češtinu - převede čísla na slova, normalizuje interpunkci,
    převede zkratky a opraví formátování.

    Tato funkce je určena pro F5-TTS český engine a XTTS engine.

    Args:
        text: Text k předzpracování
        language: Jazyk textu (pouze "cs" aktivuje české zpracování)
        enable_dialect_conversion: Zda povolit převod na nářečí (None = použít z config, True/False = přepsat)
        dialect_code: Kód nářečí (None = použít z config, jinak přepsat)
        dialect_intensity: Intenzita převodu (0.0-1.0)
        apply_voicing: Zda aplikovat spodobu znělosti (None = výchozí True)
        apply_glottal_stop: Zda vkládat ráz (None = výchozí True)

    Returns:
        Předzpracovaný text
    """
    if language != "cs":
        return text

    # 0. Fonetický přepis cizích slov (před ostatním předzpracováním)
    if ENABLE_PHONETIC_TRANSLATION:
        try:
            translator = get_phonetic_translator()
            text = translator.translate_foreign_words(text, target_language="cs")
        except Exception as e:
            print(f"[WARN] Phonetic translation selhal: {e}")

    # 0.5. Pokročilé české text processing pomocí CzechTextProcessor
    if ENABLE_CZECH_TEXT_PROCESSING:
        try:
            from backend.czech_text_processor import get_czech_text_processor
            czech_processor = get_czech_text_processor()

            # Výchozí hodnoty pro apply_voicing a apply_glottal_stop
            voicing = apply_voicing if apply_voicing is not None else True
            glottal = apply_glottal_stop if apply_glottal_stop is not None else True

            text = czech_processor.process_text(
                text,
                apply_voicing=voicing,
                apply_glottal_stop=glottal,
                apply_consonant_groups=True,
                expand_abbreviations=True,
                expand_numbers=True
            )
        except Exception as e:
            print(f"[WARN] Varování: Czech text processing selhal: {e}")

    # 1. Převod na nářečí (pokud je zapnutý)
    should_convert_dialect = enable_dialect_conversion if enable_dialect_conversion is not None else ENABLE_DIALECT_CONVERSION
    target_dialect = dialect_code if dialect_code is not None else DIALECT_CODE
    target_intensity = dialect_intensity if dialect_intensity != 1.0 else DIALECT_INTENSITY

    if should_convert_dialect and target_dialect and target_dialect != "standardni":
        try:
            from backend.dialect_converter import get_dialect_converter
            converter = get_dialect_converter()
            text = converter.convert_to_dialect(text, target_dialect, intensity=target_intensity)
        except Exception as e:
            print(f"[WARN] Varování: Dialect conversion selhal: {e}")

    return text
