"""
CZ→SK Phonetic Adapter for F5-TTS (Fáze 1)
Fonetická adaptace - text zní česky i se slovenským modelem

Principy:
- Není to překlad do slovenštiny
- Je to fonetická úprava - slovenský model vysloví "kôň" místo "kůň" a zní to česky
- Cílem je zachovat českou výslovnost
"""

from typing import Dict, List
from dataclasses import dataclass
import re


@dataclass
class ConversionResult:
    original: str
    converted: str
    changes_count: int
    applied: List[Dict]


class CzechPhoneticAdapter:
    """
    Fonetický adapter pro slovenský F5-TTS model.

    Klíčový princip: Slovak model nezná české "ů", takže ho nahradíme
    slovenským "ô" - zní to stejně jako české "ů"!

    Příklad:
    - CZ: "kůň" → SK adaptace: "kôň" → Slovak TTS řekne [kɔːɲ] ≈ CZ [kuːɲ] ✅
    """

    def __init__(self):
        # Kritická fonetická konverze: "ů" → "ô"
        # Slovak "ô" zní téměř identicky jako české "ů"
        self.PHONETIC_U_CONVERSION = {
            # Samostatné "ů"
            "ů": "ô",
            # Nejčastější slova s "ů"
            "kůň": "kôň",
            "můj": "môj",
            "důl": "dôl",
            "důvěra": "dôvera",
            "důvod": "dôvod",
            "půda": "pôda",
            "půl": "pôl",
            "původ": "pôvod",
            "hůl": "hôl",
            "kůl": "kôl",
            "vůz": "voz",  # "vůz" v SK je "voz"
            "vůně": "vôňa",
            "vůbec": "vôbec",
            "bůh": "boh",  # "bůh" → "boh"
            "hůj": "hôj",
            "čůr": "čôr",
            "džbů": "džbô",
            "chůj": "chôj",
            "lůj": "lôj",
            "můst": "most",  # "můst" → "most"
            "můzek": "mozog",  # "můzek" → "mozog"
            "půlkruh": "polkruh",
            "půlnoc": "polnoc",
            "zůstatek": "zostatok",
            "žůžo": "žôžo",
            "tůně": "tône",
            "vůdkyně": "vodkyňa",
            "hůrka": "hôrka",
            "kůrka": "kôrka",
            "lůko": "lôko",
            "sůl": "soľ",  # "sůl" je v SK "soľ"
            "tůra": "túra",  # "tůra" → "túra" (s "ú")
        }

        # Další české znaky které Slovak model špatně vyslovuje
        # "ě" po souhláskách - Slovak to často čte jako "e"
        self.PHONETIC_E_CONVERSION = {
            # Slovesa s "ě"
            "číst": "čítať",  # SK čte "číst" špatně, "čítať" správně
            "četl": "čítal",
            "četla": "čítala",
            "čtěte": "čítajte",
            "čteme": "čítame",
            "běžet": "bežať",  # "běžet" SK nezná, "bežať" zná
            "běžel": "bežal",
            "běžela": "bežala",
            "běží": "beží",
            "létat": "lietať",  # SK nezná "létat"
            "letěl": "letel",
            "letěla": "letela",
            "létá": "lieta",
            "těšit se": "tešiť sa",  # SK nezná "těšit"
            "těšil": "tešil",
            "těšila": "tešila",
            "těší": "teší",
            "tělo": "telo",  # "tělo" SK čte špatně
            "dělat": "robiť",  # "dělat" SK nezná konjugaci
            "dělal": "robil",
            "dělala": "robila",
            "dělám": "robím",
            "děláš": "robíš",
            "dělá": "robí",
            "děláme": "robíme",
            "děláte": "robíte",
            "dělají": "robia",
            "vědět": "vedieť",  # "vědět" SK čte špatně
            "věděl": "vedel",
            "věděla": "vedela",
            "vím": "viem",
            "víš": "vieš",
            "ví": "vie",
            "věděl": "vedel",
            "věřit": "veriť",  # "věřit" SK nezná
            "věřil": "veril",
            "věřila": "verila",
            "smět": "smieť",  # "smět" SK nezná
            "směl": "smel",
            "směla": "smela",
            "může": "môže",
            "můžu": "môžem",
            "můžeš": "môžeš",
            "můžeme": "môžeme",
        }

        # False friends - kritické pro srozumitelnost
        self.FALSE_FRIENDS = {
            # SK "líbiť" znamená "chutnat", ne "líbit se"!
            "líbit": "pačiť sa",
            "líbí": "páči",
            "líbí se": "páči sa",
            "líbilo": "páčilo",
            "líbilo se": "páčilo sa",
            # SK "pokoj" = "mír", ne "místnost"!
            "pokoj": "izba",
            "pokoje": "izby",
            "pokoji": "izbe",
            # SK "robot" = "práce", ne "stroj"!
            "robot": "stroj",
            "robota": "stroja",
        }

        # Další kritické rozdíly ve slovní zásobě
        self.CRITICAL_VOCAB = {
            # Slovesa
            "jet": "ísť",
            "jedu": "idem",
            "jedeš": "ideš",
            "jede": "ide",
            "jedeme": "ideme",
            "jedete": "idete",
            "jedou": "idú",
            "jel": "išiel",
            "jela": "išla",
            "jeli": "išli",
            "oběd": "obed",
            "obědvat": "obedovať",
            "večeře": "večera",
            "večeřet": "večerať",
            "snídaně": "raňajky",
            "snídat": "raňajkovať",
            "hledět": "hľadieť",
            "hleděl": "hľadel",
            "hleděla": "hľadela",
            "koukat": "dívať sa",
            "koukal": "díval sa",
            "koukala": "dívala sa",
            "poslouchat": "počúvať",
            "poslouchal": "počúval",
            "poslouchala": "počúvala",
            "vracet": "vracať",
            "vrátil": "vrátil",
            "vrátila": "vrátila",
            # Podstatná jména
            "automobil": "auto",
            "žárovka": "žiarovka",
            "lednička": "chladnička",
            "pračka": "práčka",
            "myčka": "umývačka",
            "vysavač": "vysávač",
            "příbory": "príbory",
            "sklenice": "sklenka",
            "hrnek": "hrnček",
            "talíř": "tanier",
            "příbor": "príbor",
            "ubrus": "obrus",
            "utěrka": "utierka",
            # Části těla
            "noha": "noha",  # stejné
            "ruka": "ruka",  # stejné
            "hlava": "hlava",  # stejné
            "oko": "oko",  # stejné
            "ucho": "ucho",  # stejné
            "zuby": "zuby",  # stejné
            "vlasy": "vlasy",  # stejné
            "prst": "prst",  # stejné
            "koleno": "kolená",  # SK plurál
            "loket": "lakeť",  # SK má "lakeť"
            # Města
            "Praha": "Praha",
            "Brno": "Brno",
            "Ostrava": "Ostrava",
            "Plzeň": "Plzeň",
            "Liberec": "Liberec",
            "Olomouc": "Olomouc",
        }

        # Kombinovaný slovník (priorita: false friends > fonetické > kritické)
        self.conversions = {
            **self.FALSE_FRIENDS,
            **self.PHONETIC_U_CONVERSION,
            **self.PHONETIC_E_CONVERSION,
            **self.CRITICAL_VOCAB,
        }

        # Regex pattern - case insensitive, whole words only
        words = sorted(self.conversions.keys(), key=len, reverse=True)
        self.pattern = re.compile(
            r"\b(" + "|".join(re.escape(w) for w in words) + r")\b", re.IGNORECASE
        )

    def convert(self, text: str) -> ConversionResult:
        """Konvertuje text pro slovenský F5-TTS model."""
        applied = []

        def replace_match(match):
            original = match.group(0)
            lower = original.lower()

            if lower in self.conversions:
                converted = self.conversions[lower]
                applied.append(
                    {
                        "original": original,
                        "converted": converted,
                        "type": self._get_type(lower),
                    }
                )
                return converted
            return original

        converted_text = self.pattern.sub(replace_match, text)

        return ConversionResult(
            original=text,
            converted=converted_text,
            changes_count=len(applied),
            applied=applied,
        )

    def _get_type(self, word: str) -> str:
        """Určí typ konverze."""
        if word in self.FALSE_FRIENDS:
            return "false_friend"
        elif word in self.PHONETIC_U_CONVERSION:
            return "phonetic_u"
        elif word in self.PHONETIC_E_CONVERSION:
            return "phonetic_e"
        return "vocab"

    def convert_text(self, text: str) -> str:
        """Jednoduchá konverze - vrací jen text."""
        return self.convert(text).converted


# Singleton
_adapter = None


def get_adapter() -> CzechPhoneticAdapter:
    global _adapter
    if _adapter is None:
        _adapter = CzechPhoneticAdapter()
    return _adapter


def adapt_czech_for_slovak(text: str) -> str:
    """Convenience funkce."""
    return get_adapter().convert_text(text)


if __name__ == "__main__":
    adapter = CzechPhoneticAdapter()

    # Testovací věty
    tests = [
        "Příliš žlutoučký kůň úpěl dábelské ódy.",
        "Dnes jsem jel autem do Prahy potkat kamaráda.",
        "Líbí se mi tento nový počítač.",
        "Musím jet do města koupit auto.",
        "Běžel jsem rychle kolem domu.",
        "Věděl jsem, že to bude dobré.",
    ]

    print("=" * 70)
    print("CZ→SK FONETICKÁ ADAPTACE PRO SLOVENSKÝ MODEL")
    print("=" * 70)
    print()

    for text in tests:
        result = adapter.convert(text)
        print(f"CZ: {result.original}")
        print(f"ADAPTACE: {result.converted}")
        if result.applied:
            print(
                f"  Změny: {', '.join(f'{o}→{c}' for o, c in [(a['original'], a['converted']) for a in result.applied])}"
            )
        print()
