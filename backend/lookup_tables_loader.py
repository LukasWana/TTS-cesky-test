
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class LookupTablesLoader:
    def __init__(self):
        self.base_dir = Path("c:/work/projects/2025-voice-assistent/lookup_tables")
        self._cache = {}

    def _load_json(self, filename):
        if filename in self._cache:
            return self._cache[filename]

        path = self.base_dir / filename
        if not path.exists():
            logger.warning(f"Lookup table {filename} not found at {path}")
            return {}

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._cache[filename] = data
                return data
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            return {}

    def get_znele_neznele_pary(self):
        data = self._load_json("spodoba_znelosti.json")
        return data.get("znele_neznele_pary", {})

    def get_souhlsakove_skupiny_rules(self):
        data = self._load_json("souhlsakove_skupiny.json")
        return data.get("skupiny", {})

    def get_raz_pravidla(self):
        data = self._load_json("raz_pozice.json")
        if "pravidla" in data:
            return data["pravidla"]
        return data  # Fallback pokud je to už naplocho

    def get_english_phonetic(self):
        return self._load_json("english_phonetic.json")

    def get_prejata_slova_dict(self):
        return self._load_json("prejata_slova_vyjimky.json")

    def get_prosodicke_pravidla(self):
        return self._load_json("prosodicke_pravidla.json")

    def get_czech_phonetic_fixes(self):
        return self._load_json("foneticka_abeceda.json")

_instance = None

def get_lookup_loader():
    global _instance
    if _instance is None:
        _instance = LookupTablesLoader()
    return _instance
