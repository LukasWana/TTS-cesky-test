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
            "tis.": "tisíc",
            # Rozšířené zkratky
            "ing.": "inženýr",
            "MUDr.": "doktor medicíny",
            "PhDr.": "doktor filozofie",
            "RNDr.": "doktor přírodních věd",
            "doc.": "docent",
            "prof.": "profesor",
            "p. o.": "pořadí",
            "resp.": "respektive",
            "max.": "maximálně",
            "min.": "minimálně",
            "kap.": "kapitola",
            "obr.": "obrázek",
            "tab.": "tabulka",
            "viz": "vizte",
            "tz.": "to znamená"
        }

        # Řadové číslovky
        self.ordinal_words = {
            1: "první", 2: "druhý", 3: "třetí", 4: "čtvrtý", 5: "pátý",
            6: "šestý", 7: "sedmý", 8: "osmý", 9: "devátý", 10: "desátý",
            11: "jedenáctý", 12: "dvanáctý", 13: "třináctý", 14: "čtrnáctý", 15: "patnáctý",
            16: "šestnáctý", 17: "sedmnáctý", 18: "osmnáctý", 19: "devatenáctý",
            20: "dvacátý", 30: "třicátý", 40: "čtyřicátý", 50: "padesátý",
            60: "šedesátý", 70: "sedmdesátý", 80: "osmdesátý", 90: "devadesátý",
            100: "stý", 1000: "tisící", 1_000_000: "miliontý"
        }

        # Jednotky pro čísla
        self.units = {
            'kg': 'kilogramů', 'g': 'gramů', 't': 'tun',
            'km': 'kilometrů', 'm': 'metrů', 'cm': 'centimetrů', 'mm': 'milimetrů',
            'l': 'litrů', 'ml': 'mililitrů',
            'Kč': 'korun', '€': 'eur', '$': 'dolarů', 'USD': 'dolarů', 'EUR': 'eur',
            'h': 'hodin', 'min': 'minut', 's': 'sekund',
            '°C': 'stupňů Celsia', '°F': 'stupňů Fahrenheita'
        }

        # Slovník pro základní čísla (0-100) a větší číslovky
        self.number_words = {
            # Základní čísla 0-19
            0: "nula", 1: "jedna", 2: "dva", 3: "tři", 4: "čtyři", 5: "pět",
            6: "šest", 7: "sedm", 8: "osm", 9: "devět", 10: "deset",
            11: "jedenáct", 12: "dvanáct", 13: "třináct", 14: "čtrnáct", 15: "patnáct",
            16: "šestnáct", 17: "sedmnáct", 18: "osmnáct", 19: "devatenáct",
            # Desítky
            20: "dvacet", 30: "třicet", 40: "čtyřicet", 50: "padesát", 60: "šedesát",
            70: "sedmdesát", 80: "osmdesát", 90: "devadesát",
            # Stovky
            100: "sto", 200: "dvě stě", 300: "tři sta", 400: "čtyři sta", 500: "pět set",
            600: "šest set", 700: "sedm set", 800: "osm set", 900: "devět set",
            # Tisíce
            1000: "tisíc", 2000: "dva tisíce", 3000: "tři tisíce", 4000: "čtyři tisíce",
            5000: "pět tisíc", 6000: "šest tisíc", 7000: "sedm tisíc", 8000: "osm tisíc",
            9000: "devět tisíc",
            # Milióny
            1_000_000: "milión", 2_000_000: "dva milióny", 3_000_000: "tři milióny",
            4_000_000: "čtyři milióny", 5_000_000: "pět miliónů", 6_000_000: "šest miliónů",
            7_000_000: "sedm miliónů", 8_000_000: "osm miliónů", 9_000_000: "devět miliónů",
            # Miliardy
            1_000_000_000: "miliarda", 2_000_000_000: "dvě miliardy", 3_000_000_000: "tři miliardy",
            4_000_000_000: "čtyři miliardy", 5_000_000_000: "pět miliard", 6_000_000_000: "šest miliard",
            7_000_000_000: "sedm miliard", 8_000_000_000: "osm miliard", 9_000_000_000: "devět miliard"
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

        # 2. Převod čísel (řadové číslovky, desetinná čísla, procenta, čas, jednotky)
        if expand_numbers:
            # Nejdřív zpracujeme speciální případy (čas, procenta, jednotky)
            processed = self._expand_time(processed)
            processed = self._expand_percentages(processed)
            processed = self._expand_numbers_with_units(processed)
            # Pak desetinná čísla (před řadovými, aby se nekonfliktovaly)
            processed = self._expand_decimal_numbers(processed)
            # Pak řadové číslovky
            processed = self._expand_ordinal_numbers(processed)
            # Nakonec základní čísla
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
                # Odstranění mezer a čárek z čísla (např. "1 000 000" -> "1000000")
                num_str_clean = num_str.replace(' ', '').replace(',', '').replace('_', '')
                num = int(num_str_clean)

                # Přímá shoda v slovníku
                if num in self.number_words:
                    return self.number_words[num]

                # Čísla 0-99
                if num < 100:
                    if num < 20:
                        return num_str  # Mělo by být v slovníku
                    tens = (num // 10) * 10
                    ones = num % 10
                    if tens in self.number_words:
                        if ones == 0:
                            return self.number_words[tens]
                        elif ones in self.number_words:
                            return f"{self.number_words[tens]} {self.number_words[ones]}"

                # Čísla 100-999 (stovky)
                elif num < 1000:
                    hundreds = (num // 100) * 100
                    remainder = num % 100
                    if hundreds in self.number_words:
                        if remainder == 0:
                            return self.number_words[hundreds]
                        else:
                            remainder_str = number_to_words(str(remainder))
                            return f"{self.number_words[hundreds]} {remainder_str}"

                # Čísla 1000-999999 (tisíce)
                elif num < 1_000_000:
                    thousands = num // 1000
                    remainder = num % 1000
                    thousands_str = number_to_words(str(thousands))
                    # Správný tvar "tisíc" vs "tisíce" vs "tisíc"
                    if thousands == 1:
                        thousand_word = "tisíc"
                    elif thousands in [2, 3, 4]:
                        thousand_word = "tisíce"
                    else:
                        thousand_word = "tisíc"

                    if remainder == 0:
                        return f"{thousands_str} {thousand_word}"
                    else:
                        remainder_str = number_to_words(str(remainder))
                        return f"{thousands_str} {thousand_word} {remainder_str}"

                # Čísla 1000000-999999999 (miliony)
                elif num < 1_000_000_000:
                    millions = num // 1_000_000
                    remainder = num % 1_000_000
                    millions_str = number_to_words(str(millions))
                    # Správný tvar "milión" vs "milióny" vs "miliónů"
                    if millions == 1:
                        million_word = "milión"
                    elif millions in [2, 3, 4]:
                        million_word = "milióny"
                    else:
                        million_word = "miliónů"

                    if remainder == 0:
                        return f"{millions_str} {million_word}"
                    else:
                        remainder_str = number_to_words(str(remainder))
                        return f"{millions_str} {million_word} {remainder_str}"

                # Čísla 1000000000+ (miliardy)
                else:
                    billions = num // 1_000_000_000
                    remainder = num % 1_000_000_000
                    billions_str = number_to_words(str(billions))
                    # Správný tvar "miliarda" vs "miliardy" vs "miliard"
                    if billions == 1:
                        billion_word = "miliarda"
                    elif billions in [2, 3, 4]:
                        billion_word = "miliardy"
                    else:
                        billion_word = "miliard"

                    if remainder == 0:
                        return f"{billions_str} {billion_word}"
                    else:
                        remainder_str = number_to_words(str(remainder))
                        return f"{billions_str} {billion_word} {remainder_str}"

                return num_str
            except:
                return num_str

        # Pattern zachytí čísla s mezerami, čárkami nebo podtržítky jako oddělovači
        # Např: "1000", "1 000", "1,000", "1_000", "1 000 000", "1000000", atd.
        # Zachytí čísla od 1 do 12 cifer (maximálně miliardy)
        pattern = r'\b([0-9]{1,3}(?:[\s,_][0-9]{3})*|[0-9]{4,12})\b'
        return re.sub(pattern, lambda m: number_to_words(m.group(1)), text)

    def _fix_consonant_groups(self, text: str) -> str:
        """Opraví problematické souhláskové skupiny podle lookup tabulek"""
        if not self.souhlsakove_skupiny:
            return text

        processed = text
        skupiny = self.souhlsakove_skupiny.get("skupiny", {})

        # Zpracování skupiny "mě" -> "mňe"
        if "mě" in skupiny:
            priklady = skupiny["mě"].get("priklady", {})
            for slovo, spravne in priklady.items():
                # Použijeme word boundary pro přesné nahrazení
                pattern = r'\b' + re.escape(slovo) + r'\b'
                processed = re.sub(pattern, spravne, processed, flags=re.IGNORECASE)

        # Zpracování nk/ng -> ŋ (pouze uvnitř slov, ne na hranici)
        # Poznámka: Toto je fonetická změna, která se obvykle nedělá na textové úrovni
        # ale můžeme ji aplikovat pro speciální případy z lookup tabulky
        if "nk_ng" in skupiny:
            priklady = skupiny["nk_ng"].get("priklady", {})
            for slovo, spravne in priklady.items():
                if isinstance(spravne, list):
                    spravne = spravne[0]  # Vezmeme první variantu
                pattern = r'\b' + re.escape(slovo) + r'\b'
                processed = re.sub(pattern, spravne, processed, flags=re.IGNORECASE)

        return processed

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

        # Nejdřív zpracujeme diftongy (delší sekvence), pak jednotlivé samohlásky
        # Ráz po předložkách před diftongy (ou, au, eu, ei, ai, oi)
        processed = re.sub(rf"({prepositions})\s+(ou|au|eu|ei|ai|oi)", add_raz, text, flags=re.IGNORECASE)
        # Ráz po předložkách před samohláskami
        processed = re.sub(rf"({prepositions})\s+([{vowels}])", add_raz, processed, flags=re.IGNORECASE)

        # Ráz na začátku věty nebo po interpunkci před diftongy
        processed = re.sub(rf"(^|[.!?]\s+)(ou|au|eu|ei|ai|oi)", r"\1'\2", processed, flags=re.IGNORECASE)
        # Ráz na začátku věty nebo po interpunkci před samohláskami
        processed = re.sub(rf"(^|[.!?]\s+)([{vowels}])", r"\1'\2", processed, flags=re.IGNORECASE)

        return processed

    def _number_to_words_simple(self, num: int) -> str:
        """Pomocná metoda pro převod čísla na slova (zjednodušená verze)"""
        if num in self.number_words:
            return self.number_words[num]
        if num < 100:
            tens = (num // 10) * 10
            ones = num % 10
            if tens in self.number_words and ones in self.number_words:
                return f"{self.number_words[tens]} {self.number_words[ones]}"
        return str(num)

    def _expand_ordinal_numbers(self, text: str) -> str:
        """Převede řadové číslovky na slova (1. -> první)"""
        def ordinal_to_words(match):
            num_str = match.group(1)
            try:
                num = int(num_str)
                if num in self.ordinal_words:
                    return self.ordinal_words[num]
                # Pro složená čísla použijeme základní číslovku + koncovku
                if num < 100:
                    base = self._number_to_words_simple(num)
                    # Odstraníme poslední písmeno a přidáme "ý"
                    if base.endswith('a'):
                        return base[:-1] + 'ý'
                    elif base.endswith('y'):
                        return base[:-1] + 'ý'
                    else:
                        return base + 'ý'
            except:
                pass
            return match.group(0)

        # Zachytí čísla s tečkou na konci (řadové číslovky)
        # Ale ne desetinná čísla (ty už jsou zpracovaná)
        # Pattern: číslo + tečka + mezera nebo konec řádku (ne další číslice)
        pattern = r'\b([0-9]+)\.(?=\s|$|[^0-9])'
        return re.sub(pattern, ordinal_to_words, text)

    def _expand_decimal_numbers(self, text: str) -> str:
        """Převede desetinná čísla na slova (3.14 -> tři celá čtrnáct setin)"""
        def decimal_to_words(match):
            whole = match.group(1)
            decimal = match.group(2)
            try:
                whole_str = self._number_to_words_simple(int(whole))
                # Pro desetinnou část použijeme zjednodušený převod
                decimal_num = int(decimal)
                if len(decimal) == 1:
                    decimal_str = self._number_to_words_simple(decimal_num)
                    return f"{whole_str} celá {decimal_str} desetina"
                elif len(decimal) == 2:
                    decimal_str = self._number_to_words_simple(decimal_num)
                    return f"{whole_str} celá {decimal_str} setin"
                else:
                    decimal_str = self._number_to_words_simple(decimal_num)
                    return f"{whole_str} celá {decimal_str}"
            except:
                return match.group(0)

        # Zachytí desetinná čísla s tečkou nebo čárkou
        pattern = r'\b([0-9]+)[,\.]([0-9]+)\b'
        return re.sub(pattern, decimal_to_words, text)

    def _expand_percentages(self, text: str) -> str:
        """Převede procenta na slova (50% -> padesát procent)"""
        def percent_to_words(match):
            num_str = match.group(1)
            try:
                num = int(num_str)
                num_words = self._number_to_words_simple(num)
                # Správný tvar "procento" vs "procenta" vs "procent"
                if num == 1:
                    return f"{num_words} procento"
                elif num in [2, 3, 4]:
                    return f"{num_words} procenta"
                else:
                    return f"{num_words} procent"
            except:
                return match.group(0)

        pattern = r'\b([0-9]+)\s*%\b'
        return re.sub(pattern, percent_to_words, text)

    def _expand_time(self, text: str) -> str:
        """Převede čas na slova (10:30 -> deset třicet)"""
        def time_to_words(match):
            hours = int(match.group(1))
            minutes = int(match.group(2))
            hours_str = self._number_to_words_simple(hours)
            minutes_str = self._number_to_words_simple(minutes)
            if minutes == 0:
                return f"{hours_str} hodin"
            else:
                return f"{hours_str} {minutes_str}"

        pattern = r'\b([0-9]{1,2}):([0-9]{2})\b'
        return re.sub(pattern, time_to_words, text)

    def _expand_numbers_with_units(self, text: str) -> str:
        """Převede čísla s jednotkami na slova (5 kg -> pět kilogramů)"""
        def number_unit_to_words(match):
            num_str = match.group(1)
            unit = match.group(2).lower()
            try:
                num = int(num_str)
                num_words = self._number_to_words_simple(num)
                unit_word = self.units.get(unit, unit)
                # Správné skloňování jednotek
                if num == 1:
                    # Jednotné číslo
                    if unit_word.endswith('ů'):
                        unit_word = unit_word[:-2]  # "kilogramů" -> "kilogram"
                    elif unit_word.endswith('y'):
                        unit_word = unit_word[:-1]  # "eur" -> "euro" (zjednodušeně)
                return f"{num_words} {unit_word}"
            except:
                return match.group(0)

        unit_pattern = '|'.join(re.escape(u) for u in self.units.keys())
        pattern = rf'\b([0-9]+)\s*({unit_pattern})\b'
        return re.sub(pattern, number_unit_to_words, text, flags=re.IGNORECASE)

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalizuje text"""
        # Normalizace mezer
        text = re.sub(r'\s+', ' ', text)

        # Normalizace uvozovek
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")

        # Normalizace pomlček
        text = text.replace('--', '—')
        text = text.replace('...', '…')

        # Odstranění mezer před interpunkcí
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)

        # Normalizace více interpunkčních znamének
        text = re.sub(r'([!?]){2,}', r'\1', text)

        return text.strip()


# Globální instance
_text_processor_instance = None


def get_czech_text_processor() -> CzechTextProcessor:
    """Singleton pattern for CzechTextProcessor"""
    global _text_processor_instance
    if _text_processor_instance is None:
        _text_processor_instance = CzechTextProcessor()
    return _text_processor_instance

