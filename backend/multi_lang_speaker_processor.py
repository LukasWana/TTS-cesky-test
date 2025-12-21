"""
Modul pro zpracování textu s více jazyky a mluvčími

Podporuje syntaxi: [lang:speaker]text[/lang] nebo [lang]text[/lang]
"""
import re
from typing import List, Dict, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TextSegment:
    """Reprezentuje segment textu s jazykem a mluvčím"""
    text: str
    language: str
    speaker_id: Optional[str] = None
    speaker_wav: Optional[str] = None
    start_pos: int = 0
    end_pos: int = 0


class MultiLangSpeakerProcessor:
    """Zpracovává text s více jazyky a mluvčími"""

    # Regex pro detekci anotací: [lang:speaker]text[/lang] nebo [lang]text[/lang]
    # Podporuje i jednodušší variantu bez uzavíracího tagu: [lang:speaker]text
    # POZNÁMKA: Používáme greedy matching pro text, aby se zachytil uzavírací tag
    SEGMENT_PATTERN = re.compile(
        r'\[(\w+)(?::([^\]]+))?\]'  # [lang:speaker] nebo [lang]
        r'(.*?)'                      # text (non-greedy)
        r'(?:\[/\1\]|(?=\[)|$)',     # [/lang] nebo další tag nebo konec
        re.DOTALL | re.IGNORECASE
    )

    def __init__(self, default_language: str = "cs", default_speaker: Optional[str] = None):
        """
        Inicializuje processor

        Args:
            default_language: Výchozí jazyk pro neanotované části
            default_speaker: Výchozí mluvčí (cesta k WAV souboru nebo speaker_id)
        """
        self.default_language = default_language
        self.default_speaker = default_speaker
        self.speaker_registry: Dict[str, str] = {}  # speaker_id -> speaker_wav_path

    def register_speaker(self, speaker_id: str, speaker_wav_path: str):
        """
        Registruje mluvčího s jeho audio souborem

        Args:
            speaker_id: Identifikátor mluvčího
            speaker_wav_path: Cesta k WAV souboru s hlasem mluvčího
        """
        if Path(speaker_wav_path).exists():
            self.speaker_registry[speaker_id] = speaker_wav_path
        else:
            print(f"[WARN] Speaker audio soubor neexistuje: {speaker_wav_path}")

    def parse_text(self, text: str) -> List[TextSegment]:
        """
        Parsuje text a rozdělí ho na segmenty podle jazyka a mluvčího

        Podporované syntaxe:
        - [lang:speaker]text[/lang] - plná syntaxe s uzavíracím tagem
        - [lang]text[/lang] - bez specifikace mluvčího
        - [lang:speaker]text - bez uzavíracího tagu (segment končí na další tag nebo konec)

        Args:
            text: Vstupní text s anotacemi

        Returns:
            Seznam segmentů s jazyky a mluvčími
        """
        segments = []
        last_pos = 0

        # Najdi všechny anotované segmenty
        matches = list(self.SEGMENT_PATTERN.finditer(text))

        # Debug: vypiš všechny nalezené matche
        if matches:
            print(f"[DEBUG] MultiLangParser: nalezeno {len(matches)} anotací v textu")
            for i, m in enumerate(matches):
                print(f"  Match {i+1}: {m.group(0)[:50]}... -> lang={m.group(1)}, speaker={m.group(2)}, text={m.group(3)[:30]}...")

        if not matches:
            # Žádné anotace - vrať celý text jako jeden segment
            print(f"[DEBUG] MultiLangParser: žádné anotace nalezeny, vracím celý text jako jeden segment")
            return [TextSegment(
                text=text.strip(),
                language=self.default_language,
                speaker_id=None,
                speaker_wav=self.default_speaker,
                start_pos=0,
                end_pos=len(text)
            )]

        for i, match in enumerate(matches):
            # Text před segmentem (pokud existuje)
            before_text = text[last_pos:match.start()].strip()
            if before_text:
                segments.append(TextSegment(
                    text=before_text,
                    language=self.default_language,
                    speaker_id=None,
                    speaker_wav=self.default_speaker,
                    start_pos=last_pos,
                    end_pos=match.start()
                ))

            # Anotovaný segment
            lang = match.group(1).lower()
            speaker_id = match.group(2) if match.group(2) else None

            # Urči konec segmentu
            full_match = match.group(0)
            if full_match.endswith(f'[/{lang}]'):
                # Má uzavírací tag
                segment_text = match.group(3).strip()
                end_pos = match.end()
            else:
                # Bez uzavíracího tagu - segment končí na další tag nebo konec textu
                if i + 1 < len(matches):
                    # Konec je na začátku dalšího tagu
                    end_pos = matches[i + 1].start()
                    segment_text = text[match.end():end_pos].strip()
                else:
                    # Konec textu
                    end_pos = len(text)
                    segment_text = text[match.end():].strip()

            if segment_text:
                speaker_wav = None
                if speaker_id:
                    # Zkus najít v registru
                    speaker_wav = self.speaker_registry.get(speaker_id)
                    if not speaker_wav:
                        # Možná je speaker_id přímo cesta k souboru
                        if Path(speaker_id).exists():
                            speaker_wav = speaker_id
                        else:
                            # Možná je speaker_id název demo hlasu - zkus najít v demo-voices
                            # Toto se provede v main.py, kde máme přístup k DEMO_VOICES_DIR
                            # Prozatím použij výchozího mluvčího
                            speaker_wav = self.default_speaker
                else:
                    speaker_wav = self.default_speaker

                segments.append(TextSegment(
                    text=segment_text,
                    language=lang,
                    speaker_id=speaker_id,
                    speaker_wav=speaker_wav,
                    start_pos=match.start(),
                    end_pos=end_pos
                ))

            last_pos = end_pos

        # Zbytek textu po posledním segmentu
        remaining = text[last_pos:].strip()
        if remaining:
            segments.append(TextSegment(
                text=remaining,
                language=self.default_language,
                speaker_id=None,
                speaker_wav=self.default_speaker,
                start_pos=last_pos,
                end_pos=len(text)
            ))

        return segments

    def get_segments_summary(self, segments: List[TextSegment]) -> str:
        """
        Vrátí textový souhrn segmentů pro debug

        Args:
            segments: Seznam segmentů

        Returns:
            Textový popis segmentů
        """
        lines = []
        for i, seg in enumerate(segments):
            speaker_info = f"speaker={seg.speaker_id}" if seg.speaker_id else "default_speaker"
            lines.append(f"Segment {i+1}: lang={seg.language}, {speaker_info}, text='{seg.text[:50]}...'")
        return "\n".join(lines)


# Globální instance
_processor_instance = None


def get_multi_lang_processor(
    default_language: str = "cs",
    default_speaker: Optional[str] = None
) -> MultiLangSpeakerProcessor:
    """
    Vrátí globální instanci MultiLangSpeakerProcessor (singleton pattern)

    Args:
        default_language: Výchozí jazyk
        default_speaker: Výchozí mluvčí

    Returns:
        Instance MultiLangSpeakerProcessor
    """
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = MultiLangSpeakerProcessor(
            default_language=default_language,
            default_speaker=default_speaker
        )
    return _processor_instance

