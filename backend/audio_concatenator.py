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

            # Použij VAD pro přesnější trimování (odstraní artefakty na konci)
            try:
                from backend.vad_processor import get_vad_processor
                from backend.config import ENABLE_VAD

                if ENABLE_VAD:
                    vad_processor = get_vad_processor()
                    # VAD trim s malým paddingem (30ms) pro zachování přirozených konců
                    audio_trimmed = vad_processor.trim_silence_vad(
                        audio,
                        sample_rate=sample_rate,
                        padding_ms=30.0
                    )
                    if audio_trimmed is not None and len(audio_trimmed) > 0:
                        audio = audio_trimmed
                else:
                    # Fallback na librosa trim s vyšším threshold
                    audio_trimmed, _ = librosa.effects.trim(audio, top_db=35, frame_length=2048, hop_length=512)
                    if len(audio_trimmed) > 0:
                        audio = audio_trimmed
            except Exception as e:
                # Pokud VAD selže, použij librosa trim
                try:
                    audio_trimmed, _ = librosa.effects.trim(audio, top_db=35, frame_length=2048, hop_length=512)
                    if len(audio_trimmed) > 0:
                        audio = audio_trimmed
                except Exception:
                    # Pokud i to selže, použij původní audio
                    pass

            # Kontrola délky - pro velmi dlouhé segmenty s nízkou energií (pravděpodobně ticho)
            # omezíme maximální délku na 10 sekund
            audio_duration = len(audio) / sample_rate
            if audio_duration > 10.0:
                # Zkontroluj RMS energii - pokud je velmi nízká, je to pravděpodobně ticho
                rms = np.sqrt(np.mean(audio**2))
                if rms < 0.01:  # Velmi nízká energie = ticho
                    print(f"⚠️ Segment má velmi nízkou energii ({rms:.4f}) a délku {audio_duration:.1f}s, ořezávám na 10s")
                    max_samples = int(10.0 * sample_rate)
                    audio = audio[:max_samples]
                elif audio_duration > 30.0:
                    # Pro segmenty delší než 30s použij agresivnější trim
                    print(f"⚠️ Segment je velmi dlouhý ({audio_duration:.1f}s), aplikuji agresivnější trim")
                    try:
                        from backend.vad_processor import get_vad_processor
                        from backend.config import ENABLE_VAD
                        if ENABLE_VAD:
                            vad_processor = get_vad_processor()
                            audio_trimmed = vad_processor.trim_silence_vad(
                                audio,
                                sample_rate=sample_rate,
                                padding_ms=50.0
                            )
                            if audio_trimmed is not None and len(audio_trimmed) > 0:
                                audio = audio_trimmed
                    except Exception:
                        # Fallback: agresivnější librosa trim
                        audio, _ = librosa.effects.trim(audio, top_db=40, frame_length=2048, hop_length=512)

            # Přidej jemný fade out na konec segmentu (odstraní artefakty)
            fade_out_samples = int(0.01 * sample_rate)  # 10ms fade out
            if len(audio) > fade_out_samples:
                fade_out = np.linspace(1.0, 0.0, fade_out_samples)
                audio[-fade_out_samples:] *= fade_out

            audio_segments.append(audio)
            if sr != sample_rate:
                print(f"Warning: Sample rate mismatch: {sr} vs {sample_rate}")

        # Normalizace hlasitosti všech segmentů před spojením (aby měly podobnou úroveň)
        # Použijeme RMS normalizaci pro konzistentní hlasitost
        # POZOR: Normalizujeme pouze střední část segmentu (bez konců), aby se nezvýšily artefakty
        target_rms = 0.1  # Cílová RMS úroveň (10% peak)
        for i, segment in enumerate(audio_segments):
            if len(segment) > 0:
                # Vypočítej RMS pouze ze střední části (bez prvních a posledních 10%)
                # to pomůže ignorovat artefakty na koncích
                start_idx = len(segment) // 10
                end_idx = len(segment) - len(segment) // 10
                if end_idx > start_idx:
                    middle_part = segment[start_idx:end_idx]
                    current_rms = np.sqrt(np.mean(middle_part**2))
                else:
                    current_rms = np.sqrt(np.mean(segment**2))

                if current_rms > 0:
                    # Normalizuj na cílovou RMS úroveň
                    gain = target_rms / current_rms
                    # Omez gain, aby se nepřehnal (max 2x - konzervativnější)
                    gain = min(gain, 2.0)
                    audio_segments[i] = segment * gain

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

                    # Zkontroluj, zda fade_out a fade_in neobsahují příliš mnoho šumu/artefaktů
                    # Pokud ano, použijeme kratší crossfade nebo přidáme malou pauzu
                    fade_out_rms = np.sqrt(np.mean(fade_out**2))
                    fade_in_rms = np.sqrt(np.mean(fade_in**2))

                    # Pokud je RMS příliš nízké (ticho) nebo příliš vysoké (artefakty), použij kratší crossfade
                    if fade_out_rms < 0.01 or fade_out_rms > 0.5 or fade_in_rms < 0.01 or fade_in_rms > 0.5:
                        # Použij kratší crossfade (50% původní délky)
                        short_crossfade = crossfade_samples // 2
                        if len(concatenated[-1]) >= short_crossfade and len(segment) >= short_crossfade:
                            fade_out = last_segment[-short_crossfade:]
                            fade_in = segment[:short_crossfade]
                            fade_out_weights = np.cos(np.linspace(0, np.pi/2, short_crossfade))
                            fade_in_weights = np.cos(np.linspace(np.pi/2, 0, short_crossfade))
                            crossfade_audio = fade_out * fade_out_weights + fade_in * fade_in_weights
                            concatenated[-1] = np.concatenate([
                                last_segment[:-short_crossfade],
                                crossfade_audio
                            ])
                            if len(segment) > short_crossfade:
                                concatenated.append(segment[short_crossfade:])
                        else:
                            # Pokud je i to příliš krátké, prostě je spoj
                            concatenated.append(segment)
                    else:
                        # Normální crossfade
                        # Cosine crossfade (hladší než lineární)
                        fade_out_weights = np.cos(np.linspace(0, np.pi/2, crossfade_samples))
                        fade_in_weights = np.cos(np.linspace(np.pi/2, 0, crossfade_samples))

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

        # Finální trim na konci (odstraní případné artefakty na konci celého výstupu)
        try:
            from backend.vad_processor import get_vad_processor
            from backend.config import ENABLE_VAD

            if ENABLE_VAD:
                vad_processor = get_vad_processor()
                final_trimmed = vad_processor.trim_silence_vad(
                    final_audio,
                    sample_rate=sample_rate,
                    padding_ms=50.0  # Větší padding pro finální výstup
                )
                if final_trimmed is not None and len(final_trimmed) > 0:
                    final_audio = final_trimmed
            else:
                # Fallback na librosa trim
                final_audio, _ = librosa.effects.trim(final_audio, top_db=30, frame_length=2048, hop_length=512)
        except Exception:
            # Pokud trim selže, použij původní audio
            pass

        # Finální fade out (jemný, 20ms) pro plynulý konec
        fade_out_samples = int(0.02 * sample_rate)  # 20ms fade out
        if len(final_audio) > fade_out_samples:
            fade_out = np.linspace(1.0, 0.0, fade_out_samples)
            final_audio[-fade_out_samples:] *= fade_out

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








