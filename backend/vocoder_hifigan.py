"""
HiFi-GAN Vocoder wrapper pro XTTS-v2 TTS Engine
"""
import numpy as np
from typing import Optional
from pathlib import Path
import backend.config as config
import torch


class HiFiGANVocoder:
    """
    Wrapper pro HiFi-GAN vocoder s lazy-loading a per-request parametry
    """

    def __init__(self):
        self._model = None
        self._model_loaded = False
        self._available = False
        self._parallel_wavegan_available = False
        self._models_dir = Path(config.MODELS_DIR) / "hifigan"
        self._initialize()

    def _initialize(self):
        """Inicializuje HiFi-GAN vocoder pokud je dostupný"""
        if not config.ENABLE_HIFIGAN:
            self._available = False
            return

        try:
            from colorama import Fore, Style
            COLOR_OK = Fore.GREEN
            COLOR_WARN = Fore.YELLOW
            COLOR_INFO = Fore.CYAN
            COLOR_RESET = Style.RESET_ALL
        except ImportError:
            COLOR_OK = COLOR_WARN = COLOR_INFO = COLOR_RESET = ""

        try:
            # Zkus načíst parallel-wavegan (nejběžnější implementace)
            try:
                from parallel_wavegan.utils import download_pretrained_model, load_model
                from parallel_wavegan.models import ParallelWaveGANGenerator
                self._parallel_wavegan_available = True
                self._available = True
                # Model se načte až při prvním použití (lazy loading)
                print(f"{COLOR_OK}✅ parallel-wavegan je dostupný (lazy loading modelu){COLOR_RESET}")
            except ImportError:
                # Parallel-wavegan není dostupný, zkus jiné možnosti
                try:
                    # Zkus hifigan přímo (pokud existuje)
                    import hifigan
                    self._available = True
                    print(f"{COLOR_OK}✅ hifigan je dostupný{COLOR_RESET}")
                except ImportError:
                    self._available = False
                    print(f"{COLOR_WARN}⚠️  HiFi-GAN není dostupný: parallel-wavegan ani hifigan nejsou nainstalovány{COLOR_RESET}")
        except Exception as e:
            self._available = False
            print(f"{COLOR_WARN}⚠️  HiFi-GAN inicializace selhala: {e}{COLOR_RESET}")

    def _load_model(self) -> bool:
        """
        Načte HiFi-GAN model (lazy loading)

        Returns:
            True pokud se model úspěšně načetl
        """
        if self._model_loaded:
            return self._model is not None

        if not self._available:
            return False

        try:
            if self._parallel_wavegan_available:
                # Zkus najít lokální model v models/hifigan/
                model_path = self._models_dir
                config_path = model_path / "config.yaml"
                checkpoint_path = model_path / "checkpoint.pkl"
                checkpoint_pth_path = model_path / "checkpoint.pth"

                # Zkus nejdřív .pkl, pak .pth (kompatibilita s HuggingFace modely)
                if not checkpoint_path.exists() and checkpoint_pth_path.exists():
                    checkpoint_path = checkpoint_pth_path

                # Pokud lokální model neexistuje, zkus fallback na HuggingFace cache
                if not config_path.exists() or not checkpoint_path.exists():
                    print("⚠️  Lokální HiFi-GAN model neexistuje v models/hifigan/, zkouším HuggingFace cache...")

                    # Zkus najít stažený model v HuggingFace cache
                    hf_cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
                    hf_model_dirs = [
                        "models--espnet--kan-bayashi_ljspeech_joint_finetune_conformer_fastspeech2_hifigan",
                        "models--espnet--kan-bayashi_ljspeech_hifigan",
                        "models--kan-bayashi--ljspeech_hifigan.v1"
                    ]

                    for model_dir_name in hf_model_dirs:
                        model_cache_path = hf_cache_dir / model_dir_name
                        if model_cache_path.exists():
                            # Najdi nejnovější snapshot
                            snapshots_dir = model_cache_path / "snapshots"
                            if snapshots_dir.exists():
                                snapshots = list(snapshots_dir.glob("*"))
                                if snapshots:
                                    latest_snapshot = max(snapshots, key=lambda x: x.stat().st_mtime)
                                    print(f"📦 Našel HiFi-GAN model v HuggingFace cache: {model_dir_name}")

                                    # Najdi config a checkpoint v snapshotu
                                    exp_dirs = list(latest_snapshot.glob("exp/*hifigan*"))
                                    if exp_dirs:
                                        exp_dir = exp_dirs[0]
                                        hf_config_path = exp_dir / "config.yaml"
                                        hf_checkpoint_path = exp_dir / "train.total_count.ave_5best.pth"

                                        if hf_config_path.exists() and hf_checkpoint_path.exists():
                                            print("✅ Používám HiFi-GAN model z HuggingFace cache")
                                            config_path = hf_config_path
                                            checkpoint_path = hf_checkpoint_path
                                            break

                    # Pokud se stále nepodařilo najít model
                    if not config_path.exists() or not checkpoint_path.exists():
                        print("⚠️  HiFi-GAN model nebyl nalezen ani v lokálním adresáři ani v HuggingFace cache")
                        print("   HiFi-GAN refinement bude přeskočen")
                        self._model_loaded = True  # Označíme jako "zkoušeno", abychom nezkoušeli opakovaně
                        return False

                # Načtení modelu z lokálního checkpointu
                from parallel_wavegan.utils import load_model
                # Převod Path objektů na stringy pro load_model
                self._model = load_model(str(checkpoint_path), str(config_path))
                self._model.remove_weight_norm()  # Odstranění weight norm pro inference
                self._model.eval()
                if torch.cuda.is_available():
                    self._model = self._model.cuda()
                checkpoint_type = "lokálního checkpointu (.pkl)" if checkpoint_path.suffix == ".pkl" else "HuggingFace cache (.pth)"
                print(f"✅ HiFi-GAN model načten z {checkpoint_type}")
                self._model_loaded = True
                return True
            else:
                # Jiné implementace (hifigan-direct atd.) - zatím neimplementováno
                print("⚠️  Jiné HiFi-GAN implementace zatím nejsou podporovány")
                self._model_loaded = True
                return False

        except Exception as e:
            print(f"⚠️  Chyba při načítání HiFi-GAN modelu: {e}")
            self._model_loaded = True
            return False

    @property
    def available(self) -> bool:
        """Vrací True pokud je HiFi-GAN dostupný"""
        return self._available

    def is_available(self) -> bool:
        """Vrací True pokud je HiFi-GAN dostupný a načtený"""
        if not self._available:
            return False
        return self._load_model()

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
        original_audio: Optional[np.ndarray] = None,
        refinement_intensity: Optional[float] = None,
        normalize_output: Optional[bool] = None,
        normalize_gain: Optional[float] = None
    ) -> Optional[np.ndarray]:
        """
        Převádí mel-spectrogram zpět na audio pomocí HiFi-GAN

        Args:
            mel_log: Log-mel spectrogram (numpy array, shape: [n_mels, time])
            sample_rate: Sample rate výstupního audio
            original_audio: Původní audio pro blending (volitelné)
            refinement_intensity: Intenzita refinementu (0.0-1.0, None = použít config výchozí)
            normalize_output: Normalizovat výstup (None = použít config výchozí)
            normalize_gain: Gain pro normalizaci (0.0-1.0, None = použít config výchozí)

        Returns:
            Vygenerované audio jako numpy array, nebo None pokud selže
        """
        if not self.is_available():
            return None

        # Použij per-request parametry nebo fallback na config výchozí
        intensity = refinement_intensity if refinement_intensity is not None else config.HIFIGAN_REFINEMENT_INTENSITY
        do_normalize = normalize_output if normalize_output is not None else config.HIFIGAN_NORMALIZE_OUTPUT
        gain = normalize_gain if normalize_gain is not None else config.HIFIGAN_NORMALIZE_GAIN

        try:
            if self._parallel_wavegan_available and self._model is not None:
                # Převod mel_log na torch tensor
                # parallel-wavegan očekává mel v lineárním škálování, ne log
                # (ale to závisí na konkrétním modelu - některé modely očekávají log-mel)
                # Pro bezpečnost zkusíme obě varianty
                mel_tensor = torch.from_numpy(mel_log.astype(np.float32)).unsqueeze(0)
                if torch.cuda.is_available():
                    mel_tensor = mel_tensor.cuda()

                # Inference
                with torch.no_grad():
                    # Některé modely očekávají exponenciální transformaci (pokud je mel_log skutečně log)
                    # Zkusíme přímo (pokud model očekává log-mel)
                    try:
                        vocoded = self._model.inference(mel_tensor).squeeze().cpu().numpy()
                    except Exception:
                        # Pokud selže, zkusíme exponenciální transformaci
                        mel_exp = np.exp(mel_log)
                        mel_tensor = torch.from_numpy(mel_exp.astype(np.float32)).unsqueeze(0)
                        if torch.cuda.is_available():
                            mel_tensor = mel_tensor.cuda()
                        vocoded = self._model.inference(mel_tensor).squeeze().cpu().numpy()

                # Resampling na target sample rate pokud je potřeba
                # (parallel-wavegan typicky generuje 22050 Hz, ale můžeme mít jiný target)
                if sample_rate != 22050:
                    import librosa
                    vocoded = librosa.resample(vocoded, orig_sr=22050, target_sr=sample_rate)

                # Blending s original_audio pokud je zadán a intensity < 1.0
                if original_audio is not None and intensity < 1.0:
                    # Zajistíme stejnou délku
                    min_len = min(len(vocoded), len(original_audio))
                    vocoded = vocoded[:min_len]
                    original_audio = original_audio[:min_len]
                    # Blend
                    vocoded = intensity * vocoded + (1.0 - intensity) * original_audio

                # Normalizace výstupu
                if do_normalize:
                    # Headroom ceiling - pouze ztlumit, nikdy nezesilovat (stejně jako finální headroom)
                    # POZOR: Původní implementace zesilovala audio pokud peak < gain, což způsobovalo přebuzení!
                    # Řešení: použít headroom ceiling approach - pouze ztlumit pokud peak přesáhl cíl
                    peak = np.max(np.abs(vocoded))
                    if peak > 0:
                        target_peak = gain  # gain je cílový peak (např. 0.95 = -0.45 dB)
                        # Pouze ztlumit pokud peak přesáhl cíl, nikdy nezesilovat
                        if peak > target_peak:
                            vocoded = vocoded * (target_peak / peak)
                        # Pokud je peak < target_peak, nic neděláme (nezesilujeme - to by způsobilo přebuzení)

                return vocoded
            else:
                print("⚠️  HiFi-GAN model není načten")
                return None

        except Exception as e:
            print(f"⚠️  HiFi-GAN vocoding selhal: {e}")
            import traceback
            traceback.print_exc()
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
