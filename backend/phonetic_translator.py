"""
Fonetický přepis cizích slov v českém textu

Tento modul poskytuje funkci pro přepis anglických a dalších cizích slov
na fonetické ekvivalenty v češtině, aby je TTS model správně vyslovil.
"""
import re
from typing import Dict, Optional
from backend.lookup_tables_loader import get_lookup_loader


class PhoneticTranslator:
    """Třída pro fonetický přepis cizích slov v textu"""

    def __init__(self):
        """Inicializace překladače se slovníky"""
        self.lookup_loader = get_lookup_loader()

        # Mapování jazyků na jejich slovníky
        self.language_dicts: Dict[str, Dict[str, str]] = {
            'en': self.lookup_loader.get_english_phonetic(),
        }

        # České stop words - slova, která se NEPŘEPISUJÍ foneticky
        # (předložky, spojky, zájmena, pomocná slovesa, částice, atd.)
        self.czech_stopwords = {
            # Předložky
            'za', 'na', 'v', 's', 'z', 'k', 'o', 'u', 'pro', 'před', 'pod', 'nad',
            'přes', 'bez', 'od', 'do', 'po', 'při', 'mezi', 'kolem', 'okolo', 'přes',
            'kromě', 'mimo', 'vedle', 'blízko', 'daleko', 'před', 'za', 'podle',
            # Spojky
            'a', 'i', 'ale', 'nebo', 'protože', 'když', 'že', 'aby', 'kdyby',
            'pak', 'tak', 'také', 'takže', 'proto', 'protože', 'neboť', 'nebo',
            'avšak', 'však', 'ale', 'jenže', 'přesto', 'nicméně',
            # Zájmena osobní
            'já', 'ty', 'on', 'ona', 'ono', 'my', 'vy', 'oni', 'ony', 'ona',
            'mne', 'mě', 'tebe', 'tě', 'něj', 'ho', 'ní', 'ji', 'nás', 'vás',
            'nimi', 'jimi', 'nimi', 'jimi',
            # Zájmena přivlastňovací
            'můj', 'tvůj', 'jeho', 'její', 'náš', 'váš', 'jejich',
            'mého', 'tvé', 'jeho', 'její', 'naše', 'vaše', 'jejich',
            # Zájmena ukazovací
            'to', 'ta', 'ten', 'toto', 'tato', 'tento', 'tam', 'tady', 'tamto',
            'tamhle', 'tadyhle', 'tamhleto', 'tadyhleto',
            # Zájmena tázací
            'kdo', 'co', 'jaký', 'který', 'kde', 'kam', 'kdy', 'proč', 'jak',
            'kolik', 'čí', 'čího', 'čemu', 'čím',
            # Zájmena vztažná
            'který', 'která', 'které', 'jenž', 'jež', 'jehož', 'jejíž',
            # Zájmena neurčitá
            'někdo', 'něco', 'nějaký', 'některý', 'někde', 'někam', 'někdy',
            'kdokoli', 'cokoli', 'jakýkoli', 'kdekoli', 'kdykoli',
            # Částice
            'ne', 'ano', 'ne', 'nechť', 'ať', 'kéž', 'jen', 'jenom', 'pouze',
            'také', 'i', 'ani', 'nebo', 'či', 'a', 'ale', 'však',
            # Pomocná slovesa
            'je', 'jsem', 'jsme', 'jste', 'jsou', 'být', 'mít', 'bývat', 'mívat',
            'byl', 'byla', 'bylo', 'byli', 'byly', 'bude', 'budou', 'byl by',
            # Reflexivní zájmena
            'se', 'si', 'sebe', 'sobě', 'sebou',
            # Krátké tvary zájmen
            'mi', 'ti', 'mu', 'jí', 'nám', 'vám', 'jim', 'jim',
            # Další běžná česká slova
            'jak', 'tak', 'pak', 'kde', 'kdy', 'kdo', 'co', 'proč', 'jaký',
            'takový', 'takovýto', 'takovýhle', 'takovýto',
            # Číslovky základní (1-10)
            'jeden', 'dva', 'tři', 'čtyři', 'pět', 'šest', 'sedm', 'osm', 'devět', 'deset',
            # Číslovky řadové (1-10)
            'první', 'druhý', 'třetí', 'čtvrtý', 'pátý', 'šestý', 'sedmý', 'osmý', 'devátý', 'desátý'
        }

        # Načtení lookup tabulek pro přejatá slova
        try:
            prejata_slova = self.lookup_loader.get_prejata_slova_dict()
            if prejata_slova:
                # Přidáme přejatá slova do českého slovníku
                if 'cs' not in self.language_dicts:
                    self.language_dicts['cs'] = {}
                self.language_dicts['cs'].update(prejata_slova)
                print(f"[OK] Nacteno {len(prejata_slova)} prejatych slov z lookup tabulek")
        except Exception as e:
            print(f"[WARN] Varovani: Nepodarilo se nacist lookup tabulky pro prejata slova: {e}")

    def translate_foreign_words(self, text: str, target_language: str = "cs") -> str:
        """
        Přepíše cizí slova v textu na fonetické ekvivalenty v cílovém jazyce

        Args:
            text: Vstupní text obsahující cizí slova
            target_language: Cílový jazyk pro fonetický přepis (výchozí: "cs")

        Returns:
            Text s přepsanými cizími slovy
        """
        if target_language != "cs":
            # Prozatím podporujeme pouze češtinu
            return text

        processed_text = text

        # Nejdříve aplikujeme český slovník (přejatá slova) - má prioritu
        if 'cs' in self.language_dicts:
            processed_text = self._apply_phonetic_dict(processed_text, self.language_dicts['cs'])

        # Pak projdeme ostatní jazyky
        for lang_code, phonetic_dict in self.language_dicts.items():
            if lang_code != 'cs':  # Český slovník už jsme použili
                processed_text = self._apply_phonetic_dict(processed_text, phonetic_dict)

        return processed_text

    def _apply_phonetic_dict(self, text: str, phonetic_dict: Dict[str, str]) -> str:
        """
        Aplikuje fonetický slovník na text

        Args:
            text: Vstupní text
            phonetic_dict: Slovník s mapováním cizích slov na fonetické přepisy

        Returns:
            Text s nahrazenými slovy
        """
        if not phonetic_dict:
            return text

        processed_text = text

        # Seřadíme slova od nejdelšího po nejkratší, aby se delší fráze nahradily jako první
        sorted_words = sorted(phonetic_dict.keys(), key=len, reverse=True)

        for foreign_word in sorted_words:
            # Přeskočit české stop words - nepřepisovat je foneticky
            if foreign_word.lower() in self.czech_stopwords:
                continue

            phonetic = phonetic_dict[foreign_word]

            # Pro zkratky psané velkými písmeny (např. SE, ES, USA, UK, EU)
            # použijeme case-sensitive matching, aby se nenašly česká slova
            # jako "se", "es", "at", "uk", "eu" atd.
            is_uppercase_abbreviation = (
                len(foreign_word) >= 2 and
                foreign_word.isupper() and
                foreign_word.isalpha()
            )

            pattern = r'\b' + re.escape(foreign_word) + r'\b'

            # Použijeme lambda funkci pro náhradu, aby se escape sekvence v phonetic hodnotě
            # neinterpretovaly jako regex pattern
            replacement = lambda m: phonetic

            if is_uppercase_abbreviation:
                # Case-sensitive pro zkratky psané velkými písmeny
                # nahradí pouze velká písmena (SE, ES, USA, atd.)
                processed_text = re.sub(pattern, replacement, processed_text)
            else:
                # Case-insensitive pro ostatní slova
                # nahradí pouze pokud slovo není součástí českého slova
                processed_text = re.sub(pattern, replacement, processed_text, flags=re.IGNORECASE)

        return processed_text

    def add_dictionary(self, language_code: str, phonetic_dict: Dict[str, str]):
        """
        Přidá nový fonetický slovník pro další jazyk

        Args:
            language_code: Kód jazyka (např. 'de' pro němčinu)
            phonetic_dict: Slovník s mapováním slov na fonetické přepisy
        """
        self.language_dicts[language_code] = phonetic_dict


# Globální instance pro jednoduché použití
_translator_instance = None


def get_phonetic_translator() -> PhoneticTranslator:
    """
    Vrátí globální instanci PhoneticTranslator (singleton pattern)

    Returns:
        Instance PhoneticTranslator
    """
    global _translator_instance
    if _translator_instance is None:
        _translator_instance = PhoneticTranslator()
    return _translator_instance


def preprocess_czech_text(text: str) -> str:
    """
    Jednoduchá funkce pro přepis cizích slov v českém textu (compatibilní s původním API)

    Args:
        text: Vstupní text

    Returns:
        Text s přepsanými cizími slovy
    """
    translator = get_phonetic_translator()
    return translator.translate_foreign_words(text, target_language="cs")
