#!/usr/bin/env python3
"""
Test script pro ověření kvality voice vzorku s XTTS-v2 modelem

Použití:
    python scripts/test_voice_quality.py voice_sample.wav
    python scripts/test_voice_quality.py voice_sample.wav --text "Vlastní testovací text"
"""

import argparse
import sys
from pathlib import Path

# Přidání backend do path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.tts_engine import XTTSEngine
from backend.config import OUTPUTS_DIR
import asyncio


async def test_voice_quality(voice_path: str, test_text: str = None):
    """
    Otestuje kvalitu voice vzorku s XTTS-v2 modelem

    Args:
        voice_path: Cesta k voice vzorku
        test_text: Testovací text (výchozí: ukázkový český text)
    """
    voice_file = Path(voice_path)

    if not voice_file.exists():
        print(f"❌ Chyba: Voice soubor neexistuje: {voice_path}")
        return False

    if test_text is None:
        test_text = (
            "Umělá inteligence dokáže dnes generovat velmi přirozený hlas "
            "v češtině. Tato technologie využívá pokročilé neuronové sítě "
            "a strojové učení. Kvalita syntézy je překvapivě vysoká "
            "a neustále se zlepšuje."
        )

    print("🎤 Testování kvality voice vzorku")
    print("=" * 60)
    print(f"📂 Voice soubor: {voice_path}")
    print(f"📝 Testovací text: {test_text[:50]}...")
    print()

    try:
        # Inicializace TTS engine
        print("⏳ Načítám XTTS-v2 model...")
        tts_engine = XTTSEngine()
        await tts_engine.load_model()

        if not tts_engine.is_loaded:
            print("❌ Chyba: Model se nepodařilo načíst")
            return False

        print("✅ Model načten")
        print()

        # Generování testovací řeči
        print("🎵 Generuji testovací řeč...")
        output_path = await tts_engine.generate(
            text=test_text,
            speaker_wav=str(voice_file),
            language="cs"
        )

        output_file = Path(output_path)
        if output_file.exists():
            file_size = output_file.stat().st_size / 1024
            print(f"✅ Test dokončen!")
            print(f"📁 Výstupní soubor: {output_path}")
            print(f"📊 Velikost: {file_size:.1f} KB")
            print()
            print("💡 Tip: Poslechněte si výstupní soubor a zkontrolujte:")
            print("   - Přirozenost hlasu")
            print("   - Shodu s originálním hlasem")
            print("   - Kvalitu výslovnosti")
            print("   - Absenci artefaktů")
            return True
        else:
            print("❌ Chyba: Výstupní soubor nebyl vytvořen")
            return False

    except Exception as e:
        print(f"❌ Chyba při testování: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Otestuje kvalitu voice vzorku s XTTS-v2 modelem",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Příklady použití:
  # Základní test s výchozím textem
  python scripts/test_voice_quality.py voice_sample.wav

  # Test s vlastním textem
  python scripts/test_voice_quality.py voice_sample.wav --text "Můj testovací text"
        """
    )

    parser.add_argument(
        "voice",
        help="Cesta k voice vzorku (WAV soubor)"
    )

    parser.add_argument(
        "--text",
        help="Vlastní testovací text (výchozí: ukázkový český text)",
        default=None
    )

    args = parser.parse_args()

    # Spuštění testu
    success = asyncio.run(test_voice_quality(args.voice, args.text))

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()





