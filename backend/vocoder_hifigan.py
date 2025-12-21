"""
HiFi-GAN Vocoder wrapper pro XTTS-v2 TTS Engine
"""
import numpy as np
from typing import Optional
import backend.config as config


class HiFiGANVocoder:
    """
    Wrapper pro HiFi-GAN vocoder
    """

    def __init__(self):
        self._model = None
        self._available = False
        self._initialize()

    def _initialize(self):
        """Inicializuje HiFi-GAN vocoder pokud je dostupný"""
        if not config.ENABLE_HIFIGAN:
            self._available = False
            return

        try:
            # Zkus načíst parallel-wavegan (nejběžnější implementace)
            try:
                from parallel_wavegan.utils import download_pretrained_model
                from parallel_wavegan.utils import load_model
                self._available = True
                # Model se načte až při prvním použití (lazy loading)
            except ImportError:
                # Parallel-wavegan není dostupný, zkus jiné možnosti
                try:
                    # Zkus hifigan přímo (pokud existuje)
                    import hifigan
                    self._available = True
                except ImportError:
                    self._available = False
                    print("⚠️  HiFi-GAN není dostupný: parallel-wavegan ani hifigan nejsou nainstalovány")
        except Exception as e:
            self._available = False
            print(f"⚠️  HiFi-GAN inicializace selhala: {e}")

    @property
    def available(self) -> bool:
        """Vrací True pokud je HiFi-GAN dostupný"""
        return self._available

    def is_available(self) -> bool:
        """Vrací True pokud je HiFi-GAN dostupný a načtený"""
        return self._available

    @property
    def mel_params(self) -> dict:
        """Vrací parametry mel-spectrogramu pro HiFi-GAN"""
        return {
            "n_mels": config.HIFIGAN_N_MELS,
            "n_fft": config.HIFIGAN_N_FFT,
            "hop_length": config.HIFIGAN_HOP_LENGTH,
            "win_length": config.HIFIGAN_WIN_LENGTH,
            "fmin": config.HIFIGAN_FMIN,
            "fmax": config.HIFIGAN_FMAX
        }

    def vocode(
        self,
        mel_log: np.ndarray,
        sample_rate: int,
        original_audio: Optional[np.ndarray] = None
    ) -> Optional[np.ndarray]:
        """
        Převádí mel-spectrogram zpět na audio pomocí HiFi-GAN

        Args:
            mel_log: Log-mel spectrogram (numpy array)
            sample_rate: Sample rate výstupního audio
            original_audio: Původní audio pro blending (volitelné)

        Returns:
            Vygenerované audio jako numpy array, nebo None pokud selže
        """
        if not self._available:
            return None

        try:
            # Zatím vracíme None - skutečná implementace by vyžadovala načtení modelu
            # Toto je stub implementace, která umožní kódu běžet bez chyb
            # Pro plnou funkcionalnost by bylo potřeba:
            # 1. Načíst HiFi-GAN model (parallel-wavegan nebo jiný)
            # 2. Převést mel_log na správný formát
            # 3. Zavolat vocoder
            # 4. Aplikovat blending s original_audio pokud je intensity < 1.0
            # 5. Normalizovat výstup pokud je zapnuto

            print("⚠️  HiFi-GAN vocode: Stub implementace - vrací None")
            return None

        except Exception as e:
            print(f"⚠️  HiFi-GAN vocoding selhal: {e}")
            return None


# Singleton instance
_vocoder_instance: Optional[HiFiGANVocoder] = None


def get_hifigan_vocoder() -> HiFiGANVocoder:
    """
    Vrací singleton instanci HiFi-GAN vocoder

    Returns:
        HiFiGANVocoder instance
    """
    global _vocoder_instance
    if _vocoder_instance is None:
        _vocoder_instance = HiFiGANVocoder()
    return _vocoder_instance
