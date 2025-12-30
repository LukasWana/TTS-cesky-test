"""
Text Processor - zpracování textu pro TTS
"""
import re
from pathlib import Path
from typing import Optional, List
from TTS.tts.layers.xtts import tokenizer as xtts_tokenizer

import backend.config as config
from backend.config import MAX_CHUNK_LENGTH


class TextProcessor:
    """Třída pro zpracování textu před TTS generováním"""

    def __init__(self, model=None):
        """
        Args:
            model: XTTS model instance (pro přístup k tokenizeru)
        """
        self.model = model
        # None = ještě nezkoušeno, False = není dostupné, jinak tokenizer instance
        self._bpe_tokenizer = None

    def _get_bpe_tokenizer(self):
        """
        Vytvoří/vrátí XTTS BPE tokenizer (stejný tokenizer.json jako upstream XTTS).
        Používá se pro počítání tokenů a bezpečné dělení textu pod limit 400 tokenů.
        """
        if self._bpe_tokenizer is False:
            return None
        if self._bpe_tokenizer is not None:
            return self._bpe_tokenizer

        def _silence_len_warnings(tok_obj):
            # VoiceBpeTokenizer.encode() volá check_input_length(), která printuje warningy
            # při překročení char limitu (typicky 186 pro cs). To je pro nás při token-countingu
            # velmi hlučné a není to chyba, takže to ztišíme.
            try:
                if hasattr(tok_obj, "check_input_length"):
                    tok_obj.check_input_length = lambda *_args, **_kwargs: None
            except Exception:
                pass

        # 1) Zkus tokenizer přímo z modelu (nejspolehlivější)
        try:
            if self.model is not None and hasattr(self.model, "synthesizer"):
                tts_model = getattr(self.model.synthesizer, "tts_model", None)
                model_tokenizer = getattr(tts_model, "tokenizer", None)
                if model_tokenizer is not None:
                    _silence_len_warnings(model_tokenizer)
                    self._bpe_tokenizer = model_tokenizer
                    return self._bpe_tokenizer
        except Exception:
            pass

        # 2) Fallback: tokenizer.json z balíčku (ne všechny instalace ho bohužel obsahují)
        try:
            import json
            from pathlib import Path
            import os

            # Zkus najít tokenizer.json v TTS balíčku
            try:
                import TTS
                tts_path = Path(TTS.__file__).parent
                tokenizer_path = tts_path / "tts" / "layers" / "xtts" / "tokenizer.json"
                if tokenizer_path.exists():
                    from TTS.tts.layers.xtts.tokenizer import VoiceBpeTokenizer
                    tok = VoiceBpeTokenizer(str(tokenizer_path))
                    _silence_len_warnings(tok)
                    self._bpe_tokenizer = tok
                    return self._bpe_tokenizer
            except Exception:
                pass

            # Alternativní cesta: zkus najít v cache nebo v běžných umístěních
            try:
                from TTS.tts.layers.xtts.tokenizer import VoiceBpeTokenizer
                # Zkus najít tokenizer.json v různých umístěních
                possible_paths = [
                    Path.home() / ".local" / "share" / "tts" / "tokenizer.json",
                    Path("/usr/local/share/tts/tokenizer.json"),
                    Path("/usr/share/tts/tokenizer.json"),
                ]
                for path in possible_paths:
                    if path.exists():
                        tok = VoiceBpeTokenizer(str(path))
                        _silence_len_warnings(tok)
                        self._bpe_tokenizer = tok
                        return self._bpe_tokenizer
            except Exception:
                pass

        except Exception:
            pass

        # Pokud se nepodařilo načíst tokenizer, označ to jako False
        self._bpe_tokenizer = False
        return None

    def count_xtts_tokens(self, text: str, language: str = "cs") -> Optional[int]:
        """Vrátí počet XTTS tokenů pro daný text, nebo None pokud se to nepovede."""
        tok = self._get_bpe_tokenizer()
        if tok is None:
            return None
        try:
            # VoiceBpeTokenizer má encode(txt, lang) → ids
            if hasattr(tok, "encode"):
                return len(tok.encode(text, language))
        except Exception:
            return None
        return None

    def split_text_by_xtts_tokens(self, text: str, language: str = "cs") -> List[str]:
        """
        Rozseká text tak, aby žádný chunk nepřekročil config.XTTS_TARGET_MAX_TOKENS.
        Preferuje dělení na koncích vět, pak na slovech, a nakonec nouzově po znacích.
        """
        max_tokens = getattr(config, "XTTS_TARGET_MAX_TOKENS", 380)
        text = re.sub(r"\s+", " ", (text or "").strip())
        if not text:
            return []

        # Pokud tokenizer není dostupný, drž se konzervativního char splitu (bez overlap = žádné opakování)
        if self._get_bpe_tokenizer() is None:
            try:
                from backend.text_splitter import TextSplitter
                return TextSplitter.split_text(text, max_length=MAX_CHUNK_LENGTH, overlap=0)
            except Exception:
                # úplný fallback: hrubé dělení po MAX_CHUNK_LENGTH znacích
                return [text[i:i + MAX_CHUNK_LENGTH].strip() for i in range(0, len(text), MAX_CHUNK_LENGTH) if text[i:i + MAX_CHUNK_LENGTH].strip()]

        n = self.count_xtts_tokens(text, language)
        if n is not None and n <= max_tokens:
            return [text]

        def split_hard_by_chars(s: str) -> List[str]:
            out: List[str] = []
            s = s.strip()
            if not s:
                return out
            start = 0
            while start < len(s):
                # binární vyhledání nejdelšího prefixu, který se vejde do token budgetu
                lo = start + 1
                hi = len(s)
                best = None
                while lo <= hi:
                    mid = (lo + hi) // 2
                    part = s[start:mid].strip()
                    if not part:
                        lo = mid + 1
                        continue
                    tn = self.count_xtts_tokens(part, language)
                    if tn is None:
                        # fallback: když selže tokenizer, řežeme po MAX_CHUNK_LENGTH znacích
                        best = min(start + MAX_CHUNK_LENGTH, len(s))
                        break
                    if tn <= max_tokens:
                        best = mid
                        lo = mid + 1
                    else:
                        hi = mid - 1

                if best is None:
                    best = start + 1
                chunk = s[start:best].strip()
                if chunk:
                    out.append(chunk)
                start = best
            return out

        def split_by_words(sentence: str) -> List[str]:
            words = [w for w in sentence.strip().split(" ") if w]
            out: List[str] = []
            cur = ""
            for w in words:
                cand = w if not cur else f"{cur} {w}"
                tn = self.count_xtts_tokens(cand, language)
                if tn is not None and tn <= max_tokens:
                    cur = cand
                    continue

                if cur:
                    out.append(cur)
                    cur = w
                    # Pokud i samotné slovo/fragment přetéká, řež tvrdě
                    if (self.count_xtts_tokens(cur, language) or (max_tokens + 1)) > max_tokens:
                        out.extend(split_hard_by_chars(cur))
                        cur = ""
                else:
                    out.extend(split_hard_by_chars(w))
                    cur = ""

            if cur:
                out.append(cur)
            return out

        # Primárně dělení na věty
        sentences = re.split(r"(?<=[.!?…])\s+", text)
        chunks: List[str] = []
        cur = ""
        for s in sentences:
            s = (s or "").strip()
            if not s:
                continue
            cand = s if not cur else f"{cur} {s}"
            tn = self.count_xtts_tokens(cand, language)
            if tn is not None and tn <= max_tokens:
                cur = cand
                continue

            if cur:
                chunks.append(cur)
                cur = ""

            # samotná věta je dlouhá → rozdělit podle slov / nouzově po znacích
            if (self.count_xtts_tokens(s, language) or (max_tokens + 1)) <= max_tokens:
                cur = s
            else:
                chunks.extend(split_by_words(s))

        if cur:
            chunks.append(cur)

        # Poslední pojistka: kdyby cokoli přeteklo (např. tokenizer None), dořež
        safe_chunks: List[str] = []
        for ch in chunks:
            tn = self.count_xtts_tokens(ch, language)
            if tn is None or tn <= max_tokens:
                safe_chunks.append(ch)
            else:
                safe_chunks.extend(split_hard_by_chars(ch))

        return [c for c in safe_chunks if c.strip()]

    def preprocess_text(self, text: str, language: str, enable_dialect_conversion: Optional[bool] = None,
                       dialect_code: Optional[str] = None, dialect_intensity: float = 1.0,
                       apply_voicing: Optional[bool] = None, apply_glottal_stop: Optional[bool] = None) -> str:
        """
        Předzpracuje text pro TTS generování.

        Args:
            text: Vstupní text
            language: Jazyk textu
            enable_dialect_conversion: Zapnout převod na nářečí
            dialect_code: Kód nářečí
            dialect_intensity: Intenzita převodu
            apply_voicing: Zda aplikovat spodobu znělosti
            apply_glottal_stop: Zda vkládat ráz

        Returns:
            Předzpracovaný text
        """
        from backend.cs_pipeline import preprocess_czech_text
        return preprocess_czech_text(
            text,
            language,
            enable_dialect_conversion=enable_dialect_conversion,
            dialect_code=dialect_code,
            dialect_intensity=dialect_intensity,
            apply_voicing=apply_voicing,
            apply_glottal_stop=apply_glottal_stop
        )

