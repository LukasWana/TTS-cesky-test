"""
Jednoduchý language detector pro automatickou detekci jazyků v textu

Používá heuristiku nebo externí knihovnu langdetect (pokud je dostupná)
"""
import re
from typing import List, Tuple, Optional

# Zkus načíst langdetect (volitelné)
try:
    from langdetect import detect, detect_langs, LangDetectException
    HAS_LANGDETECT = True
except ImportError:
    HAS_LANGDETECT = False
    print("[INFO] langdetect není nainstalován. Pro automatickou detekci jazyka nainstalujte: pip install langdetect")


class LanguageDetector:
    """Automaticky detekuje jazyky v textu"""

    # Jednoduchá heuristika pro češtinu (diakritika, typické znaky)
    CZECH_CHARS = set("áčďéěíňóřšťúůýžÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ")
    CZECH_WORDS = {"je", "se", "na", "v", "s", "z", "k", "o", "u", "a", "i", "to", "co", "jak", "kde", "kdy", "pro"}

    @staticmethod
    def detect_language(text: str) -> str:
        """
        Detekuje dominantní jazyk v textu

        Args:
            text: Text k analýze

        Returns:
            Kód jazyka (cs, en, de, ...)
        """
        if not text or not text.strip():
            return "cs"  # Výchozí

        # Použij langdetect pokud je dostupný
        if HAS_LANGDETECT:
            try:
                detected = detect(text)
                # Mapování některých kódů na standardní
                lang_map = {
                    "cz": "cs",  # langdetect vrací "cz" pro češtinu
                }
                return lang_map.get(detected, detected)
            except LangDetectException:
                pass
            except Exception:
                pass

        # Fallback: jednoduchá heuristika
        text_lower = text.lower()

        # Počítání českých znaků
        czech_char_count = sum(1 for c in text if c in LanguageDetector.CZECH_CHARS)
        total_chars = len([c for c in text if c.isalpha()])

        if total_chars > 0:
            czech_ratio = czech_char_count / total_chars
            if czech_ratio > 0.1:  # Více než 10% českých znaků
                return "cs"

        # Počítání českých slov
        words = re.findall(r'\b\w+\b', text_lower)
        czech_word_count = sum(1 for w in words if w in LanguageDetector.CZECH_WORDS)
        if len(words) > 0 and czech_word_count / len(words) > 0.2:
            return "cs"

        # Angličtina - typické znaky
        if re.search(r'\b(the|and|is|are|was|were|have|has|had|this|that|with|from)\b', text_lower):
            return "en"

        # Němčina - typické znaky
        if re.search(r'\b(der|die|das|und|ist|sind|war|waren|haben|hat|mit|von)\b', text_lower):
            return "de"

        # Výchozí: čeština
        return "cs"

    @staticmethod
    def detect_segments(text: str, min_segment_length: int = 10) -> List[Tuple[str, str]]:
        """
        Detekuje jazyky po větách a vrátí seznam (text, language)

        Args:
            text: Text k analýze
            min_segment_length: Minimální délka segmentu pro detekci

        Returns:
            Seznam dvojic (text, language)
        """
        # Rozděl na věty
        sentences = re.split(r'([.!?]\s+)', text)
        segments = []
        current_segment = ""
        current_lang = None

        for i, part in enumerate(sentences):
            if re.match(r'^[.!?]\s+$', part):
                # Interpunkce - přidej k aktuálnímu segmentu
                current_segment += part
                continue

            if not part.strip():
                continue

            # Detekuj jazyk věty
            detected_lang = LanguageDetector.detect_language(part)

            if detected_lang == current_lang:
                # Stejný jazyk - přidej k segmentu
                current_segment += part
            else:
                # Změna jazyka - ulož předchozí segment
                if current_segment.strip() and len(current_segment.strip()) >= min_segment_length:
                    segments.append((current_segment.strip(), current_lang or "cs"))

                # Začni nový segment
                current_segment = part
                current_lang = detected_lang

        # Přidej poslední segment
        if current_segment.strip():
            segments.append((current_segment.strip(), current_lang or "cs"))

        return segments if segments else [(text.strip(), "cs")]


# Globální instance
_detector_instance = None


def get_language_detector() -> LanguageDetector:
    """
    Vrátí globální instanci LanguageDetector (singleton pattern)

    Returns:
        Instance LanguageDetector
    """
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = LanguageDetector()
    return _detector_instance

