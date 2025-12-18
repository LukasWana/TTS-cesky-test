
import os
import sys
import torch
import numpy as np
from pathlib import Path

# Add backend to path
sys.path.append(os.getcwd())

try:
    import librosa
    import soundfile as sf
    print(f"librosa version: {librosa.__version__}")
    print(f"soundfile version: {sf.__version__}")
except ImportError as e:
    print(f"Error importing dependencies: {e}")
    sys.exit(1)

def test_speed_change(input_path, output_path, speed):
    print(f"Testing speed change: {speed}x")
    try:
        audio, sr = librosa.load(input_path, sr=None)
        print(f"Loaded audio: {len(audio)} samples at {sr} Hz")

        audio_stretched = librosa.effects.time_stretch(audio, rate=speed)
        print(f"Stretched audio: {len(audio_stretched)} samples")

        sf.write(output_path, audio_stretched, sr)
        print(f"Saved to {output_path}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    # Use a demo voice as input if available
    demo_dir = Path("frontend/assets/demo-voices")
    demo_files = list(demo_dir.glob("*.wav"))

    if not demo_files:
        print("No demo voices found in frontend/assets/demo-voices")
        # Create a dummy wav file
        sr = 22050
        duration = 2.0
        t = np.linspace(0, duration, int(sr * duration))
        audio = np.sin(2 * np.pi * 440 * t)
        input_path = "test_input.wav"
        sf.write(input_path, audio, sr)
    else:
        input_path = str(demo_files[0])

    output_path = "test_output_speed.wav"

    success = test_speed_change(input_path, output_path, 1.5)
    if success:
        print("Test PASSED")
    else:
        print("Test FAILED")
