"""
Music router - endpointy pro MusicGen generování
"""
import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Form, HTTPException

from backend.api.dependencies import music_engine
from backend.progress_manager import ProgressManager
from backend.music_history_manager import MusicHistoryManager
from backend.ambience_library import pick_many, list_ambience
from backend.audio_mix_utils import load_audio, save_wav, make_loopable
import anyio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["music"])


@router.get("/music/ambience/list")
async def get_ambience_list():
    """Vrátí seznam dostupných ambience samplů podle kategorií."""
    try:
        return {
            "stream": [p.name for p in list_ambience("stream")],
            "birds": [p.name for p in list_ambience("birds")]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/musicgen/generate")
async def generate_music(
    prompt: str = Form(...),
    job_id: str = Form(None),
    duration: float = Form(12.0),
    temperature: float = Form(1.0),
    top_k: int = Form(250),
    top_p: float = Form(0.0),
    seed: int = Form(None),
    model: str = Form("small"),
    precision: str = Form("auto"),
    offload: bool = Form(False),
    max_vram_gb: float = Form(None),
    ambience: str = Form("none"),
    ambience_gain_db: float = Form(-18.0),
    ambience_seed: int = Form(None),
    ambience_file_stream: str = Form(None),
    ambience_file_birds: str = Form(None),
):
    """
    Generuje hudbu pomocí MusicGen (AudioCraft).
    """
    try:
        if job_id:
            ProgressManager.start(job_id, meta={"endpoint": "/api/musicgen/generate", "prompt_length": len(prompt or "")})

        loop_crossfade_s = 3.0
        gen_duration = min(30.0, float(duration) + loop_crossfade_s)

        out_path = await anyio.to_thread.run_sync(
            lambda: music_engine.generate(
                prompt,
                duration_s=gen_duration,
                temperature=temperature,
                top_k=top_k,
                top_p=top_p,
                seed=seed,
                model_size=model,
                precision=precision,
                enable_offload=bool(offload),
                max_vram_gb=float(max_vram_gb) if max_vram_gb is not None else None,
                job_id=job_id,
            )
        )

        filename = Path(out_path).name
        audio_url = f"/api/audio/{filename}"

        base = load_audio(out_path)
        if gen_duration > loop_crossfade_s:
            base = make_loopable(base, crossfade_ms=int(loop_crossfade_s * 1000))
            save_wav(base, out_path)

        warning = None
        ambience_clean = (ambience or "none").strip().lower()
        kinds = []
        if ambience_clean in ("stream", "birds"):
            kinds.append(ambience_clean)
        elif ambience_clean == "both":
            kinds = ["stream", "birds"]

        if kinds:
            try:
                ambience_files = []
                for kind in kinds:
                    if kind == "stream" and ambience_file_stream:
                        ambience_files.append(ambience_file_stream)
                    elif kind == "birds" and ambience_file_birds:
                        ambience_files.append(ambience_file_birds)
                    else:
                        picked = pick_many(kind, count=1, seed=ambience_seed)
                        if picked:
                            ambience_files.append(picked[0])

                if ambience_files:
                    from backend.audio_mix_utils import overlay as mix_overlay
                    for amb_file in ambience_files:
                        amb_audio = load_audio(amb_file)
                        base = mix_overlay(base, amb_audio, gain_db=ambience_gain_db)
                    save_wav(base, out_path)
            except Exception as e:
                warning = f"Ambience mix selhal: {str(e)}"
                logger.warning(warning)

        if job_id:
            ProgressManager.done(job_id)

        history_entry = MusicHistoryManager.add_entry(
            audio_url=audio_url,
            filename=filename,
            prompt=prompt,
            music_params={
                "duration": duration,
                "model": model,
                "seed": seed,
                "ambience": ambience_clean,
                "ambience_files": ambience_files if kinds else []
            }
        )

        return {
            "audio_url": audio_url,
            "filename": filename,
            "success": True,
            "job_id": job_id,
            "history_id": history_entry["id"],
            "warning": warning,
        }

    except HTTPException:
        if job_id:
            ProgressManager.fail(job_id, "HTTPException")
        raise
    except Exception as e:
        msg = str(e)
        if job_id:
            ProgressManager.fail(job_id, msg)
        raise HTTPException(status_code=500, detail=f"Chyba při MusicGen: {msg}")


@router.get("/music/history")
async def get_music_history(limit: Optional[int] = None, offset: int = 0):
    """Samostatná historie MusicGen výstupů."""
    try:
        history = MusicHistoryManager.get_history(limit=limit, offset=offset)
        stats = MusicHistoryManager.get_stats()
        return {"history": history, "stats": stats, "limit": limit, "offset": offset}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při načítání music historie: {str(e)}")


@router.get("/music/history/{entry_id}")
async def get_music_history_entry(entry_id: str):
    try:
        entry = MusicHistoryManager.get_entry_by_id(entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Záznam nenalezen")
        return entry
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při načítání záznamu: {str(e)}")


@router.delete("/music/history/{entry_id}")
async def delete_music_history_entry(entry_id: str):
    try:
        success = MusicHistoryManager.delete_entry(entry_id)
        if not success:
            raise HTTPException(status_code=404, detail="Záznam nenalezen")
        return {"success": True, "message": "Záznam smazán"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při mazání záznamu: {str(e)}")


@router.delete("/music/history")
async def clear_music_history():
    try:
        count = MusicHistoryManager.clear_history()
        return {"success": True, "message": f"Music historie vymazána ({count} záznamů)"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při mazání music historie: {str(e)}")

