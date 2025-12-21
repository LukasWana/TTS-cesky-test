"""
Modul pro pokročilé předzpracování českého textu pomocí lookup tabulek

Aplikuje pravidla:
- Spodoba znělosti
- Vkládání rázu
- Oprava souhláskových skupin
"""
import re
from typing import List, Tuple
from backend.lookup_tables_loader import get_lookup_loader


class CzechTextProcessor:
    """Třída pro pokročilé předzpracování českého textu"""

    def __init__(self):
        """Inicializace procesoru s lookup tabulkami"""
        self.lookup_loader = get_lookup_loader()
        self.znele_neznele_pary = self.lookup_loader.get_znele_neznele_pary()
        self.souhlsakove_skupiny = self.lookup_loader.get_souhlsakove_skupiny_rules()
        self.raz_pravidla = self.lookup_loader.get_raz_pravidla()

    def process_text(self, text: str, apply_voicing: bool = True, apply_glottal_stop: bool = True,
                     apply_consonant_groups: bool = True) -> str:
        """
        Zpracuje text aplikací českých fonetických pravidel

        Args:
            text: Vstupní text
            apply_voicing: Aplikovat spodobu znělosti
            apply_glottal_stop: Aplikovat vkládání rázu
            apply_consonant_groups: Opravit souhláskové skupiny

        Returns:
            Zpracovaný text
        """
        processed = text

        # 1. Oprava souhláskových skupin (mě -> mňe)
        if apply_consonant_groups and self.souhlsakove_skupiny:
            processed = self._fix_consonant_groups(processed)

        # 2. Spodoba znělosti (na konci slova, před neznělými/znělými)
        if apply_voicing and self.znele_neznele_pary:
            processed = self._apply_voicing_assimilation(processed)

        # 3. Vkládání rázu (fakultativně - pouze pokud je to výslovně požadováno)
        # Pozn.: Ráz se obvykle nevkládá do textu, protože XTTS ho může generovat automaticky
        # Tato funkce je zde pro případné budoucí použití

        return processed

    def _fix_consonant_groups(self, text: str) -> str:
        """Opraví problematické souhláskové skupiny"""
        processed = text

        # mě -> mňe
        if "mě" in self.souhlsakove_skupiny:
            # Nahradíme "mě" na "mňe" (ale zachováme původní text, protože XTTS potřebuje správný text)
            # Pozn.: Tato oprava by měla být spíše v fonetickém přepisu, ne v textu
            # Prozatím to necháme, protože XTTS by měl správně vyslovit "mě" jako "mňe"
            pass

        # nk/ng -> ŋ (toto je fonetická změna, kterou XTTS by měl zvládnout automaticky)
        # Pro text preprocessing to necháme bez změny

        return processed

    def _apply_voicing_assimilation(self, text: str) -> str:
        """
        Aplikuje spodobu znělosti na konci slov

        Pozn.: Toto je složitější pravidlo, které by mělo být aplikováno
        na fonetické úrovni, ne na textové. Pro text preprocessing
        to necháme bez změny, protože XTTS by měl správně vyslovit
        znělé souhlásky na konci slov jako neznělé.

        Tato funkce je zde pro případné budoucí rozšíření.
        """
        # Spodoba znělosti je fonetický jev, který XTTS model
        # by měl zvládnout automaticky při správném tréninku
        # Prozatím necháme text beze změny
        return text

    def _apply_glottal_stop(self, text: str) -> str:
        """
        Vkládá ráz (glottální okluze) na správná místa

        Pozn.: Ráz se obvykle nevkládá do textu explicitně,
        protože XTTS ho může generovat automaticky. Tato funkce
        je zde pro případné budoucí použití s SSML značkami.
        """
        # Ráz se obvykle nevkládá do textu, protože XTTS ho generuje automaticky
        # Pokud by bylo potřeba, mohli bychom použít SSML značky nebo speciální znaky
        return text

    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Normalizuje text pro lepší zpracování TTS

        Args:
            text: Vstupní text

        Returns:
            Normalizovaný text
        """
        # Odstranění vícenásobných mezer
        text = re.sub(r'\s+', ' ', text)

        # Normalizace interpunkce
        text = text.replace('...', '…')
        text = text.replace('--', '—')

        # Odstranění mezer před interpunkcí
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)

        return text.strip()


# Globální instance
_text_processor_instance = None


def get_czech_text_processor() -> CzechTextProcessor:
    """
    Vrátí globální instanci CzechTextProcessor (singleton pattern)

    Returns:
        Instance CzechTextProcessor
    """
    global _text_processor_instance
    if _text_processor_instance is None:
        _text_processor_instance = CzechTextProcessor()
    return _text_processor_instance

