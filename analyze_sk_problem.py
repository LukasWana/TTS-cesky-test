
import os
import librosa
import soundfile as sf
import numpy as np

def analyze_audio(path, name):
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return None

    try:
        audio, sr = librosa.load(path, sr=None)
        duration = librosa.get_duration(y=audio, sr=sr)
        rms = np.sqrt(np.mean(audio**2))
        peak = np.max(np.abs(audio))

        print(f"--- Analysis for {name} ---")
        print(f"Path: {path}")
        print(f"Sample Rate: {sr} Hz")
        print(f"Duration: {duration:.2f} seconds")
        print(f"RMS Energy: {rms:.4f}")
        print(f"Peak Amplitude: {peak:.4f}")

        # Check for silence or clipping
        if peak > 0.99:
            print("WARNING: Audio might be clipping!")
        if rms < 0.001:
            print("WARNING: Audio is very quiet or silent!")

        return {
            "duration": duration,
            "sr": sr
        }
    except Exception as e:
        print(f"Error analyzing {path}: {e}")
        return None

if __name__ == "__main__":
    ref_path = r"c:\work\projects\2025-voice-assistent\assets\slovak voices\TazkyTyzden.wav"
    out_path = r"c:\work\projects\2025-voice-assistent\outputs\5a619a5d-2861-4c24-8031-07db46170496.wav"

    ref_info = analyze_audio(ref_path, "Reference Content")
    out_info = analyze_audio(out_path, "Model Output")

    # Text Analysis
    text = "V poslednej dobe je to u nás ako v seriali Strange Things. Krajena hore nohami a je občania, no a jediný, kto si to celé užívajú, je naž najväčší sociálny demo, trápne je najme po osobe nie tejto vlády, ktorá furt riešil len svoje boliestky. Lenže tým pádom neostava čas na naozet vôležité veci. Napríklad rastúcu kriminalitu, hudobu či ceny potravín."
    word_count = len(text.split())
    print("\n--- Text Analysis ---")
    print(f"Word count: {word_count}")

    if ref_info:
        words_per_sec = word_count / ref_info["duration"]
        print(f"Words per second in reference: {words_per_sec:.2f}")
        if words_per_sec > 4:
            print("WARNING: Reference text is likely too long for the audio duration!")
        elif words_per_sec < 1:
             print("WARNING: Reference text is likely too short for the audio duration!")
