"""
Konfigurační soubor pro XTTS-v2 Demo aplikaci
"""
import os
import torch
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
MODELS_DIR = BASE_DIR / "models"
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUTS_DIR = BASE_DIR / "outputs"
DEMO_VOICES_DIR = BASE_DIR / "frontend" / "assets" / "demo-voices"

# Vytvoření adresářů pokud neexistují
MODELS_DIR.mkdir(exist_ok=True)
UPLOADS_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)
DEMO_VOICES_DIR.mkdir(parents=True, exist_ok=True)

# Device detection with manual override
# Můžete vynutit device přes environment variable:
# FORCE_DEVICE=cpu  -> vynutí CPU (i když je GPU dostupné)
# FORCE_DEVICE=cuda -> vynutí GPU (pokud je dostupné, jinak fallback na CPU)
# FORCE_DEVICE=auto -> automatická detekce (výchozí)
FORCE_DEVICE = os.getenv("FORCE_DEVICE", "auto").lower()

if FORCE_DEVICE == "cpu":
    DEVICE = "cpu"
    print("⚠️  Device vynucen na CPU (FORCE_DEVICE=cpu)")
elif FORCE_DEVICE == "cuda":
    if torch.cuda.is_available():
        DEVICE = "cuda"
        print("✅ Device vynucen na GPU (FORCE_DEVICE=cuda)")
    else:
        DEVICE = "cpu"
        print("⚠️  GPU není dostupné, používá se CPU (FORCE_DEVICE=cuda byl ignorován)")
else:
    # Automatická detekce (výchozí)
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    if DEVICE == "cuda":
        print("✅ Automatická detekce: GPU dostupné, používá se CUDA")
    else:
        print("ℹ️  Automatická detekce: GPU nedostupné, používá se CPU")

# GPU memory optimization for 6GB VRAM cards (RTX 3060, etc.)
# Pokud máte GPU s 6GB VRAM, můžete použít tyto optimalizace:
USE_SMALL_MODELS = os.getenv("SUNO_USE_SMALL_MODELS", "False").lower() == "true"
ENABLE_CPU_OFFLOAD = os.getenv("SUNO_OFFLOAD_CPU", "False").lower() == "true"

# Pro RTX 3060 6GB doporučujeme:
# export SUNO_USE_SMALL_MODELS=True  # Použít menší modely
# export SUNO_OFFLOAD_CPU=True       # Offload části modelu na CPU

# XTTS-v2 model configuration
# Možnosti:
# 1. Hugging Face model (doporučeno) - automaticky stáhne z HF
# 2. Lokální model path
# 3. TTS model registry name
# Zkus nejprve TTS registry (stabilnější), pak Hugging Face
XTTS_MODEL_NAME = os.getenv(
    "XTTS_MODEL_NAME",
    "tts_models/multilingual/multi-dataset/xtts_v2"  # TTS registry (doporučeno)
)
# Alternativně můžete použít:
# XTTS_MODEL_NAME = "coqui/XTTS-v2"  # Hugging Face model identifier
MODEL_CACHE_DIR = str(MODELS_DIR)

# Audio processing settings
TARGET_SAMPLE_RATE = 22050
TARGET_CHANNELS = 1  # mono
MIN_VOICE_DURATION = 6.0  # sekundy
MAX_TEXT_LENGTH = 500  # znaků

# TTS generation parameters (výchozí hodnoty)
TTS_SPEED = float(os.getenv("TTS_SPEED", "1.0"))  # Rychlost řeči (0.5-2.0)
TTS_TEMPERATURE = float(os.getenv("TTS_TEMPERATURE", "0.7"))  # Teplota (0.0-1.0)
TTS_LENGTH_PENALTY = float(os.getenv("TTS_LENGTH_PENALTY", "1.0"))  # Length penalty
TTS_REPETITION_PENALTY = float(os.getenv("TTS_REPETITION_PENALTY", "2.0"))  # Repetition penalty
TTS_TOP_K = int(os.getenv("TTS_TOP_K", "50"))  # Top-k sampling
TTS_TOP_P = float(os.getenv("TTS_TOP_P", "0.85"))  # Top-p sampling

# Supported audio formats
SUPPORTED_AUDIO_FORMATS = [".wav", ".mp3", ".m4a", ".ogg", ".flac"]

# API settings
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Export device info for status endpoint
DEVICE_FORCED = FORCE_DEVICE != "auto"

