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
    UPLOADS_DIR,
    SPEAKER_CACHE_DIR,
    ENABLE_REFERENCE_VOICE_PREP,
    ENABLE_REFERENCE_VAD_SEGMENTATION,
    ENABLE_REFERENCE_LOUDNORM,
    REFERENCE_TARGET_DURATION_SEC,
    REFERENCE_SEGMENT_MIN_SEC,
    REFERENCE_SEGMENT_MAX_SEC,
    REFERENCE_MAX_SEGMENTS,
    REFERENCE_PAUSE_MS,
    REFERENCE_CROSSFADE_MS,
    REFERENCE_LOUDNORM_I,
    REFERENCE_LOUDNORM_TP,
    REFERENCE_LOUDNORM_LRA,
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
        target_channels: int = TARGET_CHANNELS,
        apply_loudnorm: bool = False
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
            loudnorm_filter = None
            if apply_loudnorm:
                # EBU R128 loudness normalization (typicky pomůže na „kolísající hlasitost“ a artefakty)
                loudnorm_filter = f"loudnorm=I={REFERENCE_LOUDNORM_I}:TP={REFERENCE_LOUDNORM_TP}:LRA={REFERENCE_LOUDNORM_LRA}"

            cmd = [
                "ffmpeg",
                "-i", str(input_path),
                "-ar", str(target_sr),
                "-ac", str(target_channels),
                # Loudness normalization (volitelné)
                *([] if loudnorm_filter is None else ["-af", loudnorm_filter]),
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
    def analyze_audio_quality(file_path: str) -> dict:
        """
        Analyzuje kvalitu audio souboru (SNR, clipping, délka)

        Returns:
            Dictionary s výsledky analýzy
        """
        try:
            audio, sr = librosa.load(file_path, sr=None)

            # 1. SNR estimation
            snr = AudioProcessor.estimate_snr(audio)

            # 2. Clipping detection
            clipping_ratio = AudioProcessor.check_clipping(audio)

            # 3. Duration
            duration = librosa.get_duration(y=audio, sr=sr)

            # 4. Celkové hodnocení
            score = "good"
            warnings = []

            if snr < 15:
                score = "poor"
                warnings.append("Vysoká úroveň šumu v pozadí")
            elif snr < 25:
                score = "fair"
                warnings.append("Mírný šum v pozadí")

            if clipping_ratio > 0.01:
                score = "poor"
                warnings.append("Audio je přebuzené (clipping)")

            if duration < 6:
                warnings.append("Audio je příliš krátké pro kvalitní klonování")

            return {
                "snr": float(snr),
                "clipping_ratio": float(clipping_ratio),
                "duration": float(duration),
                "score": score,
                "warnings": warnings
            }
        except Exception as e:
            return {"error": str(e), "score": "unknown", "warnings": ["Nepodařilo se analyzovat kvalitu"]}

    @staticmethod
    def estimate_snr(audio: np.ndarray) -> float:
        """Odhadne poměr signálu k šumu (SNR) v dB"""
        # Velmi zjednodušený odhad: RMS signálu vs RMS tichých částí
        # Najdeme tiché části (pod 10. percentil magnitudy)
        rms_total = np.sqrt(np.mean(audio**2))
        if rms_total == 0: return 0

        # Rozdělíme na okna a najdeme okno s nejnižší energií (noise floor)
        win_length = 2048
        hop_length = 512
        if len(audio) < win_length: return 20.0 # Fallback pro velmi krátké audio

        rms_windows = librosa.feature.rms(y=audio, frame_length=win_length, hop_length=hop_length)[0]
        noise_floor = np.percentile(rms_windows, 10)

        if noise_floor == 0: return 50.0 # Velmi čisté audio

        snr = 20 * np.log10(rms_total / (noise_floor + 1e-10))
        return max(0, snr)

    @staticmethod
    def check_clipping(audio: np.ndarray, threshold: float = 0.99) -> float:
        """Vrátí poměr samplů, které dosahují threshold (clipping)"""
        clipping_samples = np.sum(np.abs(audio) >= threshold)
        return clipping_samples / len(audio)

    @staticmethod
    def convert_audio(
        input_path: str,
        output_path: str,
        target_sr: int = TARGET_SAMPLE_RATE,
        target_channels: int = TARGET_CHANNELS,
        apply_advanced_processing: bool = False,
        apply_loudnorm: bool = False
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

                # DOČASNĚ VYPNUTO: Jednoduchá redukce šumu (spectral gating)
                # stft = librosa.stft(audio)
                # magnitude = np.abs(stft)
                # # Threshold na 10% maximální hodnoty
                # threshold = np.max(magnitude) * 0.1
                # mask = magnitude > threshold
                # stft_clean = stft * mask
                # audio = librosa.istft(stft_clean)

            # Lehká normalizace (librosa cesta) – podobný efekt jako loudnorm, ale bez LUFS metriky
            if apply_loudnorm:
                try:
                    from backend.audio_enhancer import AudioEnhancer
                    audio = AudioEnhancer.remove_dc_offset(audio)
                    audio = AudioEnhancer.apply_fade(audio, target_sr, fade_ms=30)
                    audio = AudioEnhancer.normalize_audio(audio, peak_target_db=-24.0, rms_target_db=-18.0)
                except Exception:
                    # Fallback: jednoduchá peak normalizace
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
                    target_channels,
                    apply_loudnorm=apply_loudnorm
                )
            else:
                return False, f"Chyba při konverzi audio: {str(e)} (FFmpeg není dostupný)"

    @staticmethod
    def _prepare_reference_voice_from_wav(
        input_wav_path: str,
        output_wav_path: str,
        target_duration_sec: float = REFERENCE_TARGET_DURATION_SEC,
        use_vad: bool = True,
        min_seg_sec: float = REFERENCE_SEGMENT_MIN_SEC,
        max_seg_sec: float = REFERENCE_SEGMENT_MAX_SEC,
        max_segments: int = REFERENCE_MAX_SEGMENTS,
        pause_ms: int = REFERENCE_PAUSE_MS,
        crossfade_ms: int = REFERENCE_CROSSFADE_MS,
    ) -> Tuple[bool, Optional[str]]:
        """
        Z připraveného WAV udělá „referenční hlas“ pro klonování:
        - vybere segmenty s řečí (VAD)
        - odstraní dlouhé ticho/hudbu
        - znormalizuje a spojí do cílové délky (např. ~15s)
        """
        try:
            import librosa
            import soundfile as sf
            from backend.audio_enhancer import AudioEnhancer

            audio, sr = librosa.load(input_wav_path, sr=TARGET_SAMPLE_RATE, mono=True)
            if len(audio) == 0:
                return False, "Referenční audio je prázdné"

            # VAD segmentace (pokud zapnuto)
            segments = []
            if use_vad and ENABLE_REFERENCE_VAD_SEGMENTATION:
                try:
                    from backend.vad_processor import get_vad_processor
                    vad = get_vad_processor()
                    segments = vad.detect_voice_segments(audio, sr)
                except Exception:
                    segments = []

            # Pokud VAD nic nenašel, fallback na trim
            if not segments:
                audio, _ = librosa.effects.trim(audio, top_db=25)
                segments = [(0.0, len(audio) / sr)]

            # Kandidáti: segmenty v rozumné délce + RMS skóre
            candidates = []
            for (s, e) in segments:
                dur = max(0.0, e - s)
                if dur < min_seg_sec:
                    continue
                # omezíme extrémně dlouhé segmenty
                if dur > max_seg_sec:
                    mid = (s + e) / 2.0
                    half = max_seg_sec / 2.0
                    s2 = max(0.0, mid - half)
                    e2 = min(len(audio) / sr, mid + half)
                    s, e = s2, e2
                    dur = max(0.0, e - s)
                if dur < min_seg_sec:
                    continue
                a = audio[int(s * sr):int(e * sr)]
                if len(a) == 0:
                    continue
                rms = float(np.sqrt(np.mean(a ** 2)) + 1e-12)
                candidates.append((rms, s, e))

            if not candidates:
                # poslední fallback: celé audio, ale oříznout ticho
                audio, _ = librosa.effects.trim(audio, top_db=25)
                candidates = [(1.0, 0.0, len(audio) / sr)]

            # Seřadit podle RMS (často koreluje s čistou řečí) a vzít top N
            candidates.sort(key=lambda x: x[0], reverse=True)
            candidates = candidates[:max(1, max_segments * 3)]  # trochu víc pro případ krátkých segmentů

            chosen = []
            total = 0.0
            for _rms, s, e in candidates:
                if len(chosen) >= max_segments:
                    break
                dur = max(0.0, e - s)
                if dur <= 0:
                    continue
                chosen.append((s, e))
                total += dur
                if total >= target_duration_sec:
                    break

            # Pokud stále krátké, vezmi i zbytek v pořadí času (aby byl vzorek „přirozený“)
            if total < min(target_duration_sec, 6.0):
                # spoj sousední segmenty „jak jdou“
                chosen = sorted([(s, e) for _rms, s, e in candidates[:max_segments]], key=lambda x: x[0])
                total = sum(max(0.0, e - s) for s, e in chosen)

            # Sestavení výstupu
            pause_samples = int(pause_ms * sr / 1000.0)
            parts = []
            for i, (s, e) in enumerate(chosen):
                part = audio[int(s * sr):int(e * sr)]
                if len(part) == 0:
                    continue
                parts.append(part)
                if i != len(chosen) - 1 and pause_samples > 0:
                    parts.append(np.zeros(pause_samples, dtype=np.float32))

            if not parts:
                return False, "Nepodařilo se vybrat žádné segmenty řeči pro referenci"

            ref = np.concatenate(parts).astype(np.float32)

            # Finální úpravy: fade + DC + normalizace
            ref = AudioEnhancer.apply_fade(ref, sr, fade_ms=50)
            ref = AudioEnhancer.remove_dc_offset(ref)
            ref = AudioEnhancer.normalize_audio(ref, peak_target_db=-24.0, rms_target_db=-18.0)

            # Uřízni na cílovou délku (když jsme nabrali víc)
            max_len = int(target_duration_sec * sr)
            if len(ref) > max_len:
                ref = ref[:max_len]

            Path(output_wav_path).parent.mkdir(parents=True, exist_ok=True)
            sf.write(output_wav_path, ref, sr)
            return True, None

        except Exception as e:
            return False, f"Chyba při tvorbě referenčního hlasu: {str(e)}"

    @staticmethod
    def process_uploaded_file(
        uploaded_file_path: str,
        output_filename: Optional[str] = None,
        remove_background: bool = False
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Zpracuje nahraný audio soubor

        Args:
            uploaded_file_path: Cesta k nahranému souboru
            output_filename: Volitelný název výstupního souboru
            remove_background: Pokud True, odstraní hudbu a zvuky v pozadí pomocí Demucs

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
            apply_advanced_processing=True,  # Použij pokročilé zpracování pro uploady
            apply_loudnorm=bool(ENABLE_REFERENCE_LOUDNORM),  # normalizace hlasitosti pro konzistenci
        )

        if not success:
            return None, error

        # Separace vokálů od pozadí pokud je požadována
        if remove_background:
            try:
                from backend.audio_separator import separate_vocals
                import logging
                import uuid
                logger = logging.getLogger(__name__)

                logger.info("Začínám separaci vokálů od pozadí...")
                temp_separated = output_path.parent / f"temp_separated_{uuid.uuid4()}.wav"
                success_sep, error_sep = separate_vocals(
                    str(output_path),
                    str(temp_separated)
                )
                if success_sep:
                    # Přepsat původní soubor separovanými vokály
                    import shutil
                    shutil.move(str(temp_separated), str(output_path))
                    logger.info("Separace vokálů dokončena úspěšně")
                else:
                    logger.warning(f"Separace vokálů selhala: {error_sep}, používám původní audio")
                    temp_separated.unlink(missing_ok=True)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Chyba při separaci vokálů: {str(e)}, používám původní audio")

        # Volitelně: vytvoř „reference voice" vhodnější pro klonování (VAD segmenty + normalizace)
        if ENABLE_REFERENCE_VOICE_PREP:
            try:
                ref_dir = SPEAKER_CACHE_DIR / "reference_wavs"
                ref_dir.mkdir(parents=True, exist_ok=True)
                ref_path = ref_dir / f"ref_{Path(output_path).stem}.wav"
                ok, prep_err = AudioProcessor._prepare_reference_voice_from_wav(
                    str(output_path),
                    str(ref_path),
                    target_duration_sec=REFERENCE_TARGET_DURATION_SEC,
                    use_vad=ENABLE_REFERENCE_VAD_SEGMENTATION,
                )
                if ok:
                    return str(ref_path), None
                else:
                    # fallback: vrať aspoň konvertovaný WAV
                    print(f"⚠️ Reference voice prep selhal: {prep_err}")
            except Exception as e:
                print(f"⚠️ Reference voice prep exception: {e}")

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

            # 2. De-essing (redukce sykavek)
            audio = AudioEnhancer.apply_deesser(audio, sr)

            # 3. Pokročilá redukce šumu
            audio = AudioEnhancer.reduce_noise_advanced(audio, sr)

            # 4. EQ korekce pro vyrovnání frekvenčního spektra
            audio = AudioEnhancer.apply_eq(audio, sr)

            # 5. Jemná komprese pro zvládnutí transientů
            audio = AudioEnhancer.compress_dynamic_range(audio, ratio=2.5)

            # 6. Fade in/out
            audio = AudioEnhancer.apply_fade(audio, sr, fade_ms=30)

            # 7. Finální normalizace podle best practices pro hlas
            # Peak: -3 dB, RMS: -16 až -20 dB
            audio = AudioEnhancer.normalize_audio(audio, peak_target_db=-24.0, rms_target_db=-18.0)

            # Uložení
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            sf.write(output_path, audio, sr)

            return True, None

        except Exception as e:
            return False, f"Chyba při vylepšování vzorku: {str(e)}"

