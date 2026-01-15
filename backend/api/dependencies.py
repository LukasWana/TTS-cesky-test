"""
Sdílené závislosti pro API routery
Optimalizace: odložení importů těžkých modulů až do inicializace enginů
"""
from backend.progress_manager import ProgressManager
from backend.audio_processor import AudioProcessor
from backend.history_manager import HistoryManager
from backend.music_history_manager import MusicHistoryManager
from backend.bark_history_manager import BarkHistoryManager
from backend.asr_engine import get_asr_engine


class LazyProxy:
    def __init__(self, factory):
        self._factory = factory
        self._instance = None

    def __getattr__(self, name):
        if self._instance is None:
            self._instance = self._factory()
        return getattr(self._instance, name)

def get_tts_engine():
    from backend.tts_engine import XTTSEngine
    return XTTSEngine()

def get_f5_tts_slovak_engine():
    from backend.f5_tts_slovak_engine import F5TTSSlovakEngine
    return F5TTSSlovakEngine()

def get_music_engine():
    from backend.musicgen_engine import MusicGenEngine
    return MusicGenEngine()

def get_bark_engine():
    from backend.bark_engine import BarkEngine
    return BarkEngine()

def get_asr_engine_lazy():
    from backend.asr_engine import get_asr_engine
    return get_asr_engine()

# Inicializace engine instancí s lazy importy pomocí LazyProxy
tts_engine = LazyProxy(get_tts_engine)
f5_tts_slovak_engine = LazyProxy(get_f5_tts_slovak_engine)
music_engine = LazyProxy(get_music_engine)
bark_engine = LazyProxy(get_bark_engine)
asr_engine = LazyProxy(get_asr_engine_lazy)

