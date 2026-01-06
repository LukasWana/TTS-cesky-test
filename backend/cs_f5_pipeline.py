"""
Sdílený modul pro český F5-TTS text preprocessing pipeline
Odděleno od XTTS pipeline pro specifické nastavení (vypnutí fonetických úprav)

Podpora pro Slovak model s fonetickou adaptací:
- Slovak model nezná některé české znaky (ů, některá slovesa)
- Fonetická adaptace nahrazuje česká slova slovenskými ekvivalenty,
  které zní podobně česky
"""

from typing import Optional
from backend.config import (
    ENABLE_PHONETIC_TRANSLATION,
    ENABLE_CZECH_TEXT_PROCESSING,
    ENABLE_DIALECT_CONVERSION,
    DIALECT_CODE,
    DIALECT_INTENSITY,
)
from backend.phonetic_translator import get_phonetic_translator


def preprocess_czech_f5_text(
    text: str,
    language: str,
    enable_dialect_conversion: Optional[bool] = None,
    dialect_code: Optional[str] = None,
    dialect_intensity: float = 1.0,
    # Slovak model s fonetickou adaptací
    use_slovak_model: bool = False,
) -> str:
    """
    Předzpracuje text pro český F5-TTS engine.

    Args:
        text: Text k předzpracování
        language: Jazyk textu (pouze "cs" aktivuje české zpracování)
        enable_dialect_conversion: Zda povolit převod na nářečí
        dialect_code: Kód nářečí
        dialect_intensity: Intenzita převodu (0.0-1.0)
        use_slovak_model: Použít Slovak model s fonetickou adaptací

    Returns:
        Předzpracovaný text
    """
    if language != "cs":
        return text

    # === SLOVAK MODEL S FONETICKOU ADAPTACÍ ===
    if use_slovak_model:
        try:
            # Použijeme nový comprehensive adapter s 600+ slovním slovníkem
            from backend.cz_sk_adapter import get_adapter

            adapter = get_adapter()
            result = adapter.convert(text)  # Získáme detailní výsledek

            # Logování změn pro debugging
            print(f"[INFO] Slovak model fonetická adaptace:")
            print(f"  Original: {result.original[:80]}...")
            print(f"  Adapted:  {result.converted[:80]}...")
            print(f"  Změn: {result.changes_count}, Confidence: {result.confidence:.2%}")
            if result.applied_conversions[:5]:  # První 5 změn
                print(f"  Příklady změn:")
                for conv in result.applied_conversions[:5]:
                    print(f"    - '{conv['original']}' → '{conv['converted']}' ({conv['type']})")

            text = result.converted
        except Exception as e:
            print(f"[WARN] Slovak fonetická adaptace selhala: {e}")
            import traceback
            traceback.print_exc()
            # Pokračujeme bez adaptace

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

            # Specifické nastavení pro F5-TTS:
            # - apply_voicing=False (způsobuje problémy)
            # - apply_glottal_stop=False (způsobuje problémy)
            # - apply_consonant_groups=False (stejně jako u SK, model na to nebyl trénován)
            text = czech_processor.process_text(
                text,
                apply_voicing=False,
                apply_glottal_stop=False,
                apply_consonant_groups=False,
                expand_abbreviations=True,
                expand_numbers=True,
            )
        except Exception as e:
            print(f"[WARN] Varování: Czech F5 text processing selhal: {e}")

    # 1. Převod na nářečí (pokud je zapnutý) - zachováno z původní pipeline
    should_convert_dialect = (
        enable_dialect_conversion
        if enable_dialect_conversion is not None
        else ENABLE_DIALECT_CONVERSION
    )
    target_dialect = dialect_code if dialect_code is not None else DIALECT_CODE
    target_intensity = (
        dialect_intensity if dialect_intensity != 1.0 else DIALECT_INTENSITY
    )

    if should_convert_dialect and target_dialect and target_dialect != "standardni":
        try:
            from backend.dialect_converter import get_dialect_converter

            converter = get_dialect_converter()
            text = converter.convert_to_dialect(
                text, target_dialect, intensity=target_intensity
            )
        except Exception as e:
            print(f"[WARN] Varování: Dialect conversion selhal: {e}")

    return text
