"""
Applio Configuration
Applio/RVC voice conversion and TTS settings
"""

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.parent.parent
APPLIO_DIR = BASE_DIR / "backend" / "applio"

# Directories
APPLIO_MODELS_DIR = APPLIO_DIR / "models"
APPLIO_VOICES_DIR = APPLIO_DIR / "voices"
APPLIO_OUTPUTS_DIR = APPLIO_DIR / "outputs"
APPLIO_ASSETS_DIR = BASE_DIR / "assets" / "applio_voices"

# Create directories
APPLIO_MODELS_DIR.mkdir(parents=True, exist_ok=True)
APPLIO_VOICES_DIR.mkdir(parents=True, exist_ok=True)
APPLIO_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
APPLIO_ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# Applio enable/disable
APPLIO_ENABLED = os.getenv("APPLIO_ENABLED", "True").lower() == "true"

# Applio server settings
APPLIO_HOST = os.getenv("APPLIO_HOST", "127.0.0.1")
APPLIO_PORT = int(os.getenv("APPLIO_PORT", "9874"))
APPLIO_BASE_URL = f"http://{APPLIO_HOST}:{APPLIO_PORT}"

# Applio script paths (auto-detect OS)
if os.name == "nt":
    APPLIO_RUN_SCRIPT = APPLIO_DIR / "run-applio.bat"
    APPLIO_INSTALL_SCRIPT = APPLIO_DIR / "run-install.bat"
else:
    APPLIO_RUN_SCRIPT = APPLIO_DIR / "run-applio.sh"
    APPLIO_INSTALL_SCRIPT = APPLIO_DIR / "run-install.sh"

# RVC Voice Conversion Settings
RVC_SAMPLE_RATE = int(os.getenv("RVC_SAMPLE_RATE", "48000"))
RVC_PITCH_METHOD = os.getenv("RVC_PITCH_METHOD", "rmvpe")  # rmvpe, crepe, fcpe
RVC_INDEX_RATIO = float(
    os.getenv("RVC_INDEX_RATIO", "0.75")
)  # 0-1, vyšší = více podobnosti
RVC_FILTER_RADIUS = int(os.getenv("RVC_FILTER_RADIUS", "7"))
RVC_OUTPUT_FORMAT = os.getenv("RVC_OUTPUT_FORMAT", "wav")

# VRAM Optimization
RVC_HALF_PRECISION = os.getenv("RVC_HALF_PRECISION", "True").lower() == "true"
RVC_BATCH_SIZE = int(os.getenv("RVC_BATCH_SIZE", "1"))

# EdgeTTS Settings (for TTS with voice cloning)
EDGE_TTS_VOICES = {
    "cs": os.getenv("EDGE_TTS_VOICE_CS", "cs-CZ-VlastaNeural"),
    "sk": os.getenv("EDGE_TTS_VOICE_SK", "sk-SR-LuboslavNeural"),
    "en": os.getenv("EDGE_TTS_VOICE_EN", "en-US-AriaNeural"),
    "de": os.getenv("EDGE_TTS_VOICE_DE", "de-DE-KatjaNeural"),
    "fr": os.getenv("EDGE_TTS_VOICE_FR", "fr-FR-DeniseNeural"),
    "es": os.getenv("EDGE_TTS_VOICE_ES", "es-ES-ElviraNeural"),
    "pl": os.getenv("EDGE_TTS_VOICE_PL", "pl-PL-ZofiaNeural"),
    "ru": os.getenv("EDGE_TTS_VOICE_RU", "ru-RU-SvetlanaNeural"),
}

# Output Settings
APPLIO_OUTPUT_SAMPLE_RATE = int(os.getenv("APPLIO_OUTPUT_SAMPLE_RATE", "44100"))

# Inference settings
APPLIO_MAX_TEXT_LENGTH = int(os.getenv("APPLIO_MAX_TEXT_LENGTH", "500"))
APPLIO_MIN_VOICE_DURATION = float(os.getenv("APPLIO_MIN_VOICE_DURATION", "6.0"))

# Supported languages
APPLIO_SUPPORTED_LANGUAGES = list(EDGE_TTS_VOICES.keys())

# Logging
APPLIO_LOG_LEVEL = os.getenv("APPLIO_LOG_LEVEL", "INFO")

# CPU fallback
APPLIO_FORCE_CPU = os.getenv("APPLIO_FORCE_CPU", "False").lower() == "true"

# Auto-start Applio server
APPLIO_AUTO_START = os.getenv("APPLIO_AUTO_START", "True").lower() == "true"

# Health check settings
APPLIO_HEALTH_CHECK_INTERVAL = int(os.getenv("APPLIO_HEALTH_CHECK_INTERVAL", "30"))
APPLIO_STARTUP_TIMEOUT = int(os.getenv("APPLIO_STARTUP_TIMEOUT", "120"))
