"""
FastAPI aplikace pro XTTS-v2 Demo
"""
import sys
import os
import asyncio
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn

from backend.api.middleware import setup_cors
from backend.api.dependencies import check_f5_tts_availability
from backend.api.routers import (
    tts,
    music,
    bark,
    history,
    progress,
    voice,
    asr,
    audio,
    models,
)
from backend.config import API_HOST, API_PORT

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler pro startup a shutdown"""
    # Startup
    try:
        # XTTS model nyní načítáme "lazy" až při prvním požadavku v /api/tts/generate
        # To šetří VRAM (zejména pro 6GB karty), pokud chce uživatel generovat jen hudbu.
        logger.info("Backend startup: ready (models will be loaded on demand)")
        # Ověření F5-TTS (neblokující, pouze informativní)
        asyncio.create_task(check_f5_tts_availability())
    except Exception as e:
        logger.error(f"Startup error: {str(e)}")

    yield  # Aplikace běží zde

    # Shutdown (volitelné, pokud potřebujete cleanup)


# Inicializace FastAPI s lifespan
app = FastAPI(title="XTTS-v2 Demo", version="1.0.0", lifespan=lifespan)

# CORS middleware
setup_cors(app)

# Serve static files (frontend)
frontend_path = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

# Registrace routerů
app.include_router(tts.router)
app.include_router(music.router)
app.include_router(bark.router)
app.include_router(history.router)
app.include_router(progress.router)
app.include_router(voice.router)
app.include_router(asr.router)
app.include_router(audio.router)
app.include_router(models.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "XTTS-v2 Demo API", "version": "1.0.0"}


if __name__ == "__main__":
    import logging
    from pathlib import Path

    # Načteme LOG_LEVEL
    try:
        from backend.config import LOG_LEVEL as CONFIG_LOG_LEVEL
    except ImportError:
        try:
            from config import LOG_LEVEL as CONFIG_LOG_LEVEL
        except ImportError:
            CONFIG_LOG_LEVEL = "INFO"

    # Logger pro hlavní aplikaci
    logger = logging.getLogger(__name__)

    # Zajistíme, že log adresář existuje
    base_dir = Path(__file__).parent.parent
    logs_dir = base_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    log_file = logs_dir / "backend.log"

    # Nastavení logování s UTF-8 podporou pro Windows
    logging.basicConfig(
        level=getattr(logging, CONFIG_LOG_LEVEL.upper(), logging.INFO),
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(str(log_file), encoding='utf-8')  # Soubor s UTF-8
        ]
    )

    # Získání cesty k backend adresáři pro reload
    # Uvicorn potřebuje absolutní cesty pro správnou detekci změn
    backend_dir = Path(__file__).parent.absolute()

    # Uvicorn log config s UTF-8 podporou
    LOGGING_CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": CONFIG_LOG_LEVEL.upper()},
            "uvicorn.error": {"level": CONFIG_LOG_LEVEL.upper()},
            "uvicorn.access": {"handlers": ["default"], "level": CONFIG_LOG_LEVEL.upper()},
        },
    }

    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=False,  # Reload vypnut - způsoboval pády při změnách souborů
        log_config=LOGGING_CONFIG,
    )
