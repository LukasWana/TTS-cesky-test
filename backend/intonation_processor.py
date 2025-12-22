"""
Intonation Processing modul pro aplikaci intonačních kontur na audio
"""
import numpy as np
from typing import List, Tuple, Optional
import warnings

# Potlačení warningů z librosa
warnings.filterwarnings("ignore", category=UserWarning)

try:
    import librosa
    LIBROSA_AVAILABLE = True

    # Workaround (Windows/librosa/numba):
    # Na některých sestavách padá librosa phase vocoder na numba ufunc `_phasor_angles`
    # ("did not contain a loop with signature..."). Přepíšeme na čistě numpy implementaci.
    try:
        import numpy as _np
        import librosa.util.utils as _luu

        def _phasor_angles_numpy(x):
            return _np.cos(x) + 1j * _np.sin(x)

        _luu._phasor_angles = _phasor_angles_numpy  # type: ignore[attr-defined]
    except Exception:
        pass
except ImportError:
    LIBROSA_AVAILABLE = False
    print("Warning: librosa není dostupný, intonační post-processing nebude fungovat")

try:
    from scipy import signal
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


class IntonationProcessor:
    """Post-processing pro aplikaci intonačních kontur na audio"""

    # Výchozí intonační profily
    INTONATION_PROFILES = {
        'FALL': [
            (0.0, 0.0),      # Začátek: žádná změna
            (0.5, 0.0),      # První polovina: žádná změna
            (0.7, -0.4),     # Začátek poklesu: mírný pokles
            (0.85, -1.0),    # Střed poklesu: střední pokles
            (1.0, -1.8)      # Konec: přirozený pokles o 1.8 semitonu (sníženo pro konzistentní barvu hlasu)
        ],
        'RISE': [
            (0.0, 0.0),      # Začátek: žádná změna
            (0.6, 0.0),      # Většina věty: žádná změna
            (0.8, +1.0),     # Začátek vzestupu: mírný vzestup
            (1.0, +3.5)      # Konec: výrazný vzestup o 3.5 semitonu
        ],
        'HALF_FALL': [
            (0.0, 0.0),      # Začátek: žádná změna
            (0.7, 0.0),      # Většina věty: žádná změna
            (1.0, -1.5)      # Konec: mírný pokles o 1.5 semitonu
        ],
        'WAVE': [
            (0.0, 0.0),      # Začátek
            (0.25, +1.0),    # První vrchol
            (0.5, -1.0),     # První údolí
            (0.75, +1.0),    # Druhý vrchol
            (1.0, 0.0)       # Konec
        ],
        'FLAT': [
            (0.0, 0.0),      # Plochá intonace - žádná změna
            (1.0, 0.0)
        ],
        'NEUTRAL': [
            (0.0, 0.0),
            (1.0, 0.0)
        ]
    }

    @staticmethod
    def _naive_pitch_shift_resample(segment: np.ndarray, n_steps: float) -> np.ndarray:
        """
        Nouzový "pitch shift" bez librosa/phase vocoderu.

        Pokud librosa.effects.pitch_shift selže (na Windows se to může stát kvůli numba/_phasor_angles),
        použijeme jednoduchý resampling/interpolaci. Změní to pitch i timing, ale pro KONCOVOU intonaci
        je to lepší než žádný efekt.
        """
        if segment is None or len(segment) < 2:
            return segment
        if abs(n_steps) < 0.05:
            return segment

        # Pitch multiplier (librosa konvence): +12 => 2x frekvence, -12 => 0.5x frekvence
        m = float(2.0 ** (n_steps / 12.0))
        if not np.isfinite(m) or m <= 0:
            return segment

        orig_len = int(len(segment))
        # Resampling "rychlostí" m: pro m<1 (pitch down) se délka zvětší
        new_len = int(max(2, round(orig_len / m)))

        # Bezpečnostní limity (aby to neustřelilo)
        new_len = min(new_len, orig_len * 4)
        new_len = max(new_len, max(2, orig_len // 4))

        x = np.asarray(segment, dtype=np.float64)
        xp = np.linspace(0.0, 1.0, orig_len, endpoint=False)
        xnew = np.linspace(0.0, 1.0, new_len, endpoint=False)
        y = np.interp(xnew, xp, x)

        # Udrž původní délku; zarovnej na KONEC (aby navazování bylo méně slyšitelné)
        if new_len > orig_len:
            y = y[-orig_len:]
        elif new_len < orig_len:
            pad = np.zeros(orig_len - new_len, dtype=y.dtype)
            y = np.concatenate([pad, y], axis=0)

        try:
            return y.astype(segment.dtype, copy=False)
        except Exception:
            return y

    @staticmethod
    def apply_contour(
        audio: np.ndarray,
        sample_rate: int,
        contour: List[Tuple[float, float]],
        smooth: bool = True
    ) -> np.ndarray:
        """
        Aplikuje intonační konturu na audio pomocí pitch shifting

        Args:
            audio: Audio signál
            sample_rate: Sample rate
            contour: Seznam (čas%, změna_pitch_v_semitonech)
                    např. [(0.0, 0.0), (0.5, +2.0), (1.0, -3.0)]
                    čas je relativní (0.0-1.0), změna v semitonech
            smooth: Použít vyhlazení přechodů (výchozí: True)

        Returns:
            Audio s aplikovanou intonační konturou
        """
        if not LIBROSA_AVAILABLE:
            print("⚠️ Librosa není dostupný, intonační kontura nebude aplikována")
            return audio

        if len(audio) == 0:
            return audio

        # Librosa pitch_shift občas selže pro float32 na některých Windows/Numpy kombinacích.
        # Stabilizace: pracuj ve float64 a případně vrať zpět původní dtype.
        orig_dtype = audio.dtype
        if audio.dtype != np.float64:
            try:
                audio = audio.astype(np.float64, copy=False)
            except Exception:
                audio = np.asarray(audio, dtype=np.float64)

        duration = len(audio) / sample_rate

        # Pokud je kontura prázdná nebo má jen jeden bod, vrať původní audio
        if len(contour) < 2:
            return audio

        # Vytvoř časovou osu pro konturu
        time_points = np.array([t for t, _ in contour])
        pitch_shifts = np.array([p for _, p in contour])

        # Normalizuj časové body na 0-1
        if time_points.max() > 1.0:
            time_points = time_points / time_points.max()

        # Pokud je audio velmi krátké (< 0.1s), použij průměrnou změnu pitch
        if duration < 0.1:
            avg_shift = np.mean(pitch_shifts)
            if abs(avg_shift) < 0.1:
                return audio.astype(orig_dtype, copy=False) if orig_dtype != audio.dtype else audio
            try:
                shifted = librosa.effects.pitch_shift(
                    audio,
                    sr=sample_rate,
                    n_steps=avg_shift
                )
                return shifted.astype(orig_dtype, copy=False) if orig_dtype != shifted.dtype else shifted
            except Exception as e:
                print(f"⚠️ Pitch shifting selhal: {e}")
                # Fallback bez librosa (slyšitelný efekt i při problémech s numba/librosa)
                try:
                    fb = IntonationProcessor._naive_pitch_shift_resample(audio, float(avg_shift))
                    return fb.astype(orig_dtype, copy=False) if orig_dtype != fb.dtype else fb
                except Exception:
                    return audio.astype(orig_dtype, copy=False) if orig_dtype != audio.dtype else audio

        # Pro delší audio: aplikuj konturu po segmentech
        # Rozděl audio na segmenty podle kontury
        num_segments = min(len(contour) - 1, 10)  # Max 10 segmentů pro výkon
        segment_length = len(audio) // num_segments

        result_segments = []

        for i in range(num_segments):
            start_idx = i * segment_length
            end_idx = (i + 1) * segment_length if i < num_segments - 1 else len(audio)
            segment = audio[start_idx:end_idx]

            if len(segment) == 0:
                continue

            # Vypočítej průměrnou změnu pitch pro tento segment
            segment_time = (start_idx + end_idx) / 2 / len(audio)

            # Najdi interpolovanou hodnotu pitch shift
            pitch_shift = np.interp(segment_time, time_points, pitch_shifts)

            # Aplikuj pitch shift pouze pokud je změna významná
            if abs(pitch_shift) > 0.1:
                try:
                    # Viz poznámka výše: pitch_shift je stabilnější na float64
                    if segment.dtype != np.float64:
                        segment = segment.astype(np.float64, copy=False)
                    shifted_segment = librosa.effects.pitch_shift(
                        segment,
                        sr=sample_rate,
                        n_steps=pitch_shift
                    )
                    result_segments.append(shifted_segment)
                except Exception as e:
                    print(f"⚠️ Pitch shifting segmentu {i} selhal: {e}")
                    # Fallback bez librosa (lepší než žádný pitch efekt)
                    try:
                        result_segments.append(IntonationProcessor._naive_pitch_shift_resample(segment, float(pitch_shift)))
                    except Exception:
                        result_segments.append(segment)
            else:
                result_segments.append(segment)

        # Spoj segmenty
        if result_segments:
            result = np.concatenate(result_segments)
            # Vyhlazení přechodů mezi segmenty
            if smooth and len(result) > sample_rate * 0.01:  # Pokud je audio delší než 10ms
                result = IntonationProcessor._smooth_transitions(result, sample_rate)
            return result.astype(orig_dtype, copy=False) if orig_dtype != result.dtype else result

        return audio.astype(orig_dtype, copy=False) if orig_dtype != audio.dtype else audio

    @staticmethod
    def apply_intonation_type(
        audio: np.ndarray,
        sample_rate: int,
        intonation_type: str,
        intensity: float = 1.0
    ) -> np.ndarray:
        """
        Aplikuje typ intonace (fall, rise, flat, wave) na celé audio

        Args:
            audio: Audio signál
            sample_rate: Sample rate
            intonation_type: 'FALL', 'RISE', 'FLAT', 'WAVE', 'HALF_FALL', 'NEUTRAL'
            intensity: Intenzita změny (0.0-2.0, výchozí: 1.0)

        Returns:
            Audio s aplikovanou intonací
        """
        if not LIBROSA_AVAILABLE:
            return audio

        if len(audio) == 0:
            return audio

        # Normalizuj intenzitu
        intensity = max(0.0, min(2.0, intensity))

        # Získej profil intonace
        profile = IntonationProcessor.INTONATION_PROFILES.get(
            intonation_type.upper(),
            IntonationProcessor.INTONATION_PROFILES['NEUTRAL']
        )

        # Aplikuj intenzitu na profil
        contour = [(t, p * intensity) for t, p in profile]

        return IntonationProcessor.apply_contour(audio, sample_rate, contour)

    @staticmethod
    def apply_intonation_to_segment(
        audio: np.ndarray,
        sample_rate: int,
        start_sample: int,
        end_sample: int,
        intonation_type: str,
        intensity: float = 1.0
    ) -> np.ndarray:
        """
        Aplikuje intonaci na konkrétní segment audio

        Args:
            audio: Celé audio signál
            sample_rate: Sample rate
            start_sample: Začátek segmentu (v samples)
            end_sample: Konec segmentu (v samples)
            intonation_type: Typ intonace
            intensity: Intenzita změny

        Returns:
            Audio s aplikovanou intonací na segmentu
        """
        if start_sample >= end_sample or end_sample > len(audio):
            return audio

        # Extrahuj segment
        segment = audio[start_sample:end_sample]

        # Aplikuj intonaci
        modified_segment = IntonationProcessor.apply_intonation_type(
            segment, sample_rate, intonation_type, intensity
        )

        # Vlož zpět do audio s vyhlazením přechodů
        result = audio.copy()

        # Vyhlazení přechodů (crossfade)
        fade_samples = min(int(sample_rate * 0.01), len(modified_segment) // 4)  # 10ms nebo 25% segmentu

        if fade_samples > 0:
            # Fade in
            fade_in = np.linspace(0.0, 1.0, fade_samples)
            modified_segment[:fade_samples] *= fade_in
            # Fade out
            fade_out = np.linspace(1.0, 0.0, fade_samples)
            modified_segment[-fade_samples:] *= fade_out

        result[start_sample:end_sample] = modified_segment

        return result

    @staticmethod
    def _smooth_transitions(audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """
        Vyhladí přechody v audio (odstraní artefakty z pitch shifting)

        Args:
            audio: Audio signál
            sample_rate: Sample rate

        Returns:
            Vyhlazené audio
        """
        if not SCIPY_AVAILABLE or len(audio) < sample_rate * 0.01:
            return audio

        try:
            # Jednoduchý low-pass filter pro vyhlazení
            # Cutoff frequency: 0.1 * Nyquist (velmi jemné vyhlazení)
            nyquist = sample_rate / 2
            cutoff = 0.1 * nyquist

            # Butterworth filter
            b, a = signal.butter(2, cutoff / nyquist, btype='low')
            smoothed = signal.filtfilt(b, a, audio)
            return smoothed
        except Exception as e:
            print(f"⚠️ Vyhlazení selhalo: {e}")
            return audio

    @staticmethod
    def parse_contour_string(contour_str: str) -> List[Tuple[float, float]]:
        """
        Parsuje SSML-like konturu z řetězce

        Formát: "(0%,0%) (50%,+10%) (100%,-20%)"

        Args:
            contour_str: Řetězec s konturou

        Returns:
            Seznam (čas%, změna_pitch)
        """
        import re

        # Regex pro parsování: (čas%, změna%)
        pattern = r'\((\d+(?:\.\d+)?)%\s*,\s*([+-]?\d+(?:\.\d+)?)%\)'
        matches = re.findall(pattern, contour_str)

        contour = []
        for time_str, pitch_str in matches:
            try:
                time_val = float(time_str) / 100.0  # Převod na 0-1
                pitch_val = float(pitch_str)  # V semitonech (nebo procentech, podle konvence)
                contour.append((time_val, pitch_val))
            except ValueError:
                continue

        # Seřaď podle času
        contour.sort(key=lambda x: x[0])

        return contour if len(contour) >= 2 else [(0.0, 0.0), (1.0, 0.0)]

