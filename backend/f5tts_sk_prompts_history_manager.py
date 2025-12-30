"""
Samostatná historie promptů pro F5-TTS-SK (slovenské slovo).

Ukládá do BASE_DIR/f5tts_sk_prompts_history.json, nezávisle na historii WAV souborů.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from backend.config import BASE_DIR

F5TTS_SK_PROMPTS_HISTORY_FILE = BASE_DIR / "f5tts_sk_prompts_history.json"


class F5TTSSKPromptsHistoryManager:
    @staticmethod
    def _load_history() -> List[Dict]:
        if not F5TTS_SK_PROMPTS_HISTORY_FILE.exists():
            return []
        try:
            with open(F5TTS_SK_PROMPTS_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    @staticmethod
    def _save_history(history: List[Dict]) -> None:
        """Uloží historii atomicky (write temp + rename)"""
        try:
            temp_file = F5TTS_SK_PROMPTS_HISTORY_FILE.with_suffix('.tmp')
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())

            if temp_file.exists():
                if F5TTS_SK_PROMPTS_HISTORY_FILE.exists():
                    F5TTS_SK_PROMPTS_HISTORY_FILE.unlink()
                temp_file.rename(F5TTS_SK_PROMPTS_HISTORY_FILE)
        except IOError as e:
            print(f"Chyba při ukládání F5-TTS-SK prompts historie: {e}")
            temp_file = F5TTS_SK_PROMPTS_HISTORY_FILE.with_suffix('.tmp')
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except:
                    pass

    @staticmethod
    def add_entry(
        *,
        prompt: str,
        tts_params: Optional[Dict] = None,
        created_at: Optional[str] = None,
    ) -> Dict:
        history = F5TTSSKPromptsHistoryManager._load_history()

        # Dedupe: kontrolovat, zda už existuje stejný prompt (s tolerancí na whitespace)
        prompt_normalized = prompt.strip()
        if history and len(history) > 0:
            existing_entry = next(
                (entry for entry in history if entry.get("prompt", "").strip() == prompt_normalized),
                None
            )
            if existing_entry:
                # Stejný prompt - aktualizovat čas a parametry
                existing_entry["created_at"] = created_at or datetime.now().isoformat()
                if tts_params:
                    existing_entry["tts_params"] = tts_params
                F5TTSSKPromptsHistoryManager._save_history(history)
                return existing_entry

        if len(history) >= 1000:
            history = history[:999]

        entry = {
            "id": f"f5tts_sk_prompt_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            "prompt": prompt,
            "tts_params": tts_params or {},
            "created_at": created_at or datetime.now().isoformat(),
        }

        history.insert(0, entry)
        F5TTSSKPromptsHistoryManager._save_history(history)
        return entry

    @staticmethod
    def get_history(limit: Optional[int] = None, offset: int = 0) -> List[Dict]:
        history = F5TTSSKPromptsHistoryManager._load_history()
        if limit is None:
            return history[offset:]
        return history[offset : offset + limit]

    @staticmethod
    def get_entry_by_id(entry_id: str) -> Optional[Dict]:
        history = F5TTSSKPromptsHistoryManager._load_history()
        for entry in history:
            if entry.get("id") == entry_id:
                return entry
        return None

    @staticmethod
    def delete_entry(entry_id: str) -> bool:
        history = F5TTSSKPromptsHistoryManager._load_history()
        original_length = len(history)
        history = [entry for entry in history if entry.get("id") != entry_id]
        if len(history) < original_length:
            F5TTSSKPromptsHistoryManager._save_history(history)
            return True
        return False

    @staticmethod
    def clear_history() -> int:
        history = F5TTSSKPromptsHistoryManager._load_history()
        count = len(history)
        F5TTSSKPromptsHistoryManager._save_history([])
        return count

    @staticmethod
    def get_stats() -> Dict:
        history = F5TTSSKPromptsHistoryManager._load_history()
        return {
            "total_entries": len(history),
            "oldest_entry": history[-1]["created_at"] if history else None,
            "newest_entry": history[0]["created_at"] if history else None,
        }

