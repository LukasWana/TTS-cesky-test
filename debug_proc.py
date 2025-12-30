
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

try:
    from backend.czech_text_processor import get_czech_text_processor
    proc = get_czech_text_processor()
    print("✅ Processor initialized")

    text = "Mám 5 jablek a např. 2 hrušky."
    print(f"Testing text: {text}")
    res = proc.process_text(text, expand_numbers=True, expand_abbreviations=True)
    print(f"✅ Result: {res}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
