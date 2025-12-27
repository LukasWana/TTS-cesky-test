"""
FastAPI aplikace pro XTTS-v2 Demo
"""
import sys
import os
import asyncio
import base64
import uuid
import time
import re
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn
import aiofiles
import anyio
from functools import lru_cache
from typing import Optional

# Potlačení deprecation warning z librosa (pkg_resources je zastaralé, ale knihovna ho ještě používá)
import warnings
warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated.*", category=UserWarning)
# Potlačení FutureWarning z huggingface_hub o resume_download
warnings.filterwarnings("ignore", message=".*resume_download.*", category=FutureWarning)
# Potlačení deprecation warning z PyTorch weight_norm (Bark/encodec používá zastaralé API)
warnings.filterwarnings("ignore", message=".*weight_norm is deprecated.*", category=UserWarning)

# Nastavení loggeru pro aplikaci s UTF-8 podporou
import logging
import sys

class ConsoleHandler(logging.StreamHandler):
    """Custom handler pro Windows konzoli s podporou českých znaků"""
    def __init__(self, stream=None):
        super().__init__(stream)
        # Nastavíme encoding pro Windows konzoli - ignorujeme problematické znaky
        if hasattr(self.stream, 'reconfigure'):
            try:
                self.stream.reconfigure(encoding='cp1252', errors='ignore')
            except Exception:
                pass

logger = logging.getLogger(__name__)

# Windows + librosa/numba: na některých sestavách padá numba ufunc (např. _phasor_angles) při pitch shifting.
# Vypneme JIT (bezpečnější, za cenu menší rychlosti pouze pro tyto operace).
if os.name == "nt":
    os.environ.setdefault("NUMBA_DISABLE_JIT", "1")

# Windows: zajisti UTF-8 pro výpisy (jinak mohou emoji/diakritika shodit proces na cp1252 konzoli).
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    from backend.progress_manager import ProgressManager
    from backend.tts_engine import XTTSEngine
    from backend.f5_tts_engine import F5TTSEngine
    from backend.f5_tts_slovak_engine import F5TTSSlovakEngine
    from backend.asr_engine import get_asr_engine
    from backend.audio_processor import AudioProcessor
    from backend.history_manager import HistoryManager
    from backend.youtube_downloader import (
        download_youtube_audio,
        validate_youtube_url,
        get_video_info,
        extract_video_id,
        sanitize_filename
    )
    from backend.config import (
        API_HOST,
        API_PORT,
        OUTPUTS_DIR,
        UPLOADS_DIR,
        DEMO_VOICES_DIR,
        DEMO_VOICES_CS_DIR,
        DEMO_VOICES_SK_DIR,
        MAX_TEXT_LENGTH,
        MIN_VOICE_DURATION,
        TTS_SPEED,
        TTS_TEMPERATURE,
        TTS_LENGTH_PENALTY,
        TTS_REPETITION_PENALTY,
        TTS_TOP_K,
        TTS_TOP_P,
        ENABLE_AUDIO_ENHANCEMENT,
        AUDIO_ENHANCEMENT_PRESET,
        ENABLE_BATCH_PROCESSING,
        LOG_LEVEL
    )
    from backend.musicgen_engine import MusicGenEngine
    from backend.music_history_manager import MusicHistoryManager
    from backend.bark_history_manager import BarkHistoryManager
    from backend.ambience_library import pick_many
    from backend.audio_mix_utils import load_audio, overlay as mix_overlay, save_wav, make_loopable
    from backend.bark_engine import BarkEngine
except ImportError:
    # Fallback pro spuštění z backend/ adresáře
    from progress_manager import ProgressManager
    from tts_engine import XTTSEngine
    from f5_tts_engine import F5TTSEngine
    from f5_tts_slovak_engine import F5TTSSlovakEngine
    from asr_engine import get_asr_engine
    from audio_processor import AudioProcessor
    from history_manager import HistoryManager
    from youtube_downloader import (
        download_youtube_audio,
        validate_youtube_url,
        get_video_info,
        extract_video_id,
        sanitize_filename
    )
    from musicgen_engine import MusicGenEngine
    from music_history_manager import MusicHistoryManager
    from bark_history_manager import BarkHistoryManager
    from ambience_library import pick_many
    from audio_mix_utils import load_audio, overlay as mix_overlay, save_wav
    from bark_engine import BarkEngine
    from config import (
        API_HOST,
        API_PORT,
        OUTPUTS_DIR,
        UPLOADS_DIR,
        DEMO_VOICES_DIR,
        MAX_TEXT_LENGTH,
        MIN_VOICE_DURATION,
        TTS_SPEED,
        TTS_TEMPERATURE,
        TTS_LENGTH_PENALTY,
        TTS_REPETITION_PENALTY,
        TTS_TOP_K,
        TTS_TOP_P,
        ENABLE_AUDIO_ENHANCEMENT,
        AUDIO_ENHANCEMENT_PRESET,
        ENABLE_BATCH_PROCESSING,
        LOG_LEVEL
    )

# Inicializace engine
tts_engine = XTTSEngine()
f5_tts_engine = F5TTSEngine()
f5_tts_slovak_engine = F5TTSSlovakEngine()
music_engine = MusicGenEngine()
bark_engine = BarkEngine()

# ASR (Whisper) – lazy singleton
asr_engine = get_asr_engine()

# Ověření dostupnosti F5-TTS CLI při startu (neblokující)
async def check_f5_tts_availability():
    """Ověří dostupnost F5-TTS CLI při startu"""
    try:
        await f5_tts_engine.load_model()
        logger.info("F5-TTS CLI je dostupné")
    except Exception as e:
        logger.info(f"F5-TTS není dostupné: {e}")
        logger.info("F5-TTS záložka bude dostupná až po instalaci: pip install f5-tts")


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
    # await tts_engine.cleanup()  # pokud máte cleanup metodu


# Inicializace FastAPI s lifespan
app = FastAPI(title="XTTS-v2 Demo", version="1.0.0", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    # Pro dev režim povolíme CORS široce, aby šly načítat WAVy přes WaveSurfer z FE na jiném portu (3000/5173/…).
    # (WaveSurfer používá fetch/XHR i <audio>, obojí vyžaduje správné CORS hlavičky.)
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (frontend)
frontend_path = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "XTTS-v2 Demo API", "version": "1.0.0"}


@app.post("/api/tts/generate")
async def generate_speech(
    text: str = Form(...),
    job_id: str = Form(None),
    voice_file: UploadFile = File(None),
    demo_voice: str = Form(None),
    speed: str = Form(None),  # Přijímáme jako string, protože Form může poslat string
    temperature: float = Form(None),
    length_penalty: float = Form(None),
    repetition_penalty: float = Form(None),
    top_k: int = Form(None),
    top_p: float = Form(None),
    quality_mode: str = Form(None),
    enhancement_preset: str = Form(None),
    enable_enhancement: str = Form(None),
    seed: int = Form(None),
    multi_pass: str = Form(None),
    multi_pass_count: int = Form(None),
    enable_vad: str = Form(None),
    enable_batch: str = Form(None),
    use_hifigan: str = Form(None),
    enable_normalization: str = Form(None),
    enable_denoiser: str = Form(None),
    enable_compressor: str = Form(None),
    enable_deesser: str = Form(None),
    enable_eq: str = Form(None),
    enable_trim: str = Form(None),
    enable_dialect_conversion: str = Form(None),
    dialect_code: str = Form(None),
    dialect_intensity: str = Form(None),
    # HiFi-GAN parametry
    hifigan_refinement_intensity: str = Form(None),
    hifigan_normalize_output: str = Form(None),
    hifigan_normalize_gain: str = Form(None),
    # Whisper efekt overrides (volitelné, pokud není quality_mode=whisper)
    enable_whisper: str = Form(None),
    whisper_intensity: str = Form(None),
    # Headroom override (volitelné)
    target_headroom_db: str = Form(None),
    # Reference voice quality gate / auto enhance
    auto_enhance_voice: str = Form(None),
    allow_poor_voice: str = Form(None),
):
    """
    Generuje řeč z textu

    Body:
        text: Text k syntéze (max 500 znaků)
        voice_file: Nahraný audio soubor (volitelné)
        demo_voice: Název demo hlasu (volitelné)
        speed: Rychlost řeči (0.5-2.0, výchozí: 1.0)
        temperature: Teplota pro sampling (0.0-1.0, výchozí: 0.7)
        length_penalty: Length penalty (výchozí: 1.0)
        repetition_penalty: Repetition penalty (výchozí: 2.0)
        top_k: Top-k sampling (výchozí: 50)
        top_p: Top-p sampling (výchozí: 0.85)
        quality_mode: Režim kvality (high_quality, natural, fast) - přepíše jednotlivé parametry
        enhancement_preset: Preset pro audio enhancement (high_quality, natural, fast)
        enable_enhancement: Zapnout/vypnout audio enhancement (true/false, výchozí: true)
        seed: Seed pro reprodukovatelnost generování (volitelné, pokud není zadán, použije se fixní seed 42)
    """
    try:
        # Zaregistruj job_id HNED na začátku (před validacemi), aby frontend mohl pollovat
        if job_id:
            ProgressManager.start(
                job_id,
                meta={
                    "text_length": len(text or ""),
                    "endpoint": "/api/tts/generate",
                },
            )

        # Lazy loading modelu XTTS
        if not tts_engine.is_loaded:
            if job_id:
                ProgressManager.update(job_id, percent=5, stage="load", message="Načítám XTTS model do VRAM…")
            await tts_engine.load_model()
        else:
            if job_id:
                ProgressManager.update(job_id, percent=10, stage="load", message="Model je připraven, začínám syntézu…")

        # --- Získání a validace všech parametrů na začátku ---

        # 1. Základní TTS parametry
        if speed is not None:
            try:
                tts_speed = float(speed) if isinstance(speed, str) else float(speed)
            except (ValueError, TypeError):
                tts_speed = TTS_SPEED
        else:
            tts_speed = TTS_SPEED

        tts_temperature = float(temperature) if temperature is not None else TTS_TEMPERATURE
        tts_length_penalty = float(length_penalty) if length_penalty is not None else TTS_LENGTH_PENALTY
        tts_repetition_penalty = float(repetition_penalty) if repetition_penalty is not None else TTS_REPETITION_PENALTY
        tts_top_k = int(top_k) if top_k is not None else TTS_TOP_K
        tts_top_p = float(top_p) if top_p is not None else TTS_TOP_P

        # 2. Nové parametry (Multi-pass, VAD, HiFi-GAN, atd.)
        use_multi_pass = (multi_pass.lower() == "true") if isinstance(multi_pass, str) else bool(multi_pass)
        multi_pass_count_value = int(multi_pass_count) if multi_pass_count is not None else 3

        enable_enh_flag = (enable_enhancement.lower() == "true") if isinstance(enable_enhancement, str) else ENABLE_AUDIO_ENHANCEMENT
        enable_vad_flag = (enable_vad.lower() == "true") if isinstance(enable_vad, str) else None
        use_batch_flag = (enable_batch.lower() == "true") if isinstance(enable_batch, str) else None
        use_hifigan_flag = (use_hifigan.lower() == "true") if isinstance(use_hifigan, str) else False

        # DŮLEŽITÉ: když tyto parametry z UI nepřijdou, NECHCEME je vynutit na True.
        # Předáme None -> rozhodnutí udělá tts_engine podle presetů / config defaultů.
        enable_norm = (enable_normalization.lower() == "true") if isinstance(enable_normalization, str) else None
        enable_den = (enable_denoiser.lower() == "true") if isinstance(enable_denoiser, str) else None
        enable_comp = (enable_compressor.lower() == "true") if isinstance(enable_compressor, str) else None
        enable_deess = (enable_deesser.lower() == "true") if isinstance(enable_deesser, str) else None
        enable_eq_flag = (enable_eq.lower() == "true") if isinstance(enable_eq, str) else None
        enable_trim_flag = (enable_trim.lower() == "true") if isinstance(enable_trim, str) else None

        # 3. Dialect conversion
        use_dialect = (enable_dialect_conversion.lower() == "true") if isinstance(enable_dialect_conversion, str) else False
        dialect_code_value = dialect_code if dialect_code and dialect_code != "standardni" else None
        try:
            dialect_intensity_value = float(dialect_intensity) if dialect_intensity else 1.0
        except (ValueError, TypeError):
            dialect_intensity_value = 1.0

        # --- Konec získávání parametrů ---

        # Validace textu
        if not text or len(text.strip()) == 0:
            raise HTTPException(status_code=400, detail="Text je prázdný")

        # Automatická detekce multi-lang/speaker anotací
        # Pokud text obsahuje syntaxi [lang:speaker] nebo [lang], použij multi-lang endpoint
        multi_lang_pattern = re.compile(r'\[(\w+)(?::([^\]]+))?\]')
        has_multi_lang_annotations = bool(multi_lang_pattern.search(text))

        if has_multi_lang_annotations:
            # Přesměruj na multi-lang zpracování
            logger.info(f"Detekovány multi-lang/speaker anotace v textu, používám multi-lang generování (multi_pass={use_multi_pass})")
            # Zpracuj výchozího mluvčího (stejný kód jako níže)
            default_speaker_wav = None
            if voice_file:
                file_ext = Path(voice_file.filename).suffix
                temp_filename = f"{uuid.uuid4()}{file_ext}"
                temp_path = UPLOADS_DIR / temp_filename
                async with aiofiles.open(temp_path, 'wb') as f:
                    content = await voice_file.read()
                    await f.write(content)
                processed_path, error = AudioProcessor.process_uploaded_file(str(temp_path))
                if error:
                    raise HTTPException(status_code=400, detail=error)
                default_speaker_wav = processed_path
            elif demo_voice:
                demo_path = get_demo_voice_path(demo_voice, lang="cs")
                if demo_path:
                    default_speaker_wav = demo_path
                else:
                    available_voices = list(DEMO_VOICES_CS_DIR.glob("*.wav"))
                    if available_voices:
                        default_speaker_wav = str(available_voices[0])
                    else:
                        raise HTTPException(status_code=404, detail="Žádné demo hlasy nejsou k dispozici")
            else:
                available_voices = list(DEMO_VOICES_CS_DIR.glob("*.wav"))
                if available_voices:
                    default_speaker_wav = str(available_voices[0])
                else:
                    raise HTTPException(status_code=400, detail="Musí být zadán voice_file nebo demo_voice")

            # Parsuj speaker mapping z textu (extrahuj všechny speaker_id)
            speaker_ids = set()
            for match in multi_lang_pattern.finditer(text):
                speaker_id = match.group(2)
                if speaker_id:
                    speaker_ids.add(speaker_id)

            # Vytvoř speaker mapping - automaticky zkus najít demo hlasy podle názvu
            speaker_map = {}
            if speaker_ids:
                for sid in speaker_ids:
                    demo_path = get_demo_voice_path(sid, lang="cs")
                    if demo_path:
                        speaker_map[sid] = demo_path
                    elif Path(sid).exists():
                        speaker_map[sid] = sid
                    else:
                        speaker_map[sid] = default_speaker_wav

            if use_multi_pass:
                # Podpora multi-pass pro multi-lang
                logger.info(f"Generuji {multi_pass_count_value} variant pro multi-lang")
                variants = []
                for i in range(multi_pass_count_value):
                    if job_id:
                        ProgressManager.update(job_id, percent=2 + (90 * i / multi_pass_count_value), message=f"Generuji variantu {i+1}/{multi_pass_count_value} (multi-lang)…")

                    v_seed = (seed or 42) + i
                    output_path = await tts_engine.generate_multi_lang_speaker(
                        text=text,
                        default_speaker_wav=default_speaker_wav,
                        default_language="cs",
                        speaker_map=speaker_map if speaker_map else None,
                        speed=tts_speed,
                        temperature=tts_temperature + (0.05 * (i % 3 - 1)),
                        length_penalty=tts_length_penalty,
                        repetition_penalty=tts_repetition_penalty,
                        top_k=tts_top_k,
                        top_p=tts_top_p,
                        quality_mode=quality_mode,
                        enhancement_preset=enhancement_preset,
                        seed=v_seed,
                        enable_vad=enable_vad_flag,
                        enable_batch=use_batch_flag,
                        enable_enhancement=enable_enh_flag,
                        enable_normalization=enable_norm,
                        enable_denoiser=enable_den,
                        enable_compressor=enable_comp,
                        enable_deesser=enable_deess,
                        enable_eq=enable_eq_flag,
                        enable_trim=enable_trim_flag,
                        enable_dialect_conversion=use_dialect,
                        dialect_code=dialect_code_value,
                        dialect_intensity=dialect_intensity_value,
                        enable_whisper=enable_whisper_value,
                        whisper_intensity=whisper_intensity_value,
                        target_headroom_db=target_headroom_db_value,
                        use_hifigan=use_hifigan_flag,
                        hifigan_refinement_intensity=hifigan_refinement_intensity_value,
                        hifigan_normalize_output=hifigan_normalize_output_value,
                        hifigan_normalize_gain=hifigan_normalize_gain_value,
                        job_id=job_id
                    )
                    filename = Path(output_path).name
                    variants.append({
                        "audio_url": f"/api/audio/{filename}",
                        "filename": filename,
                        "seed": v_seed,
                        "temperature": tts_temperature + (0.05 * (i % 3 - 1)),
                        "index": i + 1
                    })

                if job_id:
                    ProgressManager.done(job_id)

                return {
                    "variants": variants,
                    "success": True,
                    "multi_pass": True,
                    "multi_lang": True
                }

            # Standardní single multi-lang generování
            output_path = await tts_engine.generate_multi_lang_speaker(
                text=text,
                default_speaker_wav=default_speaker_wav,
                default_language="cs",
                speaker_map=speaker_map if speaker_map else None,
                speed=tts_speed,
                temperature=tts_temperature,
                length_penalty=tts_length_penalty,
                repetition_penalty=tts_repetition_penalty,
                top_k=tts_top_k,
                top_p=tts_top_p,
                quality_mode=quality_mode,
                enhancement_preset=enhancement_preset,
                seed=seed,
                enable_vad=enable_vad_flag,
                enable_batch=use_batch_flag,
                enable_enhancement=enable_enh_flag,
                enable_normalization=enable_norm,
                enable_denoiser=enable_den,
                enable_compressor=enable_comp,
                enable_deesser=enable_deess,
                enable_eq=enable_eq_flag,
                enable_trim=enable_trim_flag,
                enable_dialect_conversion=use_dialect,
                dialect_code=dialect_code_value,
                dialect_intensity=dialect_intensity_value,
                enable_whisper=enable_whisper_value,
                whisper_intensity=whisper_intensity_value,
                target_headroom_db=target_headroom_db_value,
                use_hifigan=use_hifigan_flag,
                hifigan_refinement_intensity=hifigan_refinement_intensity_value,
                hifigan_normalize_output=hifigan_normalize_output_value,
                hifigan_normalize_gain=hifigan_normalize_gain_value,
                job_id=job_id
            )

            filename = Path(output_path).name
            audio_url = f"/api/audio/{filename}"

            if job_id:
                ProgressManager.done(job_id)

            return {
                "audio_url": audio_url,
                "filename": filename,
                "success": True,
                "job_id": job_id,
                "multi_lang": True,
            }

        # Automaticky zapnout batch processing pro dlouhé texty
        text_length = len(text)
        if text_length > MAX_TEXT_LENGTH:
            logger.warning(f"Text je delší než {MAX_TEXT_LENGTH} znaků ({text_length} znaků), automaticky zapínám batch processing")
            if use_batch_flag is None or use_batch_flag is True:
                use_batch = True
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Text je příliš dlouhý ({text_length} znaků, max {MAX_TEXT_LENGTH}). Pro delší texty zapněte batch processing (enable_batch=true)."
                )
        elif text_length > 2000:
            logger.info(f"Text je dlouhý ({text_length} znaků), doporučuji zapnout batch processing pro lepší kvalitu")
            use_batch = use_batch_flag if use_batch_flag is not None else ENABLE_BATCH_PROCESSING
        else:
            use_batch = use_batch_flag if use_batch_flag is not None else False

        # Zpracování hlasu
        speaker_wav = None
        reference_quality = None

        if voice_file:
            # Uložení nahraného souboru
            file_ext = Path(voice_file.filename).suffix
            temp_filename = f"{uuid.uuid4()}{file_ext}"
            temp_path = UPLOADS_DIR / temp_filename

            async with aiofiles.open(temp_path, 'wb') as f:
                content = await voice_file.read()
                await f.write(content)

            # Zpracování audio
            processed_path, error = AudioProcessor.process_uploaded_file(
                str(temp_path)
            )

            if error:
                raise HTTPException(status_code=400, detail=error)

            speaker_wav = processed_path

        elif demo_voice:
            # Použití demo hlasu
            demo_path = get_demo_voice_path(demo_voice, lang="cs")
            if not demo_path:
                available_voices = list(DEMO_VOICES_CS_DIR.glob("*.wav"))
                if available_voices:
                    speaker_wav = str(available_voices[0])
                    logger.warning(f"Demo voice '{demo_voice}' not found, using: {speaker_wav}")
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Demo hlas '{demo_voice}' neexistuje a žádné demo hlasy nejsou k dispozici. Prosím nahrajte audio soubor."
                    )
            else:
                speaker_wav = demo_path
        else:
            raise HTTPException(
                status_code=400,
                detail="Musí být zadán buď voice_file nebo demo_voice"
            )

        # Quality gate + auto-enhance pro referenční hlas
        try:
            from backend.config import (
                ENABLE_REFERENCE_QUALITY_GATE,
                ENABLE_REFERENCE_AUTO_ENHANCE,
                REFERENCE_ALLOW_POOR_BY_DEFAULT,
                UPLOADS_DIR,
            )
            reference_quality = AudioProcessor.analyze_audio_quality(speaker_wav) if speaker_wav else None

            if ENABLE_REFERENCE_QUALITY_GATE and reference_quality and reference_quality.get("score") == "poor":
                request_auto = (auto_enhance_voice.lower() == "true") if isinstance(auto_enhance_voice, str) else None
                request_allow = (allow_poor_voice.lower() == "true") if isinstance(allow_poor_voice, str) else None

                do_auto = request_auto if request_auto is not None else ENABLE_REFERENCE_AUTO_ENHANCE

                # Demo hlasy (vybrané z demo-voices) nechceme blokovat quality gate,
                # protože uživatel očekává, že "demo" půjde použít i když je vzorek šumový.
                # Explicitní allow_poor_voice=true/false má přednost; pokud není zadáno a jde o demo hlas, povol.
                is_demo_voice = False
                try:
                    speaker_resolved = Path(speaker_wav).resolve()
                    is_demo_voice = (
                        speaker_resolved.is_relative_to(DEMO_VOICES_CS_DIR.resolve())
                        or speaker_resolved.is_relative_to(DEMO_VOICES_SK_DIR.resolve())
                    )
                except Exception:
                    # fallback pro starší Python / edge případy
                    try:
                        speaker_resolved_str = str(Path(speaker_wav).resolve())
                        is_demo_voice = (
                            speaker_resolved_str.startswith(str(DEMO_VOICES_CS_DIR.resolve()))
                            or speaker_resolved_str.startswith(str(DEMO_VOICES_SK_DIR.resolve()))
                        )
                    except Exception:
                        is_demo_voice = False

                if request_allow is None and is_demo_voice:
                    do_allow = True
                else:
                    do_allow = request_allow if request_allow is not None else REFERENCE_ALLOW_POOR_BY_DEFAULT

                if do_auto:
                    enhanced_path = UPLOADS_DIR / f"enhanced_{uuid.uuid4().hex[:10]}.wav"
                    ok, enh_err = AudioProcessor.enhance_voice_sample(speaker_wav, str(enhanced_path))
                    if ok:
                        speaker_wav = str(enhanced_path)
                        reference_quality = AudioProcessor.analyze_audio_quality(speaker_wav)
                    else:
                        logger.warning(f"Auto-enhance referenčního hlasu selhal: {enh_err}")

                if reference_quality and reference_quality.get("score") == "poor" and not do_allow:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "message": "Referenční audio má nízkou kvalitu pro klonování (šum/clipping/krátká délka). Nahrajte čistší vzorek (10–30s řeči bez hudby) nebo použijte allow_poor_voice=true.",
                            "quality": reference_quality,
                        },
                    )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Quality gate selhal (ignorováno): {e}")

        # Validace parametrů
        if not (0.5 <= tts_speed <= 2.0):
            raise HTTPException(status_code=400, detail="Speed musí být mezi 0.5 a 2.0")
        if not (0.0 <= tts_temperature <= 1.0):
            raise HTTPException(status_code=400, detail="Temperature musí být mezi 0.0 a 1.0")
        if tts_top_k < 1:
            raise HTTPException(status_code=400, detail="top_k musí být >= 1")
        if not (0.0 <= tts_top_p <= 1.0):
            raise HTTPException(status_code=400, detail="top_p musí být mezi 0.0 a 1.0")

        # Určení quality_mode a enhancement nastavení
        tts_quality_mode = quality_mode if quality_mode else None

        # Určení enhancement nastavení
        use_enhancement = enable_enh_flag
        enhancement_preset_value = enhancement_preset if enhancement_preset else (quality_mode if quality_mode else AUDIO_ENHANCEMENT_PRESET)

        # HiFi-GAN parametry
        try:
            hifigan_refinement_intensity_value = float(hifigan_refinement_intensity) if hifigan_refinement_intensity else None
            if hifigan_refinement_intensity_value is not None and not (0.0 <= hifigan_refinement_intensity_value <= 1.0):
                raise HTTPException(status_code=400, detail="hifigan_refinement_intensity musí být mezi 0.0 a 1.0")
        except (ValueError, TypeError):
            hifigan_refinement_intensity_value = None

        hifigan_normalize_output_value = (hifigan_normalize_output.lower() == "true") if isinstance(hifigan_normalize_output, str) else None

        try:
            hifigan_normalize_gain_value = float(hifigan_normalize_gain) if hifigan_normalize_gain else None
            if hifigan_normalize_gain_value is not None and not (0.0 <= hifigan_normalize_gain_value <= 1.0):
                raise HTTPException(status_code=400, detail="hifigan_normalize_gain musí být mezi 0.0 a 1.0")
        except (ValueError, TypeError):
            hifigan_normalize_gain_value = None

        # Whisper efekt overrides (volitelné)
        enable_whisper_value = (enable_whisper.lower() == "true") if isinstance(enable_whisper, str) else None
        try:
            whisper_intensity_value = float(whisper_intensity) if whisper_intensity else None
            if whisper_intensity_value is not None and not (0.0 <= whisper_intensity_value <= 1.0):
                raise HTTPException(status_code=400, detail="whisper_intensity musí být mezi 0.0 a 1.0")
        except (ValueError, TypeError):
            whisper_intensity_value = None

        # Headroom override (volitelné)
        try:
            target_headroom_db_value = float(target_headroom_db) if target_headroom_db else None
            if target_headroom_db_value is not None and not (-128.0 <= target_headroom_db_value <= 0.0):
                raise HTTPException(status_code=400, detail="target_headroom_db musí být mezi -128.0 a 0.0 dB")
        except (ValueError, TypeError):
            target_headroom_db_value = None

        # Generování řeči (efektivní nastavení se počítá v tts_engine pomocí _compute_effective_settings)
        if job_id:
            ProgressManager.update(job_id, percent=1, stage="tts", message="Generuji řeč…")
        logger.info(f"UI headroom: target_headroom_db={target_headroom_db_value} dB, enable_enhancement={enable_enh_flag}, enable_normalization={enable_norm}")
        result = await tts_engine.generate(
            text=text,
            speaker_wav=speaker_wav,
            language="cs",
            speed=tts_speed,
            temperature=tts_temperature,
            length_penalty=tts_length_penalty,
            repetition_penalty=tts_repetition_penalty,
            top_k=tts_top_k,
            top_p=tts_top_p,
            quality_mode=tts_quality_mode,
            seed=seed,
            enhancement_preset=enhancement_preset_value,
            enable_enhancement=enable_enh_flag,
            multi_pass=use_multi_pass,
            multi_pass_count=multi_pass_count_value,
            enable_batch=use_batch,
            enable_vad=enable_vad_flag,
            use_hifigan=use_hifigan_flag,
            enable_normalization=enable_norm,
            enable_denoiser=enable_den,
            enable_compressor=enable_comp,
            enable_deesser=enable_deess,
            enable_eq=enable_eq_flag,
            enable_trim=enable_trim_flag,
            enable_dialect_conversion=use_dialect,
            dialect_code=dialect_code_value,
            dialect_intensity=dialect_intensity_value,
            enable_whisper=enable_whisper_value,
            whisper_intensity=whisper_intensity_value,
            target_headroom_db=target_headroom_db_value,
            hifigan_refinement_intensity=hifigan_refinement_intensity_value,
            hifigan_normalize_output=hifigan_normalize_output_value,
            hifigan_normalize_gain=hifigan_normalize_gain_value,
            job_id=job_id
        )

        # Zpracování výsledku (může být string nebo list pro multi-pass)
        if isinstance(result, list):
            # Multi-pass: vrátit všechny varianty
            return {
                "variants": result,
                "success": True,
                "multi_pass": True,
                "reference_quality": reference_quality,
            }
        else:
            # Standardní: jeden výstup
            output_path = result
            filename = Path(output_path).name
            audio_url = f"/api/audio/{filename}"

            # Určení typu hlasu a názvu
            voice_type = "upload" if voice_file else "demo"
            voice_name = None
            if demo_voice:
                voice_name = demo_voice
            elif voice_file:
                voice_name = voice_file.filename

            # Uložení do historie
            tts_params_dict = {
                "speed": tts_speed,
                "temperature": tts_temperature,
                "length_penalty": tts_length_penalty,
                "repetition_penalty": tts_repetition_penalty,
                "top_k": tts_top_k,
                "top_p": tts_top_p
            }

            history_entry = HistoryManager.add_entry(
                audio_url=audio_url,
                filename=filename,
                text=text,
                voice_type=voice_type,
                voice_name=voice_name,
                tts_params=tts_params_dict
            )

            if job_id:
                # 99% až úplně na konci requestu (po zápisu do historie / přípravě odpovědi)
                ProgressManager.update(job_id, percent=99, stage="final", message="Ukládám do historie a odesílám…")
                ProgressManager.done(job_id)
            return {
                "audio_url": audio_url,
                "filename": filename,
                "success": True,
                "history_id": history_entry["id"],
                "job_id": job_id,
                "reference_quality": reference_quality,
            }

    except HTTPException:
        if job_id:
            ProgressManager.fail(job_id, "HTTPException")
        raise
    except Exception as e:
        msg = str(e)
        if job_id:
            ProgressManager.fail(job_id, msg)
        raise HTTPException(status_code=500, detail=f"Chyba při generování: {msg}")


@app.post("/api/tts/generate-f5")
async def generate_speech_f5(
    text: str = Form(...),
    job_id: str = Form(None),
    voice_file: UploadFile = File(None),
    demo_voice: str = Form(None),
    ref_text: str = Form(None),  # Volitelně: přepis reference audio pro lepší kvalitu
    speed: str = Form(None),
    temperature: float = Form(None),  # Ignorováno u F5, ale přijímáme pro kompatibilitu
    length_penalty: float = Form(None),  # Ignorováno
    repetition_penalty: float = Form(None),  # Ignorováno
    top_k: int = Form(None),  # Ignorováno
    top_p: float = Form(None),  # Ignorováno
    quality_mode: str = Form(None),  # Ignorováno (můžeme mapovat na NFE později)
    enhancement_preset: str = Form(None),
    enable_enhancement: str = Form(None),
    seed: int = Form(None),  # Ignorováno (F5 může mít vlastní seed handling)
    enable_vad: str = Form(None),
    use_hifigan: str = Form(None),
    enable_normalization: str = Form(None),
    enable_denoiser: str = Form(None),
    enable_compressor: str = Form(None),
    enable_deesser: str = Form(None),
    enable_eq: str = Form(None),
    enable_trim: str = Form(None),
    enable_dialect_conversion: str = Form(None),
    dialect_code: str = Form(None),
    dialect_intensity: str = Form(None),
    hifigan_refinement_intensity: str = Form(None),
    hifigan_normalize_output: str = Form(None),
    hifigan_normalize_gain: str = Form(None),
    enable_whisper: str = Form(None),
    whisper_intensity: str = Form(None),
    target_headroom_db: str = Form(None),
    auto_enhance_voice: str = Form(None),
    allow_poor_voice: str = Form(None),
):
    """
    Generuje řeč z textu pomocí F5-TTS

    Body:
        text: Text k syntéze
        voice_file: Nahraný audio soubor (volitelné)
        demo_voice: Název demo hlasu (volitelné)
        ref_text: Přepis reference audio (volitelné, pro lepší kvalitu)
        speed: Rychlost řeči (0.5-2.0, výchozí: 1.0)
        enhancement_preset: Preset pro audio enhancement (high_quality, natural, fast)
        enable_enhancement: Zapnout/vypnout audio enhancement (true/false, výchozí: true)
        (ostatní parametry jako v /api/tts/generate, ale některé jsou ignorovány u F5)
    """
    try:
        # Zaregistruj job_id
        if job_id:
            ProgressManager.start(
                job_id,
                meta={
                    "text_length": len(text or ""),
                    "endpoint": "/api/tts/generate-f5",
                },
            )

        # Lazy loading F5-TTS (CLI check)
        if not f5_tts_engine.is_loaded:
            if job_id:
                ProgressManager.update(job_id, percent=5, stage="load", message="Kontroluji F5-TTS CLI…")
            await f5_tts_engine.load_model()
        else:
            if job_id:
                ProgressManager.update(job_id, percent=10, stage="load", message="F5-TTS je připraven, začínám syntézu…")

        # Zpracování parametrů (stejné jako XTTS)
        if speed is not None:
            try:
                tts_speed = float(speed) if isinstance(speed, str) else float(speed)
            except (ValueError, TypeError):
                tts_speed = TTS_SPEED
        else:
            tts_speed = TTS_SPEED

        # Enhancement nastavení
        enable_enh_flag = (enable_enhancement.lower() == "true") if isinstance(enable_enhancement, str) else ENABLE_AUDIO_ENHANCEMENT
        enhancement_preset_value = enhancement_preset if enhancement_preset else AUDIO_ENHANCEMENT_PRESET

        # Boolean flags
        enable_vad_flag = (enable_vad.lower() == "true") if isinstance(enable_vad, str) else None
        use_hifigan_flag = (use_hifigan.lower() == "true") if isinstance(use_hifigan, str) else False
        # DŮLEŽITÉ: když tyto parametry z UI nepřijdou, NECHCEME je vynutit na True.
        # Předáme None -> rozhodnutí udělá engine podle presetů / config defaultů.
        enable_norm = (enable_normalization.lower() == "true") if isinstance(enable_normalization, str) else None
        enable_den = (enable_denoiser.lower() == "true") if isinstance(enable_denoiser, str) else None
        enable_comp = (enable_compressor.lower() == "true") if isinstance(enable_compressor, str) else None
        enable_deess = (enable_deesser.lower() == "true") if isinstance(enable_deesser, str) else None
        enable_eq_flag = (enable_eq.lower() == "true") if isinstance(enable_eq, str) else None
        enable_trim_flag = (enable_trim.lower() == "true") if isinstance(enable_trim, str) else None

        # Dialect conversion
        use_dialect = (enable_dialect_conversion.lower() == "true") if isinstance(enable_dialect_conversion, str) else False
        dialect_code_value = dialect_code if dialect_code and dialect_code != "standardni" else None
        try:
            dialect_intensity_value = float(dialect_intensity) if dialect_intensity else 1.0
        except (ValueError, TypeError):
            dialect_intensity_value = 1.0

        # HiFi-GAN parametry
        try:
            hifigan_refinement_intensity_value = float(hifigan_refinement_intensity) if hifigan_refinement_intensity else None
            if hifigan_refinement_intensity_value is not None and not (0.0 <= hifigan_refinement_intensity_value <= 1.0):
                raise HTTPException(status_code=400, detail="hifigan_refinement_intensity musí být mezi 0.0 a 1.0")
        except (ValueError, TypeError):
            hifigan_refinement_intensity_value = None

        hifigan_normalize_output_value = (hifigan_normalize_output.lower() == "true") if isinstance(hifigan_normalize_output, str) else None

        try:
            hifigan_normalize_gain_value = float(hifigan_normalize_gain) if hifigan_normalize_gain else None
            if hifigan_normalize_gain_value is not None and not (0.0 <= hifigan_normalize_gain_value <= 1.0):
                raise HTTPException(status_code=400, detail="hifigan_normalize_gain musí být mezi 0.0 a 1.0")
        except (ValueError, TypeError):
            hifigan_normalize_gain_value = None

        # Whisper efekt
        enable_whisper_value = (enable_whisper.lower() == "true") if isinstance(enable_whisper, str) else None
        try:
            whisper_intensity_value = float(whisper_intensity) if whisper_intensity else None
            if whisper_intensity_value is not None and not (0.0 <= whisper_intensity_value <= 1.0):
                raise HTTPException(status_code=400, detail="whisper_intensity musí být mezi 0.0 a 1.0")
        except (ValueError, TypeError):
            whisper_intensity_value = None

        # Headroom
        try:
            target_headroom_db_value = float(target_headroom_db) if target_headroom_db else None
            if target_headroom_db_value is not None and not (-128.0 <= target_headroom_db_value <= 0.0):
                raise HTTPException(status_code=400, detail="target_headroom_db musí být mezi -128.0 a 0.0 dB")
        except (ValueError, TypeError):
            target_headroom_db_value = None

        # Zpracování hlasu (stejné jako XTTS)
        speaker_wav = None
        reference_quality = None

        if voice_file:
            file_ext = Path(voice_file.filename).suffix
            temp_filename = f"{uuid.uuid4()}{file_ext}"
            temp_path = UPLOADS_DIR / temp_filename

            async with aiofiles.open(temp_path, 'wb') as f:
                content = await voice_file.read()
                await f.write(content)

            processed_path, error = AudioProcessor.process_uploaded_file(str(temp_path))
            if error:
                raise HTTPException(status_code=400, detail=error)
            speaker_wav = processed_path

        elif demo_voice:
            demo_path = get_demo_voice_path(demo_voice, lang="cs")
            if not demo_path:
                available_voices = list(DEMO_VOICES_CS_DIR.glob("*.wav"))
                if available_voices:
                    speaker_wav = str(available_voices[0])
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Demo hlas '{demo_voice}' neexistuje a žádné demo hlasy nejsou k dispozici."
                    )
            else:
                speaker_wav = demo_path
        else:
            raise HTTPException(
                status_code=400,
                detail="Musí být zadán buď voice_file nebo demo_voice"
            )

        # Quality gate (stejné jako XTTS)
        try:
            from backend.config import (
                ENABLE_REFERENCE_QUALITY_GATE,
                ENABLE_REFERENCE_AUTO_ENHANCE,
                REFERENCE_ALLOW_POOR_BY_DEFAULT,
            )
            reference_quality = AudioProcessor.analyze_audio_quality(speaker_wav) if speaker_wav else None

            if ENABLE_REFERENCE_QUALITY_GATE and reference_quality and reference_quality.get("score") == "poor":
                request_auto = (auto_enhance_voice.lower() == "true") if isinstance(auto_enhance_voice, str) else None
                request_allow = (allow_poor_voice.lower() == "true") if isinstance(allow_poor_voice, str) else None

                do_auto = request_auto if request_auto is not None else ENABLE_REFERENCE_AUTO_ENHANCE

                is_demo_voice = False
                try:
                    speaker_resolved = Path(speaker_wav).resolve()
                    is_demo_voice = (
                        speaker_resolved.is_relative_to(DEMO_VOICES_CS_DIR.resolve())
                        or speaker_resolved.is_relative_to(DEMO_VOICES_SK_DIR.resolve())
                    )
                except Exception:
                    try:
                        speaker_resolved_str = str(Path(speaker_wav).resolve())
                        is_demo_voice = (
                            speaker_resolved_str.startswith(str(DEMO_VOICES_CS_DIR.resolve()))
                            or speaker_resolved_str.startswith(str(DEMO_VOICES_SK_DIR.resolve()))
                        )
                    except Exception:
                        is_demo_voice = False

                if request_allow is None and is_demo_voice:
                    do_allow = True
                else:
                    do_allow = request_allow if request_allow is not None else REFERENCE_ALLOW_POOR_BY_DEFAULT

                if do_auto:
                    enhanced_path = UPLOADS_DIR / f"enhanced_{uuid.uuid4().hex[:10]}.wav"
                    ok, enh_err = AudioProcessor.enhance_voice_sample(speaker_wav, str(enhanced_path))
                    if ok:
                        speaker_wav = str(enhanced_path)
                        reference_quality = AudioProcessor.analyze_audio_quality(speaker_wav)

                if reference_quality and reference_quality.get("score") == "poor" and not do_allow:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "message": "Referenční audio má nízkou kvalitu pro klonování. Nahrajte čistší vzorek nebo použijte allow_poor_voice=true.",
                            "quality": reference_quality,
                        },
                    )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Quality gate selhal (ignorováno): {e}")

        # Validace speed
        if not (0.5 <= tts_speed <= 2.0):
            raise HTTPException(status_code=400, detail="Speed musí být mezi 0.5 a 2.0")

        # Generování řeči pomocí F5-TTS
        if job_id:
            ProgressManager.update(job_id, percent=1, stage="f5_tts", message="Generuji řeč (F5-TTS)…")

        logger.info(f"UI headroom (F5): target_headroom_db={target_headroom_db_value} dB, enable_enhancement={enable_enh_flag}, enable_normalization={enable_norm}")
        output_path = await f5_tts_engine.generate(
            text=text,
            speaker_wav=speaker_wav,
            language="cs",
            speed=tts_speed,
            temperature=0.7,  # Ignorováno, ale předáváme pro kompatibilitu
            length_penalty=1.0,
            repetition_penalty=2.0,
            top_k=50,
            top_p=0.85,
            quality_mode=quality_mode,
            seed=seed,
            enhancement_preset=enhancement_preset_value,
            enable_vad=enable_vad_flag,
            use_hifigan=use_hifigan_flag,
            enable_normalization=enable_norm,
            enable_denoiser=enable_den,
            enable_compressor=enable_comp,
            enable_deesser=enable_deess,
            enable_eq=enable_eq_flag,
            enable_trim=enable_trim_flag,
            enable_dialect_conversion=use_dialect,
            dialect_code=dialect_code_value,
            dialect_intensity=dialect_intensity_value,
            enable_whisper=enable_whisper_value,
            whisper_intensity=whisper_intensity_value,
            target_headroom_db=target_headroom_db_value,
            hifigan_refinement_intensity=hifigan_refinement_intensity_value,
            hifigan_normalize_output=hifigan_normalize_output_value,
            hifigan_normalize_gain=hifigan_normalize_gain_value,
            enable_enhancement=enable_enh_flag,
            job_id=job_id,
            ref_text=ref_text
        )

        filename = Path(output_path).name
        audio_url = f"/api/audio/{filename}"

        voice_type = "upload" if voice_file else "demo"
        voice_name = None
        if demo_voice:
            voice_name = demo_voice
        elif voice_file:
            voice_name = voice_file.filename

        # Uložení do historie
        tts_params_dict = {
            "speed": tts_speed,
            "engine": "f5-tts"
        }

        history_entry = HistoryManager.add_entry(
            audio_url=audio_url,
            filename=filename,
            text=text,
            voice_type=voice_type,
            voice_name=voice_name,
            tts_params=tts_params_dict
        )

        if job_id:
            ProgressManager.update(job_id, percent=99, stage="final", message="Ukládám do historie a odesílám…")
            ProgressManager.done(job_id)

        return {
            "audio_url": audio_url,
            "filename": filename,
            "success": True,
            "history_id": history_entry["id"],
            "job_id": job_id,
            "reference_quality": reference_quality,
        }

    except HTTPException:
        if job_id:
            ProgressManager.fail(job_id, "HTTPException")
        raise
    except Exception as e:
        msg = str(e)
        if job_id:
            ProgressManager.fail(job_id, msg)
        raise HTTPException(status_code=500, detail=f"Chyba při generování F5-TTS: {msg}")


@app.post("/api/tts/generate-f5-sk")
async def generate_speech_f5_sk(
    text: str = Form(...),
    job_id: str = Form(None),
    voice_file: UploadFile = File(None),
    demo_voice: str = Form(None),
    ref_text: str = Form(None),  # Volitelně: přepis reference audio pro lepší kvalitu
    speed: str = Form(None),
    temperature: float = Form(None),  # Ignorováno u F5, ale přijímáme pro kompatibilitu
    length_penalty: float = Form(None),  # Ignorováno
    repetition_penalty: float = Form(None),  # Ignorováno
    top_k: int = Form(None),  # Ignorováno
    top_p: float = Form(None),  # Ignorováno
    quality_mode: str = Form(None),  # Ignorováno (můžeme mapovat na NFE později)
    enhancement_preset: str = Form(None),
    enable_enhancement: str = Form(None),
    seed: int = Form(None),  # Ignorováno (F5 může mít vlastní seed handling)
    enable_vad: str = Form(None),
    use_hifigan: str = Form(None),
    enable_normalization: str = Form(None),
    enable_denoiser: str = Form(None),
    enable_compressor: str = Form(None),
    enable_deesser: str = Form(None),
    enable_eq: str = Form(None),
    enable_trim: str = Form(None),
    enable_dialect_conversion: str = Form(None),
    dialect_code: str = Form(None),
    dialect_intensity: str = Form(None),
    hifigan_refinement_intensity: str = Form(None),
    hifigan_normalize_output: str = Form(None),
    hifigan_normalize_gain: str = Form(None),
    enable_whisper: str = Form(None),
    whisper_intensity: str = Form(None),
    target_headroom_db: str = Form(None),
    auto_enhance_voice: str = Form(None),
    allow_poor_voice: str = Form(None),
):
    """
    Generuje řeč z textu pomocí F5-TTS slovenského modelu

    Body:
        text: Text k syntéze (slovensky)
        voice_file: Nahraný audio soubor (volitelné)
        demo_voice: Název demo hlasu (volitelné)
        ref_text: Přepis reference audio (volitelné, pro lepší kvalitu)
        speed: Rychlost řeči (0.5-2.0, výchozí: 1.0)
        enhancement_preset: Preset pro audio enhancement (high_quality, natural, fast)
        enable_enhancement: Zapnout/vypnout audio enhancement (true/false, výchozí: true)
        (ostatní parametry jako v /api/tts/generate-f5, ale některé jsou ignorovány u F5)
    """
    try:
        # Zaregistruj job_id
        if job_id:
            ProgressManager.start(
                job_id,
                meta={
                    "text_length": len(text or ""),
                    "endpoint": "/api/tts/generate-f5-sk",
                },
            )

        # Lazy loading F5-TTS Slovak (CLI check)
        if not f5_tts_slovak_engine.is_loaded:
            if job_id:
                ProgressManager.update(job_id, percent=5, stage="load", message="Kontroluji F5-TTS Slovak CLI…")
            await f5_tts_slovak_engine.load_model()
        else:
            if job_id:
                ProgressManager.update(job_id, percent=10, stage="load", message="F5-TTS Slovak je připraven, začínám syntézu…")

        # Zpracování parametrů (stejné jako F5-TTS)
        if speed is not None:
            try:
                tts_speed = float(speed) if isinstance(speed, str) else float(speed)
            except (ValueError, TypeError):
                tts_speed = TTS_SPEED
        else:
            tts_speed = TTS_SPEED

        # Enhancement nastavení
        enable_enh_flag = (enable_enhancement.lower() == "true") if isinstance(enable_enhancement, str) else ENABLE_AUDIO_ENHANCEMENT
        enhancement_preset_value = enhancement_preset if enhancement_preset else AUDIO_ENHANCEMENT_PRESET

        # Boolean flags
        enable_vad_flag = (enable_vad.lower() == "true") if isinstance(enable_vad, str) else None
        use_hifigan_flag = (use_hifigan.lower() == "true") if isinstance(use_hifigan, str) else False
        # DŮLEŽITÉ: když tyto parametry z UI nepřijdou, NECHCEME je vynutit na True.
        # Předáme None -> rozhodnutí udělá engine podle presetů / config defaultů.
        enable_norm = (enable_normalization.lower() == "true") if isinstance(enable_normalization, str) else None
        enable_den = (enable_denoiser.lower() == "true") if isinstance(enable_denoiser, str) else None
        enable_comp = (enable_compressor.lower() == "true") if isinstance(enable_compressor, str) else None
        enable_deess = (enable_deesser.lower() == "true") if isinstance(enable_deesser, str) else None
        enable_eq_flag = (enable_eq.lower() == "true") if isinstance(enable_eq, str) else None
        enable_trim_flag = (enable_trim.lower() == "true") if isinstance(enable_trim, str) else None

        # Dialect conversion není podporováno pro slovenštinu
        use_dialect = False
        dialect_code_value = None
        dialect_intensity_value = 1.0

        # HiFi-GAN parametry
        try:
            hifigan_refinement_intensity_value = float(hifigan_refinement_intensity) if hifigan_refinement_intensity else None
            if hifigan_refinement_intensity_value is not None and not (0.0 <= hifigan_refinement_intensity_value <= 1.0):
                raise HTTPException(status_code=400, detail="hifigan_refinement_intensity musí být mezi 0.0 a 1.0")
        except (ValueError, TypeError):
            hifigan_refinement_intensity_value = None

        hifigan_normalize_output_value = (hifigan_normalize_output.lower() == "true") if isinstance(hifigan_normalize_output, str) else None

        try:
            hifigan_normalize_gain_value = float(hifigan_normalize_gain) if hifigan_normalize_gain else None
            if hifigan_normalize_gain_value is not None and not (0.0 <= hifigan_normalize_gain_value <= 1.0):
                raise HTTPException(status_code=400, detail="hifigan_normalize_gain musí být mezi 0.0 a 1.0")
        except (ValueError, TypeError):
            hifigan_normalize_gain_value = None

        # Whisper efekt
        enable_whisper_value = (enable_whisper.lower() == "true") if isinstance(enable_whisper, str) else None
        try:
            whisper_intensity_value = float(whisper_intensity) if whisper_intensity else None
            if whisper_intensity_value is not None and not (0.0 <= whisper_intensity_value <= 1.0):
                raise HTTPException(status_code=400, detail="whisper_intensity musí být mezi 0.0 a 1.0")
        except (ValueError, TypeError):
            whisper_intensity_value = None

        # Headroom
        try:
            target_headroom_db_value = float(target_headroom_db) if target_headroom_db else None
            if target_headroom_db_value is not None and not (-128.0 <= target_headroom_db_value <= 0.0):
                raise HTTPException(status_code=400, detail="target_headroom_db musí být mezi -128.0 a 0.0 dB")
        except (ValueError, TypeError):
            target_headroom_db_value = None

        # Zpracování hlasu (stejné jako F5-TTS)
        speaker_wav = None
        reference_quality = None

        if voice_file:
            file_ext = Path(voice_file.filename).suffix
            temp_filename = f"{uuid.uuid4()}{file_ext}"
            temp_path = UPLOADS_DIR / temp_filename

            async with aiofiles.open(temp_path, 'wb') as f:
                content = await voice_file.read()
                await f.write(content)

            processed_path, error = AudioProcessor.process_uploaded_file(str(temp_path))
            if error:
                raise HTTPException(status_code=400, detail=error)
            speaker_wav = processed_path

        elif demo_voice:
            demo_path = get_demo_voice_path(demo_voice, lang="sk")
            if not demo_path:
                available_voices = list(DEMO_VOICES_SK_DIR.glob("*.wav"))
                if available_voices:
                    speaker_wav = str(available_voices[0])
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Demo hlas '{demo_voice}' neexistuje a žádné demo hlasy nejsou k dispozici."
                    )
            else:
                speaker_wav = demo_path
        else:
            raise HTTPException(
                status_code=400,
                detail="Musí být zadán buď voice_file nebo demo_voice"
            )

        # Quality gate (stejné jako F5-TTS)
        try:
            from backend.config import (
                ENABLE_REFERENCE_QUALITY_GATE,
                ENABLE_REFERENCE_AUTO_ENHANCE,
                REFERENCE_ALLOW_POOR_BY_DEFAULT,
            )
            auto_enhance_flag = (auto_enhance_voice.lower() == "true") if isinstance(auto_enhance_voice, str) else ENABLE_REFERENCE_AUTO_ENHANCE
            allow_poor_flag = (allow_poor_voice.lower() == "true") if isinstance(allow_poor_voice, str) else REFERENCE_ALLOW_POOR_BY_DEFAULT

            if ENABLE_REFERENCE_QUALITY_GATE:
                reference_quality = AudioProcessor.analyze_audio_quality(speaker_wav)
                if reference_quality["score"] == "poor" and not allow_poor_flag:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Kvalita referenčního audia je příliš nízká (SNR: {reference_quality['snr']:.1f} dB). "
                               f"Použijte allow_poor_voice=true pro povolení."
                    )
                if auto_enhance_flag and reference_quality["score"] != "good":
                    # Auto-enhance reference audio
                    enhanced_path = UPLOADS_DIR / f"enhanced_{uuid.uuid4().hex[:10]}.wav"
                    ok, enh_err = AudioProcessor.enhance_voice_sample(speaker_wav, str(enhanced_path))
                    if ok:
                        speaker_wav = str(enhanced_path)
                        reference_quality = AudioProcessor.analyze_audio_quality(speaker_wav)
                        logger.info("Referenční audio bylo automaticky vylepšeno")
                    else:
                        logger.warning(f"Auto-enhance referenčního hlasu selhal: {enh_err}")
        except Exception as e:
            logger.warning(f"Quality gate selhal: {e}")

        # Validace speed
        if not (0.5 <= tts_speed <= 2.0):
            raise HTTPException(status_code=400, detail="Speed musí být mezi 0.5 a 2.0")

        # Generování řeči pomocí F5-TTS Slovak
        if job_id:
            ProgressManager.update(job_id, percent=1, stage="f5_tts_slovak", message="Generujem reč (F5-TTS Slovak)…")

        logger.info(f"UI headroom (F5-SK): target_headroom_db={target_headroom_db_value} dB, enable_enhancement={enable_enh_flag}, enable_normalization={enable_norm}")
        output_path = await f5_tts_slovak_engine.generate(
            text=text,
            speaker_wav=speaker_wav,
            language="sk",
            speed=tts_speed,
            temperature=0.7,  # Ignorováno, ale předáváme pro kompatibilitu
            length_penalty=1.0,
            repetition_penalty=2.0,
            top_k=50,
            top_p=0.85,
            quality_mode=quality_mode,
            seed=seed,
            enhancement_preset=enhancement_preset_value,
            enable_vad=enable_vad_flag,
            use_hifigan=use_hifigan_flag,
            enable_normalization=enable_norm,
            enable_denoiser=enable_den,
            enable_compressor=enable_comp,
            enable_deesser=enable_deess,
            enable_eq=enable_eq_flag,
            enable_trim=enable_trim_flag,
            enable_dialect_conversion=use_dialect,
            dialect_code=dialect_code_value,
            dialect_intensity=dialect_intensity_value,
            enable_whisper=enable_whisper_value,
            whisper_intensity=whisper_intensity_value,
            target_headroom_db=target_headroom_db_value,
            hifigan_refinement_intensity=hifigan_refinement_intensity_value,
            hifigan_normalize_output=hifigan_normalize_output_value,
            hifigan_normalize_gain=hifigan_normalize_gain_value,
            enable_enhancement=enable_enh_flag,
            job_id=job_id,
            ref_text=ref_text
        )

        filename = Path(output_path).name
        audio_url = f"/api/audio/{filename}"

        voice_type = "upload" if voice_file else "demo"
        voice_name = None
        if demo_voice:
            voice_name = demo_voice
        elif voice_file:
            voice_name = voice_file.filename

        # Uložení do historie
        tts_params_dict = {
            "speed": tts_speed,
            "engine": "f5-tts-slovak"
        }

        history_entry = HistoryManager.add_entry(
            audio_url=audio_url,
            filename=filename,
            text=text,
            voice_type=voice_type,
            voice_name=voice_name,
            tts_params=tts_params_dict
        )

        if job_id:
            ProgressManager.update(job_id, percent=100, stage="done", message="Hotovo!")
            # ProgressManager má metodu done(), ne complete()
            ProgressManager.done(job_id)

        return {
            "success": True,
            "audio_url": audio_url,
            "filename": filename,
            "voice_type": voice_type,
            "voice_name": voice_name,
            "engine": "f5-tts-slovak",
            "reference_quality": reference_quality
        }

    except HTTPException:
        if job_id:
            ProgressManager.fail(job_id, "HTTPException")
        raise
    except Exception as e:
        msg = str(e)
        if job_id:
            ProgressManager.fail(job_id, msg)
        raise HTTPException(status_code=500, detail=f"Chyba při generování F5-TTS Slovak: {msg}")


@app.get("/api/music/ambience/list")
async def get_ambience_list():
    """Vrátí seznam dostupných ambience samplů podle kategorií."""
    try:
        from backend.ambience_library import list_ambience
        return {
            "stream": [p.name for p in list_ambience("stream")],
            "birds": [p.name for p in list_ambience("birds")]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/musicgen/generate")
async def generate_music(
    prompt: str = Form(...),
    job_id: str = Form(None),
    duration: float = Form(12.0),
    temperature: float = Form(1.0),
    top_k: int = Form(250),
    top_p: float = Form(0.0),
    seed: int = Form(None),
    model: str = Form("small"),
    precision: str = Form("auto"),  # auto|fp32|fp16|bf16
    offload: bool = Form(False),  # True = device_map/offload (šetří VRAM, ale zpomalí)
    max_vram_gb: float = Form(None),  # např. 6.0; použije se jen když offload=True
    ambience: str = Form("none"),  # none|stream|birds|both
    ambience_gain_db: float = Form(-18.0),  # typicky -22 až -14
    ambience_seed: int = Form(None),
    ambience_file_stream: str = Form(None),  # konkrétní soubor pro stream
    ambience_file_birds: str = Form(None),   # konkrétní soubor pro birds
):
    """
    Generuje hudbu pomocí MusicGen (AudioCraft).

    Body:
        prompt: Textový prompt (doporučeno přidat "no vocals" pro instrumentál)
        duration: délka v sekundách (1-30)
        model: small|medium|large (pro 6GB VRAM doporučeno small)
        precision: auto|fp32|fp16|bf16 (pro CUDA doporučeno fp16)
        offload: True = část modelu na CPU (menší VRAM, pomalejší)
        max_vram_gb: limit VRAM pro offload režim (např. 6)
        job_id: volitelné pro progress (SSE/polling)
    """
    try:
        if job_id:
            ProgressManager.start(job_id, meta={"endpoint": "/api/musicgen/generate", "prompt_length": len(prompt or "")})

        # Aby byla hudba plynule zacyklitelná (seamless loop), vygenerujeme o 3s více
        # a pak tyto 3s použijeme pro crossfade konce se začátkem.
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

        # Načteme surovou hudbu a vytvoříme plynulou smyčku
        base = load_audio(out_path)
        if gen_duration > loop_crossfade_s:
            base = make_loopable(base, crossfade_ms=int(loop_crossfade_s * 1000))
            save_wav(base, out_path)

        # --- Ambient layer (potůček / ptáci) ---
        warning = None
        ambience_clean = (ambience or "none").strip().lower()
        kinds = []
        if ambience_clean in ("stream", "birds"):
            kinds = [ambience_clean]
        elif ambience_clean == "both":
            kinds = ["stream", "birds"]

        ambience_files_list = []
        if kinds:
            # Nejprve zkusíme konkrétní soubory z Formy
            from backend.config import BASE_DIR
            nature_dir = (BASE_DIR / "assets" / "nature").resolve()

            picked_anything = False
            ambience_files_to_use = []

            if "stream" in kinds and ambience_file_stream and ambience_file_stream != "random":
                p = nature_dir / ambience_file_stream
                if p.exists():
                    ambience_files_to_use.append(p)
                    picked_anything = True

            if "birds" in kinds and ambience_file_birds and ambience_file_birds != "random":
                p = nature_dir / ambience_file_birds
                if p.exists():
                    ambience_files_to_use.append(p)
                    picked_anything = True

            # Pokud pro daný druh nebyl vybrán konkrétní soubor, použijeme pick_many (seed)
            if not picked_anything or len(ambience_files_to_use) < len(kinds):
                # Musíme odfiltrovat druhy, které už mají konkrétní soubor
                remaining_kinds = []
                if "stream" in kinds and not any(f.name.startswith("stream_") for f in ambience_files_to_use):
                    remaining_kinds.append("stream")
                if "birds" in kinds and not any(f.name.startswith("birds_") for f in ambience_files_to_use):
                    remaining_kinds.append("birds")

                if remaining_kinds:
                    picks = pick_many(remaining_kinds, seed=ambience_seed if ambience_seed is not None else seed)
                    for p in picks:
                        ambience_files_to_use.append(p.path)

            if ambience_files_to_use:
                try:
                    logger.info(f"[MusicGen] Mixuji ambience: {', '.join(p.name for p in ambience_files_to_use)} (gain: {ambience_gain_db} dB)")
                    if job_id:
                        ProgressManager.update(job_id, percent=95, stage="mix", message="Mixuji ambience (potůček/ptáci)…")

                    mixed = base
                    used = []
                    for p in ambience_files_to_use:
                        ov = load_audio(p)
                        mixed = mix_overlay(mixed, ov, overlay_gain_db=float(ambience_gain_db), loop_overlay=True, overlay_crossfade_ms=30)
                        used.append(p.name)

                    save_wav(mixed, out_path)
                    logger.info("[MusicGen] Ambience namixováno a WAV přepsán.")
                    if job_id:
                        ProgressManager.update(job_id, percent=98, stage="mix", message="Ambience namixováno.")
                    ambience_files_list = used
                except Exception as e:
                    logger.error(f"[MusicGen] Chyba při mixování: {e}")
                    # neblokuj výsledek – vrať hudbu bez ambience + warning
                    warning = f"Ambience se nepodařilo namixovat ({str(e)}). Výstup je bez ambience vrstvy."
                    ambience_files_list = []
            else:
                logger.warning("[MusicGen] Žádné ambience soubory nenalezeny v assets/nature.")
                warning = "Chybí ambience samply. Přidej WAVy do assets/nature (stream_*.wav / birds_*.wav)."

        # Samostatná music historie
        logger.info(f"[MusicGen] Ukládám do historie: {filename}")
        MusicHistoryManager.add_entry(
            audio_url=audio_url,
            filename=filename,
            prompt=prompt,
            music_params={
                "model": model,
                "duration": duration,
                "temperature": temperature,
                "top_k": top_k,
                "top_p": top_p,
                "seed": seed,
                "precision": precision,
                "offload": bool(offload),
                "max_vram_gb": float(max_vram_gb) if max_vram_gb is not None else None,
                "ambience": ambience_clean,
                "ambience_gain_db": ambience_gain_db,
                "ambience_files": ambience_files_list,
            },
        )

        if job_id:
            ProgressManager.update(job_id, percent=99, stage="final", message="Hotovo, posílám výsledek…")
            ProgressManager.done(job_id)

        logger.info(f"[MusicGen] Hotovo. Odesílám audio_url: {audio_url}")
        resp = {"success": True, "audio_url": audio_url, "filename": filename, "job_id": job_id}
        if warning:
            resp["warning"] = warning
        return resp
    except HTTPException:
        if job_id:
            ProgressManager.fail(job_id, "HTTPException")
        raise
    except Exception as e:
        msg = str(e)
        if job_id:
            ProgressManager.fail(job_id, msg)
        raise HTTPException(status_code=500, detail=f"Chyba při MusicGen: {msg}")


@app.post("/api/bark/generate")
async def generate_bark(
    text: str = Form(...),
    job_id: str = Form(None),
    model_size: str = Form("small"),  # "small" nebo "large"
    mode: str = Form("auto"),  # auto|full|mixed|small
    offload_cpu: bool = Form(False),
    temperature: float = Form(0.7),
    seed: int = Form(None),
    duration: float = Form(None),  # Délka v sekundách (None = použít výchozí ~14s)
):
    """
    Generuje audio pomocí Bark modelu (řeč, hudba, zvuky).

    Body:
        text: Textový prompt (může obsahovat [smích], [hudba], [pláč] apod.)
        model_size: Velikost modelu ("small" nebo "large")
        mode: Režim načtení submodelů (auto=staré chování, full=vše large, mixed=text large + zbytek small, small=vše small)
        offload_cpu: Část modelu na CPU (šetří VRAM, zpomaluje)
        temperature: Teplota generování (0.0-1.0, vyšší = kreativnější)
        seed: Seed pro reprodukovatelnost (volitelné)
        duration: Délka v sekundách (1-120s, None = výchozí ~14s, delší segmenty se zacyklí)
        job_id: volitelné pro progress (SSE/polling)
    """
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

        # Validace délky
        duration_s = None
        if duration is not None:
            duration_s = float(duration)
            if duration_s < 1.0 or duration_s > 120.0:
                raise HTTPException(status_code=400, detail="Délka musí být mezi 1 a 120 sekundami")

        # Generování audia
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
            )
        )

        filename = Path(out_path).name
        audio_url = f"/api/audio/{filename}"

        # Uložení do historie
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


@app.get("/api/bark/progress/{job_id}")
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


@app.get("/api/bark/progress/{job_id}/stream")
async def stream_bark_progress(job_id: str):
    """SSE stream pro real-time progress updates pro Bark."""
    import json
    import asyncio

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

                percent = info.get("percent", 0)
                status = info.get("status", "processing")
                updated = info.get("updated_at")

                # Poslat update pouze pokud se změnil percent nebo status
                if percent != last_percent or status != last_updated:
                    yield f"data: {json.dumps(info)}\n\n"
                    last_percent = percent
                    last_updated = status

                    if status in ("done", "error"):
                        break

                await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                error_data = {
                    "job_id": job_id,
                    "status": "error",
                    "error": str(e),
                }
                yield f"data: {json.dumps(error_data)}\n\n"
                break

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/music/progress/{job_id}")
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


@app.get("/api/music/progress/{job_id}/stream")
async def stream_music_progress(job_id: str):
    """SSE stream pro real-time progress updates pro MusicGen."""
    import json
    import asyncio

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


@app.get("/api/music/history")
async def get_music_history(limit: int = 50, offset: int = 0):
    """Samostatná historie MusicGen výstupů."""
    try:
        history = MusicHistoryManager.get_history(limit=limit, offset=offset)
        stats = MusicHistoryManager.get_stats()
        return {"history": history, "stats": stats, "limit": limit, "offset": offset}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při načítání music historie: {str(e)}")


@app.get("/api/music/history/{entry_id}")
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


@app.delete("/api/music/history/{entry_id}")
async def delete_music_history_entry(entry_id: str):
    try:
        success = MusicHistoryManager.delete_entry(entry_id)
        if not success:
            raise HTTPException(status_code=404, detail="Záznam nenalezen")
        return {"success": True, "message": "Záznam smazán"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při mazání: {str(e)}")


@app.delete("/api/music/history")
async def clear_music_history():
    try:
        count = MusicHistoryManager.clear_history()
        return {"success": True, "message": f"Music historie vymazána ({count} záznamů)"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při mazání music historie: {str(e)}")


@app.get("/api/bark/history")
async def get_bark_history(limit: int = 50, offset: int = 0):
    """Samostatná historie Bark výstupů."""
    try:
        history = BarkHistoryManager.get_history(limit=limit, offset=offset)
        stats = BarkHistoryManager.get_stats()
        return {"history": history, "stats": stats, "limit": limit, "offset": offset}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při načítání bark historie: {str(e)}")


@app.get("/api/bark/history/{entry_id}")
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


@app.delete("/api/bark/history/{entry_id}")
async def delete_bark_history_entry(entry_id: str):
    try:
        success = BarkHistoryManager.delete_entry(entry_id)
        if not success:
            raise HTTPException(status_code=404, detail="Záznam nenalezen")
        return {"success": True, "message": "Záznam smazán"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při mazání: {str(e)}")


@app.delete("/api/bark/history")
async def clear_bark_history():
    try:
        count = BarkHistoryManager.clear_history()
        return {"success": True, "message": f"Bark historie vymazána ({count} záznamů)"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při mazání bark historie: {str(e)}")


def _normalize_demo_lang(lang: Optional[str]) -> str:
    """Normalizuje jazyk pro výběr adresáře demo hlasů."""
    l = (lang or "cs").strip().lower()
    return "sk" if l.startswith("sk") else "cs"


def _get_demo_voices_dir(lang: Optional[str]) -> Path:
    """Vrátí adresář pro demo hlasy podle jazyka."""
    return DEMO_VOICES_SK_DIR if _normalize_demo_lang(lang) == "sk" else DEMO_VOICES_CS_DIR


def get_demo_voice_path(demo_voice_name: str, lang: Optional[str] = None) -> Optional[str]:
    """
    Vrátí cestu k demo hlasu nebo None pokud neexistuje

    Podporuje názvy s podtržítky, pomlčkami, velkými písmeny a mezerami.
    Vyhledávání je case-insensitive a ignoruje mezery na začátku/konci.

    Args:
        demo_voice_name: Název demo hlasu (např. "buchty01", "Pohadka_muz", "Klepl-Bolzakov-rusky")
        lang: Volitelně jazyk ("cs" / "sk"). Pokud není zadán, použije se default "cs".

    Returns:
        Cesta k WAV souboru nebo None
    """
    if not demo_voice_name:
        return None

    # Odstraň mezery na začátku/konci
    demo_voice_name = demo_voice_name.strip()

    # Podpora prefixu "cs:" / "sk:" nebo "cs/" / "sk/" (kvůli jednoznačnému mapování / preview_url)
    m = re.match(r"^(cs|sk)\s*[:/]\s*(.+)$", demo_voice_name, flags=re.IGNORECASE)
    if m:
        lang = m.group(1).lower()
        demo_voice_name = m.group(2).strip()

    # Pokud je to cesta, extrahuj pouze název souboru bez přípony
    if os.path.sep in demo_voice_name or '/' in demo_voice_name:
        demo_voice_name = Path(demo_voice_name).stem

    demo_dir = _get_demo_voices_dir(lang)

    # Nejdříve zkus přesný název (case-sensitive)
    demo_path = demo_dir / f"{demo_voice_name}.wav"
    if demo_path.exists():
        return str(demo_path)

    # Pak zkus case-insensitive vyhledávání
    # Projdeme všechny WAV soubory a porovnáme názvy (bez přípony)
    for wav_file in demo_dir.glob("*.wav"):
        file_stem = wav_file.stem.strip()  # Název bez přípony, bez mezer
        # Porovnej case-insensitive
        if file_stem.lower() == demo_voice_name.lower():
            return str(wav_file)

    # Pokud nic nenašlo, vrať None
    return None


@app.post("/api/tts/generate-multi")
async def generate_speech_multi(
    text: str = Form(...),
    job_id: str = Form(None),
    default_voice_file: UploadFile = File(None),
    default_demo_voice: str = Form(None),
    default_language: str = Form("cs"),
    speaker_mapping: str = Form(None),  # JSON: {"speaker1": "demo_voice_name", "speaker2": "path/to/file.wav"}
    speed: str = Form(None),
    temperature: float = Form(None),
    length_penalty: float = Form(None),
    repetition_penalty: float = Form(None),
    top_k: int = Form(None),
    top_p: float = Form(None),
    quality_mode: str = Form(None),
    enhancement_preset: str = Form(None),
    enable_enhancement: str = Form(None),
    seed: int = Form(None),
    enable_vad: str = Form(None),
    enable_normalization: str = Form(None),
    enable_denoiser: str = Form(None),
    enable_compressor: str = Form(None),
    enable_deesser: str = Form(None),
    enable_eq: str = Form(None),
    enable_trim: str = Form(None),
    # Headroom override (volitelné)
    target_headroom_db: str = Form(None),
):
    """
    Generuje řeč pro text s více jazyky a mluvčími

    Podporuje syntaxi: [lang:speaker]text[/lang] nebo [lang]text[/lang]

    Body:
        text: Text s anotacemi [lang:speaker]text[/lang] (např. "[cs:voice1]Ahoj[/cs] [en:voice2]Hello[/en]")
        default_voice_file: Výchozí hlas pro neanotované části
        default_demo_voice: Výchozí demo hlas
        default_language: Výchozí jazyk (cs, en, de, ...)
        speaker_mapping: JSON mapování speaker_id -> demo_voice_name nebo path (např. {"voice1": "demo1", "voice2": "/path/to/voice.wav"})
        speed: Rychlost řeči (0.5-2.0)
        temperature: Teplota pro sampling (0.0-1.0)
        ... (ostatní parametry jako v /api/tts/generate)
    """
    import json

    try:
        # Zaregistruj job_id
        if job_id:
            ProgressManager.start(
                job_id,
                meta={
                    "text_length": len(text or ""),
                    "endpoint": "/api/tts/generate-multi",
                },
            )

        # Lazy loading modelu XTTS
        if not tts_engine.is_loaded:
            if job_id:
                ProgressManager.update(job_id, percent=5, stage="load", message="Načítám XTTS model do VRAM…")
            await tts_engine.load_model()
        else:
            if job_id:
                ProgressManager.update(job_id, percent=10, stage="load", message="Model je připraven, začínám syntézu…")

        # Validace textu
        if not text or len(text.strip()) == 0:
            raise HTTPException(status_code=400, detail="Text je prázdný")

        # Zpracuj výchozího mluvčího
        default_speaker_wav = None

        if default_voice_file:
            # Uložení nahraného souboru
            file_ext = Path(default_voice_file.filename).suffix
            temp_filename = f"{uuid.uuid4()}{file_ext}"
            temp_path = UPLOADS_DIR / temp_filename

            async with aiofiles.open(temp_path, 'wb') as f:
                content = await default_voice_file.read()
                await f.write(content)

            # Zpracování audio
            processed_path, error = AudioProcessor.process_uploaded_file(str(temp_path))
            if error:
                raise HTTPException(status_code=400, detail=error)
            default_speaker_wav = processed_path

        elif default_demo_voice:
            demo_path = get_demo_voice_path(default_demo_voice, lang=default_language)
            if demo_path:
                default_speaker_wav = demo_path
            else:
                # Zkus najít jakýkoliv WAV soubor v demo-voices
                available_voices = list(_get_demo_voices_dir(default_language).glob("*.wav"))
                if available_voices:
                    default_speaker_wav = str(available_voices[0])
                    logger.warning(f"Demo voice '{default_demo_voice}' not found, using: {default_speaker_wav}")
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Demo hlas '{default_demo_voice}' neexistuje a žádné demo hlasy nejsou k dispozici."
                    )
        else:
            # Zkus použít první dostupný demo hlas
            available_voices = list(_get_demo_voices_dir(default_language).glob("*.wav"))
            if available_voices:
                default_speaker_wav = str(available_voices[0])
                logger.info(f"Žádný výchozí hlas zadán, používám: {default_speaker_wav}")
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Musí být zadán buď default_voice_file nebo default_demo_voice, nebo musí existovat demo hlasy"
                )

        # Parsuj speaker mapping
        # Nejdříve automaticky zkus najít demo hlasy podle názvů v textu
        speaker_map = {}
        multi_lang_pattern = re.compile(r'\[(\w+)(?::([^\]]+))?\]')
        speaker_ids_from_text = set()
        for match in multi_lang_pattern.finditer(text):
            speaker_id = match.group(2)
            if speaker_id:
                speaker_ids_from_text.add(speaker_id)

        # Automaticky mapuj demo hlasy podle jejich názvů
        for sid in speaker_ids_from_text:
            demo_path = get_demo_voice_path(sid, lang=default_language)
            if demo_path:
                speaker_map[sid] = demo_path
                logger.info(f"Auto-mapování: Speaker '{sid}' -> demo hlas: {demo_path}")
            elif Path(sid).exists():
                speaker_map[sid] = sid
                logger.info(f"Auto-mapování: Speaker '{sid}' -> soubor: {sid}")

        # Pak aplikuj explicitní speaker_mapping (přepíše automatické mapování)
        if speaker_mapping:
            try:
                mapping_data = json.loads(speaker_mapping)
                for speaker_id, voice_ref in mapping_data.items():
                    # voice_ref může být cesta k souboru nebo název demo hlasu
                    if Path(voice_ref).exists():
                        speaker_map[speaker_id] = voice_ref
                    else:
                        # Zkus demo hlas
                        demo_path = get_demo_voice_path(voice_ref, lang=default_language)
                        if demo_path:
                            speaker_map[speaker_id] = demo_path
                        else:
                            logger.warning(f"Speaker '{speaker_id}': voice '{voice_ref}' neexistuje, použije se výchozí hlas")
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=400, detail=f"Neplatný speaker_mapping JSON: {str(e)}")

        # Nastavení TTS parametrů
        if speed is not None:
            try:
                tts_speed = float(speed) if isinstance(speed, str) else float(speed)
            except (ValueError, TypeError):
                tts_speed = TTS_SPEED
        else:
            tts_speed = TTS_SPEED

        tts_temperature = temperature if temperature is not None else TTS_TEMPERATURE
        tts_length_penalty = length_penalty if length_penalty is not None else TTS_LENGTH_PENALTY
        tts_repetition_penalty = repetition_penalty if repetition_penalty is not None else TTS_REPETITION_PENALTY
        tts_top_k = top_k if top_k is not None else TTS_TOP_K
        tts_top_p = top_p if top_p is not None else TTS_TOP_P

        # Enhancement parametry
        enable_enh = (enable_enhancement.lower() == "true") if isinstance(enable_enhancement, str) else ENABLE_AUDIO_ENHANCEMENT
        enable_vad_flag = (enable_vad.lower() == "true") if isinstance(enable_vad, str) else None
        # DŮLEŽITÉ: když tyto parametry z UI nepřijdou, NECHCEME je vynutit na True.
        # Předáme None -> rozhodnutí udělá engine podle presetů / config defaultů.
        enable_norm = (enable_normalization.lower() == "true") if isinstance(enable_normalization, str) else None
        enable_den = (enable_denoiser.lower() == "true") if isinstance(enable_denoiser, str) else None
        enable_comp = (enable_compressor.lower() == "true") if isinstance(enable_compressor, str) else None
        enable_deess = (enable_deesser.lower() == "true") if isinstance(enable_deesser, str) else None
        enable_eq_flag = (enable_eq.lower() == "true") if isinstance(enable_eq, str) else None
        enable_trim_flag = (enable_trim.lower() == "true") if isinstance(enable_trim, str) else None

        # Headroom override (volitelné)
        try:
            target_headroom_db_value = float(target_headroom_db) if target_headroom_db else None
            if target_headroom_db_value is not None and not (-128.0 <= target_headroom_db_value <= 0.0):
                raise HTTPException(status_code=400, detail="target_headroom_db musí být mezi -128.0 a 0.0 dB")
        except (ValueError, TypeError):
            target_headroom_db_value = None

        # Generuj řeč
        output_path = await tts_engine.generate_multi_lang_speaker(
            text=text,
            default_speaker_wav=default_speaker_wav,
            default_language=default_language if default_language else "cs",  # Výchozí jazyk je čeština
            speaker_map=speaker_map if speaker_map else None,
            speed=tts_speed,
            temperature=tts_temperature,
            length_penalty=tts_length_penalty,
            repetition_penalty=tts_repetition_penalty,
            top_k=tts_top_k,
            top_p=tts_top_p,
            quality_mode=quality_mode,
            enhancement_preset=enhancement_preset,
            seed=seed,
            enable_vad=enable_vad_flag,
            enable_enhancement=enable_enh,
            enable_normalization=enable_norm,
            enable_denoiser=enable_den,
            enable_compressor=enable_comp,
            enable_deesser=enable_deess,
            enable_eq=enable_eq_flag,
            enable_trim=enable_trim_flag,
            target_headroom_db=target_headroom_db_value,
            job_id=job_id
        )

        filename = Path(output_path).name
        audio_url = f"/api/audio/{filename}"

        if job_id:
            ProgressManager.done(job_id)

        return {
            "audio_url": audio_url,
            "filename": filename,
            "success": True,
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
        raise HTTPException(status_code=500, detail=f"Chyba při generování: {msg}")


@app.get("/api/tts/progress/{job_id}")
async def get_tts_progress(job_id: str):
    """Vrátí průběh generování pro daný job_id (pro polling z frontendu)."""
    info = ProgressManager.get(job_id)
    if not info:
        # Pokud job ještě neexistuje, vrať "pending" stav místo 404
        # (frontend může začít pollovat dřív, než backend stihne job zaregistrovat)
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


@app.get("/api/tts/progress/{job_id}/stream")
async def stream_tts_progress(job_id: str):
    """
    Server-Sent Events (SSE) stream pro real-time progress updates.
    Frontend se připojí pomocí EventSource a dostane automatické aktualizace.
    """
    import json
    import asyncio

    async def event_generator():
        last_percent = -1
        last_updated = None

        while True:
            try:
                info = ProgressManager.get(job_id)

                if not info:
                    # Job ještě neexistuje - pošli pending stav
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
                    await asyncio.sleep(0.5)  # Počkej 500ms před dalším pokusem
                    continue

                status = info.get("status", "running")
                percent = info.get("percent", 0)
                updated_at = info.get("updated_at")

                # Poslat update pouze pokud se něco změnilo
                if percent != last_percent or updated_at != last_updated:
                    yield f"data: {json.dumps(info)}\n\n"
                    last_percent = percent
                    last_updated = updated_at

                # Pokud je job hotový nebo chybný, ukončit stream
                if status in ("done", "error"):
                    # Pošli finální stav a ukonči
                    yield f"data: {json.dumps(info)}\n\n"
                    break

                # Počkat 200ms před dalším checkem (rychlejší než polling)
                await asyncio.sleep(0.2)
            except asyncio.CancelledError:
                # Klient se odpojil - ukončit stream
                break
            except Exception as e:
                # Při chybě pošli error a ukonči
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
            "X-Accel-Buffering": "no",  # Vypnout buffering pro nginx
        }
    )


@app.post("/api/voice/upload")
async def upload_voice(voice_file: UploadFile = File(...)):
    """
    Nahraje audio soubor pro voice cloning

    Returns:
        voice_id: ID nahraného hlasu
    """
    try:
        # Uložení souboru
        file_ext = Path(voice_file.filename).suffix
        voice_id = str(uuid.uuid4())
        temp_filename = f"{voice_id}{file_ext}"
        temp_path = UPLOADS_DIR / temp_filename

        async with aiofiles.open(temp_path, 'wb') as f:
            content = await voice_file.read()
            await f.write(content)

        # Zpracování
        processed_path, error = AudioProcessor.process_uploaded_file(
            str(temp_path),
            f"{voice_id}.wav"
        )

        if error:
            raise HTTPException(status_code=400, detail=error)

        # Analýza kvality
        quality_info = AudioProcessor.analyze_audio_quality(processed_path)

        return {
            "voice_id": voice_id,
            "processed": True,
            "file_path": processed_path,
            "quality": quality_info
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při uploadu: {str(e)}")


@app.post("/api/asr/transcribe")
async def transcribe_reference_audio(
    voice_file: UploadFile = File(None),
    demo_voice: str = Form(None),
    language: str = Form("sk"),
):
    """
    Přepíše referenční audio na text (ref_text) pomocí Whisper.

    Vstup:
      - voice_file: nahraný soubor (upload)
      - demo_voice: id/název demo hlasu (bez přípony)
      - language: "sk" (výchozí) nebo "cs"/"auto" (zatím používáme hlavně pro SK prompt)
    """
    try:
        if (voice_file is None) == (demo_voice is None):
            raise HTTPException(status_code=400, detail="Zadejte buď voice_file, nebo demo_voice.")

        audio_path = None

        if voice_file is not None:
            # Ulož do uploads a zpracuj na WAV (mono, sr, apod.) pro stabilnější ASR
            file_ext = Path(voice_file.filename).suffix
            temp_filename = f"{uuid.uuid4()}{file_ext}"
            temp_path = UPLOADS_DIR / temp_filename
            async with aiofiles.open(temp_path, "wb") as f:
                content = await voice_file.read()
                await f.write(content)

            processed_path, error = AudioProcessor.process_uploaded_file(str(temp_path))
            if error:
                raise HTTPException(status_code=400, detail=error)
            audio_path = processed_path
        else:
            demo_path = get_demo_voice_path(demo_voice, lang=language)
            if not demo_path:
                raise HTTPException(status_code=404, detail=f"Demo hlas '{demo_voice}' nebyl nalezen.")
            audio_path = demo_path

        # Whisper ASR
        res = asr_engine.transcribe_file(
            audio_path,
            language=language or "sk",
            task="transcribe",
            return_timestamps=True,
        )

        return {
            "success": True,
            "text": res.text,
            "cleaned_text": res.cleaned_text,
            "language": res.language,
            "segments": res.segments,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při přepisu audia: {str(e)}")


@app.post("/api/voice/record")
async def record_voice(
    audio_blob: str = Form(...),
    filename: str = Form(None),
    lang: str = Form("cs"),
):
    """
    Uloží audio nahrané z mikrofonu jako demo hlas

    Body:
        audio_blob: Base64 encoded audio data
        filename: Název souboru (volitelné, výchozí: record_{uuid}.wav)
    """
    try:
        # Dekódování base64
        audio_data = base64.b64decode(audio_blob.split(',')[1])

        # Určení názvu souboru
        if filename:
            # Sanitizace názvu souboru
            from backend.youtube_downloader import sanitize_filename
            filename = sanitize_filename(filename)
        else:
            filename = f"record_{uuid.uuid4().hex[:8]}"

        # Zajištění .wav přípony
        if not filename.endswith('.wav'):
            filename = f"{filename}.wav"

        # Uložení do dočasného souboru
        temp_path = UPLOADS_DIR / f"temp_{uuid.uuid4()}.wav"
        with open(temp_path, 'wb') as f:
            f.write(audio_data)

        # Zpracování pomocí AudioProcessor (44100 Hz, mono, pokročilé zpracování - CD kvalita)
        demo_dir = _get_demo_voices_dir(lang)
        output_path = demo_dir / filename
        success, error = AudioProcessor.convert_audio(
            str(temp_path),
            str(output_path),
            apply_advanced_processing=True
        )

        # Smazat dočasný soubor
        temp_path.unlink(missing_ok=True)

        if not success:
            raise HTTPException(status_code=400, detail=error)

        # Validace výstupního souboru (mírnější pro nahrávání z mikrofonu)
        # Zkontroluj délku před validací
        try:
            import librosa
            duration = librosa.get_duration(path=str(output_path))
            if duration < 3.0:  # Minimálně 3 sekundy pro nahrávání z mikrofonu
                output_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=400,
                    detail=f"Audio je příliš krátké ({duration:.1f}s). Minimálně 3 sekundy pro nahrávání z mikrofonu, doporučeno 6+ sekund pro lepší kvalitu."
                )
            elif duration < MIN_VOICE_DURATION:
                # Varování, ale povolit
                logger.warning(f"Recorded audio is short ({duration:.1f}s), recommended minimum is {MIN_VOICE_DURATION}s")
        except Exception as e:
            output_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail=f"Chyba při validaci audio: {str(e)}")

        # Základní validace (formát, existence)
        path = Path(output_path)
        if not path.exists():
            raise HTTPException(status_code=400, detail="Soubor neexistuje")

        if path.suffix.lower() != ".wav":
            raise HTTPException(status_code=400, detail="Nepodporovaný formát")

        # Vytvoření URL pro přístup k souboru
        audio_url = f"/api/audio/demo/{_normalize_demo_lang(lang)}/{filename}"

        # Analýza kvality
        quality_info = AudioProcessor.analyze_audio_quality(str(output_path))

        return {
            "success": True,
            "filename": filename,
            "audio_url": audio_url,
            "file_path": str(output_path),
            "quality": quality_info
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při ukládání nahrávky: {str(e)}")


@app.get("/api/voices/demo")
async def get_demo_voices(lang: str = Query("cs")):
    """Vrátí seznam dostupných demo hlasů"""
    demo_voices = []

    lang_norm = _normalize_demo_lang(lang)
    demo_dir = _get_demo_voices_dir(lang_norm)

    for voice_file in demo_dir.glob("*.wav"):
        voice_id = voice_file.stem
        voice_id_lower = voice_id.lower()

        # Zkus určit pohlaví z názvu
        # Kontrolujeme nejdřív "female", protože má přednost pokud jsou obě přítomny
        gender = "unknown"
        gender_keywords = []

        has_female = "female" in voice_id_lower or "žena" in voice_id_lower or "demo2" in voice_id_lower
        has_male = "male" in voice_id_lower or "muž" in voice_id_lower or "demo1" in voice_id_lower

        if has_female:
            gender = "female"
            # Přidej klíčová slova pro odstranění (v lowercase pro konzistenci)
            if "female" in voice_id_lower:
                gender_keywords.append("female")
            if "žena" in voice_id_lower:
                gender_keywords.append("žena")
            if "demo2" in voice_id_lower:
                gender_keywords.append("demo2")
        elif has_male:
            gender = "male"
            # Přidej klíčová slova pro odstranění (v lowercase pro konzistenci)
            if "male" in voice_id_lower:
                gender_keywords.append("male")
            if "muž" in voice_id_lower:
                gender_keywords.append("muž")
            if "demo1" in voice_id_lower:
                gender_keywords.append("demo1")

        # Vyčisti název od klíčových slov pohlaví (case-insensitive)
        clean_name = voice_id
        for keyword in gender_keywords:
            # Odstraň klíčové slovo s podtržítky/pomlčkami kolem (case-insensitive pomocí regex)
            keyword_escaped = re.escape(keyword)
            # Pattern pro nalezení klíčového slova s okolními separátory nebo na začátku/konci
            # Odstraní: _keyword_, -keyword-, _keyword, keyword_, -keyword, keyword-, keyword (na začátku/konci)
            pattern = rf"[-_]?{keyword_escaped}[-_]?"
            clean_name = re.sub(pattern, "", clean_name, flags=re.IGNORECASE)

        # Vyčisti název od přebytečných podtržítků a pomlček
        clean_name = re.sub(r"[-_]+", "_", clean_name)
        clean_name = clean_name.strip("_-")

        # Formátuj název
        formatted_name = clean_name.replace("_", " ").title() if clean_name else voice_id.replace("_", " ").title()

        # Vytvoř zobrazovaný název s pohlavím na začátku
        if gender == "male":
            display_name = f"Muž: {formatted_name}"
        elif gender == "female":
            display_name = f"Žena: {formatted_name}"
        else:
            display_name = formatted_name

        demo_voices.append({
            "id": voice_id,
            "name": formatted_name,
            "display_name": display_name,
            "gender": gender,
            "lang": lang_norm,
            "preview_url": f"/api/audio/demo/{lang_norm}/{voice_file.name}"
        })

    return {"voices": demo_voices}


@app.get("/api/models/status")
async def get_model_status():
    """Vrátí status modelu"""
    return tts_engine.get_status()


@app.get("/api/audio/{filename}")
async def get_audio(filename: str):
    """Vrátí audio soubor"""
    # Validace filename proti path traversal
    if '..' in filename or '/' in filename or '\\' in filename:
        raise HTTPException(status_code=400, detail="Neplatný název souboru")

    # Resolve cesty a kontrola, že zůstává v OUTPUTS_DIR
    try:
        file_path = (OUTPUTS_DIR / filename).resolve()
        outputs_dir_resolved = OUTPUTS_DIR.resolve()

        # Kontrola, že file_path je uvnitř OUTPUTS_DIR
        if not str(file_path).startswith(str(outputs_dir_resolved)):
            raise HTTPException(status_code=403, detail="Přístup zamítnut")
    except (ValueError, OSError) as e:
        raise HTTPException(status_code=400, detail=f"Neplatná cesta: {str(e)}")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio soubor neexistuje")

    return FileResponse(
        str(file_path),
        media_type="audio/wav",
        filename=filename,
        headers={
            # Explicitní CORS pro případ, že klient načítá audio jako "media" request.
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
    )


@app.get("/api/audio/demo/{filename:path}")
async def get_demo_audio(filename: str):
    """Vrátí demo audio soubor"""
    # Podpora /api/audio/demo/{lang}/{filename} i původního /api/audio/demo/{filename}
    norm = filename.replace("\\", "/").strip("/")
    if norm == "" or ".." in norm:
        raise HTTPException(status_code=400, detail="Neplatný název souboru")

    parts = norm.split("/", 1)
    if len(parts) == 2 and parts[0].lower() in ("cs", "sk"):
        lang_norm = _normalize_demo_lang(parts[0])
        fname = parts[1]
    else:
        lang_norm = "cs"
        fname = norm

    # fname nesmí obsahovat další podsložky
    if "/" in fname or "\\" in fname or ".." in fname:
        raise HTTPException(status_code=400, detail="Neplatný název souboru")

    demo_dir = _get_demo_voices_dir(lang_norm)

    # Resolve cesty a kontrola, že zůstává v demo_dir
    try:
        file_path = (demo_dir / fname).resolve()
        demo_dir_resolved = demo_dir.resolve()

        # Kontrola, že file_path je uvnitř DEMO_VOICES_DIR
        if not str(file_path).startswith(str(demo_dir_resolved)):
            raise HTTPException(status_code=403, detail="Přístup zamítnut")
    except (ValueError, OSError) as e:
        raise HTTPException(status_code=400, detail=f"Neplatná cesta: {str(e)}")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Demo audio neexistuje")

    return FileResponse(
        str(file_path),
        media_type="audio/wav",
        filename=filename,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
    )


@app.post("/api/voice/youtube")
async def download_youtube_voice(
    url: str = Form(...),
    start_time: float = Form(None),
    duration: float = Form(None),
    filename: str = Form(None),
    lang: str = Form("cs"),
):
    """
    Stáhne audio z YouTube a uloží jako demo hlas

    Body:
        url: YouTube URL
        start_time: Začátek ořezu v sekundách (volitelné)
        duration: Délka ořezu v sekundách (volitelné)
        filename: Název souboru (volitelné, výchozí: youtube_{video_id}.wav)
    """
    try:
        # Validace URL
        is_valid, error = validate_youtube_url(url)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error)

        # Validace časových parametrů
        if start_time is not None and start_time < 0:
            raise HTTPException(status_code=400, detail="start_time musí být >= 0")

        if duration is not None:
            if duration < MIN_VOICE_DURATION:
                raise HTTPException(
                    status_code=400,
                    detail=f"duration musí být minimálně {MIN_VOICE_DURATION} sekund"
                )
            if duration > 600:  # Max 10 minut
                raise HTTPException(
                    status_code=400,
                    detail="duration nesmí přesáhnout 600 sekund (10 minut)"
                )

        # Získání informací o videu (pro validaci)
        video_info, error = get_video_info(url)
        if error:
            raise HTTPException(status_code=400, detail=error)

        if video_info:
            video_duration = video_info.get('duration', 0)
            if video_duration > 0:
                # Kontrola, že start_time + duration nepřesahuje délku videa
                if start_time is not None and duration is not None:
                    if start_time + duration > video_duration:
                        raise HTTPException(
                            status_code=400,
                            detail=f"start_time + duration ({start_time + duration:.1f}s) přesahuje délku videa ({video_duration:.1f}s)"
                        )

        # Určení názvu souboru
        if filename:
            filename = sanitize_filename(filename)
        else:
            video_id = extract_video_id(url)
            if video_id:
                filename = f"youtube_{video_id}"
            else:
                filename = f"youtube_{uuid.uuid4().hex[:8]}"

        # Zajištění .wav přípony
        if not filename.endswith('.wav'):
            filename = f"{filename}.wav"

        # Výstupní cesta
        demo_dir = _get_demo_voices_dir(lang)
        output_path = demo_dir / filename

        # Stáhnutí a zpracování audio
        success, error = download_youtube_audio(
            url=url,
            output_path=str(output_path),
            start_time=start_time,
            duration=duration
        )

        if not success:
            raise HTTPException(status_code=500, detail=error)

        # Vytvoření URL pro přístup k souboru
        audio_url = f"/api/audio/demo/{_normalize_demo_lang(lang)}/{filename}"

        return {
            "success": True,
            "filename": filename,
            "audio_url": audio_url,
            "file_path": str(output_path),
            "video_info": video_info
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při stahování z YouTube: {str(e)}")


@app.get("/api/history")
async def get_history(limit: int = 50, offset: int = 0):
    """
    Získá historii generovaných audio souborů

    Query params:
        limit: Maximální počet záznamů (výchozí: 50)
        offset: Offset pro stránkování (výchozí: 0)
    """
    try:
        history = HistoryManager.get_history(limit=limit, offset=offset)
        stats = HistoryManager.get_stats()

        return {
            "history": history,
            "stats": stats,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při načítání historie: {str(e)}")


@app.get("/api/history/{entry_id}")
async def get_history_entry(entry_id: str):
    """Získá konkrétní záznam z historie"""
    try:
        entry = HistoryManager.get_entry_by_id(entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Záznam nenalezen")
        return entry
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při načítání záznamu: {str(e)}")


@app.delete("/api/history/{entry_id}")
async def delete_history_entry(entry_id: str):
    """Smaže záznam z historie"""
    try:
        success = HistoryManager.delete_entry(entry_id)
        if not success:
            raise HTTPException(status_code=404, detail="Záznam nenalezen")
        return {"success": True, "message": "Záznam smazán"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při mazání záznamu: {str(e)}")


@app.delete("/api/history")
async def clear_history():
    """Vymaže celou historii"""
    try:
        count = HistoryManager.clear_history()
        return {"success": True, "message": f"Historie vymazána ({count} záznamů)"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při mazání historie: {str(e)}")


if __name__ == "__main__":
    import logging
    from pathlib import Path

    # Načteme LOG_LEVEL (pokud ještě není načten z try/except bloku výše)
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
        reload=True,
        reload_dirs=[str(backend_dir)],  # Sledovat změny v backend adresáři
        reload_includes=["*.py"],  # Sledovat pouze Python soubory
        log_config=LOGGING_CONFIG,
    )

