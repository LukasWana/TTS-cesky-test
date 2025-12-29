"""
Model Manager - správa XTTS modelu
"""
import asyncio
from pathlib import Path
from typing import Optional
import torch
from TTS.api import TTS

from backend.config import (
    DEVICE,
    XTTS_MODEL_NAME,
    USE_SMALL_MODELS,
    ENABLE_CPU_OFFLOAD,
    DEVICE_FORCED,
    FORCE_DEVICE,
    TTS_SPEED,
    TTS_TEMPERATURE,
    TTS_LENGTH_PENALTY,
    TTS_REPETITION_PENALTY,
    TTS_TOP_K,
    TTS_TOP_P,
    OUTPUTS_DIR,
)


class ModelManager:
    """Třída pro správu XTTS modelu"""

    def __init__(self, device: str = None):
        """
        Args:
            device: Device pro model (cuda/cpu)
        """
        self.model: Optional[TTS] = None
        self.device = device or DEVICE
        self.is_loading = False
        self.is_loaded = False

    async def load_model(self):
        """Načte XTTS-v2 model asynchronně"""
        if self.is_loaded:
            return

        if self.is_loading:
            # Počkej až se model načte
            while self.is_loading:
                await asyncio.sleep(0.5)
            return

        self.is_loading = True

        try:
            print(f"Loading XTTS-v2 on {self.device}...")

            # Načtení modelu v thread poolu (TTS není async)
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None,
                self._load_model_sync
            )

            self.is_loaded = True
            print("Model loaded successfully!")

        except Exception as e:
            print(f"Error loading model: {str(e)}")
            raise
        finally:
            self.is_loading = False

    def _load_model_sync(self) -> TTS:
        """Synchronní načtení modelu z Hugging Face nebo lokální cache"""
        print(f"Loading model: {XTTS_MODEL_NAME}")
        print("Model bude stažen z Hugging Face, pokud není v cache...")

        try:
            # Zkus nejprve TTS registry název (stabilnější)
            if XTTS_MODEL_NAME.startswith("coqui/"):
                # Převod z Hugging Face formátu na TTS registry
                model_name = "tts_models/multilingual/multi-dataset/xtts_v2"
                print(f"Trying TTS registry name: {model_name}")
            else:
                model_name = XTTS_MODEL_NAME

            # Načtení modelu s explicitním nastavením
            # Použijeme GPU pouze pokud je device nastaven na "cuda"
            use_gpu = (self.device == "cuda" and torch.cuda.is_available())
            model = TTS(
                model_name=model_name,
                progress_bar=True
            )

            # Optimalizace pro GPU s omezenou VRAM (6GB)
            if use_gpu and (USE_SMALL_MODELS or ENABLE_CPU_OFFLOAD):
                print("Applying GPU memory optimizations for 6GB VRAM...")
                if hasattr(model, 'synthesizer') and hasattr(model.synthesizer, 'tts_model'):
                    # Offload části modelu na CPU pokud je potřeba
                    if ENABLE_CPU_OFFLOAD:
                        print("CPU offload enabled - parts of model will be on CPU")

            # Explicitní přesun na device
            if hasattr(model, 'to'):
                model.to(self.device)
            elif hasattr(model, 'model') and hasattr(model.model, 'to'):
                model.model.to(self.device)

            return model

        except Exception as e1:
            print(f"First attempt failed: {str(e1)}")
            # Fallback: zkus přímo Hugging Face model
            try:
                print(f"Trying direct Hugging Face model: {XTTS_MODEL_NAME}")
                # Použijeme GPU pouze pokud je device nastaven na "cuda"
                use_gpu = (self.device == "cuda" and torch.cuda.is_available())
                model = TTS(
                    model_name=XTTS_MODEL_NAME,
                    progress_bar=True
                )
                if hasattr(model, 'to'):
                    model.to(self.device)
                elif hasattr(model, 'model') and hasattr(model.model, 'to'):
                    model.model.to(self.device)
                return model
            except Exception as e2:
                print(f"Both attempts failed. Error 1: {str(e1)}, Error 2: {str(e2)}")
                raise Exception(f"Failed to load model: {str(e2)}")

    async def warmup(self, demo_voice_path: Optional[str] = None, generate_func=None):
        """
        Zahřeje model prvním inference

        Args:
            demo_voice_path: Cesta k demo hlasu pro warmup
            generate_func: Funkce pro generování (z XTTSEngine)
        """
        if not self.is_loaded:
            await self.load_model()

        if demo_voice_path and Path(demo_voice_path).exists() and generate_func:
            try:
                # Generuj warmup audio s krátkým textem
                warmup_output = await generate_func(
                    text="Warmup.",
                    speaker_wav=demo_voice_path,
                    language="cs",
                    speed=TTS_SPEED,
                    temperature=TTS_TEMPERATURE,
                    length_penalty=TTS_LENGTH_PENALTY,
                    repetition_penalty=TTS_REPETITION_PENALTY,
                    top_k=TTS_TOP_K,
                    top_p=TTS_TOP_P
                )
                # Smazat warmup soubor, aby se neukládal do historie
                warmup_path = Path(warmup_output)
                if warmup_path.exists():
                    try:
                        warmup_path.unlink()
                    except Exception:
                        pass  # Ignoruj chyby při mazání
                print("Model warmup dokončen")
            except Exception as e:
                print(f"Warmup selhal: {str(e)}")

    def get_status(self, vocoder=None) -> dict:
        """Vrátí status modelu"""
        return {
            "loaded": self.is_loaded,
            "loading": self.is_loading,
            "device": self.device,
            "cuda_available": torch.cuda.is_available(),
            "device_forced": DEVICE_FORCED,
            "force_device": FORCE_DEVICE,
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "hifigan_available": vocoder.available if vocoder and hasattr(vocoder, 'available') else False
        }







