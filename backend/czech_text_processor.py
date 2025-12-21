"""
Modul pro pokročilé předzpracování českého textu pomocí lookup tabulek

Aplikuje pravidla:
- Spodoba znělosti
- Vkládání rázu
- Oprava souhláskových skupin
"""
import re
from typing import List, Tuple, Dict
from backend.lookup_tables_loader import get_lookup_loader


class CzechTextProcessor:
    """Třída pro pokročilé předzpracování českého textu"""

    def __init__(self):
        """Inicializace procesoru s lookup tabulkami"""
        self.lookup_loader = get_lookup_loader()
        self.znele_neznele_pary = self.lookup_loader.get_znele_neznele_pary()
        self.souhlsakove_skupiny = self.lookup_loader.get_souhlsakove_skupiny_rules()
        self.raz_pravidla = self.lookup_loader.get_raz_pravidla()

        # Definice skupin souhlásek pro spodobu
        self.znele = set("bdďgzžhvdz")
        self.neznele = set("ptťksšchfcč")
        self.sonory = set("mnňlrj")
        self.vsechny_souhlasky = self.znele | self.neznele | self.sonory | set("ř")

        # Mapování pro spodobu (znělá -> neznělá)
        # znele_neznele_pary je {neznele: znele}
        self.to_neznele = {v: k for k, v in self.znele_neznele_pary.items()}
        # Mapování pro spodobu (neznělá -> znělá)
        self.to_znele = self.znele_neznele_pary

        # Zkratky pro převod
        self.abbreviations = {
            "např.": "například",
            "atd.": "a tak dále",
            "tj.": "to jest",
            "tzn.": "to znamená",
            "apod.": "a podobně",
            "př.": "příklad",
            "č.": "číslo",
            "str.": "strana",
            "s.": "strana",
            "r.": "rok",
            "m.": "měsíc",
            "min.": "minuta",
            "sek.": "sekunda",
            "km/h": "kilometrů za hodinu",
            "m/s": "metrů za sekundu",
            "cca": "přibližně",
            "atp.": "a tak podobně",
            "tzv.": "takzvaný",
            "vč.": "včetně",
            "vč": "včetně",
            "čes.": "český",
            "angl.": "anglický",
            "tel.": "telefon",
            "č.p.": "číslo popisné",
            "č.j.": "číslo jednací",
            "Kč": "korun českých",
            "mil.": "milionů",
            "mld.": "miliard",
            "tis.": "tisíc"
        }

        # Slovník pro základní čísla (0-100)
        self.number_words = {
            0: "nula", 1: "jedna", 2: "dva", 3: "tři", 4: "čtyři", 5: "pět",
            6: "šest", 7: "sedm", 8: "osm", 9: "devět", 10: "deset",
            11: "jedenáct", 12: "dvanáct", 13: "třináct", 14: "čtrnáct", 15: "patnáct",
            16: "šestnáct", 17: "sedmnáct", 18: "osmnáct", 19: "devatenáct", 20: "dvacet",
            30: "třicet", 40: "čtyřicet", 50: "padesát", 60: "šedesát",
            70: "sedmdesát", 80: "osmdesát", 90: "devadesát", 100: "sto"
        }

    def process_text(self, text: str, apply_voicing: bool = True, apply_glottal_stop: bool = True,
                     apply_consonant_groups: bool = True, expand_abbreviations: bool = True,
                     expand_numbers: bool = True) -> str:
        """
        Zpracuje text aplikací českých fonetických pravidel
        """
        processed = text

        # 0. Normalizace (odstranění přebytečných mezer atd.)
        processed = self.normalize_text(processed)

        # 1. Převod zkratek
        if expand_abbreviations:
            processed = self._expand_abbreviations(processed)

        # 2. Převod čísel
        if expand_numbers:
            processed = self._expand_numbers(processed)

        # 3. Oprava souhláskových skupin (mě -> mňe)
        if apply_consonant_groups and self.souhlsakove_skupiny:
            processed = self._fix_consonant_groups(processed)

        # 4. Spodoba znělosti (na konci slova, před neznělými/znělými)
        if apply_voicing and self.znele_neznele_pary:
            processed = self._apply_voicing_assimilation(processed)

        # 5. Vkládání rázu
        if apply_glottal_stop:
            processed = self._apply_glottal_stop(processed)

        return processed

    def _expand_abbreviations(self, text: str) -> str:
        """Převede zkratky na plné formy"""
        processed = text
        for abbr, full in self.abbreviations.items():
            if abbr.endswith('.'):
                pattern = r'\b' + re.escape(abbr)
            else:
                pattern = r'\b' + re.escape(abbr) + r'\b'
            processed = re.sub(pattern, full, processed, flags=re.IGNORECASE)
        return processed

    def _expand_numbers(self, text: str) -> str:
        """Převede čísla na slova"""
        def number_to_words(num_str: str) -> str:
            try:
                num = int(num_str)
                if num in self.number_words:
                    return self.number_words[num]
                elif num < 100:
                    tens = (num // 10) * 10
                    ones = num % 10
                    if tens in self.number_words and ones in self.number_words:
                        return f"{self.number_words[tens]} {self.number_words[ones]}"
                return num_str
            except:
                return num_str

        pattern = r'\b([0-9]{1,3})\b'
        return re.sub(pattern, lambda m: number_to_words(m.group(1)), text)

    def _fix_consonant_groups(self, text: str) -> str:
        """Opraví problematické souhláskové skupiny"""
        # Prozatím jen placeholder pro budoucí rozšíření
        return text

    def _apply_voicing_assimilation(self, text: str) -> str:
        """
        Aplikuje spodobu znělosti
        """
        words = text.split()
        if not words:
            return text

        processed_words = []
        for i, word in enumerate(words):
            chars = list(word)
            n = len(chars)
            if n == 0:
                processed_words.append("")
                continue

            next_word = words[i+1] if i + 1 < len(words) else ""
            next_first_char = next_word[0].lower() if next_word else ""

            # 1. Hranice slov (poslední písmeno slova)
            last_idx = n - 1
            last_char = chars[last_idx].lower()

            # Určíme kontext následujícího zvuku
            if not next_first_char:
                # Konec promluvy -> zánik znělosti
                if last_char in self.to_neznele:
                    chars[last_idx] = self.to_neznele[last_char]
            elif next_first_char in self.neznele or next_first_char == "ch":
                # Následuje neznělá -> regrese k neznělosti
                if last_char in self.to_neznele:
                    chars[last_idx] = self.to_neznele[last_char]
            elif next_first_char in self.znele and next_first_char != "v":
                # Následuje znělá -> regrese k znělosti
                if last_char in self.to_znele:
                    chars[last_idx] = self.to_znele[last_char]

            # 2. Uvnitř slova (regresivní asimilace)
            for j in range(n - 2, -1, -1):
                curr = chars[j].lower()
                nxt = chars[j+1].lower()

                # Pokud nxt je sonora nebo 'v', asimilace se neděje
                if nxt == 'v' or nxt in self.sonory:
                    continue

                if nxt in self.neznele or nxt == "ch":
                    if curr in self.to_neznele:
                        chars[j] = self.to_neznele[curr]
                elif nxt in self.znele:
                    if curr in self.to_znele:
                        chars[j] = self.to_znele[curr]

            processed_words.append("".join(chars))

        return " ".join(processed_words)

    def _apply_glottal_stop(self, text: str) -> str:
        """Vkládá ráz (glottální okluze)"""
        prepositions = r"\b(v|z|s|k|o|u|nad|pod|před|přes|bez|od|do)\b"
        vowels = "aeiouáéíóúyý"

        def add_raz(match):
            prep = match.group(1)
            word = match.group(2)
            return f"{prep} '{word}"

        processed = re.sub(rf"({prepositions})\s+([{vowels}])", add_raz, text, flags=re.IGNORECASE)
        processed = re.sub(rf"(^|[.!?]\s+)([{vowels}])", r"\1'\2", processed, flags=re.IGNORECASE)

        return processed

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalizuje text"""
        text = re.sub(r'\s+', ' ', text)
        text = text.replace('...', '…')
        text = text.replace('--', '—')
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)
        return text.strip()


# Globální instance
_text_processor_instance = None


def get_czech_text_processor() -> CzechTextProcessor:
    """Singleton pattern for CzechTextProcessor"""
    global _text_processor_instance
    if _text_processor_instance is None:
        _text_processor_instance = CzechTextProcessor()
    return _text_processor_instance

