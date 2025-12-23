"""
Voice Activity Detection (VAD) modul pro detekci řeči vs. ticho
"""
import numpy as np
import librosa
from typing import List, Tuple, Optional
from backend.config import ENABLE_VAD, VAD_AGGRESSIVENESS, OUTPUT_SAMPLE_RATE

try:
    import webrtcvad
    WEBRTC_VAD_AVAILABLE = True
except ImportError:
    WEBRTC_VAD_AVAILABLE = False
    print("Warning: webrtcvad není dostupný, použije se librosa-based VAD")


class VADProcessor:
    """Třída pro detekci hlasové aktivity"""

    def __init__(self):
        self.vad = None
        if WEBRTC_VAD_AVAILABLE and ENABLE_VAD:
            try:
                # webrtcvad vyžaduje 16kHz, 16-bit, mono audio
                self.vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
            except Exception as e:
                print(f"Warning: Failed to initialize webrtcvad: {e}")

    def detect_voice_segments(
        self,
        audio: np.ndarray,
        sample_rate: int = OUTPUT_SAMPLE_RATE,
        frame_duration_ms: int = 30
    ) -> List[Tuple[float, float]]:
        """
        Detekuje segmenty s řečí v audio

        Args:
            audio: Audio data
            sample_rate: Sample rate audio
            frame_duration_ms: Délka frame v milisekundách

        Returns:
            Seznam tuplů (start_time, end_time) v sekundách
        """
        if not ENABLE_VAD:
            # Pokud je VAD vypnutý, vrať celý audio jako jeden segment
            duration = len(audio) / sample_rate
            return [(0.0, duration)]

        if self.vad and WEBRTC_VAD_AVAILABLE:
            return self._detect_with_webrtc(audio, sample_rate, frame_duration_ms)
        else:
            return self._detect_with_librosa(audio, sample_rate)

    def _detect_with_webrtc(
        self,
        audio: np.ndarray,
        sample_rate: int,
        frame_duration_ms: int
    ) -> List[Tuple[float, float]]:
        """
        Detekce pomocí webrtcvad (přesnější, ale vyžaduje 16kHz)
        """
        # Převod na 16kHz pokud je potřeba
        if sample_rate != 16000:
            audio_16k = librosa.resample(audio, orig_sr=sample_rate, target_sr=16000)
        else:
            audio_16k = audio

        # Převod na 16-bit integer
        audio_int16 = (audio_16k * 32767).astype(np.int16)

        # Frame size v samples (webrtcvad vyžaduje: 10, 20, nebo 30 ms)
        frame_size = int(16000 * frame_duration_ms / 1000)
        num_frames = len(audio_int16) // frame_size

        voice_segments = []
        in_voice = False
        segment_start = 0.0

        for i in range(num_frames):
            frame = audio_int16[i * frame_size:(i + 1) * frame_size]
            is_speech = self.vad.is_speech(frame.tobytes(), 16000)

            frame_time = i * frame_duration_ms / 1000.0

            if is_speech and not in_voice:
                # Začátek řeči
                in_voice = True
                segment_start = frame_time
            elif not is_speech and in_voice:
                # Konec řeči
                in_voice = False
                voice_segments.append((segment_start, frame_time))

        # Pokud jsme stále v řeči na konci
        if in_voice:
            duration = len(audio_16k) / 16000.0
            voice_segments.append((segment_start, duration))

        return voice_segments

    def _detect_with_librosa(
        self,
        audio: np.ndarray,
        sample_rate: int
    ) -> List[Tuple[float, float]]:
        """
        Detekce pomocí librosa (energie a spektrální analýza)
        """
        # Výpočet energie v oknech
        frame_length = int(0.025 * sample_rate)  # 25ms frames
        hop_length = int(0.010 * sample_rate)  # 10ms hop

        # RMS energie
        rms = librosa.feature.rms(y=audio, frame_length=frame_length, hop_length=hop_length)[0]

        # Threshold: 10% maximální energie
        threshold = np.max(rms) * 0.1

        # Detekce hlasové aktivity
        voice_frames = rms > threshold

        # Najdi souvislé segmenty
        voice_segments = []
        in_voice = False
        segment_start = 0.0

        for i, is_voice in enumerate(voice_frames):
            frame_time = i * hop_length / sample_rate

            if is_voice and not in_voice:
                # Začátek řeči
                in_voice = True
                segment_start = frame_time
            elif not is_voice and in_voice:
                # Konec řeči
                in_voice = False
                voice_segments.append((segment_start, frame_time))

        # Pokud jsme stále v řeči na konci
        if in_voice:
            duration = len(audio) / sample_rate
            voice_segments.append((segment_start, duration))

        return voice_segments

    def trim_silence_vad(
        self,
        audio: np.ndarray,
        sample_rate: int = OUTPUT_SAMPLE_RATE,
        padding_ms: float = 100.0
    ) -> np.ndarray:
        """
        Ořízne ticho na začátku a konci pomocí VAD

        Args:
            audio: Audio data
            sample_rate: Sample rate
            padding_ms: Padding v milisekundách před/po řeči

        Returns:
            Oříznuté audio
        """
        if not ENABLE_VAD:
            # Fallback na standardní trim
            audio, _ = librosa.effects.trim(audio, top_db=25)
            return audio

        segments = self.detect_voice_segments(audio, sample_rate)

        if not segments:
            # Pokud není detekována žádná řeč, vrať prázdné audio
            return np.array([])

        # Najdi první a poslední segment
        first_start = segments[0][0]
        last_end = segments[-1][1]

        # Přidej padding
        padding_samples = int(padding_ms * sample_rate / 1000.0)
        start_sample = max(0, int(first_start * sample_rate) - padding_samples)
        end_sample = min(len(audio), int(last_end * sample_rate) + padding_samples)

        return audio[start_sample:end_sample]

    def get_voice_ratio(
        self,
        audio: np.ndarray,
        sample_rate: int = OUTPUT_SAMPLE_RATE
    ) -> float:
        """
        Vrátí poměr času s řečí k celkové délce

        Args:
            audio: Audio data
            sample_rate: Sample rate

        Returns:
            Poměr (0.0 - 1.0)
        """
        segments = self.detect_voice_segments(audio, sample_rate)
        total_duration = len(audio) / sample_rate

        if total_duration == 0:
            return 0.0

        voice_duration = sum(end - start for start, end in segments)
        return voice_duration / total_duration


# Globální instance
_vad_processor = None


def get_vad_processor() -> VADProcessor:
    """Vrátí globální instanci VAD procesoru"""
    global _vad_processor
    if _vad_processor is None:
        _vad_processor = VADProcessor()
    return _vad_processor











