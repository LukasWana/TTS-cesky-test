"""
Jednoduchý in-memory progress tracker pro dlouhé operace (TTS generování).

Pozn.: Je to process-local (funguje pro 1 worker). Pro více workerů by bylo vhodné Redis.
"""

from __future__ import annotations

import time
import threading
from typing import Any, Dict, Optional


class ProgressManager:
    _lock = threading.Lock()
    _jobs: Dict[str, Dict[str, Any]] = {}

    # jak dlouho držet hotové joby v paměti (sekundy)
    TTL_SECONDS = 60 * 30  # 30 minut

    @classmethod
    def _now(cls) -> float:
        return time.time()

    @classmethod
    def _purge_expired(cls) -> None:
        now = cls._now()
        to_del = []
        for job_id, job in cls._jobs.items():
            updated_at = float(job.get("updated_at", job.get("started_at", now)))
            status = job.get("status")
            # mažeme jen hotové/neúspěšné + staré
            if status in ("done", "error") and (now - updated_at) > cls.TTL_SECONDS:
                to_del.append(job_id)
        for jid in to_del:
            cls._jobs.pop(jid, None)

    @classmethod
    def start(cls, job_id: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with cls._lock:
            cls._purge_expired()
            now = cls._now()
            cls._jobs[job_id] = {
                "job_id": job_id,
                "status": "running",  # running|done|error
                "percent": 0,
                "stage": "start",
                "message": "Zahajuji generování…",
                "started_at": now,
                "updated_at": now,
                "eta_seconds": None,
                "meta": meta or {},
                "error": None,
            }
            return dict(cls._jobs[job_id])

    @classmethod
    def update(
        cls,
        job_id: str,
        *,
        percent: Optional[float] = None,
        eta_seconds: Optional[int] = None,
        stage: Optional[str] = None,
        message: Optional[str] = None,
        meta_update: Optional[Dict[str, Any]] = None,
    ) -> None:
        with cls._lock:
            job = cls._jobs.get(job_id)
            if not job:
                return
            now = cls._now()

            if percent is not None:
                try:
                    p = float(percent)
                except Exception:
                    p = None
                if p is not None:
                    # monotonic: nikdy nesnižovat
                    old = float(job.get("percent", 0) or 0)
                    p = max(old, min(100.0, p))
                    job["percent"] = p

                    # jednoduché ETA (přibližné)
                    if p > 0 and eta_seconds is None:
                        elapsed = now - float(job.get("started_at", now))
                        job["eta_seconds"] = int(max(0.0, elapsed * (100.0 - p) / p))

            if eta_seconds is not None:
                try:
                    job["eta_seconds"] = int(max(0, int(eta_seconds)))
                except Exception:
                    pass

            if stage is not None:
                job["stage"] = str(stage)
            if message is not None:
                job["message"] = str(message)
            if meta_update:
                try:
                    job_meta = job.get("meta") or {}
                    job_meta.update(meta_update)
                    job["meta"] = job_meta
                except Exception:
                    pass

            job["updated_at"] = now

    @classmethod
    def done(cls, job_id: str) -> None:
        with cls._lock:
            job = cls._jobs.get(job_id)
            if not job:
                return
            job["status"] = "done"
            job["percent"] = 100
            job["stage"] = "done"
            job["message"] = "Hotovo."
            job["eta_seconds"] = 0
            job["updated_at"] = cls._now()

    @classmethod
    def fail(cls, job_id: str, error: str) -> None:
        with cls._lock:
            job = cls._jobs.get(job_id)
            if not job:
                return
            job["status"] = "error"
            job["stage"] = "error"
            job["message"] = "Chyba při generování."
            job["error"] = str(error)
            job["updated_at"] = cls._now()

    @classmethod
    def get(cls, job_id: str) -> Optional[Dict[str, Any]]:
        with cls._lock:
            cls._purge_expired()
            job = cls._jobs.get(job_id)
            return dict(job) if job else None


