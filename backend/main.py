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
from colorama import init, Fore, Style

# Inicializace colorama pro Windows (automaticky detekuje, zda je potřeba)
# strip=False zajišťuje, že ANSI escape sekvence nebudou odstraněny
# convert=True převádí ANSI na Windows API volání pro lepší kompatibilitu
init(autoreset=True, strip=False, convert=True)

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

    # Test barevného výstupu
    print(f"{Fore.GREEN}✓ Colorama inicializováno{Style.RESET_ALL}")
    print(f"{Fore.CYAN}DEBUG{Style.RESET_ALL} | {Fore.GREEN}INFO{Style.RESET_ALL} | {Fore.YELLOW}WARNING{Style.RESET_ALL} | {Fore.RED}ERROR{Style.RESET_ALL} | {Fore.MAGENTA}ACCESS{Style.RESET_ALL}")

    # Zajistíme, že log adresář existuje
    base_dir = Path(__file__).parent.parent
    logs_dir = base_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    log_file = logs_dir / "backend.log"

    # Custom formatter s barvami
    class ColoredFormatter(logging.Formatter):
        """Formátovač logů s barevným výstupem"""
        COLORS = {
            'DEBUG': Fore.CYAN,
            'INFO': Fore.GREEN,
            'WARNING': Fore.YELLOW,
            'ERROR': Fore.RED,
            'CRITICAL': Fore.RED + Style.BRIGHT,
        }

        def format(self, record):
            # Uložit původní hodnoty
            original_levelname = record.levelname
            original_msg = record.getMessage()

            # Získat barvu pro úroveň logu
            log_color = self.COLORS.get(record.levelname, '')
            reset_color = Style.RESET_ALL

            # Formátovat zprávu normálně
            formatted = super().format(record)

            # Aplikovat barvy na formátovaný výstup
            colored_formatted = f"{log_color}{formatted}{reset_color}"

            return colored_formatted

    # Nastavení logování s UTF-8 podporou pro Windows
    # Vytvoření handlerů s error handlingem
    handlers = []

    # Pokus o vytvoření file handleru (může selhat, pokud je soubor otevřený)
    try:
        file_handler = logging.FileHandler(str(log_file), encoding='utf-8', mode='a')  # Append mode
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
        handlers.append(file_handler)
    except (PermissionError, OSError) as e:
        # Pokud nelze otevřít log soubor (např. je otevřený v jiném procesu), pouze vypíšeme varování
        print(f"{Fore.YELLOW}WARNING: Nelze otevřít log soubor {log_file}: {e}")
        print(f"{Fore.YELLOW}Logy budou zobrazovány pouze v konzoli.{Style.RESET_ALL}")

    # Pokud máme nějaké handlery, použijeme je, jinak použijeme výchozí konfiguraci
    if handlers:
        logging.basicConfig(
            level=getattr(logging, CONFIG_LOG_LEVEL.upper(), logging.INFO),
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=handlers
        )
    else:
        # Pokud nelze vytvořit file handler, použijeme pouze výchozí konfiguraci
        logging.basicConfig(
            level=getattr(logging, CONFIG_LOG_LEVEL.upper(), logging.INFO),
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    # Přidat barevný handler pro konzoli
    console_handler = logging.StreamHandler(sys.stdout)  # Změna z stderr na stdout
    console_handler.setFormatter(ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    logging.getLogger().addHandler(console_handler)

    # Získání cesty k backend adresáři pro reload
    # Uvicorn potřebuje absolutní cesty pro správnou detekci změn
    backend_dir = Path(__file__).parent.absolute()

    # Uvicorn log config s UTF-8 podporou a barevným výstupem
    class UvicornColoredFormatter(logging.Formatter):
        """Barevný formátovač pro uvicorn logy"""
        COLORS = {
            'DEBUG': Fore.CYAN,
            'INFO': Fore.BLUE,
            'WARNING': Fore.YELLOW,
            'ERROR': Fore.RED,
            'CRITICAL': Fore.RED + Style.BRIGHT,
        }

        def format(self, record):
            # Uložit původní hodnoty
            original_levelname = record.levelname

            # Získat barvu pro úroveň logu
            log_color = self.COLORS.get(record.levelname, '')
            reset_color = Style.RESET_ALL

            # Pro uvicorn access logy použij jinou barvu
            if 'uvicorn.access' in record.name:
                log_color = Fore.MAGENTA
                record.levelname = 'ACCESS'

            # Formátovat zprávu normálně
            formatted = super().format(record)

            # Aplikovat barvy na formátovaný výstup
            colored_formatted = f"{log_color}{formatted}{reset_color}"

            # Obnovit původní levelname (pro případné další formátování)
            record.levelname = original_levelname

            return colored_formatted

    LOGGING_CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": UvicornColoredFormatter,
                "format": "%(asctime)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",  # Změna z stderr na stdout
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
