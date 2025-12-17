"""
Audio processing utilities pro XTTS-v2 Demo
"""
import os
import subprocess
import librosa
import soundfile as sf
import numpy as np
from pathlib import Path
from typing import Tuple, Optional
from backend.config import (
    TARGET_SAMPLE_RATE,
    TARGET_CHANNELS,
    MIN_VOICE_DURATION,
    SUPPORTED_AUDIO_FORMATS,
    UPLOADS_DIR
)


class AudioProcessor:
    """Třída pro zpracování audio souborů"""

    @staticmethod
    def _check_ffmpeg() -> bool:
        """Zkontroluje, jestli je FFmpeg dostupný"""
        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    @staticmethod
    def _convert_with_ffmpeg(
        input_path: str,
        output_path: str,
        target_sr: int = TARGET_SAMPLE_RATE,
        target_channels: int = TARGET_CHANNELS
    ) -> Tuple[bool, Optional[str]]:
        """
        Konvertuje audio pomocí FFmpeg (fallback pokud librosa selže)

        Args:
            input_path: Cesta k vstupnímu souboru
            output_path: Cesta k výstupnímu souboru
            target_sr: Cílová sample rate
            target_channels: Počet kanálů (1=mono, 2=stereo)

        Returns:
            (success, error_message)
        """
        try:
            # Zajištění výstupního adresáře
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            # FFmpeg příkaz
            cmd = [
                "ffmpeg",
                "-i", str(input_path),
                "-ar", str(target_sr),
                "-ac", str(target_channels),
                "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",  # Loudness normalization
                "-y",  # Přepsat výstupní soubor
                str(output_path)
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )

            return True, None

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode('utf-8', errors='ignore')
            return False, f"FFmpeg error: {error_msg[:200]}"
        except Exception as e:
            return False, f"FFmpeg conversion failed: {str(e)}"

    @staticmethod
    def validate_audio_file(file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Validuje audio soubor

        Returns:
            (is_valid, error_message)
        """
        path = Path(file_path)

        # Kontrola existence
        if not path.exists():
            return False, "Soubor neexistuje"

        # Kontrola formátu
        if path.suffix.lower() not in SUPPORTED_AUDIO_FORMATS:
            return False, f"Nepodporovaný formát. Podporované: {', '.join(SUPPORTED_AUDIO_FORMATS)}"

        # Kontrola délky
        try:
            duration = librosa.get_duration(path=file_path)
            if duration < MIN_VOICE_DURATION:
                return False, f"Audio je příliš krátké. Minimálně {MIN_VOICE_DURATION} sekund."
        except Exception as e:
            return False, f"Chyba při čtení audio: {str(e)}"

        return True, None

    @staticmethod
    def convert_audio(
        input_path: str,
        output_path: str,
        target_sr: int = TARGET_SAMPLE_RATE,
        target_channels: int = TARGET_CHANNELS,
        apply_advanced_processing: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Konvertuje audio na požadovaný formát s pokročilým zpracováním

        Args:
            input_path: Cesta k vstupnímu souboru
            output_path: Cesta k výstupnímu souboru
            target_sr: Cílová sample rate
            target_channels: Počet kanálů (1=mono, 2=stereo)
            apply_advanced_processing: Aplikovat pokročilé post-processing

        Returns:
            (success, error_message)
        """
        # Zajištění výstupního adresáře
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Zkus nejprve librosa
        try:
            # Načtení audio
            audio, sr = librosa.load(
                input_path,
                sr=target_sr,
                mono=(target_channels == 1)
            )

            # Ořez ticha na začátku a konci
            audio, _ = librosa.effects.trim(audio, top_db=20)

            # Pokročilé post-processing
            if apply_advanced_processing:
                # High-pass filter (odfiltruje hluboké frekvence pod 80 Hz)
                # Použijeme preemphasis jako aproximaci
                audio = librosa.effects.preemphasis(audio, coef=0.97)

                # Jednoduchá redukce šumu (spectral gating)
                stft = librosa.stft(audio)
                magnitude = np.abs(stft)
                # Threshold na 10% maximální hodnoty
                threshold = np.max(magnitude) * 0.1
                mask = magnitude > threshold
                stft_clean = stft * mask
                audio = librosa.istft(stft_clean)

            # Normalizace hlasitosti
            audio = librosa.util.normalize(audio)

            # Uložení
            sf.write(output_path, audio, target_sr)

            return True, None

        except Exception as e:
            # Fallback na FFmpeg pokud librosa selže
            if AudioProcessor._check_ffmpeg():
                print(f"⚠️  Librosa selhalo, zkouším FFmpeg fallback: {str(e)[:100]}")
                return AudioProcessor._convert_with_ffmpeg(
                    input_path,
                    output_path,
                    target_sr,
                    target_channels
                )
            else:
                return False, f"Chyba při konverzi audio: {str(e)} (FFmpeg není dostupný)"

    @staticmethod
    def process_uploaded_file(
        uploaded_file_path: str,
        output_filename: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Zpracuje nahraný audio soubor

        Args:
            uploaded_file_path: Cesta k nahranému souboru
            output_filename: Volitelný název výstupního souboru

        Returns:
            (processed_file_path, error_message)
        """
        # Validace
        is_valid, error = AudioProcessor.validate_audio_file(uploaded_file_path)
        if not is_valid:
            return None, error

        # Vytvoření výstupní cesty
        if output_filename is None:
            output_filename = f"processed_{Path(uploaded_file_path).stem}.wav"

        output_path = UPLOADS_DIR / output_filename

        # Konverze (s pokročilým zpracováním pro uploady)
        success, error = AudioProcessor.convert_audio(
            uploaded_file_path,
            str(output_path),
            apply_advanced_processing=True  # Použij pokročilé zpracování pro uploady
        )

        if not success:
            return None, error

        return str(output_path), None

    @staticmethod
    def get_audio_duration(file_path: str) -> float:
        """Vrátí délku audio souboru v sekundách"""
        try:
            return librosa.get_duration(path=file_path)
        except Exception as e:
            raise ValueError(f"Chyba při čtení délky audio: {str(e)}")

    @staticmethod
    def save_recorded_audio(
        audio_data: bytes,
        filename: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Uloží nahrané audio z mikrofonu

        Args:
            audio_data: Raw audio data (WAV blob)
            filename: Název souboru

        Returns:
            (saved_file_path, error_message)
        """
        try:
            # Uložení dočasného souboru
            temp_path = UPLOADS_DIR / f"temp_{filename}"
            with open(temp_path, "wb") as f:
                f.write(audio_data)

            # Zpracování
            return AudioProcessor.process_uploaded_file(
                str(temp_path),
                filename
            )

        except Exception as e:
            return None, f"Chyba při ukládání nahraného audio: {str(e)}"

    @staticmethod
    def enhance_voice_sample(
        input_path: str,
        output_path: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Vylepší kvalitu vstupního vzorku pro voice cloning

        Args:
            input_path: Cesta k vstupnímu audio souboru
            output_path: Cesta k výstupnímu audio souboru

        Returns:
            (success, error_message)
        """
        try:
            from backend.audio_enhancer import AudioEnhancer
            import librosa
            import soundfile as sf

            # Načtení audio
            audio, sr = librosa.load(input_path, sr=TARGET_SAMPLE_RATE, mono=True)

            # 1. Ořez ticha s jemnějším threshold
            audio, _ = librosa.effects.trim(audio, top_db=30)

            # 2. De-essing (redukce sykavek) - high-frequency de-emphasis
            try:
                from scipy import signal
                # Band-stop filter pro 4-8 kHz (sykavky)
                sos = signal.butter(4, [4000, 8000], btype='bandstop', fs=sr, output='sos')
                audio = signal.sosfiltfilt(sos, audio)
            except ImportError:
                print("Warning: scipy není dostupný, de-essing přeskočen")
            except Exception as e:
                print(f"Warning: De-essing failed: {e}")

            # 3. Pokročilá redukce šumu
            audio = AudioEnhancer.reduce_noise_advanced(audio, sr)

            # 4. EQ korekce pro vyrovnání frekvenčního spektra
            audio = AudioEnhancer.apply_eq(audio, sr)

            # 5. Vylepšená normalizace s kompresí
            audio = AudioEnhancer.compress_dynamic_range(audio, ratio=2.5)
            audio = AudioEnhancer.normalize_audio(audio)

            # 6. Fade in/out
            audio = AudioEnhancer.apply_fade(audio, sr, fade_ms=30)

            # Uložení
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            sf.write(output_path, audio, sr)

            return True, None

        except Exception as e:
            return False, f"Chyba při vylepšování vzorku: {str(e)}"

