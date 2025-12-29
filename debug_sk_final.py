
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(os.getcwd())

from backend.sk_pipeline import preprocess_slovak_text

# Mock lookup_loader since it's empty/broken but imported by pipeline chain
# (Actually, we'll try to let it fail silently if it's already fixed in the file)
# If it fails, we'll know the imports are still broken.

def debug_final_fix(test_text):
    print(f"Original: {test_text}")
    try:
        # Full pipeline now should have apply_voicing=False and apply_glottal_stop=False by default
        full = preprocess_slovak_text(test_text, "sk")
        print(f"Pipeline output: {full}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_phrases = [
        "v pondelok v škole",
        "v aute s otcom",
        "vzťah k nemu",
        "125 eur"
    ]

    for phrase in test_phrases:
        print("-" * 40)
        debug_final_fix(phrase)
