"""
CZ→SK Text Adapter for F5-TTS (Phase 1)
Kritická konverze pro srozumitelnost českého textu se slovenským modelem
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import re
import sys
import io


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

    def __init__(self, r_replacement: str = "r", u_replacement: str = "ú"):
        """
        Inicializuje adapter s konfigurovatelnými parametry.

        Args:
            r_replacement: Varianta nahrazení "ř" - "r" (výchozí, doporučené), "ř" (pokud model zná)
            u_replacement: Varianta nahrazení "ů" - "ú" (výchozí, doporučené), "ô" (alternativa)
        """
        # Uložit konfigurační parametry
        self.r_replacement = r_replacement
        self.u_replacement = u_replacement

        # Whitelist znaků, které zní stejně v obou jazycích
        self.WHITELIST_CHARS = set("áéíóúýbcdfghjklmnpqrstvwxzďťň")
        # Poznámka: "ch" je speciální případ, řešíme ho zvlášť
        # Whitelist se používá pro rychlé přeskočení slov, která nepotřebují konverzi

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
            "příliš": "príliš",
            "přílišný": "prílišný",
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

    def _apply_phonetic_rules(self, text: str) -> str:
        """
        Aplikuje fonetická pravidla před slovníkovým lookup.

        Priorita pravidel:
        1. "ů" → "ú" (globální, kritické - model nezná "ů")
        2. "ř" → "r" (výchozí, doporučené) nebo "ř" → "ř" (pokud model zná)
        3. "mě" → "mje" (zachytí výslovnost [mňe] pomocí "j")
        4. "ně" → "ňe" (měkké ň zachytí výslovnost [ňe])
        5. "tě" → "ťe" (měkké ť zachytí výslovnost [ťe])
        6. "dě" → "ďe" (měkké ď zachytí výslovnost [ďe])

        Args:
            text: Vstupní text

        Returns:
            Text s aplikovanými fonetickými pravidly
        """
        # 1. ů → ú (globální, kritické - model nezná "ů")
        # "ú" je standardní slovenské dlouhé u, podobné českému "ů"
        text = re.sub(r"ů", self.u_replacement, text)

        # 2. ř → fonetická reprezentace (konfigurovatelná)
        # Výchozí: "ř" → "r" (doporučené, model lépe zná "r")
        # Alternativa: "ř" → "ř" pokud model zná "ř" a zní dobře
        if self.r_replacement != "ř":
            text = re.sub(r"ř", self.r_replacement, text)
        # else: nechat "ř" beze změny (pokud model zná tento znak)

        # 3. mě → mje (zachytí výslovnost [mňe] pomocí "j")
        # "mje" lépe zachytí českou výslovnost [mňe] než prosté "me"
        # "j" zachytí palatalizaci před "e" lépe než "mňe" (dvě měkké souhlásky za sebou)
        text = re.sub(r"\b([Mm]ě)", lambda m: "Mje" if m.group(1)[0].isupper() else "mje", text)
        text = re.sub(r"([bcčdďfghjklmnňpqrsštťvwxzž])([Mm]ě)", lambda m: m.group(1) + ("Mje" if m.group(2)[0].isupper() else "mje"), text)

        # 4. ně → ňe (měkké ň zachytí výslovnost [ňe])
        text = re.sub(r"\b([Nn]ě)", lambda m: "Ňe" if m.group(1)[0].isupper() else "ňe", text)
        text = re.sub(r"([bcčdďfghjklmnňpqrsštťvwxzž])([Nn]ě)", lambda m: m.group(1) + ("Ňe" if m.group(2)[0].isupper() else "ňe"), text)

        # 5. tě → ťe (měkké ť zachytí výslovnost [ťe])
        text = re.sub(r"\b([Tt]ě)", lambda m: "Ťe" if m.group(1)[0].isupper() else "ťe", text)
        text = re.sub(r"([bcčdďfghjklmnňpqrsštťvwxzž])([Tt]ě)", lambda m: m.group(1) + ("Ťe" if m.group(2)[0].isupper() else "ťe"), text)

        # 6. dě → ďe (měkké ď zachytí výslovnost [ďe])
        text = re.sub(r"\b([Dd]ě)", lambda m: "Ďe" if m.group(1)[0].isupper() else "ďe", text)
        text = re.sub(r"([bcčdďfghjklmnňpqrsštťvwxzž])([Dd]ě)", lambda m: m.group(1) + ("Ďe" if m.group(2)[0].isupper() else "ďe"), text)

        return text

    def _is_whitelist_word(self, word: str) -> bool:
        """
        Zkontroluje, jestli slovo obsahuje pouze whitelist znaky.
        Pokud ano, může být přeskočeno v konverzi (volitelná optimalizace).

        Args:
            word: Slovo k ověření

        Returns:
            True pokud slovo obsahuje pouze whitelist znaky
        """
        word_lower = word.lower()
        # Odebrat "ch" jako speciální případ (je to jeden znak v češtině)
        word_lower = word_lower.replace("ch", "")
        return all(c in self.WHITELIST_CHARS for c in word_lower)

    def convert(self, text: str) -> ConversionResult:
        """
        Konvertuje český text pro slovenský F5-TTS model.

        Pořadí zpracování:
        1. Regex pravidla (_apply_phonetic_rules)
        2. Slovníkový lookup (stávající logika)
        3. Výpočet confidence a statistik

        Args:
            text: Vstupní český text

        Returns:
            ConversionResult s konvertovaným textem a statistikami
        """
        applied = []

        # 1. FÁZE: Regex pravidla (před slovníkem)
        text = self._apply_phonetic_rules(text)

        # 2. FÁZE: Slovníkový lookup (stávající logika)
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
    # Nastavit UTF-8 encoding pro výstup (Windows konzole)
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    # Testovací příklady z plánu
    adapter = CzechToSlovakAdapter()

    test_cases = [
        "Příliš žlutoučký kůň úpěl dábelské ódy.",
        "Příliš - žlutoučký",
        "Řeka teče kolem města.",
        "Děti si hrály na hřišti.",
    ]

    print("=" * 70)
    print("CZ-SK FONETICKA ADAPTACE - TESTOVANI")
    print("=" * 70)
    print()

    for test_text in test_cases:
        result = adapter.convert(test_text)
        print(f"Vstup:  {result.original}")
        print(f"Výstup: {result.converted}")
        print(f"Změn: {result.changes_count}, Důvěra: {result.confidence:.2f}")
        if result.applied_conversions:
            print("Aplikované konverze:")
            for conv in result.applied_conversions[:5]:  # Prvních 5
                print(f"  {conv['original']} → {conv['converted']} ({conv['type']})")
        print()

    # Test s různými konfiguracemi
    print("=" * 70)
    print("TESTOVANI S RUZNYMI KONFIGURACEMI")
    print("=" * 70)
    print()

    test_text = "Řeka teče kolem města."
    print(f"Testovaci text: {test_text}")
    print()

    # Výchozí konfigurace (ř → ř, ů → ú)
    adapter_default = CzechToSlovakAdapter(r_replacement="ř", u_replacement="ú")
    result_default = adapter_default.convert(test_text)
    print(f"Vychozi (r->r, u->u): {result_default.converted}")

    # Alternativní konfigurace (ř → r, ů → ô)
    adapter_alt = CzechToSlovakAdapter(r_replacement="r", u_replacement="ô")
    result_alt = adapter_alt.convert(test_text)
    print(f"Alternativni (r->r, u->o): {result_alt.converted}")
