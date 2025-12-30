"""
Prompts history router - endpointy pro historii textových promptů
"""
from typing import Optional
from fastapi import APIRouter, HTTPException

from backend.xtts_prompts_history_manager import XTTSPromptsHistoryManager
from backend.f5tts_prompts_history_manager import F5TTSPromptsHistoryManager
from backend.f5tts_sk_prompts_history_manager import F5TTSSKPromptsHistoryManager

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


# XTTS Prompts History
@router.get("/xtts/history")
async def get_xtts_prompts_history(limit: Optional[int] = None, offset: int = 0):
    """Získá historii XTTS promptů"""
    try:
        history = XTTSPromptsHistoryManager.get_history(limit=limit, offset=offset)
        stats = XTTSPromptsHistoryManager.get_stats()
        return {"history": history, "stats": stats, "limit": limit, "offset": offset}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při načítání XTTS prompts historie: {str(e)}")


@router.get("/xtts/history/{entry_id}")
async def get_xtts_prompt_entry(entry_id: str):
    """Získá konkrétní XTTS prompt záznam"""
    try:
        entry = XTTSPromptsHistoryManager.get_entry_by_id(entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Záznam nenalezen")
        return entry
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při načítání záznamu: {str(e)}")


@router.delete("/xtts/history/{entry_id}")
async def delete_xtts_prompt_entry(entry_id: str):
    """Smaže XTTS prompt záznam"""
    try:
        success = XTTSPromptsHistoryManager.delete_entry(entry_id)
        if not success:
            raise HTTPException(status_code=404, detail="Záznam nenalezen")
        return {"success": True, "message": "Záznam smazán"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při mazání záznamu: {str(e)}")


@router.delete("/xtts/history")
async def clear_xtts_prompts_history():
    """Vymaže celou XTTS prompts historii"""
    try:
        count = XTTSPromptsHistoryManager.clear_history()
        return {"success": True, "deleted_count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při mazání historie: {str(e)}")


# F5-TTS Prompts History
@router.get("/f5tts/history")
async def get_f5tts_prompts_history(limit: Optional[int] = None, offset: int = 0):
    """Získá historii F5-TTS promptů"""
    try:
        history = F5TTSPromptsHistoryManager.get_history(limit=limit, offset=offset)
        stats = F5TTSPromptsHistoryManager.get_stats()
        return {"history": history, "stats": stats, "limit": limit, "offset": offset}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při načítání F5-TTS prompts historie: {str(e)}")


@router.get("/f5tts/history/{entry_id}")
async def get_f5tts_prompt_entry(entry_id: str):
    """Získá konkrétní F5-TTS prompt záznam"""
    try:
        entry = F5TTSPromptsHistoryManager.get_entry_by_id(entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Záznam nenalezen")
        return entry
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při načítání záznamu: {str(e)}")


@router.delete("/f5tts/history/{entry_id}")
async def delete_f5tts_prompt_entry(entry_id: str):
    """Smaže F5-TTS prompt záznam"""
    try:
        success = F5TTSPromptsHistoryManager.delete_entry(entry_id)
        if not success:
            raise HTTPException(status_code=404, detail="Záznam nenalezen")
        return {"success": True, "message": "Záznam smazán"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při mazání záznamu: {str(e)}")


@router.delete("/f5tts/history")
async def clear_f5tts_prompts_history():
    """Vymaže celou F5-TTS prompts historii"""
    try:
        count = F5TTSPromptsHistoryManager.clear_history()
        return {"success": True, "deleted_count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při mazání historie: {str(e)}")


# F5-TTS-SK Prompts History
@router.get("/f5tts-sk/history")
async def get_f5tts_sk_prompts_history(limit: Optional[int] = None, offset: int = 0):
    """Získá historii F5-TTS-SK promptů"""
    try:
        history = F5TTSSKPromptsHistoryManager.get_history(limit=limit, offset=offset)
        stats = F5TTSSKPromptsHistoryManager.get_stats()
        return {"history": history, "stats": stats, "limit": limit, "offset": offset}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při načítání F5-TTS-SK prompts historie: {str(e)}")


@router.get("/f5tts-sk/history/{entry_id}")
async def get_f5tts_sk_prompt_entry(entry_id: str):
    """Získá konkrétní F5-TTS-SK prompt záznam"""
    try:
        entry = F5TTSSKPromptsHistoryManager.get_entry_by_id(entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Záznam nenalezen")
        return entry
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při načítání záznamu: {str(e)}")


@router.delete("/f5tts-sk/history/{entry_id}")
async def delete_f5tts_sk_prompt_entry(entry_id: str):
    """Smaže F5-TTS-SK prompt záznam"""
    try:
        success = F5TTSSKPromptsHistoryManager.delete_entry(entry_id)
        if not success:
            raise HTTPException(status_code=404, detail="Záznam nenalezen")
        return {"success": True, "message": "Záznam smazán"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při mazání záznamu: {str(e)}")


@router.delete("/f5tts-sk/history")
async def clear_f5tts_sk_prompts_history():
    """Vymaže celou F5-TTS-SK prompts historii"""
    try:
        count = F5TTSSKPromptsHistoryManager.clear_history()
        return {"success": True, "deleted_count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při mazání historie: {str(e)}")

