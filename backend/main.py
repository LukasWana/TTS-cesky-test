"""
FastAPI aplikace pro XTTS-v2 Demo
"""
import sys
import os
import asyncio
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
from uvicorn.logging import AccessFormatter
from colorama import init, Fore, Style

# Inicializace colorama co nejdříve pro barevný výstup v konzoli
# autoreset=True zajistí, že po každém printu se barva vrátí na výchozí
# strip=False zajistí, že ANSI sekvence zůstanou zachovány
# convert=None (výchozí) nebo vynechání automaticky detekuje terminál (lepší pro moderní Windows)
init(autoreset=True, strip=False)

print(f"{Fore.CYAN}[DEBUG] App initialization started...{Style.RESET_ALL}")

# Cesta k logům a základní nastavení logování
base_dir = Path(__file__).parent.parent
logs_dir = base_dir / "logs"
logs_dir.mkdir(exist_ok=True)
log_file = logs_dir / "backend.log"

# Importy, které potřebují config
from backend.config import API_HOST, API_PORT, LOG_LEVEL as CONFIG_LOG_LEVEL

print(f"{Fore.CYAN}[DEBUG] Importing middleware...{Style.RESET_ALL}")
from backend.api.middleware import setup_cors, setup_not_found_cache

print(f"{Fore.CYAN}[DEBUG] Importing dependencies...{Style.RESET_ALL}")
from backend.api.dependencies import check_f5_tts_availability

print(f"{Fore.CYAN}[DEBUG] Importing routers...{Style.RESET_ALL}")
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

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler pro startup a shutdown"""
    # Startup
    try:
        print(f"{Fore.GREEN}✓ Backend startup in progress...{Style.RESET_ALL}")
        # XTTS model nyní načítáme "lazy" až při prvním požadavku v /api/tts/generate
        logger.info("Backend startup: ready (models will be loaded on demand)")
        # Ověření F5-TTS (neblokující, pouze informativní)
        asyncio.create_task(check_f5_tts_availability())

        # Jasný indikátor, že backend běží
        print(f"{Fore.GREEN}{Style.BRIGHT}🚀 BACKEND IS READY AND RUNNING AT http://{API_HOST}:{API_PORT}{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}--- Initialization log ends here ---{Style.RESET_ALL}")
    except Exception as e:
        logger.error(f"Startup error: {str(e)}")
        print(f"{Fore.RED}[ERROR] Startup failed: {e}{Style.RESET_ALL}")

    yield  # Aplikace běží zde

    # Shutdown (volitelné, pokud potřebujete cleanup)
    print(f"{Fore.YELLOW}Backend shutting down...{Style.RESET_ALL}")

# Inicializace FastAPI
app = FastAPI(title="XTTS-v2 Demo", version="1.0.0", lifespan=lifespan)

# CORS middleware
setup_cors(app)

# 404 cache middleware (pro /api/audio/* endpointy)
setup_not_found_cache(app)

# Kontrola existence frontendu
frontend_path = Path(__file__).parent.parent / "frontend" / "dist"
frontend_index = frontend_path / "index.html"
frontend_exists = frontend_index.exists()

# Serve static files (frontend) - pouze pokud existuje build
# Poznámka: Statické soubory budou servovány s nižší prioritou než explicitní routes
# API routes a root route mají prioritu před static files
if frontend_exists:
    # Mount /assets pro JS/CSS soubory z Vite buildu
    assets_path = frontend_path / "assets"
    if assets_path.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")

# Registrace routerů (musí být před root route pro prioritu)
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
    """Root endpoint - servuje frontend pokud existuje, jinak JSON"""
    if frontend_exists:
        return FileResponse(str(frontend_index), media_type="text/html")
    return {"message": "XTTS-v2 Demo API", "version": "1.0.0"}

# Catch-all route pro SPA routing a statické soubory (musí být na konci, před uvicorn.run)
# Servuje index.html pro všechny routes, které nezačínají /api
@app.get("/{full_path:path}")
async def serve_spa(full_path: str, request: Request):
    """Catch-all route pro SPA - servuje index.html pro ne-API routes a statické soubory"""
    # Pokud route začíná /api, vrátíme 404 (mělo by být zachyceno API routes)
    if full_path.startswith("api/"):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not found")

    # Pokud frontend neexistuje, vrátíme 404
    if not frontend_exists:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not found")

    # Zkusit servovat statický soubor z frontend/dist (favicon.svg, atd.)
    static_file = frontend_path / full_path
    if static_file.exists() and static_file.is_file():
        # Zjistit MIME type podle přípony
        if full_path.endswith(".svg"):
            return FileResponse(str(static_file), media_type="image/svg+xml")
        elif full_path.endswith(".png"):
            return FileResponse(str(static_file), media_type="image/png")
        elif full_path.endswith(".jpg") or full_path.endswith(".jpeg"):
            return FileResponse(str(static_file), media_type="image/jpeg")
        elif full_path.endswith(".ico"):
            return FileResponse(str(static_file), media_type="image/x-icon")
        else:
            return FileResponse(str(static_file))

    # Pro všechny ostatní routes servuj index.html (SPA routing)
    return FileResponse(str(frontend_index), media_type="text/html")

# Formátovače logů
class ColoredFormatter(logging.Formatter):
    """Formátovač logů s barevným výstupem kompatibilní s uvicorn"""
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT,
    }

    def format(self, record):
        # Základní barevná úprava levelu
        log_color = self.COLORS.get(record.levelname, '')
        reset_color = Style.RESET_ALL

        # Předat kopii recordu pro formátování (abychom neměnili originál trvale)
        record_copy = logging.makeLogRecord(record.__dict__)
        record_copy.levelname = f"{log_color}{record_copy.levelname}{reset_color}"

        return super().format(record_copy)

class ColoredAccessFormatter(AccessFormatter):
    """Barevný access formátovač založený na uvicorn AccessFormatter"""

    def format(self, record):
        # Nejdřív necháme uvicorn AccessFormatter zpracovat záznam (vytvoří správné atributy)
        formatted = super().format(record)

        # Pak přidáme barvu
        return f"{Fore.MAGENTA}{formatted}{Style.RESET_ALL}"

def get_logging_config():
    """Vrací konfiguraci logování pro uvicorn"""
    level = CONFIG_LOG_LEVEL.upper()

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": ColoredFormatter,
                "format": "%(asctime)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "access": {
                "()": ColoredAccessFormatter,
                "format": "%(asctime)s - %(levelname)s - %(client_addr)s - \"%(request_line)s\" %(status_code)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
            "access_console": {
                "formatter": "access",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "formatter": "default",
                "class": "logging.FileHandler",
                "filename": str(log_file),
                "encoding": "utf-8",
                "mode": "a",
            },
        },
        "loggers": {
            "": {"handlers": ["console", "file"], "level": level},
            "uvicorn": {"handlers": ["console", "file"], "level": level, "propagate": False},
            "uvicorn.error": {"handlers": ["console", "file"], "level": level, "propagate": False},
            "uvicorn.access": {"handlers": ["access_console", "file"], "level": level, "propagate": False},
        },
    }

if __name__ == "__main__":
    # Nastavení logování pomocí LOGGING_CONFIG pro uvicorn
    log_config = get_logging_config()

    print(f"{Fore.GREEN}✓ Colorama initialized{Style.RESET_ALL}")
    print(f"{Fore.CYAN}DEBUG{Style.RESET_ALL} | {Fore.GREEN}INFO{Style.RESET_ALL} | {Fore.YELLOW}WARNING{Style.RESET_ALL} | {Fore.RED}ERROR{Style.RESET_ALL} | {Fore.MAGENTA}ACCESS{Style.RESET_ALL}")
    print(f"{Fore.GREEN}[DEBUG] Starting uvicorn server on {API_HOST}:{API_PORT}{Style.RESET_ALL}")

    try:
        # Používáme app instanci a předáváme log_config
        uvicorn.run(
            app,
            host=API_HOST,
            port=API_PORT,
            reload=False,
            log_config=log_config,
        )
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Error starting uvicorn: {e}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


