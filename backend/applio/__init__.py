"""
Applio Integration Module
Voice conversion a TTS s Applio/RVC
"""

from .config import (
    APPLIO_ENABLED,
    APPLIO_DIR,
    APPLIO_MODELS_DIR,
    APPLIO_VOICES_DIR,
    APPLIO_OUTPUTS_DIR,
    APPLIO_BASE_URL,
    APPLIO_PORT,
    RVC_PITCH_METHOD,
    RVC_INDEX_RATIO,
    EDGE_TTS_VOICES,
    APPLIO_OUTPUT_SAMPLE_RATE,
)

from .engine import ApplioEngine
from .subprocess_manager import ApplioSubprocessManager
from .integration import (
    ApplioIntegration,
    get_applio_integration,
    init_applio,
    ensure_applio_running,
)

__all__ = [
    "ApplioEngine",
    "ApplioSubprocessManager",
    "ApplioIntegration",
    "get_applio_integration",
    "init_applio",
    "ensure_applio_running",
    "APPLIO_ENABLED",
    "APPLIO_DIR",
    "APPLIO_MODELS_DIR",
    "APPLIO_VOICES_DIR",
    "APPLIO_OUTPUTS_DIR",
    "APPLIO_BASE_URL",
    "RVC_PITCH_METHOD",
    "RVC_INDEX_RATIO",
    "EDGE_TTS_VOICES",
]
