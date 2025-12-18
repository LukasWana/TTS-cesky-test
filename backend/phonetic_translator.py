"""
Fonetický přepis cizích slov v českém textu

Tento modul poskytuje funkci pro přepis anglických a dalších cizích slov
na fonetické ekvivalenty v češtině, aby je TTS model správně vyslovil.
"""
import re
from typing import Dict
# Slovník anglických slov a jejich fonetických přepisů do češtiny
ENGLISH_PHONETIC = {
    'email': 'ímejl',
    'marketing': 'marketink',
    'manager': 'menedžer',
    'meeting': 'mítink',
    'feedback': 'fídbek',
    'hashtag': 'heštek',
    'influencer': 'influensr',
    'business': 'biznis',
    'brand': 'brent',
    'startup': 'startap',

    # Wellbeing & Mental Health
    'wellbeing': 'velbíink',
    'wellness': 'velnes',
    'mindfulness': 'majndfulnes',
    'awareness': 'evérnes',
    'balance': 'balans',
    'harmony': 'harmoní',
    'peace': 'pís',
    'calm': 'kám',
    'relax': 'rileks',
    'relaxation': 'rileksejšn',
    'stress': 'stres',
    'burnout': 'brnaut',
    'selfcare': 'selfker',
    'self-care': 'selfker',
    'healing': 'hílink',
    'therapy': 'terепí',
    'mental health': 'mentl hels',
    'emotional': 'imóušnl',
    'positive': 'pozitiv',
    'negative': 'negativ',
    'energy': 'enrdží',
    'vibe': 'vajb',
    'mood': 'můd',
    'feeling': 'fílink',
    'happy': 'hепí',
    'joy': 'džoj',
    'gratitude': 'gretitjůd',
    'compassion': 'kmpešn',
    'empathy': 'empeti',
    'confidence': 'konfidens',
    'motivation': 'motivejšn',
    'inspiration': 'inspirejšn',
    'growth': 'grous',
    'personal growth': 'prsnl grous',
    'self-love': 'selflav',
    'self-esteem': 'selfistím',

    # Yoga & Meditation
    'yoga': 'jóga',
    'meditation': 'meditejšn',
    'mindful': 'majndfl',
    'breathwork': 'bresvork',
    'breathing': 'brísink',
    'pranayama': 'pranajáma',
    'asana': 'ásana',
    'vinyasa': 'vinása',
    'hatha': 'hata',
    'ashtanga': 'aštanga',
    'kundalini': 'kundalíní',
    'yin': 'jin',
    'restorative': 'ristorativ',
    'flow': 'flou',
    'chakra': 'čakra',
    'mantra': 'mantra',
    'mudra': 'mudra',
    'namaste': 'namasté',
    'om': 'óm',
    'zen': 'zen',
    'karma': 'karma',
    'dharma': 'dharma',
    'enlightenment': 'enlajtnment',
    'consciousness': 'konšesnes',
    'spiritual': 'spiričuál',
    'spirituality': 'spiričuelití',
    'practice': 'praktis',
    'ritual': 'ričuál',
    'ceremony': 'sérimoní',
    'sacred': 'sejkrid',
    'divine': 'divajn',
    'soul': 'soul',
    'spirit': 'spirit',
    'inner peace': 'inr pís',
    'transformation': 'transformejšn',
    'journey': 'džrní',

    # Healthy Lifestyle
    'healthy': 'helsí',
    'health': 'hels',
    'lifestyle': 'lajfstajl',
    'detox': 'dítoks',
    'cleanse': 'klenz',
    'organic': 'organik',
    'natural': 'nečrl',
    'bio': 'bío',
    'vegan': 'vígen',
    'vegetarian': 'vedžitérién',
    'plant-based': 'plantbejzd',
    'raw': 'ró',
    'superfood': 'superfůd',
    'protein': 'proutín',
    'vitamin': 'vitamín',
    'mineral': 'minrl',
    'supplement': 'saplment',
    'nutrition': 'njůtríšn',
    'diet': 'dajet',
    'fasting': 'fastink',
    'intermittent': 'intrmitn',
    'macro': 'makro',
    'calories': 'keloris',
    'hydration': 'hajdrejšn',
    'water': 'vótr',
    'juice': 'džůs',
    'green': 'grín',
    'salad': 'seled',
    'bowl': 'boul',
    'bowl food': 'boul fůd',
    'fresh': 'freš',
    'whole': 'houl',
    'grain': 'grejn',
    'seed': 'síd',
    'nut': 'nat',
    'berry': 'berí',
    'antioxidant': 'antioksidnt',

    # Sleep & Recovery
    'sleep': 'slíp',
    'rest': 'rest',
    'recovery': 'rikаvrí',
    'regeneration': 'ridženerejšn',
    'power nap': 'pauernep',
    'bedtime': 'bedtajm',
    'routine': 'rutín',
    'ritual': 'ričuál',
    'insomnia': 'insomnie',
    'deep sleep': 'dípslíp',
    'rem': 'rem',
    'dream': 'drím',

    # Movement & Exercise
    'stretching': 'stečink',
    'flexibility': 'fleksibilití',
    'mobility': 'mobilitі',
    'pilates': 'pilátis',
    'barre': 'bár',
    'dance': 'dens',
    'cardio': 'kardio',
    'hiit': 'híít',
    'interval': 'intrvl',
    'core': 'kór',
    'strength': 'strengs',
    'endurance': 'endjurns',
    'stamina': 'stemina',
    'balance': 'balans',
    'posture': 'posčr',
    'alignment': 'alajnment',
    'body': 'bodí',
    'mind': 'majnd',
    'body-mind': 'bodímajnd',
    'connection': 'knekšn',

    # Spa & Treatments
    'spa': 'spá',
    'massage': 'masáž',
    'aromatherapy': 'aromaterapí',
    'sauna': 'sauna',
    'jacuzzi': 'džakuzí',
    'facial': 'fejšl',
    'treatment': 'trítment',
    'scrub': 'skrab',
    'peel': 'píl',
    'mask': 'mask',
    'oil': 'ojl',
    'essential': 'esenšl',
    'lavender': 'levendr',
    'eucalyptus': 'jukaliptus',
    'peppermint': 'peprmint',
    'chamomile': 'kemomail',
    'rose': 'rouz',
    'sandalwood': 'sendlvud',

    # Holistic Practices
    'holistic': 'holistik',
    'alternative': 'alternativ',
    'ayurveda': 'ájurvéda',
    'acupuncture': 'ekjupankčr',
    'reiki': 'rejkí',
    'sound healing': 'saund hílink',
    'crystal': 'kristl',
    'tarot': 'tarot',
    'oracle': 'orekl',
    'astrology': 'estrolodží',
    'horoscope': 'horoskop',
    'intuition': 'intjuíšn',
    'manifestation': 'menifestejšn',
    'affirmation': 'afrmejšn',
    'visualization': 'vizualizejšn',
    'intention': 'intenšn',
    'mindset': 'majndset',
    'abundance': 'ebandns',
    'gratitude journal': 'gretitjůd džrnl',
    'journal': 'džrnl',
    'journaling': 'džrnlink',

    # Community & Support
    'community': 'komjunitі',
    'tribe': 'trajb',
    'circle': 'srkl',
    'retreat': 'ritrít',
    'workshop': 'vorkšop',
    'class': 'klás',
    'session': 'sešn',
    'instructor': 'instrаktr',
    'teacher': 'tíčr',
    'guide': 'gajd',
    'mentor': 'mentor',
    'coach': 'kouč',
    'coaching': 'koučink',
    'support': 'sapórt',
    'group': 'grůp',

    # IT & Tech
    'email': 'ímejl',
    'e-mail': 'ímejl',
    'online': 'onlajn',
    'offline': 'oflajn',
    'internet': 'intrnet',
    'web': 'veb',
    'website': 'vebsajt',
    'browser': 'brauzr',
    'server': 'servr',
    'software': 'softver',
    'hardware': 'hardver',
    'update': 'apdejt',
    'upgrade': 'apgrejd',
    'download': 'daunloud',
    'upload': 'aploud',
    'login': 'login',
    'logout': 'logaut',
    'password': 'pasword',
    'username': 'juzrnejm',
    'database': 'datábejs',
    'backup': 'bekap',
    'cloud': 'klaud',
    'app': 'ep',
    'application': 'aplikejšn',
    'laptop': 'leptop',
    'desktop': 'desktop',
    'smartphone': 'smartfoun',
    'tablet': 'teblet',
    'screenshot': 'skrínšot',
    'bluetooth': 'blůtůs',
    'wifi': 'vajfaj',
    'wi-fi': 'vajfaj',

    # Business & Marketing
    'meeting': 'mítink',
    'deadline': 'dedlajn',
    'feedback': 'fídbek',
    'marketing': 'marketink',
    'manager': 'menedžer',
    'management': 'menedžment',
    'business': 'biznis',
    'startup': 'startap',
    'brand': 'brent',
    'branding': 'brendink',
    'briefing': 'brífink',
    'debriefing': 'díbrífink',
    'brainstorming': 'brejnstormink',
    'workshop': 'vorkšop',
    'teamwork': 'tímvork',
    'team': 'tým',
    'leader': 'lídr',
    'leadership': 'lídrship',
    'budget': 'badžet',
    'project': 'prodžekt',
    'presentation': 'prezentejšn',
    'report': 'ripórt',
    'strategy': 'stretedži',
    'target': 'targt',
    'goal': 'goul',
    'profit': 'profit',
    'sales': 'sejls',
    'deal': 'díl',
    'contract': 'kontrekt',
    'invoice': 'invoys',
    'cash': 'keš',
    'cashflow': 'kešflou',

    # Social Media
    'hashtag': 'heštek',
    'influencer': 'influensr',
    'follower': 'folouer',
    'like': 'lajk',
    'share': 'šer',
    'post': 'poust',
    'story': 'stóri',
    'stories': 'stóris',
    'reels': 'ríls',
    'content': 'kontent',
    'creator': 'kríejtr',
    'streamer': 'strýmr',
    'streaming': 'strýmink',
    'podcast': 'podkást',
    'vlog': 'vlog',
    'blog': 'blog',
    'blogger': 'blogr',
    'youtuber': 'júťubr',
    'subscriber': 'sabskrajbr',
    'comment': 'koment',
    'thread': 'tred',
    'viral': 'vajrl',
    'trending': 'trendink',
    'feed': 'fíd',
    'timeline': 'tajmlajn',
    'profile': 'proufajl',
    'avatar': 'avatár',

    # Lifestyle & Fashion
    'cool': 'kúl',
    'style': 'stajl',
    'fashion': 'fešn',
    'design': 'dizajn',
    'designer': 'dizajnr',
    'look': 'luk',
    'outfit': 'autfit',
    'shopping': 'šopink',
    'sale': 'sejl',
    'bestseller': 'bestselr',
    'trend': 'trend',
    'vintage': 'vintidž',
    'retro': 'retro',
    'street': 'strít',
    'casual': 'kežuál',
    'formal': 'formál',
    'party': 'párty',
    'event': 'ivent',
    'weekend': 'víkend',
    'hobby': 'hobi',
    'lifestyle': 'lajfstajl',

    # Food & Drink
    'fast food': 'fastfůd',
    'fastfood': 'fastfůd',
    'burger': 'brgr',
    'hot dog': 'hotdog',
    'hotdog': 'hotdog',
    'sandwich': 'sendvič',
    'smoothie': 'smůdí',
    'milkshake': 'milkšejk',
    'coffee': 'kofí',
    'latte': 'late',
    'cappuccino': 'kapučíno',
    'espresso': 'espreso',
    'cocktail': 'koktejl',
    'drink': 'drink',
    'snack': 'snek',
    'chips': 'čips',
    'popcorn': 'popkorn',
    'grill': 'gril',
    'barbecue': 'bárbekjů',
    'picnic': 'piknik',
    'brunch': 'branč',
    'breakfast': 'brekfest',
    'lunch': 'lanč',
    'dinner': 'dinr',

    # Sport & Fitness
    'fitness': 'fitness',
    'workout': 'vorkaut',
    'training': 'trejnink',
    'coach': 'kouč',
    'team': 'tým',
    'match': 'meč',
    'game': 'gejm',
    'player': 'plejr',
    'champion': 'čempion',
    'trophy': 'trofí',
    'sport': 'sport',
    'football': 'futbol',
    'basketball': 'basketbol',
    'hockey': 'hokej',
    'tennis': 'tenis',
    'golf': 'golf',
    'boxing': 'boksink',
    'running': 'ranink',
    'jogging': 'džogink',
    'cycling': 'sajklink',
    'gym': 'džim',
    'bodybuilding': 'bodybuildink',

    # Entertainment
    'show': 'šou',
    'performance': 'prformns',
    'concert': 'koncert',
    'festival': 'festivl',
    'movie': 'mový',
    'film': 'film',
    'series': 'síríz',
    'episode': 'epizoud',
    'season': 'sízn',
    'trailer': 'trejlr',
    'premiere': 'premjéra',
    'soundtrack': 'saundtrek',
    'album': 'album',
    'single': 'singl',
    'hit': 'hit',
    'remix': 'rímiks',
    'cover': 'kavr',
    'live': 'lajv',
    'tour': 'túr',
    'backstage': 'bekstejdž',

    # Travel
    'travel': 'trevl',
    'trip': 'trip',
    'tour': 'túr',
    'tourist': 'turist',
    'hotel': 'houtl',
    'hostel': 'hostl',
    'resort': 'rizort',
    'airport': 'érport',
    'flight': 'flajt',
    'booking': 'bukink',
    'check-in': 'čekin',
    'checkout': 'čekaut',
    'ticket': 'tiket',
    'visa': 'víza',
    'passport': 'pásport',
    'baggage': 'begidž',
    'suitcase': 'sůtkejs',
    'backpack': 'bekpek',
    'camping': 'kempink',
    'adventure': 'edvenčr',

    # Běžné fráze
    'okay': 'oukej',
    'ok': 'oukej',
    'yes': 'jes',
    'no': 'nou',
    'wow': 'vau',
    'sorry': 'sori',
    'please': 'plís',
    'thanks': 'tenks',
    'thank you': 'tenk jů',
    'hello': 'helou',
    'hi': 'haj',
    'bye': 'baj',
    'goodbye': 'gudbaj',
    'welcome': 'velkm',
    'excuse me': 'ekskjůz mí',
    'pardon': 'párdn',
    'maybe': 'mејbí',
    'sure': 'šůr',
    'exactly': 'igzektlí',
    'perfect': 'prfekt',
    'awesome': 'ósm',
    'great': 'grejt',
    'super': 'super',
    'amazing': 'emejzink',
    'fantastic': 'fentestik',
    'wonderful': 'vandrfl',

    # Další časté výrazy
    'discount': 'diskаunt',
    'voucher': 'vaučr',
    'gift': 'gift',
    'premium': 'prímium',
    'standard': 'standardní',
    'basic': 'bejzik',
    'pro': 'prou',
    'plus': 'plas',
    'extra': 'extra',
    'bonus': 'bónus',
    'special': 'spešl',
    'limited': 'limitid',
    'exclusive': 'ekskluziv',
    'private': 'pravit',
    'public': 'pablik',
    'open': 'oupn',
    'closed': 'klouzd',
    'free': 'frí',
    'trial': 'trajl',
    'demo': 'demo',
    'beta': 'beta',
    'release': 'rilís',
    'version': 'veržn',
    'support': 'sapórt',
    'help': 'help',
    'guide': 'gajd',
    'tutorial': 'tjútóriál',
    'tips': 'tips',
    'tricks': 'triks',
    'hacks': 'heks',
}

# Místo pro další jazyky - připravíme strukturu pro snadné rozšíření
# GERMAN_PHONETIC = {
#     'example': 'příklad',
# }
#
# FRENCH_PHONETIC = {
#     'example': 'příklad',
# }


class PhoneticTranslator:
    """Třída pro fonetický přepis cizích slov v textu"""

    def __init__(self):
        """Inicializace překladače se slovníky"""
        # Mapování jazyků na jejich slovníky
        self.language_dicts: Dict[str, Dict[str, str]] = {
            'en': ENGLISH_PHONETIC,
            # Místo pro další jazyky:
            # 'de': GERMAN_PHONETIC,
            # 'fr': FRENCH_PHONETIC,
        }

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

        # Projdeme všechny podporované jazyky a přepíšeme jejich slova
        for lang_code, phonetic_dict in self.language_dicts.items():
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
        processed_text = text

        for foreign_word, phonetic in phonetic_dict.items():
            # Case-insensitive nahrazení celých slov pomocí word boundaries
            # \b zajišťuje, že nahrazujeme pouze celá slova, ne části slov
            pattern = r'\b' + re.escape(foreign_word) + r'\b'
            processed_text = re.sub(pattern, phonetic, processed_text, flags=re.IGNORECASE)

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
