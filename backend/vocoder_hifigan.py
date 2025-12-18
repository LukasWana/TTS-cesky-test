"""
HiFi-GAN Vocoder wrapper pro vylepšení kvality audio
"""
import torch
import numpy as np
from pathlib import Path
from typing import Optional
import backend.config as config
from backend.config import (
    ENABLE_HIFIGAN,
    HIFIGAN_MODEL_PATH,
    OUTPUT_SAMPLE_RATE,
    DEVICE,
    MODELS_DIR,
    HIFIGAN_PREFERRED_TYPE,
    HIFIGAN_N_MELS,
    HIFIGAN_N_FFT,
    HIFIGAN_HOP_LENGTH,
    HIFIGAN_WIN_LENGTH,
    HIFIGAN_FMIN,
    HIFIGAN_FMAX,
    HIFIGAN_ENABLE_BATCH,
    HIFIGAN_BATCH_SIZE
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

    # Additional support for vtuber-plan HiFi-GAN via torch.hub
    try:
        import torch
        VTUBER_PLAN_AVAILABLE = True
    except ImportError:
        VTUBER_PLAN_AVAILABLE = False

    HIFIGAN_AVAILABLE = PARALLEL_WAVEGAN_AVAILABLE or HIFIGAN_DIRECT_AVAILABLE or VTUBER_PLAN_AVAILABLE
except:
    HIFIGAN_AVAILABLE = False
    PARALLEL_WAVEGAN_AVAILABLE = False
    HIFIGAN_DIRECT_AVAILABLE = False
    VTUBER_PLAN_AVAILABLE = False

if not HIFIGAN_AVAILABLE:
    print("Warning: HiFi-GAN není dostupný. Pro použití nainstalujte parallel-wavegan nebo hifigan.")


class HiFiGANVocoder:
    """Wrapper pro HiFi-GAN vocoder"""

    def __init__(self):
        self.model = None
        self.available = HIFIGAN_AVAILABLE and ENABLE_HIFIGAN
        self.model_path = HIFIGAN_MODEL_PATH
        self._model_loaded = False
        self.preferred_type = HIFIGAN_PREFERRED_TYPE
        # Pozn.: intensity/normalizace/gain se mohou měnit za běhu (UI → backend.config),
        # proto je bereme dynamicky z modulu `backend.config` ve `vocode()`.
        self.refinement_intensity = config.HIFIGAN_REFINEMENT_INTENSITY
        self.normalize_output = config.HIFIGAN_NORMALIZE_OUTPUT
        self.normalize_gain = config.HIFIGAN_NORMALIZE_GAIN
        self.mel_params = {
            "n_mels": HIFIGAN_N_MELS,
            "n_fft": HIFIGAN_N_FFT,
            "hop_length": HIFIGAN_HOP_LENGTH,
            "win_length": HIFIGAN_WIN_LENGTH,
            "fmin": HIFIGAN_FMIN,
            "fmax": HIFIGAN_FMAX
        }
        self.enable_batch = HIFIGAN_ENABLE_BATCH
        self.batch_size = HIFIGAN_BATCH_SIZE

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

            # Pokud je nastaven preferred_type, zkus ho použít jako první
            if self.preferred_type != "auto":
                if self.preferred_type == "parallel-wavegan" and PARALLEL_WAVEGAN_AVAILABLE:
                    success = self._load_parallel_wavegan(model_path)
                    if success:
                        self._model_loaded = True
                        return True
                elif self.preferred_type == "vtuber-plan" and VTUBER_PLAN_AVAILABLE:
                    success = self._load_vtuber_plan()
                    if success:
                        self._model_loaded = True
                        return True
                elif self.preferred_type == "hifigan-direct" and HIFIGAN_DIRECT_AVAILABLE:
                    success = self._load_hifigan_direct(model_path)
                    if success:
                        self._model_loaded = True
                        return True

            # Pokud preferred_type selhal nebo je "auto", zkus automaticky
            if not success:
                # Zkus různé metody v pořadí podle dostupnosti a spolehlivosti
                if PARALLEL_WAVEGAN_AVAILABLE:
                    success = self._load_parallel_wavegan(model_path)
                    if success:
                        self._model_loaded = True
                        return True

                # Fallback na vtuber-plan (dostupný přes torch.hub)
                if not success and VTUBER_PLAN_AVAILABLE:
                    print("⚠️ parallel-wavegan selhal, zkouším vtuber-plan model...")
                    success = self._load_vtuber_plan()
                    if success:
                        self._model_loaded = True
                        return True

                # Fallback na přímou hifigan knihovnu
                if not success and HIFIGAN_DIRECT_AVAILABLE:
                    print("⚠️ vtuber-plan selhal, zkouším přímou hifigan knihovnu...")
                    success = self._load_hifigan_direct(model_path)
                    if success:
                        self._model_loaded = True
                        return True

            if not success:
                print("Warning: Žádná HiFi-GAN implementace se nepodařila načíst")
                print("   HiFi-GAN refinement bude vypnutý")
                return False

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
                # Zkus nejprve parallel-wavegan pretrained modely
                try:
                    from parallel_wavegan.utils import download_pretrained_model
                    print("📥 Stahuji HiFi-GAN model pomocí parallel-wavegan pretrained...")
                    # Použijeme univerzální model - ljspeech je kompatibilní s většinou TTS
                    model_path = download_pretrained_model("ljspeech_parallel_wavegan.v1")
                    print(f"✅ Model stažen: {model_path}")
                except Exception as e:
                    print(f"⚠️ parallel-wavegan download selhal: {e}")
                    # Fallback na vlastní download metodu
                    model_path = self._download_default_model()
                    if model_path is None:
                        print("Warning: Nepodařilo se stáhnout výchozí HiFi-GAN model")
                        print("   Zkusím použít vtuber-plan model jako fallback...")
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
        Stáhne výchozí HiFi-GAN model z různých zdrojů

        Returns:
            Cesta k modelu nebo None pokud selže
        """
        # Poznámka: parallel-wavegan pretrained modely se stahují přímo v _load_parallel_wavegan
        # Tato metoda je fallback pro případ, že parallel-wavegan není dostupný

        # Fallback: Zkus Hugging Face modely (pokud jsou dostupné)
        try:
            from huggingface_hub import snapshot_download

            # Modely, které by mohly být dostupné (ale nejsou garantované)
            # Poznámka: Většina HiFi-GAN modelů není přímo na Hugging Face
            # Lepší je použít parallel-wavegan nebo vtuber-plan
            model_names = []

            cache_dir = MODELS_DIR / "hifigan"
            cache_dir.mkdir(parents=True, exist_ok=True)

            for model_name in model_names:
                try:
                    print(f"📥 Zkouším stáhnout HiFi-GAN model z Hugging Face: {model_name}")
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
                    if not checkpoints:
                        checkpoints = list(model_dir.glob("*.ckpt"))

                    if checkpoints:
                        print(f"✅ Model stažen: {checkpoints[0]}")
                        return str(checkpoints[0])
                    else:
                        # Pokud není checkpoint, vrať adresář
                        print(f"✅ Model stažen do adresáře: {downloaded_path}")
                        return downloaded_path
                except Exception as e:
                    print(f"⚠️ Model {model_name} selhal: {e}")
                    continue

        except ImportError:
            print("Warning: huggingface_hub není dostupný pro automatické stahování")
            print("   Nainstalujte: pip install huggingface_hub")
        except Exception as e:
            print(f"⚠️ Warning: Stahování z Hugging Face selhalo: {e}")

        # Pokud vše selže, vrať None
        # Systém zkusí použít vtuber-plan jako automatický fallback
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
    def _load_vtuber_plan(self) -> bool:
        """Load HiFi-GAN model from vtuber-plan repository via torch.hub.
        Returns True on success, False otherwise.
        """
        try:
            # vtuber-plan provides a torch.hub entry point
            # Zkusíme různé varianty modelu
            model_variants = ['hifigan_48k', 'hifigan', 'generator']

            for variant in model_variants:
                try:
                    print(f"📥 Zkouším načíst vtuber-plan HiFi-GAN model: {variant}...")
                    model = torch.hub.load('vtuber-plan/hifi-gan', variant, force_reload=False, trust_repo=True)
                    self.model = model.to(DEVICE)
                    self.model.eval()
                    print(f"✅ HiFi-GAN model načten z vtuber-plan via torch.hub ({variant})")
                    return True
                except Exception as e:
                    if variant != model_variants[-1]:  # Nezobrazuj error pro poslední variantu
                        print(f"⚠️ Varianta {variant} selhala: {e}, zkouším další...")
                        continue
                    else:
                        raise e
            return False
        except Exception as e:
            print(f"⚠️ Error loading vtuber-plan HiFi-GAN model: {e}")
            return False
    def vocode(
        self,
        mel_spectrogram: np.ndarray,
        sample_rate: int = OUTPUT_SAMPLE_RATE,
        original_audio: Optional[np.ndarray] = None
    ) -> Optional[np.ndarray]:
        """
        Převede mel-spectrogram na audio pomocí HiFi-GAN

        Args:
            mel_spectrogram: Mel-spectrogram (shape: [n_mels, time] nebo [batch, n_mels, time])
            sample_rate: Sample rate výstupního audio
            original_audio: Původní audio pro blending (pokud je refinement_intensity < 1.0)

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
            # Použít aktuální hodnoty z configu (mohly být změněny z UI)
            refinement_intensity = config.HIFIGAN_REFINEMENT_INTENSITY
            normalize_output = config.HIFIGAN_NORMALIZE_OUTPUT
            normalize_gain = config.HIFIGAN_NORMALIZE_GAIN

            # Vocode pomocí HiFi-GAN
            if PARALLEL_WAVEGAN_AVAILABLE and hasattr(self.model, 'inference'):
                refined_audio = self._vocode_parallel_wavegan(mel_spectrogram, sample_rate)
            elif HIFIGAN_DIRECT_AVAILABLE or VTUBER_PLAN_AVAILABLE:
                refined_audio = self._vocode_hifigan_direct(mel_spectrogram, sample_rate)
            else:
                return None

            if refined_audio is None:
                return None

            # Normalizace výstupu (pokud je zapnuto)
            if normalize_output:
                if np.max(np.abs(refined_audio)) > 0:
                    refined_audio = refined_audio / np.max(np.abs(refined_audio)) * normalize_gain

            # Blending s původním audio (pokud je zadáno a intensity < 1.0)
            if original_audio is not None and refinement_intensity < 1.0:
                # Zajistit stejnou délku
                min_len = min(len(refined_audio), len(original_audio))
                refined_audio = refined_audio[:min_len]
                original_audio = original_audio[:min_len]

                # Blendování
                blended = (refinement_intensity * refined_audio +
                          (1.0 - refinement_intensity) * original_audio)
                return blended

            return refined_audio
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

