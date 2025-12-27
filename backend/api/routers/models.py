"""
Models router - endpointy pro status modelů
"""
import logging
from fastapi import APIRouter

from backend.api.dependencies import tts_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("/status")
async def get_model_status():
    """Vrátí status modelu"""
    return tts_engine.get_status()

