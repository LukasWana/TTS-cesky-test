"""
Diagnostic script to test F5-TTS CLI directly with Czech text.
"""
import subprocess
import os
import sys
from pathlib import Path

# Find CLI
cli_exe = None
venv_scripts = Path(sys.executable).parent / "f5-tts_infer-cli.exe"
if venv_scripts.exists():
    cli_exe = str(venv_scripts)
else:
    import shutil
    cli_exe = shutil.which("f5-tts_infer-cli")

if not cli_exe:
    print("ERROR: f5-tts_infer-cli not found")
    sys.exit(1)

print(f"CLI: {cli_exe}")

# Paths
OUTPUT_DIR = Path("c:/work/projects/2025-voice-assistent/outputs")
REF_AUDIO = Path("c:/work/projects/2025-voice-assistent/assets/czech voices")
OUTPUT_DIR.mkdir(exist_ok=True)

# Find a reference audio
ref_files = list(REF_AUDIO.glob("*.wav"))
if not ref_files:
    print(f"ERROR: No reference audio found in {REF_AUDIO}")
    sys.exit(1)

ref_audio = str(ref_files[0])
print(f"Reference audio: {ref_audio}")

# Test text
test_text = "Ahoj, toto je test českého modelu."
print(f"Test text: {test_text}")

# Build command (base model, no finetuning)
cmd = [
    cli_exe,
    "-m", "F5TTS_v1_Base",
    "-r", ref_audio,
    "-t", test_text,
    "-o", str(OUTPUT_DIR),
    "-w", "test_czech_base.wav",
    "--device", "cpu",
    "--nfe_step", "16",
]

print(f"\nCommand: {' '.join(cmd)}")
print("\n--- Running F5-TTS CLI ---")

env = os.environ.copy()
env["PYTHONUTF8"] = "1"
env["PYTHONIOENCODING"] = "utf-8"
env["WANDB_MODE"] = "disabled"

result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(OUTPUT_DIR), env=env)

print("\n--- STDOUT ---")
print(result.stdout)
print("\n--- STDERR ---")
print(result.stderr)
print(f"\nExit code: {result.returncode}")

output_file = OUTPUT_DIR / "test_czech_base.wav"
if output_file.exists():
    print(f"\n✅ Output file exists: {output_file}")
    print(f"   Size: {output_file.stat().st_size} bytes")
else:
    print(f"\n❌ Output file NOT found: {output_file}")
