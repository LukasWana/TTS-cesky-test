"""
Audio enhancement modul pro post-processing generovaného audio
"""
import numpy as np
import librosa
import soundfile as sf
from pathlib import Path
from typing import Optional
from backend.config import OUTPUT_SAMPLE_RATE

try:
    from scipy import signal
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("Warning: scipy není dostupný, některé funkce budou omezené")


class AudioEnhancer:
    """Třída pro vylepšení kvality generovaného audio"""

    @staticmethod
    def enhance_output(
        audio_path: str,
        preset: str = "natural",
        enable_eq: Optional[bool] = None,
        enable_noise_reduction: Optional[bool] = None,
        enable_compression: Optional[bool] = None
    ) -> str:
        """
        Hlavní metoda pro post-processing audio

        Args:
            audio_path: Cesta k audio souboru
            preset: Preset kvality (high_quality, natural, fast)
            enable_eq: Zapnout EQ korekci (None = použít preset)
            enable_noise_reduction: Zapnout noise reduction (None = použít preset)
            enable_compression: Zapnout kompresi (None = použít preset)

        Returns:
            Cesta k vylepšenému audio souboru
        """
        # Načtení audio
        audio, sr = librosa.load(audio_path, sr=OUTPUT_SAMPLE_RATE)

        # Určení nastavení podle presetu
        try:
            from backend.config import QUALITY_PRESETS
            preset_config = QUALITY_PRESETS.get(preset, QUALITY_PRESETS["natural"])
            enhancement_config = preset_config.get("enhancement", {})
        except ImportError:
            # Fallback pokud import selže
            from backend import config
            preset_config = config.QUALITY_PRESETS.get(preset, config.QUALITY_PRESETS["natural"])
            enhancement_config = preset_config.get("enhancement", {})

        # Použití preset hodnot nebo explicitních parametrů
        # EQ a komprese jsou vypnuté pro eliminaci preboostu a zachování přirozené dynamiky
        use_eq = False  # Vypnuto - eliminace preboostu
        use_noise_reduction = enable_noise_reduction if enable_noise_reduction is not None else enhancement_config.get("enable_noise_reduction", False)
        use_compression = False  # Vypnuto - zachování přirozené dynamiky

        # 1. Ořez ticha (s VAD pokud je dostupné)
        try:
            from backend.vad_processor import get_vad_processor
            from backend.config import ENABLE_VAD
            if ENABLE_VAD:
                vad_processor = get_vad_processor()
                audio = vad_processor.trim_silence_vad(audio, sr)
            else:
                audio = AudioEnhancer.trim_silence(audio, sr, top_db=25)
        except Exception as e:
            print(f"Warning: VAD trim failed, using standard trim: {e}")
            audio = AudioEnhancer.trim_silence(audio, sr, top_db=25)

        # 2. Pokročilá redukce šumu (pokud zapnuto)
        if use_noise_reduction:
            audio = AudioEnhancer.reduce_noise_advanced(audio, sr)

        # 3. EQ korekce (pokud zapnuto)
        if use_eq:
            audio = AudioEnhancer.apply_eq(audio, sr)

        # 4. Komprese dynamiky (pokud zapnuto) - jemná komprese pro transienty
        if use_compression:
            audio = AudioEnhancer.compress_dynamic_range(audio, ratio=2.5)

        # 5. Fade in/out
        audio = AudioEnhancer.apply_fade(audio, sr, fade_ms=50)

        # 6. Finální normalizace podle best practices pro hlas
        # Peak: -3 dB, RMS: -16 až -20 dB (výchozí -18 dB)
        audio = AudioEnhancer.normalize_audio(audio, peak_target_db=-3.0, rms_target_db=-18.0)

        # Uložení zpět do souboru
        sf.write(audio_path, audio, sr)

        return audio_path

    @staticmethod
    def trim_silence(audio: np.ndarray, sr: int, top_db: int = 25) -> np.ndarray:
        """
        Ořez ticha na začátku a konci s jemnějším threshold

        Args:
            audio: Audio data
            sr: Sample rate
            top_db: Threshold v dB (vyšší = jemnější ořez)

        Returns:
            Oříznuté audio
        """
        audio, _ = librosa.effects.trim(audio, top_db=top_db)
        return audio

    @staticmethod
    def apply_fade(audio: np.ndarray, sr: int, fade_ms: int = 50) -> np.ndarray:
        """
        Fade in/out pro přirozený začátek a konec

        Args:
            audio: Audio data
            sr: Sample rate
            fade_ms: Délka fade v milisekundách

        Returns:
            Audio s fade in/out
        """
        fade_samples = int(fade_ms * sr / 1000)

        if len(audio) < fade_samples * 2:
            # Pokud je audio příliš krátké, použij kratší fade
            fade_samples = len(audio) // 4

        # Fade in
        audio[:fade_samples] *= np.linspace(0, 1, fade_samples)

        # Fade out
        audio[-fade_samples:] *= np.linspace(1, 0, fade_samples)

        return audio

    @staticmethod
    def normalize_audio(audio: np.ndarray, peak_target_db: float = -3.0, rms_target_db: float = -18.0) -> np.ndarray:
        """
        Normalizace audio podle best practices pro hlas:
        - Peak: -3 dB (ne 0 dB!)
        - RMS: -16 až -20 dB (ne -6 dB!)

        Args:
            audio: Audio data
            peak_target_db: Cílová peak úroveň v dB (výchozí: -3.0)
            rms_target_db: Cílová RMS úroveň v dB (výchozí: -18.0, rozsah -20 až -16)

        Returns:
            Normalizované audio
        """
        if len(audio) == 0:
            return audio

        # 1. RMS normalizace - POUZE snižovat, neboostovat
        current_rms = np.sqrt(np.mean(audio ** 2))
        if current_rms > 0:
            rms_target_linear = 10 ** (rms_target_db / 20)
            # Pouze snižovat pokud je RMS vyšší než cíl, neboostovat pokud je nižší
            if current_rms > rms_target_linear:
                rms_gain = rms_target_linear / current_rms
                audio = audio * rms_gain
            # Pokud je RMS nižší než cíl, necháme ho být (neboostujeme)

        # 2. Peak normalizace na -3 dB - POUZE snižovat, nezvětšovat
        peak_target_linear = 10 ** (peak_target_db / 20)  # -3 dB = 0.7079
        current_peak = np.max(np.abs(audio))
        if current_peak > peak_target_linear:
            # Pokud je peak vyšší než cíl, snížíme
            peak_gain = peak_target_linear / current_peak
            audio = audio * peak_gain
        # Pokud je peak nižší než cíl, necháme ho být (neboostujeme)

        # 3. Soft limiter na -0.1 dB jako ochrana proti popům
        limiter_threshold = 10 ** (-0.1 / 20)  # -0.1 dB = 0.9886
        audio = np.clip(audio, -limiter_threshold, limiter_threshold)

        return audio

    @staticmethod
    def apply_eq(audio: np.ndarray, sr: int) -> np.ndarray:
        """
        EQ korekce pro zvýraznění frekvencí řeči (1-4 kHz)

        Args:
            audio: Audio data
            sr: Sample rate

        Returns:
            Audio s EQ korekcí
        """
        if not SCIPY_AVAILABLE:
            return audio

        try:
            # Boost středních frekvencí (1-4 kHz) - hlavní frekvence řeči
            # Vytvoření bandpass filtru
            sos = signal.butter(4, [1000, 4000], btype='band', fs=sr, output='sos')
            boosted = signal.sosfiltfilt(sos, audio)

            # Jemné zvýraznění (sníženo z 3% na 1.5% pro eliminaci preboostu)
            audio = audio + 0.015 * boosted

            # NENORMALIZUJEME - normalizace bude až na konci řetězce

        except Exception as e:
            print(f"Warning: EQ correction failed: {e}, continuing without EQ")

        return audio

    @staticmethod
    def reduce_noise_advanced(audio: np.ndarray, sr: int) -> np.ndarray:
        """
        Pokročilá redukce šumu pomocí spektrální subtrakce

        Args:
            audio: Audio data
            sr: Sample rate

        Returns:
            Audio s redukovaným šumem
        """
        try:
            # STFT transformace
            stft = librosa.stft(audio)
            magnitude = np.abs(stft)
            phase = np.angle(stft)

            # Odhad šumu z tichých částí (10. percentil)
            noise_floor = np.percentile(magnitude, 10)

            # Spektrální subtrakce (zmírněno pro lepší kvalitu)
            alpha = 1.5  # Over-subtraction factor (sníženo z 2.0 na 1.5)
            beta = 0.01  # Spectral floor

            magnitude_clean = magnitude - alpha * noise_floor
            magnitude_clean = np.maximum(magnitude_clean, beta * magnitude)

            # Rekonstrukce signálu
            stft_clean = magnitude_clean * np.exp(1j * phase)
            audio_clean = librosa.istft(stft_clean)

            return audio_clean

        except Exception as e:
            print(f"Warning: Advanced noise reduction failed: {e}, continuing without noise reduction")
            return audio

    @staticmethod
    def compress_dynamic_range(audio: np.ndarray, ratio: float = 2.5, threshold: float = -12.0) -> np.ndarray:
        """
        Jemná komprese dynamiky pro zvládnutí transientů (zmírněno pro lepší kvalitu)

        Args:
            audio: Audio data
            ratio: Kompresní poměr (sníženo z 3.0 na 2.5 pro jemnější kompresi)
            threshold: Threshold v dB

        Returns:
            Komprimované audio (BEZ normalizace - normalizace bude až na konci)
        """
        try:
            # Převod na dB
            audio_db = 20 * np.log10(np.abs(audio) + 1e-10)

            # Aplikace komprese nad threshold
            threshold_linear = 10 ** (threshold / 20)
            compressed_db = audio_db.copy()

            # Komprese pouze nad threshold
            mask = audio_db > threshold
            excess = audio_db[mask] - threshold
            compressed_db[mask] = threshold + excess / ratio

            # Převod zpět
            compressed_linear = 10 ** (compressed_db / 20)
            compressed_audio = np.sign(audio) * compressed_linear

            # NENORMALIZUJEME - normalizace bude až na konci řetězce
            return compressed_audio

        except Exception as e:
            print(f"Warning: Dynamic compression failed: {e}, continuing without compression")
            return audio

