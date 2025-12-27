"""
Progress router - endpointy pro progress tracking
"""
import json
import asyncio
import logging
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.progress_manager import ProgressManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["progress"])


@router.get("/tts/progress/{job_id}")
async def get_tts_progress(job_id: str):
    """Vrátí průběh generování pro daný job_id (pro polling z frontendu)."""
    info = ProgressManager.get(job_id)
    if not info:
        return {
            "job_id": job_id,
            "status": "pending",
            "percent": 0,
            "stage": "pending",
            "message": "Čekám na zahájení…",
            "eta_seconds": None,
            "error": None,
        }
    return info


@router.get("/tts/progress/{job_id}/stream")
async def stream_tts_progress(job_id: str):
    """
    Server-Sent Events (SSE) stream pro real-time progress updates.
    Frontend se připojí pomocí EventSource a dostane automatické aktualizace.
    """
    async def event_generator():
        last_percent = -1
        last_updated = None

        while True:
            try:
                info = ProgressManager.get(job_id)

                if not info:
                    pending_data = {
                        'job_id': job_id,
                        'status': 'pending',
                        'percent': 0,
                        'stage': 'pending',
                        'message': 'Čekám na zahájení…',
                        'eta_seconds': None,
                        'error': None,
                    }
                    yield f"data: {json.dumps(pending_data)}\n\n"
                    await asyncio.sleep(0.5)
                    continue

                status = info.get("status", "running")
                percent = info.get("percent", 0)
                updated_at = info.get("updated_at")

                if percent != last_percent or updated_at != last_updated:
                    yield f"data: {json.dumps(info)}\n\n"
                    last_percent = percent
                    last_updated = updated_at

                if status in ("done", "error"):
                    yield f"data: {json.dumps(info)}\n\n"
                    break

                await asyncio.sleep(0.2)
            except asyncio.CancelledError:
                break
            except Exception as e:
                error_data = {
                    'job_id': job_id,
                    'status': 'error',
                    'error': str(e),
                }
                yield f"data: {json.dumps(error_data)}\n\n"
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/music/progress/{job_id}")
async def get_music_progress(job_id: str):
    """Vrátí průběh generování hudby pro daný job_id (polling)."""
    info = ProgressManager.get(job_id)
    if not info:
        return {
            "job_id": job_id,
            "status": "pending",
            "percent": 0,
            "stage": "pending",
            "message": "Čekám na zahájení…",
            "eta_seconds": None,
            "error": None,
        }
    return info


@router.get("/music/progress/{job_id}/stream")
async def stream_music_progress(job_id: str):
    """SSE stream pro real-time progress updates pro MusicGen."""
    async def event_generator():
        last_percent = -1
        last_updated = None

        while True:
            try:
                info = ProgressManager.get(job_id)
                if not info:
                    pending_data = {
                        "job_id": job_id,
                        "status": "pending",
                        "percent": 0,
                        "stage": "pending",
                        "message": "Čekám na zahájení…",
                        "eta_seconds": None,
                        "error": None,
                    }
                    yield f"data: {json.dumps(pending_data)}\n\n"
                    await asyncio.sleep(0.5)
                    continue

                status = info.get("status", "running")
                percent = info.get("percent", 0)
                updated_at = info.get("updated_at")

                if percent != last_percent or updated_at != last_updated:
                    yield f"data: {json.dumps(info)}\n\n"
                    last_percent = percent
                    last_updated = updated_at

                if status in ("done", "error"):
                    yield f"data: {json.dumps(info)}\n\n"
                    break

                await asyncio.sleep(0.2)
            except asyncio.CancelledError:
                break
            except Exception as e:
                yield f"data: {json.dumps({'job_id': job_id, 'status': 'error', 'error': str(e)})}\n\n"
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/bark/progress/{job_id}")
async def get_bark_progress(job_id: str):
    """Vrátí průběh generování Bark pro daný job_id (polling)."""
    info = ProgressManager.get(job_id)
    if not info:
        return {
            "job_id": job_id,
            "status": "pending",
            "percent": 0,
            "stage": "pending",
            "message": "Čekám na zahájení…",
            "eta_seconds": None,
            "error": None,
        }
    return info


@router.get("/bark/progress/{job_id}/stream")
async def stream_bark_progress(job_id: str):
    """SSE stream pro real-time progress updates pro Bark."""
    async def event_generator():
        last_percent = -1
        last_updated = None

        while True:
            try:
                info = ProgressManager.get(job_id)
                if not info:
                    pending_data = {
                        "job_id": job_id,
                        "status": "pending",
                        "percent": 0,
                        "stage": "pending",
                        "message": "Čekám na zahájení…",
                        "eta_seconds": None,
                        "error": None,
                    }
                    yield f"data: {json.dumps(pending_data)}\n\n"
                    await asyncio.sleep(0.5)
                    continue

                status = info.get("status", "running")
                percent = info.get("percent", 0)
                updated_at = info.get("updated_at")

                if percent != last_percent or updated_at != last_updated:
                    yield f"data: {json.dumps(info)}\n\n"
                    last_percent = percent
                    last_updated = updated_at

                if status in ("done", "error"):
                    yield f"data: {json.dumps(info)}\n\n"
                    break

                await asyncio.sleep(0.2)
            except asyncio.CancelledError:
                break
            except Exception as e:
                yield f"data: {json.dumps({'job_id': job_id, 'status': 'error', 'error': str(e)})}\n\n"
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

