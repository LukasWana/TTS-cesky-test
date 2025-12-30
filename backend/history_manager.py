"""
Správa historie generovaných audio souborů
"""
import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from backend.config import BASE_DIR, OUTPUTS_DIR

logger = logging.getLogger(__name__)


class HistoryManager:
    """Správa historie generovaných audio souborů"""
    HISTORY_FILE = BASE_DIR / "history.json"

    @classmethod
    def _load_history(cls) -> List[Dict]:
        """Načte historii z JSON souboru"""
        if not cls.HISTORY_FILE.exists():
            return []

        try:
            with open(cls.HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    @classmethod
    def _save_history(cls, history: List[Dict]):
        """Uloží historii do JSON souboru atomicky."""
        temp_path = cls.HISTORY_FILE.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())

            # os.replace handles overwriting existing files atomically on both Windows and POSIX
            os.replace(str(temp_path), str(cls.HISTORY_FILE))
        except Exception as e:
            logger.error(f"Failed to save history: {e}")
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except:
                    pass

    @staticmethod
    def add_entry(
        audio_url: str,
        filename: str,
        text: str,
        voice_type: str,
        voice_name: Optional[str] = None,
        tts_params: Optional[Dict] = None,
        created_at: Optional[str] = None
    ) -> Dict:
        """
        Přidá nový záznam do historie

        Args:
            audio_url: URL audio souboru
            filename: Název souboru
            text: Text který byl syntetizován
            voice_type: Typ hlasu ('demo', 'upload', 'record', 'youtube')
            voice_name: Název hlasu (volitelné)
            tts_params: TTS parametry (volitelné)
            created_at: Čas vytvoření (volitelné, výchozí: aktuální čas)

        Returns:
            Vytvořený záznam
        """
        # Kontrola existence souboru před přidáním do historie
        if filename and not (OUTPUTS_DIR / filename).exists():
            logger.warning(f"Audio soubor neexistuje při přidávání do historie: {filename}")
            # Pokračujeme i když soubor neexistuje (může být race condition)

        history = HistoryManager._load_history()

        # Dedupe: kontrolovat pouze filename (každý generovaný soubor má unikátní UUID)
        # Pokud je filename stejné, vrátit existující záznam (to by se nemělo stát, ale pro jistotu)
        if history and len(history) > 0:
            # Zkontroluj, zda už existuje záznam se stejným filename
            existing_entry = next((entry for entry in history if entry.get("filename") == filename), None)
            if existing_entry:
                # Stejný filename - vrátit existující záznam (to by se nemělo stát, protože filename je UUID)
                return existing_entry

        # Omezit historii na max 1000 záznamů před přidáním nového
        if len(history) >= 1000:
            history = history[:999]  # Necháme místo pro nový záznam

        entry = {
            "id": filename.replace('.wav', ''),
            "audio_url": audio_url,
            "filename": filename,
            "text": text,
            "voice_type": voice_type,
            "voice_name": voice_name,
            "tts_params": tts_params or {},
            "created_at": created_at or datetime.now().isoformat()
        }

        # Přidat na začátek (nejnovější první)
        history.insert(0, entry)

        HistoryManager._save_history(history)
        return entry

    @staticmethod
    def get_history(limit: Optional[int] = None, offset: int = 0) -> List[Dict]:
        """
        Získá historii generovaných audio

        Args:
            limit: Maximální počet záznamů (None = všechny)
            offset: Offset pro stránkování

        Returns:
            Seznam záznamů
        """
        history = HistoryManager._load_history()

        # Prune záznamy, které ukazují na soubory, jež už neexistují v outputs/
        # (jinak FE dostává 404 a WaveSurfer hlásí chyby)
        try:
            before = len(history)
            filtered = []
            for entry in history:
                fn = entry.get("filename")
                if fn and (OUTPUTS_DIR / fn).exists():
                    filtered.append(entry)
            if len(filtered) != before:
                HistoryManager._save_history(filtered)
                history = filtered
        except Exception:
            # Nechceme blokovat API kvůli problému s FS; v nejhorším vrať původní list
            pass

        if limit is None:
            return history[offset:]
        else:
            return history[offset:offset + limit]

    @staticmethod
    def get_entry_by_id(entry_id: str) -> Optional[Dict]:
        """Získá konkrétní záznam podle ID"""
        history = HistoryManager._load_history()
        for entry in history:
            if entry.get("id") == entry_id:
                return entry
        return None

    @staticmethod
    def delete_entry(entry_id: str) -> bool:
        """
        Smaže záznam z historie

        Args:
            entry_id: ID záznamu

        Returns:
            True pokud byl záznam smazán
        """
        history = HistoryManager._load_history()
        original_length = len(history)

        history = [entry for entry in history if entry.get("id") != entry_id]

        if len(history) < original_length:
            HistoryManager._save_history(history)
            return True
        return False

    @staticmethod
    def clear_history() -> int:
        """
        Vymaže celou historii

        Returns:
            Počet smazaných záznamů
        """
        history = HistoryManager._load_history()
        count = len(history)
        HistoryManager._save_history([])
        return count

    @staticmethod
    def get_stats() -> Dict:
        """Získá statistiky historie"""
        history = HistoryManager._load_history()
        return {
            "total_entries": len(history),
            "oldest_entry": history[-1]["created_at"] if history else None,
            "newest_entry": history[0]["created_at"] if history else None
        }




