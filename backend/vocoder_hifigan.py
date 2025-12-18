"""
HiFi-GAN Vocoder wrapper pro vylepšení kvality audio
"""
import torch
import numpy as np
from pathlib import Path
from typing import Optional
from backend.config import (
    ENABLE_HIFIGAN,
    HIFIGAN_MODEL_PATH,
    OUTPUT_SAMPLE_RATE,
    DEVICE,
    MODELS_DIR
)

try:
    # Zkus importovat HiFi-GAN (různé možné implementace)
    try:
        from parallel_wavegan.utils import load_model
        from parallel_wavegan.utils import download_pretrained_model
        PARALLEL_WAVEGAN_AVAILABLE = True
    except ImportError:
        PARALLEL_WAVEGAN_AVAILABLE = False

    try:
        import hifigan
        HIFIGAN_DIRECT_AVAILABLE = True
    except ImportError:
        HIFIGAN_DIRECT_AVAILABLE = False

    HIFIGAN_AVAILABLE = PARALLEL_WAVEGAN_AVAILABLE or HIFIGAN_DIRECT_AVAILABLE
except:
    HIFIGAN_AVAILABLE = False
    PARALLEL_WAVEGAN_AVAILABLE = False
    HIFIGAN_DIRECT_AVAILABLE = False

if not HIFIGAN_AVAILABLE:
    print("Warning: HiFi-GAN není dostupný. Pro použití nainstalujte parallel-wavegan nebo hifigan.")


class HiFiGANVocoder:
    """Wrapper pro HiFi-GAN vocoder"""

    def __init__(self):
        self.model = None
        self.available = HIFIGAN_AVAILABLE and ENABLE_HIFIGAN
        self.model_path = HIFIGAN_MODEL_PATH
        self._model_loaded = False

    def load_model(self, model_path: Optional[str] = None):
        """
        Načte HiFi-GAN model

        Args:
            model_path: Cesta k modelu (None = použít výchozí nebo stáhnout)

        Returns:
            True pokud se podařilo načíst, False jinak
        """
        if not self.available:
            print("Warning: HiFi-GAN není dostupný nebo není zapnutý")
            return False

        if self._model_loaded and self.model is not None:
            return True

        try:
            success = False
            if PARALLEL_WAVEGAN_AVAILABLE:
                success = self._load_parallel_wavegan(model_path)
            elif HIFIGAN_DIRECT_AVAILABLE:
                success = self._load_hifigan_direct(model_path)
            else:
                print("Warning: Žádná HiFi-GAN implementace není dostupná")
                return False

            if success:
                self._model_loaded = True
            return success
        except Exception as e:
            print(f"Error loading HiFi-GAN model: {e}")
            return False

    def _ensure_model_loaded(self):
        """Zajistí, že je model načten (lazy loading)"""
        if not self._model_loaded and self.available:
            self.load_model()

    def _load_parallel_wavegan(self, model_path: Optional[str] = None) -> bool:
        """Načte model pomocí parallel-wavegan"""
        try:
            if model_path is None:
                model_path = self.model_path

            # Pokud není cesta zadána, zkus stáhnout výchozí model
            if model_path is None:
                model_path = self._download_default_model()
                if model_path is None:
                    print("Warning: Nepodařilo se stáhnout výchozí HiFi-GAN model")
                    return False

            # Pokud cesta existuje jako adresář, najdi checkpoint
            model_path_obj = Path(model_path)
            if model_path_obj.exists() and model_path_obj.is_dir():
                # Hledej checkpoint soubory
                checkpoints = list(model_path_obj.glob("*.pkl"))
                if not checkpoints:
                    checkpoints = list(model_path_obj.glob("checkpoint*.pth"))
                if not checkpoints:
                    checkpoints = list(model_path_obj.glob("*.pt"))

                if checkpoints:
                    model_path = str(checkpoints[0])
                    print(f"📁 Nalezen checkpoint: {model_path}")
                else:
                    # Zkus najít config.yaml a použít download_pretrained_model
                    config_path = model_path_obj / "config.yaml"
                    if config_path.exists():
                        try:
                            print(f"📥 Stahuji HiFi-GAN model pomocí parallel-wavegan...")
                            model_path = download_pretrained_model(str(model_path_obj))
                            print(f"✅ Model stažen do: {model_path}")
                        except Exception as e:
                            print(f"Warning: Failed to download model: {e}")
                            return False

            if model_path and Path(model_path).exists():
                self.model = load_model(model_path)
                self.model = self.model.to(DEVICE)
                self.model.eval()
                print("✅ HiFi-GAN model načten (parallel-wavegan)")
                return True
            else:
                print("Warning: HiFi-GAN model path není zadán nebo neexistuje")
                return False
        except Exception as e:
            print(f"Error loading parallel-wavegan model: {e}")
            return False

    def _download_default_model(self) -> Optional[str]:
        """
        Stáhne výchozí HiFi-GAN model z Hugging Face

        Returns:
            Cesta k modelu nebo None pokud selže
        """
        try:
            from huggingface_hub import snapshot_download

            # Výchozí HiFi-GAN model pro TTS (kompatibilní s XTTS)
            # Použijeme model, který je kompatibilní s mel-spectrogramy z TTS
            model_name = "kan-bayashi/jsut_hifigan.v1"

            print(f"📥 Stahuji HiFi-GAN model z Hugging Face: {model_name}")

            cache_dir = MODELS_DIR / "hifigan"
            cache_dir.mkdir(parents=True, exist_ok=True)

            # Stáhni model
            downloaded_path = snapshot_download(
                repo_id=model_name,
                cache_dir=str(cache_dir),
                local_files_only=False
            )

            # Najdi checkpoint v staženém adresáři
            model_dir = Path(downloaded_path)
            checkpoints = list(model_dir.glob("*.pkl"))
            if not checkpoints:
                checkpoints = list(model_dir.glob("checkpoint*.pth"))
            if not checkpoints:
                checkpoints = list(model_dir.glob("*.pt"))

            if checkpoints:
                print(f"✅ Model stažen: {checkpoints[0]}")
                return str(checkpoints[0])
            else:
                # Pokud není checkpoint, vrať adresář (parallel-wavegan ho najde)
                print(f"✅ Model stažen do adresáře: {downloaded_path}")
                return downloaded_path

        except ImportError:
            print("Warning: huggingface_hub není dostupný pro automatické stahování")
            print("   Nainstalujte: pip install huggingface_hub")
            return None
        except Exception as e:
            print(f"Error downloading HiFi-GAN model: {e}")
            return None

    def _download_default_model(self) -> Optional[str]:
        """
        Stáhne výchozí HiFi-GAN model z Hugging Face

        Returns:
            Cesta k modelu nebo None pokud selže
        """
        try:
            from huggingface_hub import snapshot_download

            # Výchozí HiFi-GAN model pro TTS (kompatibilní s XTTS)
            # Použijeme model, který je kompatibilní s mel-spectrogramy z TTS
            model_name = "kan-bayashi/jsut_hifigan.v1"

            print(f"📥 Stahuji HiFi-GAN model z Hugging Face: {model_name}")

            cache_dir = MODELS_DIR / "hifigan"
            cache_dir.mkdir(parents=True, exist_ok=True)

            # Stáhni model
            downloaded_path = snapshot_download(
                repo_id=model_name,
                cache_dir=str(cache_dir),
                local_files_only=False
            )

            # Najdi checkpoint v staženém adresáři
            model_dir = Path(downloaded_path)
            checkpoints = list(model_dir.glob("*.pkl"))
            if not checkpoints:
                checkpoints = list(model_dir.glob("checkpoint*.pth"))
            if not checkpoints:
                checkpoints = list(model_dir.glob("*.pt"))

            if checkpoints:
                print(f"✅ Model stažen: {checkpoints[0]}")
                return str(checkpoints[0])
            else:
                # Pokud není checkpoint, vrať adresář (parallel-wavegan ho najde)
                print(f"✅ Model stažen do adresáře: {downloaded_path}")
                return downloaded_path

        except ImportError:
            print("Warning: huggingface_hub není dostupný pro automatické stahování")
            print("   Nainstalujte: pip install huggingface_hub")
            return None
        except Exception as e:
            print(f"Error downloading HiFi-GAN model: {e}")
            return None

    def _load_hifigan_direct(self, model_path: Optional[str] = None) -> bool:
        """Načte model pomocí přímé hifigan knihovny"""
        try:
            if model_path is None:
                model_path = self.model_path

            if model_path and Path(model_path).exists():
                # Načtení pomocí hifigan knihovny
                self.model = hifigan.load_model(model_path)
                print("✅ HiFi-GAN model načten (hifigan)")
                return True
            else:
                print("Warning: HiFi-GAN model path není zadán nebo neexistuje")
                return False
        except Exception as e:
            print(f"Error loading hifigan model: {e}")
            return False

    def vocode(
        self,
        mel_spectrogram: np.ndarray,
        sample_rate: int = OUTPUT_SAMPLE_RATE
    ) -> Optional[np.ndarray]:
        """
        Převede mel-spectrogram na audio pomocí HiFi-GAN

        Args:
            mel_spectrogram: Mel-spectrogram (shape: [n_mels, time] nebo [batch, n_mels, time])
            sample_rate: Sample rate výstupního audio

        Returns:
            Audio data nebo None pokud selže
        """
        if not self.available:
            return None

        # Zajistit, že je model načten
        self._ensure_model_loaded()

        if self.model is None:
            return None

        try:
            if PARALLEL_WAVEGAN_AVAILABLE:
                return self._vocode_parallel_wavegan(mel_spectrogram, sample_rate)
            elif HIFIGAN_DIRECT_AVAILABLE:
                return self._vocode_hifigan_direct(mel_spectrogram, sample_rate)
            else:
                return None
        except Exception as e:
            print(f"Error during HiFi-GAN vocoding: {e}")
            return None

    def _vocode_parallel_wavegan(
        self,
        mel_spectrogram: np.ndarray,
        sample_rate: int
    ) -> Optional[np.ndarray]:
        """Vocode pomocí parallel-wavegan"""
        try:
            # Převod na tensor
            if len(mel_spectrogram.shape) == 2:
                mel_spectrogram = mel_spectrogram[np.newaxis, :, :]  # Přidat batch dimenzi

            mel_tensor = torch.from_numpy(mel_spectrogram).float().to(DEVICE)

            # Generování
            with torch.no_grad():
                audio = self.model.inference(mel_tensor)

            # Převod zpět na numpy
            audio_np = audio.cpu().numpy()

            # Pokud je batch dimenze, vezmi první
            if len(audio_np.shape) > 1:
                audio_np = audio_np[0]

            return audio_np
        except Exception as e:
            print(f"Error in parallel-wavegan vocoding: {e}")
            return None

    def _vocode_hifigan_direct(
        self,
        mel_spectrogram: np.ndarray,
        sample_rate: int
    ) -> Optional[np.ndarray]:
        """Vocode pomocí přímé hifigan knihovny"""
        try:
            # Převod na tensor pokud je potřeba
            if isinstance(mel_spectrogram, np.ndarray):
                mel_tensor = torch.from_numpy(mel_spectrogram).float()
            else:
                mel_tensor = mel_spectrogram

            # Generování
            with torch.no_grad():
                audio = self.model(mel_tensor)

            # Převod zpět na numpy
            if isinstance(audio, torch.Tensor):
                audio_np = audio.cpu().numpy()
            else:
                audio_np = audio

            # Normalizace
            if len(audio_np.shape) > 1:
                audio_np = audio_np[0]

            return audio_np
        except Exception as e:
            print(f"Error in hifigan direct vocoding: {e}")
            return None

    def is_available(self) -> bool:
        """Vrátí True pokud je HiFi-GAN dostupný a načtený"""
        if not self.available:
            return False
        # Zajistit, že je model načten
        self._ensure_model_loaded()
        return self.model is not None


# Globální instance
_hifigan_vocoder = None


def get_hifigan_vocoder() -> HiFiGANVocoder:
    """Vrátí globální instanci HiFi-GAN vocoderu"""
    global _hifigan_vocoder
    if _hifigan_vocoder is None:
        _hifigan_vocoder = HiFiGANVocoder()
    return _hifigan_vocoder

