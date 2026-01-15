"""
Test skript pro CZ Split by Commas
Ověří dělení textu po čárkách a 8-10 slovech
"""

import sys
import os
import io
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Nastavení kódování pro Windows konzoli
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from backend.config import (
    ENABLE_CZ_SPLIT_BY_COMMAS,
    CZ_SPLIT_MAX_WORDS,
    CZ_SPLIT_LANGUAGES,
    ENABLE_CZ_SENTENCE_QUOTES,
)


def split_text_by_commas_and_words(
    text: str, language: str = "cs", force_enabled=False
):
    """Simulace logiky z tts_engine.py"""

    # Aplikovat jen pro konfigurované jazyky
    if language not in CZ_SPLIT_LANGUAGES:
        return [text]

    # Pokud je funkce vypnutá a není vynuceno zapnutí, vrať původní text
    if not ENABLE_CZ_SPLIT_BY_COMMAS and not force_enabled:
        return [text]

    # Normalizace mezer
    text = re.sub(r"\s+", " ", text.strip())

    # 1. Primárně dělit po čárkách (včetně čárek s mezerami)
    # Regex zachytí: "," - čárku s mezerou nebo bez
    comma_parts = re.split(r",\s*", text)

    # 2. Dělit každou část podle max. počtu slov
    max_words = CZ_SPLIT_MAX_WORDS
    chunks = []

    for part in comma_parts:
        part = part.strip()
        if not part:
            continue

        # Počítat slova (mezera jako oddělovač)
        words = [w for w in part.split(" ") if w]

        if len(words) <= max_words:
            # Pokud je část dostatečně krátká, přidat jako jeden chunk
            chunks.append(part)
        else:
            # Dělit dále po slovech
            for i in range(0, len(words), max_words):
                chunk_words = words[i : i + max_words]
                chunk = " ".join(chunk_words)
                chunks.append(chunk)

    # 3. Předzpracovat každou část
    processed_chunks = []
    for chunk in chunks:
        if not chunk.strip():
            continue

        # Odstranit koncovou interpunkci (tečka, otazník, vykřičník, ...)
        chunk = re.sub(r"\s*[.!?…]+(\s*)$", r"\1", chunk).rstrip()

        # Přidat uvozovky
        if ENABLE_CZ_SENTENCE_QUOTES:
            chunk = f'"{chunk}"'

        processed_chunks.append(chunk)

    return processed_chunks


def test_cz_split_by_commas():
    """Testuje dělení textu po čárkách a slovech"""
    print("=" * 70)
    print("Test CZ Split by Commas")
    print("=" * 70)
    print(f"ENABLE_CZ_SPLIT_BY_COMMAS = {ENABLE_CZ_SPLIT_BY_COMMAS}")
    print(f"CZ_SPLIT_MAX_WORDS = {CZ_SPLIT_MAX_WORDS}")
    print(f"CZ_SPLIT_LANGUAGES = {CZ_SPLIT_LANGUAGES}")
    print(f"ENABLE_CZ_SENTENCE_QUOTES = {ENABLE_CZ_SENTENCE_QUOTES}")
    print()

    # Testovací případy
    test_cases = [
        (
            "Útočiště ve Třech klenotech by mělo být motivováno znepokojením naší současné situací a přesvědčením, že právě Buddha, Dharma a Sangha nabízí její řešení.",
            [
                '"Útočiště ve Třech klenotech by mělo být motivováno znepokojením naší"',
                '"současné situací a přesvědčením"',
                '"že právě Buddha"',
                '"Dharma a Sangha nabízí její řešení"',
            ],
        ),
        (
            "Pro každý pár si vyber stranu, která ti připadá nejpřirozenější.",
            ['"Pro každý pár si vyber stranu"', '"která ti připadá nejpřirozenější"'],
        ),
        (
            "Ahoj, jak se máš?",
            [
                '"Ahoj"',
                '"jak se máš"',  # Otazník se odstraní podle pravidla B (odstranit koncovou interpunkci)
            ],
        ),
        (
            "Pozor! Nepoužívejte tento výtah při požáru.",
            [
                '"Pozor! Nepoužívejte tento výtah při požáru"'  # Jen jedna část bez čárky
            ],
        ),
        (
            "Toto je velmi dlouhá věta s mnoha slovy, která přesáhne limit deseti slov v jednom úseku, takže bude rozdělena na více částí.",
            [
                '"Toto je velmi dlouhá věta s mnoha slovy"',
                '"která přesáhne limit deseti slov v jednom úseku"',
                '"takže bude rozdělena na více částí"',
            ],
        ),
        ("Toto je kratká věta bez čárky.", ['"Toto je kratká věta bez čárky"']),
        (
            "Text s více čárek, první část, druhá část, třetí část.",
            [
                '"Text s více čárek"',  # Tečka z "čárka" se odstraní
                '"první část"',
                '"druhá část"',
                '"třetí část"',
            ],
        ),
    ]

    all_passed = True

    for original, expected in test_cases:
        result = split_text_by_commas_and_words(original, "cs", force_enabled=True)

        passed = result == expected
        all_passed = all_passed and passed

        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status}: '{original[:80]}...'")
        print(f"   Očekáváno {len(expected)} částí:")
        for i, chunk in enumerate(expected):
            print(f"     [{i + 1}] {chunk}")
        print(f"   Získáno {len(result)} částí:")
        for i, chunk in enumerate(result):
            print(f"     [{i + 1}] {chunk}")
        if not passed:
            print("   ❌ NEODPOVÍDÁ!")
        print()

    print("=" * 70)
    if all_passed:
        print("[OK] Všechny testy PROŠLY!")
    else:
        print("[FAIL] Některé testy NEPROŠLY!")
    print("=" * 70)

    return all_passed


if __name__ == "__main__":
    success = test_cz_split_by_commas()
    sys.exit(0 if success else 1)
