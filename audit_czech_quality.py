
import os
import asyncio
import sys
from pathlib import Path

# Přidat kořenový adresář do sys.path pro importy z backendu
sys.path.append(str(Path(__file__).parent))

from backend.tts_engine import XTTSEngine
from backend.config import DEMO_VOICES_CS_DIR, OUTPUTS_DIR

async def run_audit():
    print("🚀 Spouštím audit české TTS kvality...")

    engine = XTTSEngine()
    await engine.load_model()

    # Testovací texty s problematickými jevy (spodoba znělosti, ráz)
    test_cases = [
        ("Lev v autě.", "voicing_and_glottal_stop"),
        ("Včera jsem byl v kině.", "voicing_v_v_s"),
        ("To je ale pěkné údolí.", "glottal_stop_u"),
        ("Mě se to líbí.", "consonant_group_me")
    ]

    # Výchozí hlas
    speaker_wav = str(DEMO_VOICES_CS_DIR / "Brodsky-male.wav")
    if not os.path.exists(speaker_wav):
        # Fallback na první dostupný hlas
        available = list(DEMO_VOICES_CS_DIR.glob("*.wav"))
        if available:
            speaker_wav = str(available[0])
        else:
            print("❌ Žádný demo hlas nebyl nalezen!")
            return

    print(f"🎤 Používám hlas: {Path(speaker_wav).name}")

    for text, slug in test_cases:
        print(f"\n📝 Testuji: '{text}'")

        # 1. S agresivním preprocessingem (původní stav)
        print("   - Generuji s fonetickou normalizací (ON)...")
        path_on = await engine.generate(
            text=text,
            speaker_wav=speaker_wav,
            apply_voicing=True,
            apply_glottal_stop=True,
            job_id=f"audit_{slug}_on"
        )
        final_path_on = OUTPUTS_DIR / f"audit_{slug}_normalization_ON.wav"
        if os.path.exists(path_on):
            os.replace(path_on, final_path_on)
            print(f"     ✅ Uloženo: {final_path_on.name}")

        # 2. Bez agresivního preprocessingu (nový stav)
        print("   - Generuji bez fonetické normalizace (OFF)...")
        path_off = await engine.generate(
            text=text,
            speaker_wav=speaker_wav,
            apply_voicing=False,
            apply_glottal_stop=False,
            job_id=f"audit_{slug}_off"
        )
        final_path_off = OUTPUTS_DIR / f"audit_{slug}_normalization_OFF.wav"
        if os.path.exists(path_off):
            os.replace(path_off, final_path_off)
            print(f"     ✅ Uloženo: {final_path_off.name}")

    print("\n✨ Audit dokončen. Výsledky jsou v adresáři outputs.")

if __name__ == "__main__":
    asyncio.run(run_audit())
