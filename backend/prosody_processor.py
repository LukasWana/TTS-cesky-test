"""
Prosody Control modul pro kontrolu intonace a důrazu
"""
import re
from typing import Dict, List, Tuple
from backend.config import ENABLE_PROSODY_CONTROL


class ProsodyProcessor:
    """Třída pro zpracování prosody značek v textu"""

    # SSML-like značky pro prosody
    EMPHASIS_PATTERNS = [
        (r'<emphasis\s+level=["\']strong["\']>(.*?)</emphasis>', 'STRONG'),
        (r'<emphasis\s+level=["\']moderate["\']>(.*?)</emphasis>', 'MODERATE'),
        (r'<emphasis>(.*?)</emphasis>', 'MODERATE'),
    ]

    PROSODY_RATE_PATTERNS = [
        (r'<prosody\s+rate=["\']slow["\']>(.*?)</prosody>', 'SLOW'),
        (r'<prosody\s+rate=["\']fast["\']>(.*?)</prosody>', 'FAST'),
        (r'<prosody\s+rate=["\']x-slow["\']>(.*?)</prosody>', 'X_SLOW'),
        (r'<prosody\s+rate=["\']x-fast["\']>(.*?)</prosody>', 'X_FAST'),
    ]

    PROSODY_PITCH_PATTERNS = [
        (r'<prosody\s+pitch=["\']high["\']>(.*?)</prosody>', 'HIGH'),
        (r'<prosody\s+pitch=["\']low["\']>(.*?)</prosody>', 'LOW'),
        (r'<prosody\s+pitch=["\']x-high["\']>(.*?)</prosody>', 'X_HIGH'),
        (r'<prosody\s+pitch=["\']x-low["\']>(.*?)</prosody>', 'X_LOW'),
    ]

    # Jednoduché kontrolní znaky
    SIMPLE_PATTERNS = [
        (r'\*\*(.*?)\*\*', 'STRONG'),  # **text** pro důraz
        (r'\*(.*?)\*', 'MODERATE'),    # *text* pro mírný důraz
        (r'__(.*?)__', 'STRONG'),      # __text__ pro důraz
        (r'_(.*?)_', 'MODERATE'),      # _text_ pro mírný důraz
    ]

    PAUSE_PATTERNS = [
        (r'\[PAUSE\]', 'PAUSE_MEDIUM'),
        (r'\[PAUSE:(\d+)\]', 'PAUSE_CUSTOM'),
        (r'\.\.\.', 'PAUSE_SHORT'),
        (r'…', 'PAUSE_SHORT'),
    ]

    @staticmethod
    def process_text(text: str, use_simple_markers: bool = True) -> Tuple[str, Dict]:
        """
        Zpracuje text s prosody značkami a převede je na textové modifikace

        Args:
            text: Text s prosody značkami
            use_simple_markers: Použít jednoduché kontrolní znaky (*, **, atd.)

        Returns:
            Tuple (zpracovaný text, metadata o prosody)
        """
        if not ENABLE_PROSODY_CONTROL:
            return text, {}

        metadata = {
            'emphasis': [],
            'rate_changes': [],
            'pitch_changes': [],
            'pauses': []
        }

        processed = text

        # Zpracuj SSML-like značky
        processed, emphasis_meta = ProsodyProcessor._process_emphasis(processed)
        metadata['emphasis'].extend(emphasis_meta)

        processed, rate_meta = ProsodyProcessor._process_rate(processed)
        metadata['rate_changes'].extend(rate_meta)

        processed, pitch_meta = ProsodyProcessor._process_pitch(processed)
        metadata['pitch_changes'].extend(pitch_meta)

        # Zpracuj jednoduché kontrolní znaky pokud jsou povolené
        if use_simple_markers:
            processed, simple_meta = ProsodyProcessor._process_simple_markers(processed)
            metadata['emphasis'].extend(simple_meta)

        # Zpracuj pauzy
        processed, pause_meta = ProsodyProcessor._process_pauses(processed)
        metadata['pauses'].extend(pause_meta)

        return processed, metadata

    @staticmethod
    def _process_emphasis(text: str) -> Tuple[str, List[Dict]]:
        """Zpracuje emphasis značky"""
        metadata = []
        processed = text

        for pattern, level in ProsodyProcessor.EMPHASIS_PATTERNS:
            def replace_emphasis(match):
                content = match.group(1)
                # Pro důraz použijeme velká písmena (XTTS lépe reaguje)
                if level == 'STRONG':
                    emphasized = content.upper()
                else:
                    emphasized = content.capitalize()

                metadata.append({
                    'type': 'emphasis',
                    'level': level,
                    'content': content,
                    'position': match.start()
                })
                return emphasized

            processed = re.sub(pattern, replace_emphasis, processed, flags=re.IGNORECASE | re.DOTALL)

        return processed, metadata

    @staticmethod
    def _process_rate(text: str) -> Tuple[str, List[Dict]]:
        """Zpracuje rate (rychlost) značky"""
        metadata = []
        processed = text

        for pattern, rate in ProsodyProcessor.PROSODY_RATE_PATTERNS:
            def replace_rate(match):
                content = match.group(1)
                # Pro změnu rychlosti přidáme mezery (zpomalí) nebo je odstraníme (zrychlí)
                if rate == 'SLOW' or rate == 'X_SLOW':
                    modified = ' '.join(list(content))  # Přidá mezery mezi znaky
                elif rate == 'FAST' or rate == 'X_FAST':
                    modified = content.replace(' ', '')  # Odstraní mezery
                else:
                    modified = content

                metadata.append({
                    'type': 'rate',
                    'rate': rate,
                    'content': content,
                    'position': match.start()
                })
                return modified

            processed = re.sub(pattern, replace_rate, processed, flags=re.IGNORECASE | re.DOTALL)

        return processed, metadata

    @staticmethod
    def _process_pitch(text: str) -> Tuple[str, List[Dict]]:
        """Zpracuje pitch (výška) značky"""
        metadata = []
        processed = text

        for pattern, pitch in ProsodyProcessor.PROSODY_PITCH_PATTERNS:
            def replace_pitch(match):
                content = match.group(1)
                # Pro vyšší pitch použijeme více velkých písmen
                if pitch == 'HIGH' or pitch == 'X_HIGH':
                    modified = content.upper()
                elif pitch == 'LOW' or pitch == 'X_LOW':
                    modified = content.lower()
                else:
                    modified = content

                metadata.append({
                    'type': 'pitch',
                    'pitch': pitch,
                    'content': content,
                    'position': match.start()
                })
                return modified

            processed = re.sub(pattern, replace_pitch, processed, flags=re.IGNORECASE | re.DOTALL)

        return processed, metadata

    @staticmethod
    def _process_simple_markers(text: str) -> Tuple[str, List[Dict]]:
        """Zpracuje jednoduché kontrolní znaky (*, **, atd.)"""
        metadata = []
        processed = text

        for pattern, level in ProsodyProcessor.SIMPLE_PATTERNS:
            def replace_simple(match):
                content = match.group(1)
                if level == 'STRONG':
                    emphasized = content.upper()
                else:
                    emphasized = content.capitalize()

                metadata.append({
                    'type': 'emphasis',
                    'level': level,
                    'content': content,
                    'position': match.start()
                })
                return emphasized

            processed = re.sub(pattern, replace_simple, processed)

        return processed, metadata

    @staticmethod
    def _process_pauses(text: str) -> Tuple[str, List[Dict]]:
        """Zpracuje pauzy"""
        metadata = []
        processed = text

        # Vlastní pauzy s délkou
        def replace_custom_pause(match):
            pause_duration = int(match.group(1)) if match.group(1) else 500
            pause_text = ' ' * (pause_duration // 100)  # Přibližně 1 mezera = 100ms
            metadata.append({
                'type': 'pause',
                'duration': pause_duration,
                'position': match.start()
            })
            return pause_text

        processed = re.sub(r'\[PAUSE:(\d+)\]', replace_custom_pause, processed)

        # Standardní pauzy
        pause_replacements = {
            r'\[PAUSE\]': '   ',  # Střední pauza (3 mezery)
            r'\.\.\.': '  ',      # Krátká pauza (2 mezery)
            r'…': '  ',           # Krátká pauza (2 mezery)
        }

        for pattern, replacement in pause_replacements.items():
            def replace_pause(match):
                metadata.append({
                    'type': 'pause',
                    'duration': len(replacement) * 100,  # Přibližně
                    'position': match.start()
                })
                return replacement

            processed = re.sub(pattern, replace_pause, processed)

        return processed, metadata

    @staticmethod
    def clean_prosody_markers(text: str) -> str:
        """
        Odstraní všechny prosody značky z textu (pro čistý text)

        Args:
            text: Text s prosody značkami

        Returns:
            Text bez prosody značek
        """
        # Odstranit SSML značky
        text = re.sub(r'</?emphasis[^>]*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'</?prosody[^>]*>', '', text, flags=re.IGNORECASE)

        # Odstranit jednoduché kontrolní znaky
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **text**
        text = re.sub(r'\*([^*]+)\*', r'\1', text)     # *text*
        text = re.sub(r'__([^_]+)__', r'\1', text)      # __text__
        text = re.sub(r'_([^_]+)_', r'\1', text)        # _text_

        # Odstranit pauzy
        text = re.sub(r'\[PAUSE(?::\d+)?\]', '', text)
        text = text.replace('...', '')
        text = text.replace('…', '')

        return text.strip()

