"""
Sdílené závislosti pro API routery
"""
from backend.progress_manager import ProgressManager
from backend.tts_engine import XTTSEngine
from backend.f5_tts_slovak_engine import F5TTSSlovakEngine

from backend.asr_engine import get_asr_engine
from backend.audio_processor import AudioProcessor
from backend.history_manager import HistoryManager
from backend.musicgen_engine import MusicGenEngine
from backend.music_history_manager import MusicHistoryManager
from backend.bark_history_manager import BarkHistoryManager
from backend.bark_engine import BarkEngine
from backend.bark_engine import BarkEngine

# Inicializace engine instancí
# Inicializace engine instancí
tts_engine = XTTSEngine()
f5_tts_slovak_engine = F5TTSSlovakEngine()

music_engine = MusicGenEngine()
bark_engine = BarkEngine()

# ASR (Whisper) – lazy singleton
asr_engine = get_asr_engine()

