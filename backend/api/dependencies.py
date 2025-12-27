"""
Sdílené závislosti pro API routery
"""
from backend.progress_manager import ProgressManager
from backend.tts_engine import XTTSEngine
from backend.f5_tts_engine import F5TTSEngine
from backend.f5_tts_slovak_engine import F5TTSSlovakEngine
from backend.asr_engine import get_asr_engine
from backend.audio_processor import AudioProcessor
from backend.history_manager import HistoryManager
from backend.musicgen_engine import MusicGenEngine
from backend.music_history_manager import MusicHistoryManager
from backend.bark_history_manager import BarkHistoryManager
from backend.bark_engine import BarkEngine

# Inicializace engine instancí
tts_engine = XTTSEngine()
f5_tts_engine = F5TTSEngine()
f5_tts_slovak_engine = F5TTSSlovakEngine()
music_engine = MusicGenEngine()
bark_engine = BarkEngine()

# ASR (Whisper) – lazy singleton
asr_engine = get_asr_engine()

# Ověření dostupnosti F5-TTS CLI při startu (neblokující)
async def check_f5_tts_availability():
    """Ověří dostupnost F5-TTS CLI při startu"""
    import logging
    logger = logging.getLogger(__name__)
    try:
        await f5_tts_engine.load_model()
        logger.info("F5-TTS CLI je dostupné")
    except Exception as e:
        logger.info(f"F5-TTS není dostupné: {e}")
        logger.info("F5-TTS záložka bude dostupná až po instalaci: pip install f5-tts")

