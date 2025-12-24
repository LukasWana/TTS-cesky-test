"""
Samostatná historie pro generování hudby (MusicGen).

Ukládá do BASE_DIR/music_history.json, nezávisle na TTS historii (history.json).
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from backend.config import BASE_DIR, OUTPUTS_DIR

MUSIC_HISTORY_FILE = BASE_DIR / "music_history.json"


class MusicHistoryManager:
    @staticmethod
    def _load_history() -> List[Dict]:
        if not MUSIC_HISTORY_FILE.exists():
            return []
        try:
            with open(MUSIC_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    @staticmethod
    def _save_history(history: List[Dict]) -> None:
        """Uloží historii atomicky (write temp + rename)"""
        try:
            temp_file = MUSIC_HISTORY_FILE.with_suffix('.tmp')
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())

            if temp_file.exists():
                if MUSIC_HISTORY_FILE.exists():
                    MUSIC_HISTORY_FILE.unlink()
                temp_file.rename(MUSIC_HISTORY_FILE)
        except IOError as e:
            print(f"Chyba při ukládání music historie: {e}")
            temp_file = MUSIC_HISTORY_FILE.with_suffix('.tmp')
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except:
                    pass

    @staticmethod
    def add_entry(
        *,
        audio_url: str,
        filename: str,
        prompt: str,
        music_params: Optional[Dict] = None,
        created_at: Optional[str] = None,
    ) -> Dict:
        history = MusicHistoryManager._load_history()

        # Dedupe: kontrolovat prompt + parametry + filename
        if history and len(history) > 0:
            last_entry = history[0]
            if (last_entry.get("prompt") == prompt and
                last_entry.get("filename") == filename and
                last_entry.get("music_params") == (music_params or {})):
                # Všechno stejné, neukládat duplikát
                return last_entry

        if len(history) >= 1000:
            history = history[:999]

        entry = {
            "id": filename.replace(".wav", ""),
            "audio_url": audio_url,
            "filename": filename,
            "prompt": prompt,
            "music_params": music_params or {},
            "created_at": created_at or datetime.now().isoformat(),
        }

        history.insert(0, entry)
        MusicHistoryManager._save_history(history)
        return entry

    @staticmethod
    def get_history(limit: Optional[int] = None, offset: int = 0) -> List[Dict]:
        history = MusicHistoryManager._load_history()

        # Prune záznamy, které ukazují na neexistující soubory v outputs/
        try:
            before = len(history)
            filtered = []
            for entry in history:
                fn = entry.get("filename")
                if fn and (OUTPUTS_DIR / fn).exists():
                    filtered.append(entry)
            if len(filtered) != before:
                MusicHistoryManager._save_history(filtered)
                history = filtered
        except Exception:
            pass
        if limit is None:
            return history[offset:]
        return history[offset : offset + limit]

    @staticmethod
    def get_entry_by_id(entry_id: str) -> Optional[Dict]:
        history = MusicHistoryManager._load_history()
        for entry in history:
            if entry.get("id") == entry_id:
                return entry
        return None

    @staticmethod
    def delete_entry(entry_id: str) -> bool:
        history = MusicHistoryManager._load_history()
        original_length = len(history)
        history = [entry for entry in history if entry.get("id") != entry_id]
        if len(history) < original_length:
            MusicHistoryManager._save_history(history)
            return True
        return False

    @staticmethod
    def clear_history() -> int:
        history = MusicHistoryManager._load_history()
        count = len(history)
        MusicHistoryManager._save_history([])
        return count

    @staticmethod
    def get_stats() -> Dict:
        history = MusicHistoryManager._load_history()
        return {
            "total_entries": len(history),
            "oldest_entry": history[-1]["created_at"] if history else None,
            "newest_entry": history[0]["created_at"] if history else None,
        }



