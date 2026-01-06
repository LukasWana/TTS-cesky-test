"""
CZ→SK Text Adapter for F5-TTS (Phase 1)
Kritická konverze pro srozumitelnost českého textu se slovenským modelem
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import re


@dataclass
class ConversionResult:
    """Výsledek konverze"""

    original: str
    converted: str
    changes_count: int
    confidence: float
    applied_conversions: List[Dict]


class CzechToSlovakAdapter:
    """
    Adapter pro konverzi českého textu pro slovenský F5-TTS model.

    Fáze 1: Kritická konverze
    - "ů" → "ô" / "u"
    - Nejčastější CZ→SK rozdíly (~100 slov)
    """

    def __init__(self):
        # Kritická konverze: "ů" → "ô"
        # Slovak model nezná "ů", takže ho nahradíme "ô" (nejbližší zvuk)
        self.U_TO_O_CONVERSIONS = {
            # Samostatné "ů"
            "ů": "ô",
            # "ů" po souhláskách (typické české)
            "kůň": "kôň",
            "můj": "môj",
            "svoj": "svoj",  # už slovašnsky
            "tůně": "tône",
            "důl": "dôl",
            "důvěra": "dôvera",
            "důvod": "dôvod",
            "půda": "pôda",
            "půl": "pôl",
            "původ": "pôvod",
            "hůl": "hôl",
            "kůl": "kôl",
            "lůn": "lôn",
            "růž": "rôž",
            "sůl": "soľ",  # "sůl" → "soľ" (místo "sôl")
            "tůra": "túra",  # "tůra" → "túra" (s "ú")
            "vůz": "voz",
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
            "půlkruh": "polkruh",  # "půlkruh" → "polkruh"
            "půlnoc": "polnoc",
            "sůstatek": "sused",  # chybné, ale zkusíme
            "tůně": "tône",
            "vůdkyně": "vodkyňa",
            "zůstatek": "zostatok",
            "žůžo": "žôžo",
        }

        # Častá CZ→SK slovní zásoba (Fáze 1: ~100 slov)
        self.COMMON_CONVERSIONS = {
            # Slovesa (nejdůležitější)
            "být": "byť",
            "mít": "mať",
            "jet": "ísť",  # nebo "cestovať"
            "jít": "ísť",
            "jeti": "ísť",
            "číst": "čítať",
            "psát": "písať",
            "vidět": "vidieť",
            "vědět": "vedieť",
            "chtít": "chcieť",
            "moci": "môcť",
            "muset": "musieť",
            "říct": "povedať",
            "říkala": "povedala",
            "říkal": "povedal",
            "dát": "dať",
            "vzít": "vziať",
            "dělat": "robiť",
            "dělal": "robil",
            "dělala": "robila",
            "dělám": "robím",
            "mluvit": "hovoriť",
            "mluvil": "hovoril",
            "mluvila": "hovorila",
            "přijít": "prísť",
            "přišel": "prišiel",
            "přišla": "prišla",
            "oběd": "obed",
            "večeře": "večera",
            "snídaně": "raňajky",
            "spát": "spať",
            "ležet": "ležať",
            "stát": "stáť",
            "ležel": "ležal",
            "stál": "stál",
            "běžet": "bežať",
            "běžel": "bežal",
            "letět": "letieť",
            "letěl": "letel",
            "padat": "padať",  # Fixed: was Cyrillic
            "chodit": "chodiť",
            "chodil": "chodil",
            "chodila": "chodila",
            "jezdit": "jazdiť",
            "jezdil": "jazdil",
            "bydlit": "bývať",
            "bydlel": "býval",
            "bydlela": "bývala",
            "potřebovat": "potrebovať",
            "potřeboval": "potreboval",
            "potřebovala": "potrebovala",
            "rozumět": "rozumieť",
            "rozuměl": "rozumel",
            "rozuměla": "rozumela",
            "zajímat": "zaujímať",
            "zajímalo": "zaujímalo",
            "dívat": "dívať",
            "díval": "díval",
            "dívala": "dívala",
            "myslet": "myslieť",
            "myslel": "myslel",
            "myslela": "myslela",
            "hledět": "hľadieť",
            "hleděl": "hľadel",
            "hleděla": "hľadela",
            "sledovat": "sledovať",
            "sledoval": "sledoval",
            "sledovala": "sledovala",
            "čekat": "čakať",
            "čekal": "čakal",
            "čekala": "čakala",
            "začít": "začať",
            "začal": "začal",
            "začala": "začala",
            "potkat": "potkať",
            "potkal": "potkal",
            "potkala": "potkala",
            "potkávat": "potkávat",
            "najít": "nájsť",
            "našel": "našiel",
            "našla": "našla",
            "dát": "dať",
            "dal": "dal",
            "dala": "dala",
            "dával": "dával",
            "dávala": "dávala",
            "vzít": "vziať",
            "vzal": "vzal",
            "vzala": "vzala",
            "brát": "brať",
            "bral": "bral",
            "brala": "brala",
            "dostat": "dostať",
            "dostal": "dostal",
            "dostala": "dostala",
            "dostávat": "dostávat",
            "dostával": "dostával",
            "dostávala": "dostávala",
            # Další slovesa (rozšíření)
            "stát": "stáť",
            "stojí": "stojí",  # stejné
            "stojí": "stojí",
            "čeká": "čaká",
            "čekat": "čakať",
            "potřebovat": "potrebovať",
            "koukat": "dívať sa",
            "koukal": "díval sa",
            "dívat se": "dívať sa",
            "dívám se": "dívam sa",
            "poslouchat": "počúvať",
            "poslouchal": "počúval",
            "poslouchala": "počúvala",
            "slyšet": "počuť",
            "slyšel": "počul",
            "slyšela": "počula",
            "cítit": "cítiť",
            "cítil": "cítil",
            "cítila": "cítila",
            "vnímat": "vnínať",
            "vnímal": "vnímal",
            "vnímla": "vnímla",
            "milovat": "milovať",
            "miloval": "miloval",
            "milovala": "milovala",
            "nenávidět": "nenávidieť",
            "nenáviděl": "nenávidel",
            "návidět": "vidieť rád",
            "obdivovat": "obdivovať",
            "obdivoval": "obdivoval",
            "zamilovat se": "zaľúbiť sa",
            "zamiloval": "zaľúbil",
            "zamilovaný": "zamilovaný",
            "potkat": "potkať",
            "potkala": "potkala",
            "potkávat": "potkávat",
            "seznamovat": "zoznámiť",
            "seznámil": "zoznámil",
            "seznámila": "zoznámila",
            "volat": "volať",
            "volal": "volal",
            "volala": "volala",
            "telefonovat": "telefonovať",
            "telefonoval": "telefonoval",
            "psát": "písať",
            "psal": "písal",
            "psala": "písala",
            "číst": "čítať",
            "četl": "čítal",
            "četla": "čítala",
            "četli": "čítali",
            "číst": "čítať",
            "učit se": "učiť sa",
            "učil se": "učil sa",
            "učila se": "učila sa",
            "studovat": "študovať",
            "studoval": "študoval",
            "studovala": "študovala",
            "učit": "učiť",
            "učil": "učil",
            "učila": "učila",
            "zkoušet": "skúšať",
            "zkoušel": "skúšal",
            "zkoušela": "skúšala",
            "maturovat": "maturovať",
            "maturuje": "maturuje",
            "pracovat": "pracovať",
            "pracoval": "pracoval",
            "pracovala": "pracovala",
            "pracuji": "pracujem",
            "pracuješ": "pracuješ",
            "pracuje": "pracuje",
            "vydělávat": "zarobiť",
            "vydělal": "zarobil",
            "vydělala": "zarobila",
            "utrácet": "minúť",
            "utratil": "minul",
            "utratila": "minula",
            "šetřit": "šetriť",
            "šetřil": "šetril",
            "investovat": "investovať",
            "investoval": "investoval",
            "platit": "platiť",
            "platil": "platil",
            "platila": "platila",
            "zaplatit": "zaplatiť",
            "zaplatil": "zaplatil",
            "vracet": "vracať",
            "vrátil": "vrátil",
            "vrátila": "vrátila",
            "oblékat": "obliekať",
            "oblékl": "obliekol",
            "oblékla": "obliekla",
            "oblékat se": "obliekať sa",
            "obléká se": "oblieka sa",
            "svlékat": "vliekať",
            "svlékl": "vliekol",
            "sprchovat se": "sprchovať sa",
            "sprchoval se": "sprchoval sa",
            "holit se": "holiť sa",
            "holil se": "holil sa",
            "česat se": "česať sa",
            "česal se": "česal sa",
            "umývat se": "umývať sa",
            "umyl se": "umyl sa",
            "čistit si": "čistiť si",
            "čistil si": "čistil si",
            "rajhat": "raňajkovať",
            "večeřet": "večerať",
            "večeřel": "večeral",
            "obědvat": "obedovať",
            "obědval": "obedoval",
            "jíst": "jesť",
            "jedl": "jedol",
            "jedla": "jedla",
            "pít": "piť",
            "pil": "pil",
            "pila": "pila",
            "vařit": "variť",
            "vařil": "varil",
            "vařila": "varila",
            "grilovat": "grilovať",
            "griloval": "griloval",
            "smazat": "zmazať",
            "smazal": "zmazal",
            "uklidit": "upratať",
            "uklidil": "upratol",
            "prát": "prať",
            "pral": "pral",
            "prala": "prala",
            "žehlit": "žehliť",
            "žehlil": "žehlil",
            "žehlila": "žehlila",
            "utírat": "utierať",
            "utřel": "utrel",
            "luxovat": "vysávať",
            "luxoval": "vysával",
            "zametat": "zametať",
            "zametal": "zametal",
            "myt": "umývať",
            "myl": "umýval",
            "myla": "umývala",
            # Podstatná jména (častá) - ROZŠÍŘENÍ
            "auto": "auto",
            "automobil": "auto",
            "dům": "dom",
            "okno": "okno",
            "dveře": "dvere",
            "stůl": "stôl",
            "židle": "stolička",
            "postel": "posteľ",
            "kniha": "kniha",
            "ruka": "ruka",
            "noha": "noha",
            "hlava": "hlava",
            "oči": "oči",
            "uši": "uši",
            "nos": "nos",
            "ústa": "usta",
            "vlasy": "vlasy",
            "tělo": "telo",
            "srdce": "srdce",
            "mozek": "mozog",
            "kost": "kosť",
            "kůže": "koža",
            "krev": "krv",
            "voda": "voda",
            "ohně": "oheň",
            "země": "zem",
            "nebe": "nebo",
            "hvězda": "hviezda",
            "měsíc": "mesiac",
            "slunce": "slnko",
            "déšť": "dážď",
            "sněh": "sneh",
            "vítr": "vietor",
            "mrak": "mrak",
            "strom": "strom",
            "list": "list",
            "květina": "kvetina",
            "tráva": "tráva",
            "hora": "hora",
            "řeka": "rieka",
            "moře": "more",
            "jezero": "jazero",
            "rybník": "rybník",
            "cesta": "cesta",
            "silnice": "cesta",
            "ulice": "ulica",
            "město": "mesto",
            "vesnice": "dedina",
            "Praha": "Praha",
            "Brno": "Brno",
            "Ostrava": "Ostrava",
            "člověk": "človek",
            "muž": "muž",
            "žena": "žena",
            "dítě": "dieťa",
            "děti": "deti",
            "matka": "matka",
            "otec": "otec",
            "sestra": "sestra",
            "bratr": "brat",
            "bratranec": "bratranec",
            "sestřenice": "sesternica",
            "přítel": "priateľ",
            "přítelkyně": "priateľka",
            "kamarád": "kamarát",
            "kamarádka": "kamarátka",
            "kolega": "kolega",
            "kolegyně": "kolegyňa",
            "šéf": "šéf",
            "šéfka": "šéfka",
            "manžel": "manžel",
            "manželka": "manželka",
            "syn": "syn",
            "dcera": "dcéra",
            "strýc": "strýko",
            "teta": "teta",
            "babička": "babička",
            "dědeček": "dedko",
            "vnuk": "vnuk",
            "vnučka": "vnučka",
            "otec": "otec",
            "máma": "mama",
            "táta": "tata",
            "rodič": "rodič",
            "rodiče": "rodičia",
            "sourozenec": "súrodenec",
            "bratr": "brat",
            "sestra": "sestra",
            "dvojče": "dvojča",
            "partners": "partner",
            "přítelkyně": "priateľka",
            "kluk": "kluk",
            "holka": "holka",
            "kluk": "chlapec",
            "holčička": "dievčatko",
            "kluk": "chlapec",
            "dívka": "dievča",
            "mladý muž": "mladý muž",
            "mladá žena": "mladá žena",
            "starý muž": "starý muž",
            "stará žena": "stará žena",
            # Barvy (rozšíření pro barevné popisy)
            "žlutý": "žltý",
            "žlutoučký": "žltučký",
            "červený": "červený",
            "modrý": "modrý",
            "zelený": "zelený",
            "černý": "čierny",
            "bílý": "biely",
            "oranžový": "oranžový",
            "fialový": "fialový",
            "růžový": "ružový",
            "hnědý": "hnedý",
            "šedý": "sivý",
            "bílá": "biela",
            "černá": "čierna",
            "červená": "červená",
            "modrá": "modrá",
            "zelená": "zelená",
            "žlutá": "žltá",
            "oranžová": "oranžová",
            "fialová": "fialová",
            "růžová": "ružová",
            "hnědá": "hnedá",
            "šedá": "sivá",
            # Příslovce a předložky
            "dnes": "dnes",
            "zítra": "zajtra",
            "včera": "včera",
            "teď": "teraz",
            "potom": "potom",
            "brzy": "čoskoro",
            "pozdě": "neskoro",
            "nikdy": "nikdy",
            "vždy": "vždy",
            "často": "často",
            "zřídka": "zriedka",
            "někdy": "niekedy",
            "kdysi": "kedysi",
            "tam": "tam",
            "tady": "tu",
            "tady": "tutok",
            "zde": "tu",
            "doma": "doma",
            "venku": "vonku",
            "uvnitř": "vnútri",
            "nahoře": "hore",
            "dole": "dole",
            "vpředu": "vpredu",
            "vzadu": "vzadu",
            "vedle": "vedľa",
            "mezi": "medzi",
            "za": "za",
            "před": "pred",
            "nad": "nad",
            "pod": "pod",
            "pro": "pre",
            "s": "s",
            "bez": "bez",
            "k": "k",
            "o": "o",
            "u": "u",
            "i": "i",
            "a": "a",
            "ale": "ale",
            "nebo": "alebo",
            "když": "keď",
            "protože": "pretože",
            "aby": "aby",
            "kdyby": "keby",
            "jak": "ako",
            "co": "čo",
            "kdo": "kto",
            "kde": "kde",
            "kam": "kam",
            "odkud": "odkiaľ",
            "proč": "prečo",
            "kolik": "koľko",
            # Zájmena a ukazovací
            "já": "ja",
            "ty": "ty",
            "on": "on",
            "ona": "ona",
            "ono": "ono",
            "my": "my",
            "vy": "vy",
            "oni": "oni",
            "onen": "onion",
            "tento": "tento",
            "tenhle": "tento",
            "ten": "ten",
            "ta": "ta",
            "to": "to",
            "tito": "títo",
            "tato": "táto",
            "toto": "toto",
            "můj": "môj",
            "tvůj": "tvoj",
            "jeho": "jeho",
            "její": "jej",
            "náš": "náš",
            "váš": "váš",
            "jejich": "ich",
            "svůj": "svoj",
            "tento": "tento",
            "onen": "onen",
            "tato": "táto",
            "tamta": "tamta",
            "tamten": "tamten",
            "tamhleten": "tamhleten",
            "takhle": "takto",
            "takle": "takto",
            "tady": "tu",
            "tady": "tutok",
            "tady": "tu",
            "zde": "tu",
            "támhle": "tam",
            "támhle": "tamto",
            "támhleten": "tamhleten",
            # Číslovky
            "jedna": "jedna",
            "dva": "dva",
            "tři": "tri",
            "čtyři": "štyri",
            "pět": "päť",
            "šest": "šesť",
            "sedm": "sedem",
            "osm": "osem",
            "devět": "deväť",
            "deset": "desať",
            # Interjekce (často používané)
            "ahoj": "ahoj",
            "čau": "čau",
            "prosím": "prosim",
            "děkuji": "ďakujem",
            "dík": "dík",
            "promiň": "prepáč",
            "omlouvám": "ospravedlňujem",
            "vidím": "vidím",
            "chápu": "chápem",
            "nerozumím": "nerozumiem",
            "jistě": "iste",
            "samozřejmě": "samozrejme",
            "možná": "možno",
            "určitě": "určite",
            "fajn": "fajn",
            "super": "super",
            "perfektní": "perfektné",
            "skvělé": "skvelé",
            "úžasné": "úžasné",
            "hrozný": "hrozný",
            "strašný": "strašný",
            "špatný": "zlý",
            "dobře": "dobre",
            "špatně": "zle",
            # False friends (KRITICKÉ!)
            "líbit": "pačiť sa",  # CZ "líbit se" = SK "pačiť sa"
            "dělat": "robiť",  # CZ "dělat" = SK "robiť"
            "přítel": "priateľ",  # CZ "přítel" = SK "priateľ" (stejné!)
            "pokoj": "izba",  # CZ "pokoj" (místnost) = SK "izba"
            "přijít": "prísť",  # CZ "přijít" = SK "prísť"
            # Technická slova
            "počítač": "počítač",
            "program": "program",
            "software": "softvér",
            "hardware": "hardvér",
            "internet": "internet",
            "email": "email",
            "telefon": "telefón",
            "zpráva": "správa",
            "zprávy": "správy",
            "kontakt": "kontakt",
            "adresa": "adresa",
            "heslo": "heslo",
            "přihlásit": "prihlásiť",
            "odhlásit": "odhlásiť",
            "registrace": "registrácia",
            # Časové výrazy
            "minuta": "minúta",
            "hodina": "hodina",
            "den": "deň",
            "týden": "týždeň",
            "měsíc": "mesiac",
            "rok": "rok",
            "pondělí": "pondelok",
            "úterý": "utorok",
            "středa": "streda",
            "čtvrtek": "štvrtok",
            "pátek": "piatok",
            "sobota": "sobota",
            "neděle": "nedeľa",
            "dneska": "dnes",
            "zítra": "zajtra",
            "pozítří": "pozajtra",
            "včera": "včera",
            "předevčírem": "predvčerom",
            "ráno": "ráno",
            "večer": "večer",
            "poledne": "poludnie",
            "půlnoc": "polnoc",
            "dopoledne": "dopoludnie",
            "odpoledne": "odpoludnie",
            # Peníze
            "koruna": "koruna",
            "peníze": "peniaze",
            "plat": "plat",
            "mzda": "mzda",
            "účet": "účet",
            "banka": "banka",
            "karta": "karta",
            "hotovost": "hotovosť",
            "platit": "platiť",
            "zaplatit": "zaplatiť",
            "utratit": "minúť",
            "vydělat": "zarobiť",
        }

        # Kombinovaný slovník (prioritizovaný)
        self.conversions = {**self.U_TO_O_CONVERSIONS, **self.COMMON_CONVERSIONS}

        # Regex pro hledání slov (case insensitive)
        self.word_pattern = re.compile(
            r"\b("
            + "|".join(re.escape(word) for word in self.conversions.keys())
            + r")\b",
            re.IGNORECASE,
        )

    def convert(self, text: str) -> ConversionResult:
        """
        Konvertuje český text pro slovenský F5-TTS model.

        Args:
            text: Vstupní český text

        Returns:
            ConversionResult s konvertovaným textem a statistikami
        """
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
                        "type": "u_conversion"
                        if lower in self.U_TO_O_CONVERSIONS
                        else "vocabulary",
                    }
                )
                return converted
            return original

        converted_text = self.word_pattern.sub(replace_match, text)

        # Výpočet confidence
        if len(text) > 0:
            # Základní confidence na základě změn
            confidence = 1.0 - (len(applied) / max(len(text.split()), 1) * 0.1)
            confidence = max(0.7, min(1.0, confidence))
        else:
            confidence = 1.0

        return ConversionResult(
            original=text,
            converted=converted_text,
            changes_count=len(applied),
            confidence=confidence,
            applied_conversions=applied,
        )

    def convert_text_only(self, text: str) -> str:
        """
        Jednoduchá konverze - vrací jen upravený text.

        Args:
            text: Vstupní český text

        Returns:
            Konvertovaný text
        """
        result = self.convert(text)
        return result.converted


# Singleton instance
_adapter = None


def get_adapter() -> CzechToSlovakAdapter:
    """Získá singleton instanci adapteru"""
    global _adapter
    if _adapter is None:
        _adapter = CzechToSlovakAdapter()
    return _adapter


def convert_czech_for_slovak_model(text: str) -> str:
    """
    Convenience funkce pro rychlou konverzi.

    Args:
        text: Český text

    Returns:
        Text připravený pro slovenský F5-TTS model
    """
    return get_adapter().convert_text_only(text)


if __name__ == "__main__":
    # Test na pangramu
    adapter = CzechToSlovakAdapter()

    test_text = "Příliš žlutoučký kůň úpěl dábelské ódy."
    result = adapter.convert(test_text)

    print(f"Původní: {result.original}")
    print(f"Konvertovaný: {result.converted}")
    print(f"Změn: {result.changes_count}")
    print(f"Důvěra: {result.confidence:.2f}")
    print(f"\nAplikované konverze:")
    for conv in result.applied_conversions:
        print(f"  {conv['original']} → {conv['converted']} ({conv['type']})")
