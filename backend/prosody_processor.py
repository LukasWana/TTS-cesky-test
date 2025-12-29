"""
Prosody Control modul pro kontrolu intonace a důrazu
"""
import re
from typing import Dict, List, Tuple, Optional
from backend.config import ENABLE_PROSODY_CONTROL


class ProsodyProcessor:
    """Třída pro zpracování prosody značek v textu"""

    def __init__(self):
        """Inicializace procesoru s prosodickými pravidly z lookup tabulek"""
        try:
            from backend.lookup_tables_loader import get_lookup_loader
            self.lookup_loader = get_lookup_loader()
            self.prosodicke_pravidla = self.lookup_loader.get_prosodicke_pravidla()
        except Exception as e:
            print(f"[WARN] Varovani: Nepodarilo se nacist prosodicka pravidla: {e}")
            self.prosodicke_pravidla = None

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

    # Intonační značky
    INTONATION_PATTERNS = [
        (r'\[intonation:fall\](.*?)\[/intonation\]', 'FALL'),
        (r'\[intonation:rise\](.*?)\[/intonation\]', 'RISE'),
        (r'\[intonation:flat\](.*?)\[/intonation\]', 'FLAT'),
        (r'\[intonation:wave\](.*?)\[/intonation\]', 'WAVE'),
        (r'\[intonation:half_fall\](.*?)\[/intonation\]', 'HALF_FALL'),
    ]

    # SSML-like kontury
    PROSODY_CONTOUR_PATTERN = re.compile(
        r'<prosody\s+contour=["\']([^"\']+)["\']>(.*?)</prosody>',
        re.IGNORECASE | re.DOTALL
    )

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

        # Použijeme instanci pro přístup k lookup tabulkám
        processor = ProsodyProcessor()

        metadata = {
            'emphasis': [],
            'rate_changes': [],
            'pitch_changes': [],
            'pauses': [],
            'intonation': []
        }

        processed = text

        # Zpracuj SSML-like značky
        processed, emphasis_meta = processor._process_emphasis(processed)
        metadata['emphasis'].extend(emphasis_meta)

        processed, rate_meta = processor._process_rate(processed)
        metadata['rate_changes'].extend(rate_meta)

        processed, pitch_meta = processor._process_pitch(processed)
        metadata['pitch_changes'].extend(pitch_meta)

        # Zpracuj jednoduché kontrolní znaky pokud jsou povolené
        if use_simple_markers:
            processed, simple_meta = processor._process_simple_markers(processed)
            metadata['emphasis'].extend(simple_meta)

        # Zpracuj pauzy
        processed, pause_meta = processor._process_pauses(processed)
        metadata['pauses'].extend(pause_meta)

        # Zpracuj intonační značky
        processed, intonation_meta = processor._process_intonation(processed)
        metadata['intonation'].extend(intonation_meta)

        # Zpracuj SSML kontury
        processed, contour_meta = processor._process_contours(processed)
        metadata['intonation'].extend(contour_meta)

        # Automatická detekce intonace podle typu věty (pokud není explicitně zadána)
        if not metadata['intonation']:
            auto_intonation = processor._detect_sentence_intonation(processed)
            if auto_intonation:
                metadata['intonation'].append(auto_intonation)

                # Pro vykřičník přidej automatický emphasis na celou větu pro větší důraz
                if auto_intonation.get('is_exclamation'):
                    # Přidej emphasis metadata pro celou větu s vykřičníkem
                    emphasis_meta = {
                        'type': 'emphasis',
                        'level': 'STRONG',  # Silný důraz pro vykřičník
                        'content': processed,  # Celá věta
                        'processed_content': processed.upper(),  # Velká písmena pro důraz
                        'position': 0,
                        'processed_position': 0,
                        'processed_length': len(processed),
                        'auto_detected': True
                    }
                    metadata['emphasis'].append(emphasis_meta)
                    print(f"💥 Automatický důraz detekován pro vykřičník: '{processed[:50]}...'")

        return processed, metadata

    def _process_emphasis(self, text: str) -> Tuple[str, List[Dict]]:
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
                    'content': content,  # Původní obsah
                    'processed_content': emphasized,  # Zpracovaný obsah
                    'position': match.start()  # Pozice v původním textu
                })
                return emphasized

            processed = re.sub(pattern, replace_emphasis, processed, flags=re.IGNORECASE | re.DOTALL)

        # Přepočítej pozice podle zpracovaného textu
        for meta in metadata:
            processed_content = meta.get('processed_content', meta['content'])
            # Najdi pozici zpracovaného obsahu v zpracovaném textu
            try:
                # Začni hledat od původní pozice (přibližně)
                start_pos = max(0, meta['position'] - 10)
                found_pos = processed.find(processed_content, start_pos)
                if found_pos != -1:
                    meta['processed_position'] = found_pos
                    meta['processed_length'] = len(processed_content)
                else:
                    # Pokud nenajdeme, použijeme původní pozici
                    meta['processed_position'] = meta['position']
                    meta['processed_length'] = len(processed_content)
            except Exception:
                meta['processed_position'] = meta['position']
                meta['processed_length'] = len(processed_content)

        return processed, metadata

    def _process_rate(self, text: str) -> Tuple[str, List[Dict]]:
        """Zpracuje rate (rychlost) značky"""
        metadata = []
        processed = text

        for pattern, rate in ProsodyProcessor.PROSODY_RATE_PATTERNS:
            def replace_rate(match):
                content = match.group(1)
                # Pro změnu rychlosti použijeme interpunkci nebo mikro-pauzy
                if rate == 'SLOW' or rate == 'X_SLOW':
                    # Pro zpomalení vložíme tečku za každé slovo (mikropauzy)
                    modified = content.replace(' ', '. ') + '.'
                elif rate == 'FAST' or rate == 'X_FAST':
                    # Pro zrychlení odstraníme přebytečné mezery a interpunkci
                    modified = content.replace(' ', '')
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

    def _process_pitch(self, text: str) -> Tuple[str, List[Dict]]:
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

    def _process_simple_markers(self, text: str) -> Tuple[str, List[Dict]]:
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
                    'content': content,  # Původní obsah
                    'processed_content': emphasized,  # Zpracovaný obsah
                    'position': match.start()  # Pozice v původním textu
                })
                return emphasized

            processed = re.sub(pattern, replace_simple, processed)

        # Přepočítej pozice podle zpracovaného textu
        for meta in metadata:
            processed_content = meta.get('processed_content', meta['content'])
            # Najdi pozici zpracovaného obsahu v zpracovaném textu
            try:
                # Začni hledat od původní pozice (přibližně)
                start_pos = max(0, meta['position'] - 10)
                found_pos = processed.find(processed_content, start_pos)
                if found_pos != -1:
                    meta['processed_position'] = found_pos
                    meta['processed_length'] = len(processed_content)
                else:
                    # Pokud nenajdeme, použijeme původní pozici
                    meta['processed_position'] = meta['position']
                    meta['processed_length'] = len(processed_content)
            except Exception:
                meta['processed_position'] = meta['position']
                meta['processed_length'] = len(processed_content)

        return processed, metadata

    def _process_pauses(self, text: str) -> Tuple[str, List[Dict]]:
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

    def _process_intonation(self, text: str) -> Tuple[str, List[Dict]]:
        """Zpracuje intonační značky [intonation:type]text[/intonation]"""
        metadata = []
        processed = text

        for pattern, intonation_type in ProsodyProcessor.INTONATION_PATTERNS:
            def replace_intonation(match):
                content = match.group(1)
                metadata.append({
                    'type': 'intonation',
                    'intonation_type': intonation_type,
                    'content': content,
                    'position': match.start(),
                    'length': len(content),
                    'intensity': 1.0
                })
                return content  # Vrátíme obsah bez značek

            processed = re.sub(pattern, replace_intonation, processed, flags=re.IGNORECASE | re.DOTALL)

        return processed, metadata

    def _process_contours(self, text: str) -> Tuple[str, List[Dict]]:
        """Zpracuje SSML-like kontury <prosody contour="...">text</prosody>"""
        metadata = []
        processed = text

        matches = list(ProsodyProcessor.PROSODY_CONTOUR_PATTERN.finditer(text))

        for match in matches:
            contour_str = match.group(1)
            content = match.group(2)

            # Parsuj konturu
            try:
                from backend.intonation_processor import IntonationProcessor
                contour = IntonationProcessor.parse_contour_string(contour_str)
            except Exception:
                contour = []

            metadata.append({
                'type': 'contour',
                'contour': contour,
                'content': content,
                'position': match.start(),
                'length': len(content),
                'intensity': 1.0
            })

        # Odstraň značky z textu
        processed = ProsodyProcessor.PROSODY_CONTOUR_PATTERN.sub(r'\2', processed)

        return processed, metadata

    @staticmethod
    def _detect_sentence_intonation(text: str) -> Optional[Dict]:
        """
        Automaticky detekuje intonaci podle typu věty

        Args:
            text: Text věty

        Returns:
            Metadata o intonaci nebo None
        """
        text = text.strip()
        if not text:
            return None

        # Zkontroluj přímo konec textu (nebo poslední znak před mezerou)
        # Odstraň mezery na konci pro kontrolu
        text_clean = text.rstrip()

        intonation_type = None

        # Zkontroluj poslední znak (nebo poslední znaky před mezerou)
        intonation_intensity = 1.0
        is_exclamation = False

        if text_clean.endswith('?'):
            intonation_type = 'RISE'  # Stoupavá pro otázky
        elif text_clean.endswith('.'):
            intonation_type = 'FALL'  # Klesavá pro oznamovací
        elif text_clean.endswith(','):
            intonation_type = 'HALF_FALL'  # Polokadence
        elif text_clean.endswith('!'):
            intonation_type = 'FALL'  # Klesavá pro rozkazy/výkřiky
            intonation_intensity = 1.5  # Zvýšená intenzita pro výraznější efekt
            is_exclamation = True

        if intonation_type:
            result = {
                'type': 'intonation',
                'intonation_type': intonation_type,
                'content': text,
                'position': 0,
                'length': len(text),
                'intensity': intonation_intensity,
                'auto_detected': True
            }

            # Pro vykřičník přidej také emphasis metadata pro větší důraz
            if is_exclamation:
                result['is_exclamation'] = True

            return result

        return None

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

        # Odstranit intonační značky
        for pattern, _ in ProsodyProcessor.INTONATION_PATTERNS:
            text = re.sub(pattern, r'\1', text, flags=re.IGNORECASE | re.DOTALL)

        # Odstranit SSML kontury
        text = ProsodyProcessor.PROSODY_CONTOUR_PATTERN.sub(r'\2', text)

        return text.strip()






