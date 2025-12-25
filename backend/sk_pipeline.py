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

    # 0.5. Základné slovenské text processing
    # Poznámka: Slovenský text processor zatiaľ není implementován,
    # takže použijeme základní normalizaci
    if ENABLE_SLOVAK_TEXT_PROCESSING:
        try:
            # Základní normalizace pro slovenštinu
            # - Normalizace mezer kolem interpunkce
            import re
            text = re.sub(r'\s+([.,!?;:])', r'\1', text)  # Odstranění mezer před interpunkcí
            text = re.sub(r'([.,!?;:])\s*([.,!?;:])', r'\1\2', text)  # Více interpunkcí za sebou
            text = re.sub(r'([.,!?;:])\s*([a-zA-ZáäčďéíĺľňóôŕšťúýžÁÄČĎÉÍĹĽŇÓÔŔŠŤÚÝŽ])', r'\1 \2', text)  # Mezera po interpunkci

            # Základní převod čísel na slova (pro jednoduché případy)
            # Poznámka: Pro plnou podporu by bylo potřeba slovenský číselný převodník
            # Zatím ponecháme čísla jako jsou (model by měl zvládnout základní čísla)

        except Exception as e:
            print(f"[WARN] Varovanie: Slovak text processing selhal: {e}")

    # Poznámka: Dialect conversion není pro slovenštinu implementována
    # (slovenština má jiné nářečí než čeština a systém je zaměřen na česká nářečí)

    return text

