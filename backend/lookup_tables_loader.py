"""
Modul pro načítání a použití lookup tabulek pro zlepšení kvality XTTS-v2

Tento modul načítá strukturované lookup tabulky z adresáře lookup_tables
a poskytuje funkce pro jejich použití při předzpracování textu.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from backend.config import BASE_DIR

LOOKUP_TABLES_DIR = BASE_DIR / "lookup_tables"


class LookupTablesLoader:
    """Třída pro načítání a správu lookup tabulek"""

    def __init__(self):
        """Inicializace loaderu s načtením všech tabulek"""
        self.foneticka_abeceda: Optional[Dict] = None
        self.spodoba_znelosti: Optional[Dict] = None
        self.prejata_slova: Optional[Dict] = None
        self.prosodicke_pravidla: Optional[Dict] = None
        self.raz_pozice: Optional[Dict] = None
        self.souhlsakove_skupiny: Optional[Dict] = None
        self.ceska_nareci: Optional[Dict] = None
        self._load_all_tables()

    def _load_all_tables(self):
        """Načte všechny lookup tabulky z JSON souborů"""
        try:
            # Načtení fonetické abecedy
            self.foneticka_abeceda = self._load_json("foneticka_abeceda.json")

            # Načtení pravidel spodoby znělosti
            self.spodoba_znelosti = self._load_json("spodoba_znelosti.json")

            # Načtení přejatých slov a výjimek
            self.prejata_slova = self._load_json("prejata_slova_vyjimky.json")

            # Načtení prosodických pravidel
            self.prosodicke_pravidla = self._load_json("prosodicke_pravidla.json")

            # Načtení pravidel pro ráz
            self.raz_pozice = self._load_json("raz_pozice.json")

            # Načtení souhláskových skupin
            self.souhlsakove_skupiny = self._load_json("souhlsakove_skupiny.json")

            # Načtení pravidel pro česká nářečí
            self.ceska_nareci = self._load_json("ceska_nareci.json")

            print("[OK] Lookup tabulky uspesne nacteny")
        except Exception as e:
            print(f"[WARN] Varovani: Nektere lookup tabulky se nepodarilo nacist: {e}")

    def _load_json(self, filename: str) -> Optional[Dict]:
        """Načte JSON soubor z lookup_tables adresáře"""
        file_path = LOOKUP_TABLES_DIR / filename
        if not file_path.exists():
            print(f"[WARN] Soubor {filename} neexistuje v {LOOKUP_TABLES_DIR}")
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Chyba pri nacitani {filename}: {e}")
            return None

    def get_prejata_slova_dict(self) -> Dict[str, str]:
        """
        Vrátí slovník přejatých slov pro použití v phonetic_translator

        Returns:
            Slovník mapující přejatá slova na jejich správnou výslovnost
        """
        if not self.prejata_slova:
            return {}

        result = {}
        kategorie = self.prejata_slova.get("kategorie", {})

        # Samohlásková délka - kolísání
        samohlaskova = kategorie.get("samohlaskova_delka", {})
        for kolise_type, data in samohlaskova.get("kolise", {}).items():
            for slovo, varianty in data.get("priklady", {}).items():
                if isinstance(varianty, list) and len(varianty) > 0:
                    # Použijeme první (správnou) variantu
                    result[slovo.lower()] = varianty[0]

        # Souhlásková znělost - dublety
        souhlsakova = kategorie.get("souhlsakova_znelost", {})
        for zvuk_type, data in souhlsakova.items():
            if isinstance(data, dict):
                for slovo, varianty in data.get("dublety", {}).items():
                    if isinstance(varianty, list) and len(varianty) > 0:
                        result[slovo.lower()] = varianty[0]
                for slovo, varianty in data.get("pouze_z", {}).items():
                    if isinstance(varianty, list) and len(varianty) > 0:
                        result[slovo.lower()] = varianty[0]
                for slovo, varianty in data.get("pouze_s", {}).items():
                    if isinstance(varianty, list) and len(varianty) > 0:
                        result[slovo.lower()] = varianty[0]

        # Di, ti, ni - pouze neznělé
        di_ti_ni = kategorie.get("di_ti_ni", {})
        for slovo, vyslovnost in di_ti_ni.get("pouze_neznele", {}).items():
            result[slovo.lower()] = vyslovnost

        # Vlastní jména
        vlastni_jmena = kategorie.get("vlastni_jmena", {})
        for kategorie_type, data in vlastni_jmena.items():
            if isinstance(data, dict):
                for jmeno, varianty in data.items():
                    if isinstance(varianty, list):
                        result[jmeno.lower()] = varianty[0]
                    elif isinstance(varianty, dict):
                        # Pro vlastní jména s více variantami použijeme první
                        if "1p" in varianty:
                            result[jmeno.lower()] = varianty["1p"]

        return result

    def get_znele_neznele_pary(self) -> Dict[str, str]:
        """
        Vrátí mapování znělých a neznělých souhlásek

        Returns:
            Slovník mapující neznělé souhlásky na znělé
        """
        if not self.spodoba_znelosti:
            return {}

        return self.spodoba_znelosti.get("znele_neznele_pary", {})

    def get_souhlsakove_skupiny_rules(self) -> Dict[str, Dict]:
        """
        Vrátí pravidla pro problematické souhláskové skupiny

        Returns:
            Slovník s pravidly pro jednotlivé skupiny
        """
        if not self.souhlsakove_skupiny:
            return {}

        return self.souhlsakove_skupiny.get("skupiny", {})

    def get_prosodicke_pravidla(self) -> Dict:
        """
        Vrátí prosodická pravidla

        Returns:
            Slovník s prosodickými pravidly
        """
        if not self.prosodicke_pravidla:
            return {}

        return self.prosodicke_pravidla

    def get_raz_pravidla(self) -> Dict:
        """
        Vrátí pravidla pro vkládání rázu

        Returns:
            Slovník s pravidly pro ráz
        """
        if not self.raz_pozice:
            return {}

        return self.raz_pozice

    def get_ceska_nareci(self) -> Dict:
        """
        Vrátí pravidla pro česká nářečí

        Returns:
            Slovník s pravidly pro nářečí
        """
        if not self.ceska_nareci:
            return {}

        return self.ceska_nareci


# Globální instance pro jednoduché použití
_lookup_loader_instance: Optional[LookupTablesLoader] = None


def get_lookup_loader() -> LookupTablesLoader:
    """
    Vrátí globální instanci LookupTablesLoader (singleton pattern)

    Returns:
        Instance LookupTablesLoader
    """
    global _lookup_loader_instance
    if _lookup_loader_instance is None:
        _lookup_loader_instance = LookupTablesLoader()
    return _lookup_loader_instance

