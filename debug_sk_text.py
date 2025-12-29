
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(os.getcwd())

from backend.slovak_text_processor import SlovakTextProcessor

def debug_slovak_processing(test_text):
    print(f"Original: {test_text}")

    processor = SlovakTextProcessor()

    # 1. Base processing (abbreviations, numbers)
    processed = processor.process_text(test_text, apply_voicing=False, apply_glottal_stop=False)
    print(f"Base processed: {processed}")

    # 2. With voicing
    with_voicing = processor.process_text(test_text, apply_voicing=True, apply_glottal_stop=False)
    print(f"With voicing: {with_voicing}")

    # 3. With glottal stop
    with_glottal = processor.process_text(test_text, apply_voicing=False, apply_glottal_stop=True)
    print(f"With glottal stop: {with_glottal}")

    # 4. Both
    both = processor.process_text(test_text, apply_voicing=True, apply_glottal_stop=True)
    print(f"Both: {both}")

if __name__ == "__main__":
    test_phrases = [
        "v pondelok v škole",
        "v aute s otcom",
        "vzťah k nemu",
        "125 eur a 50 centov",
        "o 15:30 v Bratislave",
        "v'akváriu" # Test matching existing quotes
    ]

    for phrase in test_phrases:
        print("-" * 40)
        debug_slovak_processing(phrase)
