"""
History router - endpointy pro TTS historii
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException

from backend.history_manager import HistoryManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("")
async def get_history(limit: Optional[int] = None, offset: int = 0):
    """Vrátí historii TTS generování."""
    try:
        history = HistoryManager.get_history(limit=limit, offset=offset)
        stats = HistoryManager.get_stats()
        return {"history": history, "stats": stats, "limit": limit, "offset": offset}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při načítání historie: {str(e)}")


@router.get("/{entry_id}")
async def get_history_entry(entry_id: str):
    """Vrátí konkrétní záznam z historie."""
    try:
        entry = HistoryManager.get_entry_by_id(entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Záznam nenalezen")
        return entry
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při načítání záznamu: {str(e)}")


@router.delete("/{entry_id}")
async def delete_history_entry(entry_id: str):
    """Smaže konkrétní záznam z historie."""
    try:
        success = HistoryManager.delete_entry(entry_id)
        if not success:
            raise HTTPException(status_code=404, detail="Záznam nenalezen")
        return {"success": True, "message": "Záznam smazán"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při mazání záznamu: {str(e)}")


@router.delete("")
async def clear_history():
    """Vymaže celou historii."""
    try:
        count = HistoryManager.clear_history()
        return {"success": True, "message": f"Historie vymazána ({count} záznamů)"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při mazání historie: {str(e)}")

