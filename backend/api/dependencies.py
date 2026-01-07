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

# Inicializace engine instancí s lazy importy těžkých modulů
# Enginy se vytvoří hned, ale importy těžkých modulů (TTS, torch) jsou odložené
# do __init__ metod jednotlivých enginů

# TTS engine - import je odložen do XTTSEngine.__init__
from backend.tts_engine import XTTSEngine
tts_engine = XTTSEngine()

# F5-TTS Slovak engine - import je odložen do F5TTSSlovakEngine.__init__
from backend.f5_tts_slovak_engine import F5TTSSlovakEngine
f5_tts_slovak_engine = F5TTSSlovakEngine()

# MusicGen engine - import je odložen do MusicGenEngine.__init__
from backend.musicgen_engine import MusicGenEngine
music_engine = MusicGenEngine()

# Bark engine - import je odložen do BarkEngine.__init__
from backend.bark_engine import BarkEngine
bark_engine = BarkEngine()

# ASR (Whisper) – lazy singleton (už má lazy loading)
asr_engine = get_asr_engine()

