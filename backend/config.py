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
    print("[WARN] Device vynucen na CPU (FORCE_DEVICE=cpu)")
elif FORCE_DEVICE == "cuda":
    if torch.cuda.is_available():
        DEVICE = "cuda"
        print("[OK] Device vynucen na GPU (FORCE_DEVICE=cuda)")
    else:
        DEVICE = "cpu"
        print("[WARN] GPU není dostupné, používá se CPU (FORCE_DEVICE=cuda byl ignorován)")
else:
    # Automatická detekce (výchozí)
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    if DEVICE == "cuda":
        print("[OK] Automatická detekce: GPU dostupné, používá se CUDA")
    else:
        print("[INFO] Automatická detekce: GPU nedostupné, používá se CPU")

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
TARGET_SAMPLE_RATE = 44100  # CD kvalita (44.1 kHz)
TARGET_CHANNELS = 1  # mono
MIN_VOICE_DURATION = 6.0  # sekundy
MAX_TEXT_LENGTH = 100000  # znaků

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

# Audio enhancement settings
ENABLE_AUDIO_ENHANCEMENT = os.getenv("ENABLE_AUDIO_ENHANCEMENT", "True").lower() == "true"
AUDIO_ENHANCEMENT_PRESET = os.getenv("AUDIO_ENHANCEMENT_PRESET", "natural")  # high_quality, natural, fast
OUTPUT_SAMPLE_RATE = int(os.getenv("OUTPUT_SAMPLE_RATE", "44100"))  # 22050, 24000, 44100 (výchozí: 44100 = CD kvalita)
ENABLE_EQ_CORRECTION = os.getenv("ENABLE_EQ_CORRECTION", "True").lower() == "true"
ENABLE_ADVANCED_NOISE_REDUCTION = os.getenv("ENABLE_ADVANCED_NOISE_REDUCTION", "False").lower() == "true"
ENABLE_DEESSER = os.getenv("ENABLE_DEESSER", "True").lower() == "true"

# Výstupní headroom (dB). Pomáhá proti "přebuzelému" pocitu i když to neklipuje.
# Doporučení: -6.0 dB (víc headroomu), případně -3.0 dB
OUTPUT_HEADROOM_DB = float(os.getenv("OUTPUT_HEADROOM_DB", "-6.0"))

# Multi-pass generování
ENABLE_MULTI_PASS = os.getenv("ENABLE_MULTI_PASS", "False").lower() == "true"
MULTI_PASS_COUNT = int(os.getenv("MULTI_PASS_COUNT", "3"))

# Voice Activity Detection
ENABLE_VAD = os.getenv("ENABLE_VAD", "True").lower() == "true"
VAD_AGGRESSIVENESS = int(os.getenv("VAD_AGGRESSIVENESS", "2"))  # 0-3

# Prosody Control
ENABLE_PROSODY_CONTROL = os.getenv("ENABLE_PROSODY_CONTROL", "True").lower() == "true"

# Phonetic Translation (fonetický přepis cizích slov)
ENABLE_PHONETIC_TRANSLATION = os.getenv("ENABLE_PHONETIC_TRANSLATION", "True").lower() == "true"

# Czech Text Processing (pokročilé předzpracování pomocí lookup tabulek)
ENABLE_CZECH_TEXT_PROCESSING = os.getenv("ENABLE_CZECH_TEXT_PROCESSING", "True").lower() == "true"

# Dialect Conversion (převod textu na nářečí)
ENABLE_DIALECT_CONVERSION = os.getenv("ENABLE_DIALECT_CONVERSION", "False").lower() == "true"
DIALECT_CODE = os.getenv("DIALECT_CODE", "standardni")  # standardni, moravske, hanacke, slezske, chodske, brnenske
DIALECT_INTENSITY = float(os.getenv("DIALECT_INTENSITY", "1.0"))  # 0.0-1.0 (1.0 = plný převod)

# Speaker Adaptation
ENABLE_SPEAKER_CACHE = os.getenv("ENABLE_SPEAKER_CACHE", "True").lower() == "true"
SPEAKER_CACHE_DIR = BASE_DIR / "speaker_cache"
SPEAKER_CACHE_DIR.mkdir(exist_ok=True)

# Reference voice (voice cloning) – příprava a quality gate
# Cíl: stabilnější klon hlasu (méně ticha/hudby, konzistentní loudness, lepší segmenty řeči)
ENABLE_REFERENCE_VOICE_PREP = os.getenv("ENABLE_REFERENCE_VOICE_PREP", "True").lower() == "true"
ENABLE_REFERENCE_VAD_SEGMENTATION = os.getenv("ENABLE_REFERENCE_VAD_SEGMENTATION", "True").lower() == "true"
REFERENCE_TARGET_DURATION_SEC = float(os.getenv("REFERENCE_TARGET_DURATION_SEC", "15.0"))  # doporučeno 10–30s
REFERENCE_SEGMENT_MIN_SEC = float(os.getenv("REFERENCE_SEGMENT_MIN_SEC", "0.7"))
REFERENCE_SEGMENT_MAX_SEC = float(os.getenv("REFERENCE_SEGMENT_MAX_SEC", "4.0"))
REFERENCE_MAX_SEGMENTS = int(os.getenv("REFERENCE_MAX_SEGMENTS", "10"))
REFERENCE_PAUSE_MS = int(os.getenv("REFERENCE_PAUSE_MS", "80"))
REFERENCE_CROSSFADE_MS = int(os.getenv("REFERENCE_CROSSFADE_MS", "30"))

# Loudness normalizace referenčního audia (FFmpeg loudnorm pokud je k dispozici)
ENABLE_REFERENCE_LOUDNORM = os.getenv("ENABLE_REFERENCE_LOUDNORM", "True").lower() == "true"
REFERENCE_LOUDNORM_I = float(os.getenv("REFERENCE_LOUDNORM_I", "-16.0"))     # Integrated loudness (LUFS)
REFERENCE_LOUDNORM_TP = float(os.getenv("REFERENCE_LOUDNORM_TP", "-1.5"))    # True peak (dBTP)
REFERENCE_LOUDNORM_LRA = float(os.getenv("REFERENCE_LOUDNORM_LRA", "11.0"))  # Loudness range

# Quality gate pro referenční audio
ENABLE_REFERENCE_QUALITY_GATE = os.getenv("ENABLE_REFERENCE_QUALITY_GATE", "True").lower() == "true"
ENABLE_REFERENCE_AUTO_ENHANCE = os.getenv("ENABLE_REFERENCE_AUTO_ENHANCE", "True").lower() == "true"
REFERENCE_ALLOW_POOR_BY_DEFAULT = os.getenv("REFERENCE_ALLOW_POOR_BY_DEFAULT", "False").lower() == "true"

# Vocoder Upgrade - HiFi-GAN
ENABLE_HIFIGAN = os.getenv("ENABLE_HIFIGAN", "True").lower() == "true"
HIFIGAN_MODEL_PATH = os.getenv("HIFIGAN_MODEL_PATH", None)

# HiFi-GAN nastavení
HIFIGAN_PREFERRED_TYPE = os.getenv("HIFIGAN_PREFERRED_TYPE", "auto").lower()  # auto, parallel-wavegan, vtuber-plan, hifigan-direct
HIFIGAN_REFINEMENT_INTENSITY = float(os.getenv("HIFIGAN_REFINEMENT_INTENSITY", "1.0"))  # 0.0-1.0 (1.0 = plný refinement, 0.0 = žádný)
HIFIGAN_NORMALIZE_OUTPUT = os.getenv("HIFIGAN_NORMALIZE_OUTPUT", "True").lower() == "true"
HIFIGAN_NORMALIZE_GAIN = float(os.getenv("HIFIGAN_NORMALIZE_GAIN", "0.95"))  # 0.0-1.0 (gain pro normalizaci)

# HiFi-GAN mel-spectrogram parametry
HIFIGAN_N_MELS = int(os.getenv("HIFIGAN_N_MELS", "80"))  # Počet mel bins
HIFIGAN_N_FFT = int(os.getenv("HIFIGAN_N_FFT", "1024"))  # FFT window size
HIFIGAN_HOP_LENGTH = int(os.getenv("HIFIGAN_HOP_LENGTH", "256"))  # Hop length
HIFIGAN_WIN_LENGTH = int(os.getenv("HIFIGAN_WIN_LENGTH", "1024"))  # Window length
HIFIGAN_FMIN = float(os.getenv("HIFIGAN_FMIN", "0.0"))  # Minimální frekvence
HIFIGAN_FMAX = float(os.getenv("HIFIGAN_FMAX", "8000.0"))  # Maximální frekvence

# HiFi-GAN batch processing (pro dlouhé audio)
HIFIGAN_ENABLE_BATCH = os.getenv("HIFIGAN_ENABLE_BATCH", "False").lower() == "true"
HIFIGAN_BATCH_SIZE = int(os.getenv("HIFIGAN_BATCH_SIZE", "1"))  # Batch size pro inference

# Batch Processing
ENABLE_BATCH_PROCESSING = os.getenv("ENABLE_BATCH_PROCESSING", "True").lower() == "true"
MAX_CHUNK_LENGTH = int(os.getenv("MAX_CHUNK_LENGTH", "200"))  # znaků
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "20"))  # znaků

# XTTS token limit (XTTS má tvrdý limit ~400 tokenů na jeden vstup)
# Pozn.: Používáme "cílový" limit o trochu menší kvůli prefixům / speciálním tokenům.
XTTS_MAX_TOKENS = int(os.getenv("XTTS_MAX_TOKENS", "400"))
XTTS_TOKEN_SAFETY_MARGIN = int(os.getenv("XTTS_TOKEN_SAFETY_MARGIN", "20"))
XTTS_TARGET_MAX_TOKENS = int(os.getenv("XTTS_TARGET_MAX_TOKENS", str(max(50, XTTS_MAX_TOKENS - XTTS_TOKEN_SAFETY_MARGIN))))

# Quality presets pro TTS generování
QUALITY_PRESETS = {
    "high_quality": {
        "speed": 1.0,
        "temperature": 0.5,
        "length_penalty": 1.2,
        "repetition_penalty": 2.5,
        "top_k": 30,
        "top_p": 0.8,
        "enhancement": {
            "enable_eq": True,
            "enable_noise_reduction": True,
            "enable_compression": True,
            "enable_deesser": True
        }
    },
    "natural": {
        "speed": 1.0,
        "temperature": 0.7,
        "length_penalty": 1.0,
        "repetition_penalty": 2.0,
        "top_k": 50,
        "top_p": 0.85,
        "enhancement": {
            "enable_eq": True,
            "enable_noise_reduction": False,
            "enable_compression": True,
            "enable_deesser": True
        }
    },
    "fast": {
        "speed": 1.0,
        "temperature": 0.8,
        "length_penalty": 1.0,
        "repetition_penalty": 2.0,
        "top_k": 60,
        "top_p": 0.9,
        "enhancement": {
            "enable_eq": False,
            "enable_noise_reduction": False,
            "enable_compression": True,
            "enable_deesser": False
        }
    }
}

