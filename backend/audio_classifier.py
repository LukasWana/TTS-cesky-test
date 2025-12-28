"""
Audio classification modul pomocí PyAudio Analysis
Klasifikuje typ audio obsahu (řeč vs. hudba, vhodnost pro voice cloning)
"""
import logging
from typing import Dict, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import pyAudioAnalysis
try:
    from pyAudioAnalysis import audioSegmentation as aS
    from pyAudioAnalysis import audioBasicIO
    PY_AUDIO_ANALYSIS_AVAILABLE = True
except ImportError:
    PY_AUDIO_ANALYSIS_AVAILABLE = False
    logger.warning("pyAudioAnalysis není dostupný - klasifikace audia bude vypnutá")


def classify_audio_content(file_path: str) -> Dict[str, Any]:
    """
    Klasifikuje typ audio obsahu pomocí PyAudio Analysis

    Args:
        file_path: Cesta k audio souboru

    Returns:
        Dictionary s klasifikačními daty:
        {
            'type': 'speech' | 'music' | 'mixed' | 'unknown',
            'speech_ratio': float,  # 0.0-1.0
            'has_music': bool,
            'suitable_for_cloning': bool,
            'classification_available': bool
        }
    """
    if not PY_AUDIO_ANALYSIS_AVAILABLE:
        return {
            'type': 'unknown',
            'speech_ratio': 0.0,
            'has_music': False,
            'suitable_for_cloning': True,  # Fallback: povolit, pokud není klasifikace dostupná
            'classification_available': False
        }

    try:
        # Kontrola existence souboru
        if not Path(file_path).exists():
            logger.warning(f"Audio soubor neexistuje: {file_path}")
            return {
                'type': 'unknown',
                'speech_ratio': 0.0,
                'has_music': False,
                'suitable_for_cloning': False,
                'classification_available': False
            }

        # Načtení audio pomocí pyAudioAnalysis
        # audioBasicIO.read_audio_file vrací [Fs, x] kde Fs je sample rate a x je audio data
        try:
            [Fs, x] = audioBasicIO.read_audio_file(file_path)
        except Exception as e:
            logger.warning(f"Chyba při načítání audio pro klasifikaci: {e}")
            return {
                'type': 'unknown',
                'speech_ratio': 0.0,
                'has_music': False,
                'suitable_for_cloning': True,  # Fallback: povolit
                'classification_available': False
            }

        # Klasifikace řeč vs. hudba
        # PyAudio Analysis má vestavěný model pro tuto klasifikaci
        # Použijeme mtFileClassification s pre-trained modelem
        try:
            # Model path - pyAudioAnalysis má vestavěné modely
            # Zkusíme použít vestavěný model pro speech/music klasifikaci
            # Pokud model není dostupný, použijeme jednodušší metodu

            # Metoda 1: Použití vestavěného modelu (pokud je dostupný)
            # Pozn.: Model může být v různých umístěních podle instalace
            model_paths = [
                "pyAudioAnalysis/data/models/svmSpeechMusic",
                "svmSpeechMusic",
            ]

            segments = None
            for model_path in model_paths:
                try:
                    # mtFileClassification vrací segmenty s klasifikací
                    # 0 = speech, 1 = music
                    segments = aS.mtFileClassification(
                        file_path,
                        model_path,
                        "svm",
                        False  # neukládat výsledky
                    )
                    break
                except Exception:
                    continue

            if segments is None:
                # Fallback: jednodušší klasifikace na základě spektrálních vlastností
                logger.debug("Vestavěný model není dostupný, používáme fallback metodu")
                return _classify_audio_fallback(file_path, Fs, x)

            # Analýza výsledků segmentace
            if len(segments) == 0:
                return {
                    'type': 'unknown',
                    'speech_ratio': 0.0,
                    'has_music': False,
                    'suitable_for_cloning': False,
                    'classification_available': True
                }

            # Počítání segmentů
            speech_frames = sum(1 for s in segments if s == 0)  # 0 = speech
            music_frames = sum(1 for s in segments if s == 1)    # 1 = music
            total_frames = len(segments)

            if total_frames == 0:
                return {
                    'type': 'unknown',
                    'speech_ratio': 0.0,
                    'has_music': False,
                    'suitable_for_cloning': False,
                    'classification_available': True
                }

            speech_ratio = speech_frames / total_frames
            has_music = music_frames > 0

            # Určení typu
            if speech_ratio > 0.8:
                audio_type = 'speech'
            elif speech_ratio < 0.2:
                audio_type = 'music'
            else:
                audio_type = 'mixed'

            # Vhodnost pro cloning: alespoň 50% řeči a není to čistá hudba
            suitable_for_cloning = speech_ratio >= 0.5 and audio_type != 'music'

            return {
                'type': audio_type,
                'speech_ratio': float(speech_ratio),
                'has_music': has_music,
                'suitable_for_cloning': suitable_for_cloning,
                'classification_available': True
            }

        except Exception as e:
            logger.warning(f"Chyba při klasifikaci audia: {e}, používáme fallback")
            return _classify_audio_fallback(file_path, Fs, x)

    except Exception as e:
        logger.error(f"Neočekávaná chyba při klasifikaci audia: {e}")
        return {
            'type': 'unknown',
            'speech_ratio': 0.0,
            'has_music': False,
            'suitable_for_cloning': True,  # Fallback: povolit
            'classification_available': False
        }


def _classify_audio_fallback(file_path: str, Fs: int, x) -> Dict[str, Any]:
    """
    Fallback klasifikační metoda, pokud vestavěný model není dostupný
    Používá jednoduché spektrální vlastnosti pro odhad typu audia
    """
    try:
        import numpy as np
        import librosa

        # Načtení pomocí librosa pro konzistenci
        audio, sr = librosa.load(file_path, sr=None)

        # Jednoduchá analýza na základě spektrálních vlastností
        # Řeč má typicky více energie v pásmu 1-4 kHz
        # Hudba má širší spektrum

        # Výpočet spektrálního centroidu (průměrná frekvence)
        spectral_centroids = librosa.feature.spectral_centroid(y=audio, sr=sr)[0]
        mean_centroid = np.mean(spectral_centroids)

        # Výpočet spektrálního rolloff (frekvence pod kterou je 85% energie)
        spectral_rolloff = librosa.feature.spectral_rolloff(y=audio, sr=sr)[0]
        mean_rolloff = np.mean(spectral_rolloff)

        # Zero crossing rate (ZCR) - řeč má vyšší ZCR než hudba
        zcr = librosa.feature.zero_crossing_rate(audio)[0]
        mean_zcr = np.mean(zcr)

        # Jednoduché pravidla pro klasifikaci
        # (Tyto pravidla jsou zjednodušená a nemusí být přesná)
        # Řeč: střední centroid (1-3 kHz), střední rolloff, vyšší ZCR
        # Hudba: variabilní centroid, vyšší rolloff, nižší ZCR

        # Heuristika: pokud je ZCR vysoké a centroid je v rozsahu řeči, je to pravděpodobně řeč
        is_speech_like = (
            mean_zcr > 0.05 and  # Řeč má vyšší ZCR
            mean_centroid > 500 and mean_centroid < 3000  # Řeč má energii v tomto pásmu
        )

        if is_speech_like:
            audio_type = 'speech'
            speech_ratio = 0.8  # Odhad
            has_music = False
        else:
            # Může to být hudba nebo směs
            audio_type = 'mixed'
            speech_ratio = 0.3  # Konzervativní odhad
            has_music = True

        suitable_for_cloning = speech_ratio >= 0.5

        return {
            'type': audio_type,
            'speech_ratio': float(speech_ratio),
            'has_music': has_music,
            'suitable_for_cloning': suitable_for_cloning,
            'classification_available': True
        }

    except Exception as e:
        logger.warning(f"Fallback klasifikace selhala: {e}")
        return {
            'type': 'unknown',
            'speech_ratio': 0.0,
            'has_music': False,
            'suitable_for_cloning': True,  # Fallback: povolit
            'classification_available': False
        }

