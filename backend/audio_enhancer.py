"""
Audio enhancement modul pro post-processing generovaného audio
"""
import numpy as np
import librosa
import soundfile as sf
from pathlib import Path
from typing import Optional, Callable
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
        enable_compression: Optional[bool] = None,
        enable_deesser: Optional[bool] = None,
        enable_normalization: Optional[bool] = None,
        enable_trim: bool = True,
        enable_whisper: bool = False,
        whisper_intensity: float = 1.0,
        enable_vad: Optional[bool] = None,
        target_headroom_db: Optional[float] = None,
        progress_callback: Optional[Callable[[float, str, str], None]] = None
    ) -> str:
        """
        Hlavní metoda pro post-processing audio

        Args:
            audio_path: Cesta k audio souboru
            preset: Preset kvality (high_quality, natural, fast) - použije se pouze pokud explicitní parametry nejsou zadány
            enable_eq: Zapnout EQ korekci (None = použít preset)
            enable_noise_reduction: Zapnout noise reduction (None = použít preset)
            enable_compression: Zapnout kompresi (None = použít preset)
            enable_deesser: Zapnout de-esser (None = použít preset)
            enable_normalization: Zapnout finální normalizaci (výchozí: True)
            enable_trim: Zapnout ořez ticha (výchozí: True)
            enable_whisper: Zapnout whisper efekt (výchozí: False)
            whisper_intensity: Intenzita whisper efektu (0.0-1.0, výchozí: 1.0)
            enable_vad: Použít VAD pro trim (None = použít config, True/False = explicitně)
            target_headroom_db: Cílový headroom v dB po normalizaci (None = použít globální OUTPUT_HEADROOM_DB)
            progress_callback: Volitelná callback funkce pro progress updates (funkce(percent, stage, message))

        Returns:
            Cesta k vylepšenému audio souboru
        """
        from backend.config import OUTPUT_HEADROOM_DB, ENABLE_VAD as CONFIG_ENABLE_VAD

        # Načtení audio
        if progress_callback:
            progress_callback(0, "enhance", "Načítám audio pro enhancement…")
        audio, sr = librosa.load(audio_path, sr=OUTPUT_SAMPLE_RATE)

        # Určení nastavení podle presetu (pouze pokud explicitní parametry nejsou zadány)
        use_eq = enable_eq
        use_noise_reduction = enable_noise_reduction
        use_compression = enable_compression
        use_deesser = enable_deesser
        if any(p is None for p in [enable_eq, enable_noise_reduction, enable_compression, enable_deesser]):
            try:
                from backend.config import QUALITY_PRESETS
                preset_config = QUALITY_PRESETS.get(preset, QUALITY_PRESETS["natural"])
                enhancement_config = preset_config.get("enhancement", {})
            except ImportError:
                from backend import config
                preset_config = config.QUALITY_PRESETS.get(preset, config.QUALITY_PRESETS["natural"])
                enhancement_config = preset_config.get("enhancement", {})

            # Použití preset hodnot pouze pro parametry, které nejsou explicitně zadány
            use_eq = enable_eq if enable_eq is not None else enhancement_config.get("enable_eq", True)
            use_noise_reduction = enable_noise_reduction if enable_noise_reduction is not None else enhancement_config.get("enable_noise_reduction", True)
            use_compression = enable_compression if enable_compression is not None else enhancement_config.get("enable_compression", True)
            use_deesser = enable_deesser if enable_deesser is not None else enhancement_config.get("enable_deesser", True)

        # Určení, zda použít VAD
        use_vad = enable_vad if enable_vad is not None else CONFIG_ENABLE_VAD

        # Určení, zda použít normalizaci
        use_normalization = enable_normalization if enable_normalization is not None else enhancement_config.get("enable_normalization", False)

        # Počítáme aktivní kroky pro progress
        active_steps = []
        if enable_trim:
            active_steps.append("trim")
        if use_noise_reduction:
            active_steps.append("denoiser")
        if use_eq:
            active_steps.append("eq")
        if use_compression:
            active_steps.append("compressor")
        if use_deesser:
            active_steps.append("deesser")
        if enable_whisper:
            active_steps.append("whisper")
        active_steps.append("final")  # fade + DC + normalizace + headroom

        step_size = 100.0 / max(1, len(active_steps))
        current_pct = 0.0

        # 1. Ořez ticha (s VAD pokud je dostupné)
        if enable_trim:
            current_pct += step_size
            if progress_callback:
                progress_callback(current_pct, "enhance", "Ořez ticha…")
            try:
                if use_vad:
                    from backend.vad_processor import get_vad_processor
                    vad_processor = get_vad_processor()
                    audio = vad_processor.trim_silence_vad(audio, sr)
                else:
                    audio = AudioEnhancer.trim_silence(audio, sr, top_db=25)
            except Exception as e:
                print(f"Warning: VAD trim failed, using standard trim: {e}")
                audio = AudioEnhancer.trim_silence(audio, sr, top_db=25)

        # 2. Pokročilá redukce šumu (pokud zapnuto)
        if use_noise_reduction:
            current_pct += step_size
            if progress_callback:
                progress_callback(current_pct, "enhance", "Redukce šumu…")
            audio = AudioEnhancer.reduce_noise_advanced(audio, sr)

        # 3. EQ korekce (pokud zapnuto)
        if use_eq:
            current_pct += step_size
            if progress_callback:
                progress_callback(current_pct, "enhance", "EQ korekce…")
            audio = AudioEnhancer.apply_eq(audio, sr)

        # 4. Komprese dynamiky (pokud zapnuto) - jemná komprese pro transienty
        if use_compression:
            current_pct += step_size
            if progress_callback:
                progress_callback(current_pct, "enhance", "Komprese dynamiky…")
            audio = AudioEnhancer.compress_dynamic_range(audio)  # Použije default hodnoty optimalizované pro řeč

        # 5. De-esser (pokud zapnuto) - odstranění ostrých sykavek
        if use_deesser:
            current_pct += step_size
            if progress_callback:
                progress_callback(current_pct, "enhance", "De-esser…")
            audio = AudioEnhancer.apply_deesser(audio, sr)

        # 5.5. Whisper effect (pokud zapnuto) - šeptavý efekt
        if enable_whisper:
            current_pct += step_size
            if progress_callback:
                progress_callback(current_pct, "enhance", "Šeptavý efekt…")
            audio = AudioEnhancer.apply_whisper_effect(audio, sr, intensity=whisper_intensity)

        # 6. Fade in/out + DC offset + normalizace
        current_pct += step_size
        if progress_callback:
            progress_callback(current_pct, "enhance", "Finální úpravy enhancement…")
        audio = AudioEnhancer.apply_fade(audio, sr, fade_ms=50)
        audio = AudioEnhancer.remove_dc_offset(audio)

        # 7. Finální normalizace podle best practices pro hlas
        if use_normalization:
            # Použij target_headroom_db pokud je zadán, jinak výchozí -24 dB
            peak_target = target_headroom_db if target_headroom_db is not None else -24.0
            # Peak: použije se target_headroom_db z UI (umožňuje ovládat hlasitost výstupu), RMS: -18 dB
            audio = AudioEnhancer.normalize_audio(audio, peak_target_db=peak_target, rms_target_db=-18.0)

        # 8. Headroom se aplikuje v normalizaci výše (pokud enable_normalization=True)
        # Pokud je normalizace vypnutá, headroom se aplikuje až po HiFi-GAN a speed změně
        # (viz tts_engine._generate_sync finální headroom sekce)

        # Uložení zpět do souboru
        sf.write(audio_path, audio, sr)

        if progress_callback:
            progress_callback(100.0, "enhance", "Enhancement dokončen")

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
    def remove_dc_offset(audio: np.ndarray) -> np.ndarray:
        """
        Odstraní DC offset (stejnosměrnou složku) ze signálu
        """
        if len(audio) == 0:
            return audio
        return audio - np.mean(audio)

    @staticmethod
    def normalize_audio(audio: np.ndarray, peak_target_db: float = -24.0, rms_target_db: float = -18.0) -> np.ndarray:
        """
        Normalizace audio podle best practices pro hlas:
        - Peak: -24 dB (tišší výstup pro češtinu)
        - RMS: -18 dB
        - Ochrana proti extrémnímu zesílení (max +12 dB)
        """
        if len(audio) == 0:
            return audio

        # 1. RMS normalizace
        current_rms = np.sqrt(np.mean(audio ** 2))
        if current_rms > 0:
            rms_target_linear = 10 ** (rms_target_db / 20)
            rms_gain = rms_target_linear / current_rms

            # Omezení maximálního zesílení na +12 dB (cca 4x)
            max_gain = 10 ** (12 / 20)
            rms_gain = min(rms_gain, max_gain)

            audio = audio * rms_gain

        # 2. Peak normalizace na cílovou hodnotu (výchozí -24 dB pro tišší výstup)
        peak_target_linear = 10 ** (peak_target_db / 20)
        current_peak = np.max(np.abs(audio))
        if current_peak > 0:
            peak_gain = peak_target_linear / current_peak
            # Opět omezení gainu
            max_gain = 10 ** (12 / 20)
            peak_gain = min(peak_gain, max_gain)
            audio = audio * peak_gain

        # 3. Soft limiter (tanh) pro přirozenější ořez špiček
        # POZOR: Původní threshold -1 dB byl příliš blízko 0 dB a způsoboval přebuzení
        # Změněno na -3 dB pro bezpečnější limit
        threshold = 10 ** (-3.0 / 20)  # -3 dB místo -1 dB
        mask = np.abs(audio) > threshold
        if np.any(mask):
            # Aplikujeme tanh pro hladký ořez
            audio[mask] = np.sign(audio[mask]) * (threshold + (1.0 - threshold) * np.tanh((np.abs(audio[mask]) - threshold) / (1.0 - threshold)))

        # Finální hard clip na -0.5 dB pro jistotu (místo -0.1 dB)
        # POZOR: Původní -0.1 dB byl příliš blízko 0 dB a způsoboval přebuzení
        limiter_threshold = 10 ** (-0.5 / 20)  # -0.5 dB místo -0.1 dB
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

            # Jemné zvýraznění (sníženo na 1% pro eliminaci přebuzení)
            audio = audio + 0.01 * boosted

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
    def apply_whisper_effect(audio: np.ndarray, sr: int, intensity: float = 1.0) -> np.ndarray:
        """
        Aplikuje šeptavý efekt na audio na základě frekvenčních charakteristik šeptání.

        Šeptání je charakterizováno:
        - Absencí fundamentální frekvence (F0) - hlasivky nevibrují
        - Širokopásmovým spektrem s energií rozloženou napříč frekvencemi
        - Hlavní energie v pásmu 200-5000 Hz
        - Formanty (rezonance hlasového traktu) v pásmu 1-3 kHz
        - Šumovým charakterem bez periodické struktury
        - Menším dynamickým rozsahem než běžná řeč

        Args:
            audio: Audio data
            sr: Sample rate
            intensity: Intenzita efektu (0.0-1.0, výchozí: 1.0)
                     0.0 = žádný efekt, 1.0 = plný šeptavý efekt

        Returns:
            Audio se šeptavým efektem
        """
        if not SCIPY_AVAILABLE:
            return audio

        if len(audio) == 0:
            return audio

        try:
            nyquist = sr / 2

            # 1. Snížení velmi nízkých frekvencí (pod 100-150 Hz)
            # Šeptání má minimální energii pod 100 Hz (bez fundamentální frekvence)
            # Při intenzitě 1.0: cutoff = 100 Hz, při 0.5: cutoff = 150 Hz
            low_cutoff = 100 + (50 * (1.0 - intensity))  # 100-150 Hz podle intenzity
            low_cutoff = max(low_cutoff, 50)  # Minimální limit
            sos_hp_low = signal.butter(4, low_cutoff / nyquist, btype='high', output='sos')
            # Větší redukce basů pro autentičnost šeptání
            bass_reduction = 0.15 + (0.15 * intensity)  # 15-30% redukce
            high_passed_low = signal.sosfiltfilt(sos_hp_low, audio)
            audio = audio * (1.0 - bass_reduction) + high_passed_low * bass_reduction

            # 2. Zvýšení středních frekvencí (1-3 kHz) - formanty šeptání
            # Formanty (rezonance hlasového traktu) jsou stále přítomné v šeptání
            # Toto pásmo obsahuje hlavní energii šeptavého hlasu
            sos_boost_formants = signal.butter(4, [1000, 3000], btype='band', fs=sr, output='sos')
            boosted_formants = signal.sosfiltfilt(sos_boost_formants, audio)
            # Mírně vyšší boost pro lepší simulaci formantů (5-10% boost)
            boost_amount = 0.05 + (0.05 * intensity)  # 5-10%
            audio = audio + (boost_amount * boosted_formants)

            # 3. Mírné zvýšení středně-vysokých frekvencí (3-4 kHz)
            # Šeptání má ještě určitou energii v tomto pásmu
            sos_boost_mid = signal.butter(4, [3000, 4000], btype='band', fs=sr, output='sos')
            boosted_mid = signal.sosfiltfilt(sos_boost_mid, audio)
            # Jemné zvýraznění (2-4% boost)
            mid_boost = 0.02 + (0.02 * intensity)  # 2-4%
            audio = audio + (mid_boost * boosted_mid)

            # 4. Snížení vysokých frekvencí (high-frequency roll-off)
            # Šeptání má výrazně méně vysokých frekvencí než běžná řeč
            # Hlavní energie je v pásmu 200-5000 Hz, nad 5 kHz výrazný pokles
            # Při intenzitě 1.0: cutoff = 4000 Hz, při 0.5: cutoff = 5500 Hz
            cutoff = 4000 + (1500 * (1.0 - intensity))  # 4.0-5.5 kHz podle intenzity
            cutoff = min(cutoff, nyquist * 0.9)  # Bezpečnostní limit

            # Použijeme strmější low-pass filter pro autentičnost
            sos_lp = signal.butter(8, cutoff / nyquist, btype='low', output='sos')
            audio = signal.sosfiltfilt(sos_lp, audio)

            # 5. Výraznější pokles velmi vysokých frekvencí (nad 5-6 kHz)
            # Šeptání má téměř žádné frekvence nad 5 kHz
            if cutoff < 5500:
                # Další pokles pro frekvence nad cutoff
                sos_lp2 = signal.butter(6, (cutoff + 500) / nyquist, btype='low', output='sos')
                high_freq = signal.sosfiltfilt(sos_lp2, audio)
                # Větší redukce vysokých frekvencí (60-85% podle intenzity)
                reduction = 0.6 + (0.25 * intensity)  # 0.6-0.85
                audio = audio * (1.0 - reduction) + high_freq * reduction

            # 6. Přidání jemného šumu pro autentičnost šumového charakteru šeptání
            # Šeptání má šumový charakter bez periodické struktury
            noise_level = 0.005 * intensity  # 0-0.5% šumu podle intenzity
            noise = np.random.normal(0, noise_level * np.std(audio), len(audio))
            audio = audio + noise

            # 7. Snížení dynamiky (komprese) - šeptání má menší dynamický rozsah
            # Vyšší kompresní poměr pro autentičnost
            compression_ratio = 2.5 + (0.5 * intensity)  # 2.5-3.0
            audio = AudioEnhancer.compress_dynamic_range(audio, ratio=compression_ratio, threshold=-18.0)

            # NENÍ snížení celkové hlasitosti - šeptání se simuluje pouze EQ úpravami!
            # Hlasitost zůstane na normální úrovni

            return audio
        except Exception as e:
            print(f"⚠️ Warning: Whisper effect failed: {e}, continuing without whisper effect")
            return audio

    @staticmethod
    def compress_dynamic_range(audio: np.ndarray, ratio: float = 2.0, threshold: float = -18.0) -> np.ndarray:
        """
        Komprese dynamiky optimalizovaná pro řeč - zlepšuje inteligibilitu a konzistenci

        Args:
            audio: Audio data
            ratio: Kompresní poměr (2.0-4.0 pro řeč, výchozí 2.0 pro jemnou kompresi)
            threshold: Threshold v dB (-18 dB pro řeč - zachovává přirozenou dynamiku)

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

    @staticmethod
    def apply_deesser(audio: np.ndarray, sr: int, freq_range: tuple = (4000, 10000), threshold: float = -18.0, ratio: float = 4.0) -> np.ndarray:
        """
        De-esser pro potlačení ostrých sykavek (s, š, c, č)

        Args:
            audio: Audio data
            sr: Sample rate
            freq_range: Rozsah frekvencí sykavek (výchozí 4-10 kHz)
            threshold: Threshold v dB pro detekci sykavek
            ratio: Kompresní poměr pro sykavky

        Returns:
            Audio s potlačenými sykavkami
        """
        if not SCIPY_AVAILABLE:
            return audio

        try:
            # 1. Izolace frekvencí sykavek pomocí bandpass filtru
            sos = signal.butter(4, freq_range, btype='band', fs=sr, output='sos')
            sibilance = signal.sosfiltfilt(sos, audio)

            # 2. Detekce obálky (envelope) sykavek
            envelope = np.abs(signal.hilbert(sibilance))

            # Vyhlazení obálky (lowpass)
            sos_lp = signal.butter(2, 50, btype='low', fs=sr, output='sos')
            envelope = signal.sosfiltfilt(sos_lp, envelope)

            # 3. Výpočet gain redukce
            threshold_linear = 10 ** (threshold / 20)

            # Gain je 1.0 pokud je pod threshold, jinak se snižuje podle ratio
            gain = np.ones_like(envelope)
            mask = envelope > threshold_linear
            if np.any(mask):
                # Výpočet redukce v dB
                envelope_db = 20 * np.log10(envelope[mask] + 1e-10)
                reduction_db = (envelope_db - threshold) * (1 - 1/ratio)
                gain[mask] = 10 ** (-reduction_db / 20)

            # 4. Aplikace redukce na původní signál
            # Redukci aplikujeme pouze na sibilantní část nebo na celé audio s váhou?
            # Standardní de-esser (wideband) aplikuje gain na celé audio, když detekuje sykavku.
            # Split-band de-esser aplikuje gain pouze na sibilantní pásmo.
            # Zde zkusíme wideband pro přirozenější zvuk bez fázových problémů.
            audio_deessed = audio * gain

            return audio_deessed

        except Exception as e:
            print(f"Warning: De-esser failed: {e}, continuing without de-essing")
            return audio

    @staticmethod
    def apply_emphasis_effect(audio: np.ndarray, sr: int, level: str = 'MODERATE', intensity: float = 1.0) -> np.ndarray:
        """
        Aplikuje důraz na audio segment

        Args:
            audio: Audio data
            sr: Sample rate
            level: Úroveň důrazu ('STRONG' nebo 'MODERATE')
            intensity: Intenzita efektu (0.0-2.0, výchozí: 1.0, hodnoty > 1.0 zvyšují efekt)

        Returns:
            Audio s aplikovaným důrazem
        """
        if not SCIPY_AVAILABLE:
            return audio

        if len(audio) == 0:
            return audio

        try:
            # 1. Zvýšení hlasitosti podle úrovně důrazu
            # POZOR: Tyto hodnoty byly zvýšeny a způsobily přebuzení - vráceno na původní bezpečné hodnoty
            if level == 'STRONG':
                # Silný důraz: +3-6 dB podle intenzity (původní bezpečná hodnota)
                gain_db = 3.0 + (3.0 * intensity)  # 3-6 dB
            else:  # MODERATE
                # Mírný důraz: +1.5-3 dB podle intenzity (původní bezpečná hodnota)
                gain_db = 1.5 + (1.5 * intensity)  # 1.5-3 dB

            gain_linear = 10 ** (gain_db / 20.0)
            audio = audio * gain_linear

            # 2. Zvýšení středních frekvencí (1-4 kHz) - kde je důraz nejvýraznější
            nyquist = sr / 2
            sos_boost = signal.butter(4, [1000, 4000], btype='band', fs=sr, output='sos')
            boosted = signal.sosfiltfilt(sos_boost, audio)
            # Boost podle úrovně a intenzity
            # POZOR: Tyto hodnoty byly zvýšeny a způsobily přebuzení - vráceno na původní bezpečné hodnoty
            if level == 'STRONG':
                boost_amount = 0.05 + (0.05 * intensity)  # 5-10% boost (původní bezpečná hodnota)
            else:
                boost_amount = 0.02 + (0.03 * intensity)  # 2-5% boost (původní bezpečná hodnota)
            audio = audio + (boost_amount * boosted)

            # 3. Dynamická komprese pro větší kontrast (pouze pro STRONG)
            if level == 'STRONG':
                # Mírná komprese pro větší dynamiku
                threshold = -20.0  # dB
                ratio = 3.0
                # Aplikuj jednoduchou kompresi
                audio_abs = np.abs(audio)
                audio_max = np.max(audio_abs) if np.max(audio_abs) > 0 else 1.0
                audio_db = 20 * np.log10(audio_abs / audio_max + 1e-10)

                # Komprese nad prahem
                compressed_db = np.where(
                    audio_db > threshold,
                    threshold + (audio_db - threshold) / ratio,
                    audio_db
                )

                # Převeď zpět na lineární
                compressed_linear = 10 ** (compressed_db / 20.0) * audio_max
                audio = np.sign(audio) * compressed_linear

            # 4. Pro silný důraz: mírné zvýšení pitch (simulace větší energie)
            if level == 'STRONG' and intensity > 0.5:
                try:
                    import librosa
                    # Zvýšení pitch (0.5-1.0 semiton podle intenzity - původní bezpečná hodnota)
                    # POZOR: Hodnota byla zvýšena na 1.0-2.0 a způsobila přebuzení
                    pitch_shift = 0.5 + (0.5 * (intensity - 0.5) * 2)  # 0.5-1.0 semiton
                    audio = librosa.effects.pitch_shift(audio, sr=sr, n_steps=pitch_shift)
                except Exception:
                    pass  # Pokud pitch shift selže, pokračuj bez něj

            # 5. Ochrana proti clippingu - zajistit, že audio nikdy nepřekročí bezpečný limit
            # Headroom -18 dB = 0.125 v lineárních jednotkách, použijeme -3 dB = 0.708 pro bezpečnost
            max_safe_amplitude = 10 ** (-3.0 / 20.0)  # -3 dB jako bezpečný limit
            peak = np.max(np.abs(audio)) if len(audio) > 0 else 0.0
            if peak > max_safe_amplitude:
                # Ztlumit audio, aby nepřekročilo bezpečný limit
                scale = max_safe_amplitude / peak
                audio = audio * scale

            return audio
        except Exception as e:
            print(f"⚠️ Warning: Emphasis effect failed: {e}, continuing without emphasis")
            return audio

    @staticmethod
    def apply_rate_effect(audio: np.ndarray, sr: int, rate: str = 'NORMAL', intensity: float = 1.0) -> np.ndarray:
        """
        Aplikuje změnu rychlosti řeči na audio segment

        Args:
            audio: Audio data
            sr: Sample rate
            rate: Úroveň rychlosti ('SLOW', 'X_SLOW', 'FAST', 'X_FAST', 'NORMAL')
            intensity: Intenzita efektu (0.0-1.0, výchozí: 1.0)

        Returns:
            Audio s aplikovanou změnou rychlosti
        """
        if len(audio) == 0:
            return audio

        try:
            import librosa

            # Určení faktoru rychlosti
            if rate == 'X_SLOW':
                speed_factor = 0.6 + (0.2 * (1.0 - intensity))  # 0.6-0.8x (pomalejší)
            elif rate == 'SLOW':
                speed_factor = 0.75 + (0.15 * (1.0 - intensity))  # 0.75-0.9x (mírně pomalejší)
            elif rate == 'X_FAST':
                speed_factor = 1.3 + (0.3 * intensity)  # 1.3-1.6x (rychlejší)
            elif rate == 'FAST':
                speed_factor = 1.1 + (0.2 * intensity)  # 1.1-1.3x (mírně rychlejší)
            else:  # NORMAL
                return audio  # Žádná změna

            # Aplikuj změnu rychlosti pomocí time-stretching (zachová pitch)
            # Použijeme librosa.effects.time_stretch
            audio_stretched = librosa.effects.time_stretch(audio, rate=speed_factor)

            return audio_stretched
        except Exception as e:
            print(f"⚠️ Warning: Rate effect failed: {e}, continuing without rate change")
            return audio

    @staticmethod
    def apply_pitch_effect(audio: np.ndarray, sr: int, pitch: str = 'NORMAL', intensity: float = 1.0) -> np.ndarray:
        """
        Aplikuje změnu výšky hlasu (pitch) na audio segment

        Args:
            audio: Audio data
            sr: Sample rate
            pitch: Úroveň pitch ('HIGH', 'X_HIGH', 'LOW', 'X_LOW', 'NORMAL')
            intensity: Intenzita efektu (0.0-1.0, výchozí: 1.0)

        Returns:
            Audio s aplikovanou změnou pitch
        """
        if len(audio) == 0:
            return audio

        try:
            import librosa

            # Určení změny pitch v semitonech
            if pitch == 'X_HIGH':
                pitch_shift = 2.0 + (2.0 * intensity)  # +2 až +4 semitony
            elif pitch == 'HIGH':
                pitch_shift = 1.0 + (1.0 * intensity)  # +1 až +2 semitony
            elif pitch == 'X_LOW':
                pitch_shift = -2.0 - (2.0 * intensity)  # -2 až -4 semitony
            elif pitch == 'LOW':
                pitch_shift = -1.0 - (1.0 * intensity)  # -1 až -2 semitony
            else:  # NORMAL
                return audio  # Žádná změna

            # Aplikuj pitch shift
            audio_shifted = librosa.effects.pitch_shift(audio, sr=sr, n_steps=pitch_shift)

            return audio_shifted
        except Exception as e:
            print(f"⚠️ Warning: Pitch effect failed: {e}, continuing without pitch change")
            return audio

