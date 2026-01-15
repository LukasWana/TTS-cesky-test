"""
Rychlý manuální test pro CZ Sentence Quotes
Ukazuje jak se text transformuje s funkcí zapnutou/vypnutou
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

import re


def test_manual_demo():
    """Manuální testování různých textů"""
    print("=" * 70)
    print("Manuální test CZ Sentence Quotes")
    print("=" * 70)
    print()

    # Testovací texty
    test_texts = [
        "Pro každý pár si vyber stranu, která ti připadá nejpřirozenější.",
        "Ahoj, jak se máš?",
        "Pozor! Nepoužívejte tento výtah při požáru.",
        'Řekl: "Ahoj světe!"',
        'Text s "uvozovkami uvnitř" věty a tečkou.',
    ]

    # Test s funkcí ZAPNUTOU
    print("-" * 70)
    print("S funkcí ZAPNUTOU (ENABLE_CZ_SENTENCE_QUOTES = True)")
    print("-" * 70)
    for original in test_texts:
        # Simulace logiky z tts_engine.py
        text_for_model = original
        if isinstance(text_for_model, str):
            # Odstranit koncovou interpunkci
            text_for_model = re.sub(r"\s*[.!?…]+(\s*)$", r"\1", text_for_model).rstrip()
            # Přidat uvozovky
            text_for_model = f'"{text_for_model}"'

        print(f"Vstup:   {original}")
        print(f"Výstup:  {text_for_model}")
        print()

    # Test s funkcí VYPNUTOU
    print("-" * 70)
    print("S funkcí VYPNUTOU (ENABLE_CZ_SENTENCE_QUOTES = False)")
    print("-" * 70)
    for original in test_texts:
        # Simulace logiky z tts_engine.py
        text_for_model = original
        if isinstance(text_for_model, str):
            # Odstranit koncovou interpunkci
            text_for_model = re.sub(r"\s*[.!?…]+(\s*)$", r"\1", text_for_model).rstrip()
            # Žádné uvozovky
            pass

        print(f"Vstup:   {original}")
        print(f"Výstup:  {text_for_model}")
        print()

    print("=" * 70)
    print("Manuální test dokončen")
    print("=" * 70)


if __name__ == "__main__":
    test_manual_demo()
