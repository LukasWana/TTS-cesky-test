#!/usr/bin/env python3
"""
Utility script pro přípravu audio vzorků pro XTTS-v2 voice cloning

Použití:
    python scripts/prepare_demo_voice.py input.mp3 output.wav
    python scripts/prepare_demo_voice.py input.mp3 --output demo-voices/male_cz.wav --trim 5 15
"""

import argparse
import sys
from pathlib import Path

# Přidání backend do path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.audio_processor import AudioProcessor
from backend.config import TARGET_SAMPLE_RATE, DEMO_VOICES_DIR
import librosa
import soundfile as sf
import numpy as np


def prepare_voice_sample(
    input_path: str,
    output_path: str,
    trim_start: float = None,
    trim_duration: float = None,
    apply_noise_reduction: bool = False,
    apply_highpass: bool = False
):
    """
    Připraví audio vzorek pro XTTS-v2

    Args:
        input_path: Cesta k vstupnímu audio souboru
        output_path: Cesta k výstupnímu WAV souboru
        trim_start: Začátek ořezu v sekundách (volitelné)
        trim_duration: Délka ořezu v sekundách (volitelné)
        apply_noise_reduction: Aplikovat jednoduchou redukci šumu
        apply_highpass: Aplikovat high-pass filter
    """
    input_file = Path(input_path)
    output_file = Path(output_path)

    # Kontrola existence vstupního souboru
    if not input_file.exists():
        print(f"❌ Chyba: Vstupní soubor neexistuje: {input_path}")
        return False

    try:
        print(f"📂 Načítám: {input_path}")

        # Načtení audio
        audio, sr = librosa.load(
            input_path,
            sr=TARGET_SAMPLE_RATE,
            mono=True,
            offset=trim_start if trim_start else None,
            duration=trim_duration if trim_duration else None
        )

        print(f"   Původní sample rate: {sr} Hz")
        print(f"   Délka: {len(audio)/sr:.2f} sekund")

        # Ořez ticha na začátku a konci
        audio, _ = librosa.effects.trim(audio, top_db=20)
        print(f"   Po ořezu ticha: {len(audio)/sr:.2f} sekund")

        # High-pass filter (odfiltruje hluboké frekvence pod 80 Hz)
        if apply_highpass:
            print("   Aplikuji high-pass filter (80 Hz)...")
            audio = librosa.effects.preemphasis(audio, coef=0.97)
            # Alternativně: audio = scipy.signal.butter + filtfilt

        # Jednoduchá redukce šumu (spectral gating)
        if apply_noise_reduction:
            print("   Aplikuji redukci šumu...")
            # Jednoduchá metoda: odstranění tichých částí spektra
            stft = librosa.stft(audio)
            magnitude = np.abs(stft)
            # Threshold na 10% maximální hodnoty
            threshold = np.max(magnitude) * 0.1
            mask = magnitude > threshold
            stft_clean = stft * mask
            audio = librosa.istft(stft_clean)

        # Normalizace hlasitosti
        print("   Normalizuji hlasitost...")
        audio = librosa.util.normalize(audio)

        # Zajištění, že výstupní adresář existuje
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Uložení
        sf.write(str(output_file), audio, TARGET_SAMPLE_RATE)

        # Validace výstupu
        duration = librosa.get_duration(path=str(output_file))
        print(f"\n✅ Připraveno: {output_path}")
        print(f"   Sample rate: {TARGET_SAMPLE_RATE} Hz")
        print(f"   Délka: {duration:.2f} sekund")
        print(f"   Velikost: {output_file.stat().st_size / 1024:.1f} KB")

        # Kontrola minimální délky
        if duration < 6.0:
            print(f"   ⚠️  Varování: Délka je pod doporučeným minimem (6s)")
        elif duration >= 10.0:
            print(f"   ✓ Délka je optimální (10-30s doporučeno)")

        return True

    except Exception as e:
        print(f"❌ Chyba při zpracování: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Připraví audio vzorek pro XTTS-v2 voice cloning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Příklady použití:
  # Základní konverze
  python scripts/prepare_demo_voice.py input.mp3 output.wav

  # Ořez na 10 sekund od 5. sekundy
  python scripts/prepare_demo_voice.py input.mp3 output.wav --trim 5 10

  # S pokročilým zpracováním
  python scripts/prepare_demo_voice.py input.mp3 output.wav --noise-reduction --highpass

  # Do demo-voices složky
  python scripts/prepare_demo_voice.py input.mp3 --output demo-voices/male_cz.wav
        """
    )

    parser.add_argument(
        "input",
        help="Vstupní audio soubor (jakýkoliv podporovaný formát)"
    )

    parser.add_argument(
        "-o", "--output",
        help="Výstupní WAV soubor (výchozí: input.wav ve stejné složce)",
        default=None
    )

    parser.add_argument(
        "--trim",
        nargs=2,
        type=float,
        metavar=("START", "DURATION"),
        help="Ořez audio: START (sekundy) DURATION (sekundy)"
    )

    parser.add_argument(
        "--noise-reduction",
        action="store_true",
        help="Aplikovat jednoduchou redukci šumu"
    )

    parser.add_argument(
        "--highpass",
        action="store_true",
        help="Aplikovat high-pass filter (odfiltruje hluboké frekvence)"
    )

    parser.add_argument(
        "--demo-dir",
        action="store_true",
        help="Uložit do frontend/assets/demo-voices/ (automaticky nastaví výstupní cestu)"
    )

    args = parser.parse_args()

    # Určení výstupní cesty
    if args.output:
        output_path = args.output
    elif args.demo_dir:
        input_name = Path(args.input).stem
        output_path = DEMO_VOICES_DIR / f"{input_name}.wav"
    else:
        output_path = Path(args.input).with_suffix(".wav")

    # Ořez
    trim_start = None
    trim_duration = None
    if args.trim:
        trim_start = args.trim[0]
        trim_duration = args.trim[1]

    # Spuštění zpracování
    success = prepare_voice_sample(
        args.input,
        str(output_path),
        trim_start=trim_start,
        trim_duration=trim_duration,
        apply_noise_reduction=args.noise_reduction,
        apply_highpass=args.highpass
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()


















