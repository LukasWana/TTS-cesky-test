"""
Text splitter pro rozdělení dlouhých textů na části pro batch processing
"""
import re
from typing import List, Tuple
from backend.config import MAX_CHUNK_LENGTH, CHUNK_OVERLAP


class TextSplitter:
    """Třída pro inteligentní rozdělení textu na části"""

    @staticmethod
    def split_text(text: str, max_length: int = None, overlap: int = None) -> List[str]:
        """
        Rozdělí text na části s inteligentním rozdělením na větách

        Args:
            text: Text k rozdělení
            max_length: Maximální délka části (výchozí: MAX_CHUNK_LENGTH)
            overlap: Překrytí mezi částmi (výchozí: CHUNK_OVERLAP)

        Returns:
            Seznam textových částí
        """
        if max_length is None:
            max_length = MAX_CHUNK_LENGTH
        if overlap is None:
            overlap = CHUNK_OVERLAP

        # Pokud je text krátký, vrať ho jako jednu část
        if len(text) <= max_length:
            return [text]

        # Normalizace mezer
        text = re.sub(r'\s+', ' ', text.strip())

        chunks = []
        current_pos = 0

        while current_pos < len(text):
            # Určení konce aktuální části
            end_pos = current_pos + max_length

            if end_pos >= len(text):
                # Zbývající text
                chunk = text[current_pos:].strip()
                if chunk:
                    chunks.append(chunk)
                break

            # Pokus najít konec věty (., !, ?, ...)
            # Hledáme nejbližší konec věty před end_pos
            sentence_end_pattern = r'[.!?…]\s+'
            matches = list(re.finditer(sentence_end_pattern, text[current_pos:end_pos]))

            if matches:
                # Použij poslední konec věty v rozsahu
                last_match = matches[-1]
                end_pos = current_pos + last_match.end()
            else:
                # Pokud není konec věty, hledáme čárku
                comma_pattern = r',\s+'
                comma_matches = list(re.finditer(comma_pattern, text[current_pos:end_pos]))
                if comma_matches:
                    last_match = comma_matches[-1]
                    end_pos = current_pos + last_match.end()
                else:
                    # Pokud není ani čárka, rozděl na mezeře
                    space_pattern = r'\s+'
                    space_matches = list(re.finditer(space_pattern, text[current_pos:end_pos]))
                    if space_matches:
                        last_match = space_matches[-1]
                        end_pos = current_pos + last_match.end()

            # Extrahuj část
            chunk = text[current_pos:end_pos].strip()
            if chunk:
                chunks.append(chunk)

            # Přesuň pozici s překrytím
            if end_pos < len(text):
                # Vrať se o overlap znaků zpět pro plynulý přechod
                current_pos = max(current_pos + 1, end_pos - overlap)
            else:
                current_pos = end_pos

        return chunks

    @staticmethod
    def split_by_sentences(text: str, max_sentences: int = 3) -> List[str]:
        """
        Rozdělí text na části podle počtu vět

        Args:
            text: Text k rozdělení
            max_sentences: Maximální počet vět v části

        Returns:
            Seznam textových částí
        """
        # Rozděl na věty
        sentence_pattern = r'[.!?…]\s+'
        sentences = re.split(sentence_pattern, text)
        sentences = [s.strip() + '.' for s in sentences if s.strip()]

        chunks = []
        current_chunk = []

        for sentence in sentences:
            current_chunk.append(sentence)

            # Pokud máme dost vět nebo překročíme délku
            if len(current_chunk) >= max_sentences or len(' '.join(current_chunk)) > MAX_CHUNK_LENGTH:
                chunks.append(' '.join(current_chunk))
                current_chunk = []

        # Přidej zbývající věty
        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks if chunks else [text]








