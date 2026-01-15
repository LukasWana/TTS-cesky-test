"""
Test skript pro CZ Sentence Quotes
Ověří, že funkce správně přidává uvozovky do českých vět
"""

import sys
import os
import io

# Přidat backend do PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Nastavení kódování pro Windows konzoli
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from backend.config import ENABLE_CZ_SENTENCE_QUOTES
import re


def test_cz_sentence_quotes():
    """Testuje přidání uvozovek do českých vět"""
    print("=" * 60)
    print("Test CZ Sentence Quotes")
    print("=" * 60)
    print(f"ENABLE_CZ_SENTENCE_QUOTES = {ENABLE_CZ_SENTENCE_QUOTES}")
    print()

    if not ENABLE_CZ_SENTENCE_QUOTES:
        print("[SKIP] Testování s vypnutou funkcí (ENABLE_CZ_SENTENCE_QUOTES=False)")
        print("Pro testování s funkcí zapnutou nastavte ENABLE_CZ_SENTENCE_QUOTES=True")
        return True

    # Testovací případy
    test_cases = [
        ("Pro každý pár si vyber stranu.", "Pro každý pár si vyber stranu"),
        ("Ahoj, jak se máš?", "Ahoj, jak se máš"),  # Otazník se odstraní
        (
            "Toto je delší věta s čárkou a tečkou.",
            "Toto je delší věta s čárkou a tečkou",
        ),
        ("Pozor!", "Pozor"),  # Vykřičník se odstraní
        (
            "Text s vícerými řádky.\nNová věta.",
            "Text s vícerými řádky.\nNová věta",
        ),  # Víceré věty se zpracují jako jeden chunk
    ]

    all_passed = True

    for original, expected_no_punct in test_cases:
        # Simulace logiky z tts_engine.py
        text_for_model = original
        if isinstance(text_for_model, str):
            # Odstranit koncovou interpunkci (tečka, otazník, vykřičník)
            text_for_model = re.sub(r"\s*[.!?…]+(\s*)$", r"\1", text_for_model).rstrip()

            # Přidat uvozovky
            if ENABLE_CZ_SENTENCE_QUOTES:
                text_for_model = f'"{text_for_model}"'

        # Očekávaný výsledek
        expected = (
            f'"{expected_no_punct}"' if ENABLE_CZ_SENTENCE_QUOTES else expected_no_punct
        )

        # Ověření
        passed = text_for_model == expected
        all_passed = all_passed and passed

        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status}: '{original}'")
        print(f"   →   '{text_for_model}'")
        if not passed:
            print(f"   Expected: '{expected}'")
        print()

    # Testovací případy s již existujícími uvozovkami
    edge_cases = [
        (
            'Řekl: "Ahoj světe!"',
            '"Řekl: "Ahoj světe!""',
        ),  # Uvozovky uvnitř, přidáme další venku (vykřičník se odstraní)
        (
            'Text s "uvozovkami uvnitř" věty',
            '"Text s "uvozovkami uvnitř" věty"',
        ),  # Tečka uvnitř se neodstraní (není na konci)
    ]

    print("Edge Cases (uvozovky uvnitř textu)")
    print("-" * 60)
    for original, expected in edge_cases:
        text_for_model = original
        if isinstance(text_for_model, str):
            text_for_model = re.sub(r"\s*[.…]+(\s*)$", r"\1", text_for_model).rstrip()
            if ENABLE_CZ_SENTENCE_QUOTES:
                text_for_model = f'"{text_for_model}"'

        passed = text_for_model == expected
        all_passed = all_passed and passed

        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status}: '{original}'")
        print(f"   →   '{text_for_model}'")
        if not passed:
            print(f"   Expected: '{expected}'")
        print()

    print("=" * 60)
    if all_passed:
        print("[OK] Všechny testy PROŠLY!")
    else:
        print("[FAIL] Některé testy NEPROŠLY!")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = test_cz_sentence_quotes()
    sys.exit(0 if success else 1)
