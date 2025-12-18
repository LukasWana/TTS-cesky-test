"""
Audio concatenator pro spojení audio částí s plynulými přechody
"""
import numpy as np
import librosa
import soundfile as sf
from pathlib import Path
from typing import List
from backend.config import OUTPUT_SAMPLE_RATE


class AudioConcatenator:
    """Třída pro spojení audio částí s crossfade přechody"""

    @staticmethod
    def concatenate_audio(
        audio_files: List[str],
        output_path: str,
        crossfade_ms: int = 50,
        pause_ms: int = 0
    ) -> str:
        """
        Spojí více audio souborů s plynulými přechody

        Args:
            audio_files: Seznam cest k audio souborům
            output_path: Cesta k výstupnímu souboru
            crossfade_ms: Délka crossfade přechodu v milisekundách
            pause_ms: Délka pauzy mezi částmi v milisekundách (0 = žádná pauza)

        Returns:
            Cesta k výstupnímu souboru
        """
        if not audio_files:
            raise ValueError("Seznam audio souborů je prázdný")

        if len(audio_files) == 1:
            # Pokud je jen jeden soubor, zkopíruj ho
            import shutil
            shutil.copy(audio_files[0], output_path)
            return output_path

        # Načtení všech audio souborů
        audio_segments = []
        sample_rate = OUTPUT_SAMPLE_RATE

        for audio_file in audio_files:
            if not Path(audio_file).exists():
                raise FileNotFoundError(f"Audio soubor neexistuje: {audio_file}")

            audio, sr = librosa.load(audio_file, sr=OUTPUT_SAMPLE_RATE)
            audio_segments.append(audio)
            if sr != sample_rate:
                print(f"Warning: Sample rate mismatch: {sr} vs {sample_rate}")

        # Spojení s crossfade
        crossfade_samples = int(crossfade_ms * sample_rate / 1000)
        pause_samples = int(pause_ms * sample_rate / 1000)

        concatenated = []

        for i, segment in enumerate(audio_segments):
            if i == 0:
                # První segment - přidej celý
                concatenated.append(segment)
            else:
                # Následující segmenty - přidej crossfade
                if len(concatenated[-1]) >= crossfade_samples and len(segment) >= crossfade_samples:
                    # Crossfade: fade out posledního segmentu, fade in nového
                    last_segment = concatenated[-1]
                    fade_out = last_segment[-crossfade_samples:]
                    fade_in = segment[:crossfade_samples]

                    # Lineární crossfade
                    fade_out_weights = np.linspace(1.0, 0.0, crossfade_samples)
                    fade_in_weights = np.linspace(0.0, 1.0, crossfade_samples)

                    # Kombinuj fade out a fade in
                    crossfade_audio = fade_out * fade_out_weights + fade_in * fade_in_weights

                    # Nahraď konec posledního segmentu crossfade částí
                    concatenated[-1] = np.concatenate([
                        last_segment[:-crossfade_samples],
                        crossfade_audio
                    ])

                    # Přidej zbytek nového segmentu
                    if len(segment) > crossfade_samples:
                        concatenated.append(segment[crossfade_samples:])
                else:
                    # Pokud segmenty jsou příliš krátké, prostě je spoj
                    concatenated.append(segment)

                # Přidej pauzu pokud je zadána
                if pause_samples > 0:
                    pause = np.zeros(pause_samples)
                    concatenated.append(pause)

        # Spoj všechny části
        final_audio = np.concatenate(concatenated)

        # Uložení
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        sf.write(output_path, final_audio, sample_rate)

        return output_path

    @staticmethod
    def concatenate_with_smoothing(
        audio_files: List[str],
        output_path: str,
        smoothing_window_ms: int = 100
    ) -> str:
        """
        Spojí audio soubory s jemným vyhlazením přechodů

        Args:
            audio_files: Seznam cest k audio souborům
            output_path: Cesta k výstupnímu souboru
            smoothing_window_ms: Délka vyhlazovacího okna v milisekundách

        Returns:
            Cesta k výstupnímu souboru
        """
        return AudioConcatenator.concatenate_audio(
            audio_files,
            output_path,
            crossfade_ms=smoothing_window_ms,
            pause_ms=0
        )

