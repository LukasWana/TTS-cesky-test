import sys
import os

# Přidání kořenového adresáře do sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.czech_text_processor import get_czech_text_processor
from backend.phonetic_translator import get_phonetic_translator

def test_phonetics():
    processor = get_czech_text_processor()
    translator = get_phonetic_translator()

    test_cases = [
        # Spodoba znělosti na konci slova
        ("chléb", "chlép"),
        ("hrad", "hrat"),
        # Spodoba znělosti před neznělou
        ("hloubka", "hloupka"),
        ("hladký", "hlatký"),
        # Spodoba znělosti před znělou
        ("šéf dirigent", "šév dirigent"),
        # Ráz po předložkách
        ("v lese", "v lese"), # v před l zůstává znělé
        ("v autě", "f 'autě"),
        ("nad očima", "nat 'očima"),
        # Zkratky
        ("např. dnes", "například dnes"),
        ("atd.", "a tak dále"),
        # Čísla
        ("mám 5 jablek", "mám pět jablek"),
        ("je mu 20 let", "je mu dvacet let"),
        # Cizí slova (z nového JSONu)
        ("I love you", "I light-o you"),
        ("it is about time", "it is abaut time"),
    ]

    print("--- Spoustim testy fonetiky ---")
    all_passed = True

    for input_text, expected_output in test_cases:
        # Nejdříve fonetický přepis cizích slov
        mid_text = translator.translate_foreign_words(input_text)
        # Poté český text processing
        actual_output = processor.process_text(mid_text)

        try:
            if actual_output.lower() == expected_output.lower():
                print(f"[OK] '{input_text}' -> '{actual_output}'")
            else:
                print(f"[FAIL] '{input_text}'")
                print(f"  Ocekavano: '{expected_output}'")
                print(f"  Ziskano:   '{actual_output}'")
                all_passed = False
        except UnicodeEncodeError:
            # Fallback pro Windows konzoli
            if actual_output.lower() == expected_output.lower():
                print(f"[OK] (unicode conflict)")
            else:
                print(f"[FAIL] (unicode conflict)")
                all_passed = False

    if all_passed:
        print("\n--- Vsechny testy probehly uspesne! ---")
    else:
        print("\n--- Nektere testy selhaly. ---")

if __name__ == "__main__":
    test_phonetics()

