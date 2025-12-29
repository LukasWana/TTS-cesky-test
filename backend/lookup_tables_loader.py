
import logging

logger = logging.getLogger(__name__)

class LookupTablesLoader:
    """Safeguard implementation for missing lookup tables"""
    def __init__(self):
        logger.warning("LookupTablesLoader initialized with empty dictionaries (file was empty)")

    def get_english_phonetic(self):
        return {}

    def get_prejata_slova_dict(self):
        return {}

    def get_prosodicke_pravidla(self):
        return {}

    def get_czech_phonetic_fixes(self):
        return {}

def get_lookup_loader():
    """Singleton for LookupTablesLoader"""
    return LookupTablesLoader()
