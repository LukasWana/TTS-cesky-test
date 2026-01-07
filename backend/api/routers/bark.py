"""
Bark router - endpointy pro Bark generování
"""
import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Form, File, HTTPException, UploadFile

from backend.api.dependencies import bark_engine
from backend.api.resolvers.voice_resolver import resolve_voice_file
from backend.progress_manager import ProgressManager
from backend.bark_history_manager import BarkHistoryManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bark", tags=["bark"])


@router.post("/generate")
async def generate_bark(
    text: str = Form(...),
    job_id: str = Form(None),
    model_size: str = Form("small"),
    mode: str = Form("auto"),
    offload_cpu: bool = Form(False),
    temperature: float = Form(0.7),
    seed: int = Form(None),
    duration: float = Form(None),
    target_headroom_db: str = Form(None),
    voice_file: UploadFile = File(None),
    demo_voice: str = Form(None),
):
    """
    Generuje audio pomocí Bark modelu (řeč, hudba, zvuky).
    """
    import anyio

    try:
        if job_id:
            ProgressManager.start(job_id, meta={"endpoint": "/api/bark/generate", "text_length": len(text or "")})

        if not text or len(text.strip()) == 0:
            raise HTTPException(status_code=400, detail="Text je prázdný")

        if model_size not in ("small", "large"):
            model_size = "small"

        mode_clean = (mode or "auto").strip().lower()
        if mode_clean not in ("auto", "full", "mixed", "small"):
            mode_clean = "auto"

        duration_s = None
        if duration is not None:
            duration_s = float(duration)
            if duration_s < 1.0 or duration_s > 120.0:
                raise HTTPException(status_code=400, detail="Délka musí být mezi 1 a 120 sekundami")

        # Parsování target_headroom_db
        target_headroom_db_value = None
        if target_headroom_db is not None and target_headroom_db.strip():
            try:
                target_headroom_db_value = float(target_headroom_db)
                if not (-128.0 <= target_headroom_db_value <= 0.0):
                    raise HTTPException(
                        status_code=400,
                        detail="target_headroom_db musí být mezi -128.0 a 0.0 dB",
                    )
            except ValueError:
                target_headroom_db_value = None

        # Resolvování voice souboru pro history_prompt (klonování hlasu)
        history_prompt_path = None
        if voice_file or demo_voice:
            try:
                # Použijeme resolve_voice_file helper (podporuje upload i demo)
                # Pro Bark použijeme "en" jako default jazyk (Bark je primárně anglický)
                speaker_wav, _ = await resolve_voice_file(
                    voice_file=voice_file,
                    demo_voice=demo_voice,
                    lang="en",  # Bark je primárně anglický model
                )
                if speaker_wav and Path(speaker_wav).exists():
                    history_prompt_path = speaker_wav
                    logger.info(f"[Bark] Používám referenční hlas: {history_prompt_path}")
            except HTTPException:
                # Pokud není hlas zadán nebo neexistuje, použije se výchozí (None)
                logger.info("[Bark] Žádný referenční hlas, použije se výchozí hlas modelu")
                history_prompt_path = None
            except Exception as e:
                logger.warning(f"[Bark] Chyba při resolvování hlasu: {e}, použije se výchozí hlas")
                history_prompt_path = None

        out_path = await anyio.to_thread.run_sync(
            lambda: bark_engine.generate(
                text=text,
                model_size=model_size,
                model_mode=mode_clean,
                offload_cpu=bool(offload_cpu),
                temperature=float(temperature) if temperature else 0.7,
                seed=int(seed) if seed else None,
                duration_s=duration_s,
                job_id=job_id,
                target_headroom_db=target_headroom_db_value,
                history_prompt=history_prompt_path,
            )
        )

        filename = Path(out_path).name
        audio_url = f"/api/audio/{filename}"

        logger.info(f"[Bark] Ukládám do historie: {filename}")
        BarkHistoryManager.add_entry(
            audio_url=audio_url,
            filename=filename,
            prompt=text,
            bark_params={
                "model_size": model_size,
                "mode": mode_clean,
                "offload_cpu": bool(offload_cpu),
                "temperature": float(temperature) if temperature else 0.7,
                "seed": int(seed) if seed else None,
                "duration": duration_s,
            },
        )

        if job_id:
            ProgressManager.update(job_id, percent=99, stage="final", message="Hotovo, posílám výsledek…")
            ProgressManager.done(job_id)

        logger.info(f"[Bark] Hotovo. Odesílám audio_url: {audio_url}")
        return {
            "success": True,
            "audio_url": audio_url,
            "filename": filename,
            "job_id": job_id,
        }

    except HTTPException:
        if job_id:
            ProgressManager.fail(job_id, "HTTPException")
        raise
    except Exception as e:
        msg = str(e)
        if job_id:
            ProgressManager.fail(job_id, msg)
        raise HTTPException(status_code=500, detail=f"Chyba při Bark: {msg}")


@router.get("/history")
async def get_bark_history(limit: Optional[int] = None, offset: int = 0):
    """Samostatná historie Bark výstupů."""
    try:
        history = BarkHistoryManager.get_history(limit=limit, offset=offset)
        stats = BarkHistoryManager.get_stats()
        return {"history": history, "stats": stats, "limit": limit, "offset": offset}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při načítání bark historie: {str(e)}")


@router.get("/history/{entry_id}")
async def get_bark_history_entry(entry_id: str):
    try:
        entry = BarkHistoryManager.get_entry_by_id(entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Záznam nenalezen")
        return entry
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při načítání záznamu: {str(e)}")


@router.delete("/history/{entry_id}")
async def delete_bark_history_entry(entry_id: str):
    try:
        success = BarkHistoryManager.delete_entry(entry_id)
        if not success:
            raise HTTPException(status_code=404, detail="Záznam nenalezen")
        return {"success": True, "message": "Záznam smazán"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při mazání záznamu: {str(e)}")


@router.delete("/history")
async def clear_bark_history():
    try:
        count = BarkHistoryManager.clear_history()
        return {"success": True, "message": f"Bark historie vymazána ({count} záznamů)"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při mazání bark historie: {str(e)}")

