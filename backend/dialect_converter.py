"""
Modul pro převod standardní češtiny na různá česká nářečí

Tento modul umožňuje převádět text ze standardní češtiny na různé nářeční varianty
pomocí pravidel z lookup tabulek.
"""
import re
import json
from pathlib import Path
from typing import Dict, List, Optional
from backend.lookup_tables_loader import get_lookup_loader
from backend.config import BASE_DIR

LOOKUP_TABLES_DIR = BASE_DIR / "lookup_tables"


class DialectConverter:
    """Třída pro převod textu na různá česká nářečí"""

    def __init__(self):
        """Inicializace converteru s načtením pravidel nářečí"""
        self.lookup_loader = get_lookup_loader()
        self.nareci_pravidla = self._load_dialect_rules()
        self._compile_patterns()

    def _load_dialect_rules(self) -> Optional[Dict]:
        """Načte pravidla nářečí z JSON souboru"""
        file_path = LOOKUP_TABLES_DIR / "ceska_nareci.json"
        if not file_path.exists():
            print(f"[WARN] Soubor ceska_nareci.json neexistuje v {LOOKUP_TABLES_DIR}")
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Chyba pri nacitani ceska_nareci.json: {e}")
            return None

    def _compile_patterns(self):
        """Zkompiluje regex patterny pro rychlejší zpracování"""
        self.compiled_patterns = {}
        if not self.nareci_pravidla:
            return

        nareci = self.nareci_pravidla.get("nareci", {})
        for nareci_kod, nareci_data in nareci.items():
            self.compiled_patterns[nareci_kod] = {}
            pravidla = nareci_data.get("pravidla", {})

            # Kompilace vzorů pro samohlásky
            samohlasky = pravidla.get("samohlasky", {})
            for pravidlo_type, pravidlo_data in samohlasky.items():
                vzory = pravidlo_data.get("vzory", [])
                for vzor in vzory:
                    pattern = vzor.get("pattern")
                    if pattern:
                        try:
                            self.compiled_patterns[nareci_kod][pattern] = re.compile(pattern)
                        except Exception as e:
                            print(f"[WARN] Chyba pri kompilaci patternu {pattern}: {e}")

    def get_available_dialects(self) -> List[str]:
        """
        Vrátí seznam dostupných nářečí

        Returns:
            Seznam kódů nářečí (např. ['moravske', 'hanacke', 'slezske', ...])
        """
        if not self.nareci_pravidla:
            return []

        nareci = self.nareci_pravidla.get("nareci", {})
        return list(nareci.keys())

    def get_dialect_info(self, dialect_code: str) -> Optional[Dict]:
        """
        Vrátí informace o konkrétním nářečí

        Args:
            dialect_code: Kód nářečí (např. 'moravske', 'hanacke')

        Returns:
            Slovník s informacemi o nářečí nebo None
        """
        if not self.nareci_pravidla:
            return None

        nareci = self.nareci_pravidla.get("nareci", {})
        return nareci.get(dialect_code)

    def convert_to_dialect(self, text: str, dialect_code: str, intensity: float = 1.0) -> str:
        """
        Převádí text ze standardní češtiny na zvolené nářečí

        Args:
            text: Vstupní text ve standardní češtině
            dialect_code: Kód nářečí (např. 'moravske', 'hanacke', 'slezske', 'chodske', 'brnenske')
            intensity: Intenzita převodu (0.0-1.0), kde 1.0 = plný převod, 0.5 = částečný

        Returns:
            Text převedený na zvolené nářečí
        """
        if not self.nareci_pravidla:
            return text

        if dialect_code not in self.get_available_dialects():
            print(f"[WARN] Neznamy kod nareci: {dialect_code}")
            return text

        nareci_data = self.nareci_pravidla.get("nareci", {}).get(dialect_code, {})
        pravidla = nareci_data.get("pravidla", {})

        # Seznam slov, která se NEMĚNÍ (stopwords - krátké funkční slova)
        # Tyto slova se obvykle nepřevádějí na nářečí
        stopwords = {'pro', 'na', 'v', 's', 'z', 'k', 'o', 'u', 'se', 'si', 'je', 'jsem', 'jsme', 'jste', 'jsou'}

        processed_text = text

        # 1. Převod slovních základů (jsem -> sem, atd.)
        slovni_zaklad = pravidla.get("slovni_zaklad", {}).get("priklady", {})
        processed_text = self._apply_word_replacements(processed_text, slovni_zaklad, intensity)

        # 2. Převod samohlásek
        samohlasky = pravidla.get("samohlasky", {})
        processed_text = self._apply_vowel_rules(processed_text, samohlasky, dialect_code, intensity)

        # 3. Převod souhlásek
        souhlasky = pravidla.get("souhlasky", {})
        processed_text = self._apply_consonant_rules(processed_text, souhlasky, intensity)

        # 4. Převod koncovek
        koncovky = pravidla.get("koncovky", {}).get("priklady", {})
        processed_text = self._apply_word_replacements(processed_text, koncovky, intensity)

        # 5. Místopisný slovník (pro brněnský hantec)
        mistopisny = pravidla.get("mistopisny_slovnik", {}).get("priklady", {})
        processed_text = self._apply_word_replacements(processed_text, mistopisny, intensity)

        # 6. Slovník činností, věcí, obecná mluva (pro brněnský hantec)
        slovnik_cinnosti = pravidla.get("slovnik_cinnosti_veci", {}).get("priklady", {})
        processed_text = self._apply_word_replacements(processed_text, slovnik_cinnosti, intensity)

        # 7. Specifická slova
        specificka_slova = pravidla.get("specificka_slova", {}).get("priklady", {})
        processed_text = self._apply_word_replacements(processed_text, specificka_slova, intensity)

        return processed_text

    def _apply_word_replacements(self, text: str, replacements: Dict[str, str], intensity: float) -> str:
        """
        Aplikuje náhrady slov podle intenzity

        Args:
            text: Vstupní text
            replacements: Slovník náhrad (standardní -> nářeční)
            intensity: Intenzita převodu (0.0-1.0)

        Returns:
            Text s aplikovanými náhradami
        """
        if intensity <= 0:
            return text

        processed = text
        for standardni, narecni in replacements.items():
            # Přeskočit stopwords - krátká funkční slova se nemění
            if standardni.lower() in {'pro', 'na', 'v', 's', 'z', 'k', 'o', 'u'}:
                continue
            # Použijeme word boundary pro přesné nahrazení celých slov
            pattern = r'\b' + re.escape(standardni) + r'\b'
            if intensity >= 1.0:
                # Plný převod
                processed = re.sub(pattern, narecni, processed, flags=re.IGNORECASE)
            else:
                # Částečný převod - náhodně aplikujeme pouze část náhrad
                import random
                if random.random() < intensity:
                    processed = re.sub(pattern, narecni, processed, flags=re.IGNORECASE)

        return processed

    def _apply_vowel_rules(self, text: str, vowel_rules: Dict, dialect_code: str, intensity: float) -> str:
        """
        Aplikuje pravidla pro samohlásky

        Args:
            text: Vstupní text
            vowel_rules: Pravidla pro samohlásky
            dialect_code: Kód nářečí
            intensity: Intenzita převodu

        Returns:
            Text s aplikovanými pravidly pro samohlásky
        """
        if intensity <= 0:
            return text

        processed = text

        # Aplikace vzorů (regex patternů)
        if dialect_code in self.compiled_patterns:
            for pattern_str, compiled_pattern in self.compiled_patterns[dialect_code].items():
                # Najdeme odpovídající pravidlo pro tento pattern
                for rule_type, rule_data in vowel_rules.items():
                    vzory = rule_data.get("vzory", [])
                    for vzor in vzory:
                        if vzor.get("pattern") == pattern_str:
                            replacement = vzor.get("replacement", "")
                            if intensity >= 1.0:
                                processed = compiled_pattern.sub(replacement, processed)
                            else:
                                # Částečný převod
                                import random
                                if random.random() < intensity:
                                    processed = compiled_pattern.sub(replacement, processed)
                            break

        # Aplikace příkladů (jednoduché náhrady)
        for rule_type, rule_data in vowel_rules.items():
            priklady = rule_data.get("priklady", {})
            processed = self._apply_word_replacements(processed, priklady, intensity)

        return processed

    def _apply_consonant_rules(self, text: str, consonant_rules: Dict, intensity: float) -> str:
        """
        Aplikuje pravidla pro souhlásky

        Args:
            text: Vstupní text
            consonant_rules: Pravidla pro souhlásky
            intensity: Intenzita převodu

        Returns:
            Text s aplikovanými pravidly pro souhlásky
        """
        if intensity <= 0:
            return text

        processed = text

        # Aplikace příkladů (jednoduché náhrady)
        for rule_type, rule_data in consonant_rules.items():
            priklady = rule_data.get("priklady", {})
            processed = self._apply_word_replacements(processed, priklady, intensity)

        return processed


# Globální instance
_dialect_converter_instance: Optional[DialectConverter] = None


def get_dialect_converter() -> DialectConverter:
    """
    Vrátí globální instanci DialectConverter (singleton pattern)

    Returns:
        Instance DialectConverter
    """
    global _dialect_converter_instance
    if _dialect_converter_instance is None:
        _dialect_converter_instance = DialectConverter()
    return _dialect_converter_instance

