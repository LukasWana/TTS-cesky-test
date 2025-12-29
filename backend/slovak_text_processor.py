"""
Modul pre pokročilé predspracovanie slovenského textu

Aplikuje pravidlá:
- Spodoba znelosti (asimilácia znelosti)
- Vkladanie rázu (glottálny stop)
"""
import re
from typing import Dict


class SlovakTextProcessor:
    """Trieda pre pokročilé predspracovanie slovenského textu"""

    def __init__(self):
        """Inicializácia procesora"""
        # Definícia skupín spoluhlások pre spodobu
        self.znele = set("bdďgzžhvdz")
        self.neznele = set("ptťksšchfcč")
        self.sonory = set("mnňlrjľ")
        self.vsetky_spoluhlasy = self.znele | self.neznele | self.sonory

        # Mapovanie pre spodobu (znelá -> neznela)
        # Páry: neznelá -> znelá
        self.znele_neznele_pary = {
            "p": "b", "t": "d", "ť": "ď", "k": "g", "s": "z",
            "š": "ž", "ch": "h", "f": "v", "c": "dz", "č": "dž"
        }
        # Mapovanie pre spodobu (znelá -> neznela)
        self.to_neznele = {v: k for k, v in self.znele_neznele_pary.items()}
        # Mapovanie pre spodobu (neznela -> znelá)
        self.to_znele = self.znele_neznele_pary

        # Skratky pre prevod
        self.abbreviations = {
            "napr.": "napríklad",
            "atď.": "a tak ďalej",
            "tzn.": "to znamená",
            "resp.": "respektíve",
            "č.": "číslo",
            "str.": "strana",
            "s.": "strana",
            "r.": "rok",
            "m.": "mesiac",
            "min.": "minúta",
            "sek.": "sekunda",
            "km/h": "kilometrov za hodinu",
            "m/s": "metrov za sekundu",
            "cca": "približne",
            "tzv.": "takzvaný",
            "vč.": "vrátane",
            "vč": "vrátane",
            "tel.": "telefón",
            "Kč": "korún českých",
            "€": "eur",
            "mil.": "miliónov",
            "mld.": "miliárd",
            "tis.": "tisíc",
            # Rozšírené skratky
            "ing.": "inžinier",
            "MUDr.": "doktor medicíny",
            "PhDr.": "doktor filozofie",
            "RNDr.": "doktor prírodných vied",
            "doc.": "docent",
            "prof.": "profesor",
            "max.": "maximálne",
            "min.": "minimálne",
            "kap.": "kapitola",
            "obr.": "obrázok",
            "tab.": "tabuľka",
            "viz": "viďte",
            "tz.": "to znamená"
        }

        # Radové číslovky
        self.ordinal_words = {
            1: "prvý", 2: "druhý", 3: "tretí", 4: "štvrtý", 5: "piaty",
            6: "šiesty", 7: "siedmy", 8: "ôsmy", 9: "deviaty", 10: "desiaty",
            11: "jedenásty", 12: "dvanásty", 13: "trinásty", 14: "štrnásty", 15: "pätnásty",
            16: "šestnásty", 17: "sedemnásty", 18: "osemnásty", 19: "devätnásty",
            20: "dvadsiaty", 30: "tridsiaty", 40: "štyridsiaty", 50: "päťdesiaty",
            60: "šesťdesiaty", 70: "sedemdesiaty", 80: "osemdesiaty", 90: "deväťdesiaty",
            100: "stý", 1000: "tisíci", 1_000_000: "miliontý"
        }

        # Jednotky pre čísla
        self.units = {
            'kg': 'kilogramov', 'g': 'gramov', 't': 'tún',
            'km': 'kilometrov', 'm': 'metrov', 'cm': 'centimetrov', 'mm': 'milimetrov',
            'l': 'litrov', 'ml': 'mililitrov',
            '€': 'eur', '$': 'dolárov', 'USD': 'dolárov', 'EUR': 'eur',
            'h': 'hodín', 'min': 'minút', 's': 'sekúnd',
            '°C': 'stupňov Celzia', '°F': 'stupňov Fahrenheita'
        }

        # Slovník pre základné čísla (0-100) a väčšie číslovky
        self.number_words = {
            # Základné čísla 0-19
            0: "nula", 1: "jeden", 2: "dva", 3: "tri", 4: "štyri", 5: "päť",
            6: "šesť", 7: "sedem", 8: "osem", 9: "deväť", 10: "desať",
            11: "jedenásť", 12: "dvanásť", 13: "trinásť", 14: "štrnásť", 15: "pätnásť",
            16: "šestnásť", 17: "sedemnásť", 18: "osemnásť", 19: "devätnásť",
            # Desiatky
            20: "dvadsať", 30: "tridsať", 40: "štyridsať", 50: "päťdesiat", 60: "šesťdesiat",
            70: "sedemdesiat", 80: "osemdesiat", 90: "deväťdesiat",
            # Stovky
            100: "sto", 200: "dvesto", 300: "tristo", 400: "štyristo", 500: "päťsto",
            600: "šesťsto", 700: "sedemsto", 800: "osemsto", 900: "deväťsto",
            # Tisíce
            1000: "tisíc", 2000: "dva tisíce", 3000: "tri tisíce", 4000: "štyri tisíce",
            5000: "päť tisíc", 6000: "šesť tisíc", 7000: "sedem tisíc", 8000: "osem tisíc",
            9000: "deväť tisíc",
            # Milióny
            1_000_000: "milión", 2_000_000: "dva milióny", 3_000_000: "tri milióny",
            4_000_000: "štyri milióny", 5_000_000: "päť miliónov", 6_000_000: "šesť miliónov",
            7_000_000: "sedem miliónov", 8_000_000: "osem miliónov", 9_000_000: "deväť miliónov",
            # Miliardy
            1_000_000_000: "miliarda", 2_000_000_000: "dve miliardy", 3_000_000_000: "tri miliardy",
            4_000_000_000: "štyri miliardy", 5_000_000_000: "päť miliárd", 6_000_000_000: "šesť miliárd",
            7_000_000_000: "sedem miliárd", 8_000_000_000: "osem miliárd", 9_000_000_000: "deväť miliárd"
        }

    def process_text(self, text: str, apply_voicing: bool = True, apply_glottal_stop: bool = True,
                     apply_consonant_groups: bool = False, expand_abbreviations: bool = True,
                     expand_numbers: bool = True) -> str:
        """
        Spracuje text aplikáciou slovenských fonetických pravidiel
        """
        processed = text

        # 0. Normalizácia (odstránenie prebytočných medzier atď.)
        processed = self.normalize_text(processed)

        # 1. Prevod skratiek
        if expand_abbreviations:
            processed = self._expand_abbreviations(processed)

        # 2. Prevod čísel (radové číslovky, desatinné čísla, percentá, čas, jednotky)
        if expand_numbers:
            # Najprv spracujeme špeciálne prípady (čas, percentá, jednotky)
            processed = self._expand_time(processed)
            processed = self._expand_percentages(processed)
            processed = self._expand_numbers_with_units(processed)
            # Potom desatinné čísla (pred radovými, aby sa nekonfliktovali)
            processed = self._expand_decimal_numbers(processed)
            # Potom radové číslovky
            processed = self._expand_ordinal_numbers(processed)
            # Nakoniec základné čísla
            processed = self._expand_numbers(processed)

        # 3. Oprava spoluhláskových skupín (zatiaľ neimplementované)
        # if apply_consonant_groups:
        #     processed = self._fix_consonant_groups(processed)

        # 4. Spodoba znelosti (na konci slova, pred neznelými/znelými)
        if apply_voicing:
            processed = self._apply_voicing_assimilation(processed)

        # 5. Vkladanie rázu
        if apply_glottal_stop:
            processed = self._apply_glottal_stop(processed)

        return processed

    def _expand_abbreviations(self, text: str) -> str:
        """Prevedie skratky na plné formy"""
        processed = text
        for abbr, full in self.abbreviations.items():
            if abbr.endswith('.'):
                pattern = r'\b' + re.escape(abbr)
            else:
                pattern = r'\b' + re.escape(abbr) + r'\b'
            processed = re.sub(pattern, full, processed, flags=re.IGNORECASE)
        return processed

    def _expand_numbers(self, text: str) -> str:
        """Prevedie čísla na slová"""
        def number_to_words(num_str: str) -> str:
            try:
                # Odstránenie medzier a čiarky z čísla (napr. "1 000 000" -> "1000000")
                num_str_clean = num_str.replace(' ', '').replace(',', '').replace('_', '')
                num = int(num_str_clean)

                # Priama zhoda v slovníku
                if num in self.number_words:
                    return self.number_words[num]

                # Čísla 0-99
                if num < 100:
                    if num < 20:
                        return num_str  # Malo by byť v slovníku
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
                    # Správny tvar "tisíc" vs "tisíce" vs "tisíc"
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

                # Čísla 1000000-999999999 (milióny)
                elif num < 1_000_000_000:
                    millions = num // 1_000_000
                    remainder = num % 1_000_000
                    millions_str = number_to_words(str(millions))
                    # Správny tvar "milión" vs "milióny" vs "miliónov"
                    if millions == 1:
                        million_word = "milión"
                    elif millions in [2, 3, 4]:
                        million_word = "milióny"
                    else:
                        million_word = "miliónov"

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
                    # Správny tvar "miliarda" vs "miliardy" vs "miliárd"
                    if billions == 1:
                        billion_word = "miliarda"
                    elif billions in [2, 3, 4]:
                        billion_word = "miliardy"
                    else:
                        billion_word = "miliárd"

                    if remainder == 0:
                        return f"{billions_str} {billion_word}"
                    else:
                        remainder_str = number_to_words(str(remainder))
                        return f"{billions_str} {billion_word} {remainder_str}"

                return num_str
            except:
                return num_str

        # Pattern zachytí čísla s medzerami, čiarkami alebo podčiarkovníkmi ako oddelovačmi
        # Napr: "1000", "1 000", "1,000", "1_000", "1 000 000", "1000000", atď.
        # Zachytí čísla od 1 do 12 cifier (maximálne miliardy)
        pattern = r'\b([0-9]{1,3}(?:[\s,_][0-9]{3})*|[0-9]{4,12})\b'
        return re.sub(pattern, lambda m: number_to_words(m.group(1)), text)

    def _apply_voicing_assimilation(self, text: str) -> str:
        """
        Aplikuje spodobu znelosti
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

            # 1. Hranice slov (posledné písmeno slova)
            last_idx = n - 1
            last_char = chars[last_idx].lower()

            # Určíme kontext nasledujúceho zvuku
            if not next_first_char:
                # Koniec prejavu -> zánik znelosti
                if last_char in self.to_neznele:
                    chars[last_idx] = self.to_neznele[last_char]
            elif next_first_char in self.neznele or next_first_char == "ch":
                # Nasleduje neznela -> regresia k neznelosti
                if last_char in self.to_neznele:
                    chars[last_idx] = self.to_neznele[last_char]
            elif next_first_char in self.znele and next_first_char != "v":
                # Nasleduje znelá -> regresia k znelosti
                if last_char in self.to_znele:
                    chars[last_idx] = self.to_znele[last_char]

            # 2. Vnútri slova (regresívna asimilácia)
            for j in range(n - 2, -1, -1):
                curr = chars[j].lower()
                nxt = chars[j+1].lower()

                # Ak nxt je sonora alebo 'v', asimilácia sa nedeje
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
        """Vkladá ráz (glottálna oklúzia)"""
        # Pattern pre predložky
        prepositions_pattern = r"(v|z|s|k|o|u|nad|pod|pred|cez|bez|od|do)"
        vowels = "aeiouáäéíóôúý"  # Slovenské samohlásky včetně ä a ô

        def add_raz(match):
            prep = match.group(1)
            word = match.group(2)
            return f"{prep} '{word}"

        # Najprv spracujeme diftongy (dlhšie sekvencie), potom jednotlivé samohlásky
        # Ráz po predložkách pred diftongmi (ia, ie, iu, ô) - zachytíme celé slovo
        processed = re.sub(rf"\b{prepositions_pattern}\s+((ia|ie|iu|ô)\w*)", add_raz, text, flags=re.IGNORECASE)
        # Ráz po predložkách pred samohláskami - zachytíme celé slovo
        processed = re.sub(rf"\b{prepositions_pattern}\s+([{vowels}]\w*)", add_raz, processed, flags=re.IGNORECASE)

        # Ráz na začiatku vety alebo po interpunkcii pred diftongmi - zachytíme celé slovo
        processed = re.sub(rf"(^|[.!?]\s+)((ia|ie|iu|ô)\w*)", r"\1'\2", processed, flags=re.IGNORECASE)
        # Ráz na začiatku vety alebo po interpunkcii pred samohláskami - zachytíme celé slovo
        processed = re.sub(rf"(^|[.!?]\s+)([{vowels}]\w*)", r"\1'\2", processed, flags=re.IGNORECASE)

        return processed

    def _number_to_words_simple(self, num: int) -> str:
        """Pomocná metóda pre prevod čísla na slová (zjednodušená verzia)"""
        if num in self.number_words:
            return self.number_words[num]
        if num < 100:
            tens = (num // 10) * 10
            ones = num % 10
            if tens in self.number_words and ones in self.number_words:
                return f"{self.number_words[tens]} {self.number_words[ones]}"
        return str(num)

    def _expand_ordinal_numbers(self, text: str) -> str:
        """Prevedie radové číslovky na slová (1. -> prvý)"""
        def ordinal_to_words(match):
            num_str = match.group(1)
            try:
                num = int(num_str)
                if num in self.ordinal_words:
                    return self.ordinal_words[num]
                # Pre zložené čísla použijeme základnú číslovku + koncovku
                if num < 100:
                    base = self._number_to_words_simple(num)
                    # Odstránime posledné písmeno a pridáme "ý"
                    if base.endswith('a'):
                        return base[:-1] + 'ý'
                    elif base.endswith('y'):
                        return base[:-1] + 'ý'
                    else:
                        return base + 'ý'
            except:
                pass
            return match.group(0)

        # Zachytí čísla s bodkou na konci (radové číslovky)
        # Ale nie desatinné čísla (tie už sú spracované)
        # Pattern: číslo + bodka + medzera alebo koniec riadku (nie ďalšia číslica)
        pattern = r'\b([0-9]+)\.(?=\s|$|[^0-9])'
        return re.sub(pattern, ordinal_to_words, text)

    def _expand_decimal_numbers(self, text: str) -> str:
        """Prevedie desatinné čísla na slová (3.14 -> tri celá štrnásť stotín)"""
        def decimal_to_words(match):
            whole = match.group(1)
            decimal = match.group(2)
            try:
                whole_str = self._number_to_words_simple(int(whole))
                # Pre desatinnú časť použijeme zjednodušený prevod
                decimal_num = int(decimal)
                if len(decimal) == 1:
                    decimal_str = self._number_to_words_simple(decimal_num)
                    return f"{whole_str} celá {decimal_str} desatina"
                elif len(decimal) == 2:
                    decimal_str = self._number_to_words_simple(decimal_num)
                    return f"{whole_str} celá {decimal_str} stotín"
                else:
                    decimal_str = self._number_to_words_simple(decimal_num)
                    return f"{whole_str} celá {decimal_str}"
            except:
                return match.group(0)

        # Zachytí desatinné čísla s bodkou alebo čiarkou
        pattern = r'\b([0-9]+)[,\.]([0-9]+)\b'
        return re.sub(pattern, decimal_to_words, text)

    def _expand_percentages(self, text: str) -> str:
        """Prevedie percentá na slová (50% -> päťdesiat percent)"""
        def percent_to_words(match):
            num_str = match.group(1)
            try:
                num = int(num_str)
                num_words = self._number_to_words_simple(num)
                # Správny tvar "percento" vs "percentá" vs "percent"
                if num == 1:
                    return f"{num_words} percento"
                elif num in [2, 3, 4]:
                    return f"{num_words} percentá"
                else:
                    return f"{num_words} percent"
            except:
                return match.group(0)

        pattern = r'\b([0-9]+)\s*%\b'
        return re.sub(pattern, percent_to_words, text)

    def _expand_time(self, text: str) -> str:
        """Prevedie čas na slová (10:30 -> desať tridsať)"""
        def time_to_words(match):
            hours = int(match.group(1))
            minutes = int(match.group(2))
            hours_str = self._number_to_words_simple(hours)
            minutes_str = self._number_to_words_simple(minutes)
            if minutes == 0:
                return f"{hours_str} hodín"
            else:
                return f"{hours_str} {minutes_str}"

        pattern = r'\b([0-9]{1,2}):([0-9]{2})\b'
        return re.sub(pattern, time_to_words, text)

    def _expand_numbers_with_units(self, text: str) -> str:
        """Prevedie čísla s jednotkami na slová (5 kg -> päť kilogramov)"""
        def number_unit_to_words(match):
            num_str = match.group(1)
            unit = match.group(2).lower()
            try:
                num = int(num_str)
                num_words = self._number_to_words_simple(num)
                unit_word = self.units.get(unit, unit)
                # Správne skloňovanie jednotiek
                if num == 1:
                    # Jednotné číslo
                    if unit_word.endswith('ov'):
                        unit_word = unit_word[:-2]  # "kilogramov" -> "kilogram"
                    elif unit_word.endswith('y'):
                        unit_word = unit_word[:-1]  # "eur" -> "euro" (zjednodušene)
                return f"{num_words} {unit_word}"
            except:
                return match.group(0)

        unit_pattern = '|'.join(re.escape(u) for u in self.units.keys())
        pattern = rf'\b([0-9]+)\s*({unit_pattern})\b'
        return re.sub(pattern, number_unit_to_words, text, flags=re.IGNORECASE)

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalizuje text"""
        # Normalizácia medzier
        text = re.sub(r'\s+', ' ', text)

        # Normalizácia úvodzoviek
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")

        # Normalizácia pomlčiek
        text = text.replace('--', '—')
        text = text.replace('...', '…')

        # Odstránenie medzier pred interpunkciou
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)

        # Normalizácia viacerých interpunkčných znamienok
        text = re.sub(r'([!?]){2,}', r'\1', text)

        return text.strip()


# Globálna inštancia
_slovak_text_processor_instance = None


def get_slovak_text_processor() -> SlovakTextProcessor:
    """Singleton pattern for SlovakTextProcessor"""
    global _slovak_text_processor_instance
    if _slovak_text_processor_instance is None:
        _slovak_text_processor_instance = SlovakTextProcessor()
    return _slovak_text_processor_instance









