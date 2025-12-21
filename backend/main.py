"""
FastAPI aplikace pro XTTS-v2 Demo
"""
import os
import base64
import uuid
import time
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn
import aiofiles
from functools import lru_cache
from typing import Optional

# Potlačení deprecation warning z librosa (pkg_resources je zastaralé, ale knihovna ho ještě používá)
import warnings
warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated.*", category=UserWarning)

from backend.progress_manager import ProgressManager
try:
    from backend.tts_engine import XTTSEngine
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
        ENABLE_BATCH_PROCESSING
    )
except ImportError:
    # Fallback pro spuštění z backend/ adresáře
    from tts_engine import XTTSEngine
    from audio_processor import AudioProcessor
    from history_manager import HistoryManager
    from youtube_downloader import (
        download_youtube_audio,
        validate_youtube_url,
        get_video_info,
        extract_video_id,
        sanitize_filename
    )
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
        ENABLE_BATCH_PROCESSING
    )

# Inicializace engine
tts_engine = XTTSEngine()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler pro startup a shutdown"""
    # Startup
    try:
        await tts_engine.load_model()
        # Warmup s demo hlasem pokud existuje
        demo_voices = list(DEMO_VOICES_DIR.glob("*.wav"))
        if demo_voices:
            await tts_engine.warmup(str(demo_voices[0]))
    except Exception as e:
        print(f"Startup error: {str(e)}")

    yield  # Aplikace běží zde

    # Shutdown (volitelné, pokud potřebujete cleanup)
    # await tts_engine.cleanup()  # pokud máte cleanup metodu


# Inicializace FastAPI s lifespan
app = FastAPI(title="XTTS-v2 Demo", version="1.0.0", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    # FE dev servery typicky běží na 5173 (Vite), 3000 apod.
    # SSE (EventSource) je na CORS citlivé stejně jako fetch, takže povolíme lokální originy.
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    # Bezpečné povolení libovolného lokálního portu (např. Vite 5174 po kolizi).
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
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
        # Validace textu
        if not text or len(text.strip()) == 0:
            raise HTTPException(status_code=400, detail="Text je prázdný")

        # Automatická detekce multi-lang/speaker anotací
        # Pokud text obsahuje syntaxi [lang:speaker] nebo [lang], použij multi-lang endpoint
        import re
        multi_lang_pattern = re.compile(r'\[(\w+)(?::([^\]]+))?\]')
        has_multi_lang_annotations = bool(multi_lang_pattern.search(text))

        if has_multi_lang_annotations:
            # Přesměruj na multi-lang zpracování
            print(f"🔍 Detekovány multi-lang/speaker anotace v textu, používám multi-lang generování")
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
                demo_path = DEMO_VOICES_DIR / f"{demo_voice}.wav"
                if demo_path.exists():
                    default_speaker_wav = str(demo_path)
                else:
                    available_voices = list(DEMO_VOICES_DIR.glob("*.wav"))
                    if available_voices:
                        default_speaker_wav = str(available_voices[0])
                    else:
                        raise HTTPException(status_code=404, detail="Žádné demo hlasy nejsou k dispozici")
            else:
                available_voices = list(DEMO_VOICES_DIR.glob("*.wav"))
                if available_voices:
                    default_speaker_wav = str(available_voices[0])
                else:
                    raise HTTPException(status_code=400, detail="Musí být zadán voice_file nebo demo_voice")

            # Parsuj speaker mapping z textu (extrahuj všechny speaker_id)
            # Automaticky mapuj demo hlasy podle jejich názvů
            speaker_ids = set()
            for match in multi_lang_pattern.finditer(text):
                speaker_id = match.group(2)
                if speaker_id:
                    speaker_ids.add(speaker_id)

            # Vytvoř speaker mapping - automaticky zkus najít demo hlasy podle názvu
            speaker_map = {}
            if speaker_ids:
                for sid in speaker_ids:
                    # Zkus najít demo hlas podle názvu
                    demo_path = get_demo_voice_path(sid)
                    if demo_path:
                        speaker_map[sid] = demo_path
                        print(f"🎤 Speaker '{sid}' mapován na demo hlas: {demo_path}")
                    elif Path(sid).exists():
                        # Je to cesta k souboru
                        speaker_map[sid] = sid
                        print(f"🎤 Speaker '{sid}' mapován na soubor: {sid}")
                    else:
                        # Použij výchozího mluvčího
                        speaker_map[sid] = default_speaker_wav
                        print(f"🎤 Speaker '{sid}' mapován na výchozí hlas (demo hlas '{sid}' neexistuje)")

            # Nastavení parametrů
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

            enable_enh = (enable_enhancement.lower() == "true") if isinstance(enable_enhancement, str) else ENABLE_AUDIO_ENHANCEMENT
            enable_vad_flag = (enable_vad.lower() == "true") if isinstance(enable_vad, str) else None
            enable_norm = (enable_normalization.lower() == "true") if isinstance(enable_normalization, str) else True
            enable_den = (enable_denoiser.lower() == "true") if isinstance(enable_denoiser, str) else True
            enable_comp = (enable_compressor.lower() == "true") if isinstance(enable_compressor, str) else True
            enable_deess = (enable_deesser.lower() == "true") if isinstance(enable_deesser, str) else True
            enable_eq_flag = (enable_eq.lower() == "true") if isinstance(enable_eq, str) else True
            enable_trim_flag = (enable_trim.lower() == "true") if isinstance(enable_trim, str) else True

            # Generuj pomocí multi-lang metody
            # Výchozí jazyk je čeština (cs)
            output_path = await tts_engine.generate_multi_lang_speaker(
                text=text,
                default_speaker_wav=default_speaker_wav,
                default_language="cs",  # Výchozí jazyk je čeština
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
                enable_normalization=enable_norm,
                enable_denoiser=enable_den,
                enable_compressor=enable_comp,
                enable_deesser=enable_deess,
                enable_eq=enable_eq_flag,
                enable_trim=enable_trim_flag,
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
            print(f"⚠️ Text je delší než {MAX_TEXT_LENGTH} znaků ({text_length} znaků), automaticky zapínám batch processing")
            # Automaticky zapnout batch pokud není explicitně zakázán
            if enable_batch is None or (isinstance(enable_batch, str) and enable_batch.lower() != "false"):
                use_batch = True
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Text je příliš dlouhý ({text_length} znaků, max {MAX_TEXT_LENGTH}). Pro delší texty zapněte batch processing (enable_batch=true)."
                )
        elif text_length > 2000:  # Pro středně dlouhé texty doporučit batch
            print(f"ℹ️ Text je dlouhý ({text_length} znaků), doporučuji zapnout batch processing pro lepší kvalitu")
            use_batch = (enable_batch.lower() == "true" if isinstance(enable_batch, str) else None) if enable_batch else ENABLE_BATCH_PROCESSING
        else:
            use_batch = (enable_batch.lower() == "true" if isinstance(enable_batch, str) else None) if enable_batch else None

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
            demo_path = DEMO_VOICES_DIR / f"{demo_voice}.wav"
            if not demo_path.exists():
                # Zkus najít jakýkoliv WAV soubor v demo-voices
                available_voices = list(DEMO_VOICES_DIR.glob("*.wav"))
                if available_voices:
                    # Použij první dostupný demo hlas
                    speaker_wav = str(available_voices[0])
                    print(f"Demo voice '{demo_voice}' not found, using: {speaker_wav}")
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Demo hlas '{demo_voice}' neexistuje a žádné demo hlasy nejsou k dispozici. Prosím nahrajte audio soubor."
                    )
            else:
                speaker_wav = str(demo_path)
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
                do_allow = request_allow if request_allow is not None else REFERENCE_ALLOW_POOR_BY_DEFAULT

                if do_auto:
                    enhanced_path = UPLOADS_DIR / f"enhanced_{uuid.uuid4().hex[:10]}.wav"
                    ok, enh_err = AudioProcessor.enhance_voice_sample(speaker_wav, str(enhanced_path))
                    if ok:
                        speaker_wav = str(enhanced_path)
                        reference_quality = AudioProcessor.analyze_audio_quality(speaker_wav)
                    else:
                        print(f"⚠️ Auto-enhance referenčního hlasu selhal: {enh_err}")

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
            print(f"⚠️ Quality gate selhal (ignorováno): {e}")

        # Nastavení TTS parametrů (použij výchozí hodnoty pokud nejsou zadány)
        # Parsování speed - může být string z Form, takže převedeme na float
        if speed is not None:
            try:
                if isinstance(speed, str):
                    tts_speed = float(speed)
                else:
                    tts_speed = float(speed)
            except (ValueError, TypeError):
                print(f"⚠️ Warning: Neplatná hodnota speed '{speed}', použiji výchozí {TTS_SPEED}")
                tts_speed = TTS_SPEED
        else:
            tts_speed = TTS_SPEED

        # (bez debug logů)

        tts_temperature = temperature if temperature is not None else TTS_TEMPERATURE
        tts_length_penalty = length_penalty if length_penalty is not None else TTS_LENGTH_PENALTY
        tts_repetition_penalty = repetition_penalty if repetition_penalty is not None else TTS_REPETITION_PENALTY
        tts_top_k = top_k if top_k is not None else TTS_TOP_K
        tts_top_p = top_p if top_p is not None else TTS_TOP_P

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

        # Pokud je zadán quality_mode, použij ho místo jednotlivých parametrů
        if tts_quality_mode:
            # Quality mode přepíše jednotlivé parametry
            pass  # Parametry budou aplikovány v tts_engine pomocí presetu
        else:
            # Použij jednotlivé parametry nebo výchozí hodnoty
            pass

        # Určení enhancement nastavení
        use_enhancement = enable_enhancement.lower() == "true" if enable_enhancement else ENABLE_AUDIO_ENHANCEMENT
        enhancement_preset_value = enhancement_preset if enhancement_preset else (quality_mode if quality_mode else AUDIO_ENHANCEMENT_PRESET)

        # Nové parametry
        use_multi_pass = multi_pass.lower() == "true" if multi_pass else False
        multi_pass_count_value = multi_pass_count if multi_pass_count is not None else 3
        use_vad = enable_vad.lower() == "true" if enable_vad else None
        # use_batch je už nastaveno výše podle délky textu - NEPŘEPISOVAT!
        use_hifigan_value = use_hifigan.lower() == "true" if use_hifigan else False
        use_normalization = enable_normalization.lower() == "true" if enable_normalization else True
        use_denoiser = enable_denoiser.lower() == "true" if enable_denoiser else True
        use_compressor = enable_compressor.lower() == "true" if enable_compressor else True
        use_deesser = enable_deesser.lower() == "true" if enable_deesser else True
        use_eq = enable_eq.lower() == "true" if enable_eq else True
        use_trim = enable_trim.lower() == "true" if enable_trim else True

        # Dialect conversion parametry
        use_dialect = enable_dialect_conversion.lower() == "true" if enable_dialect_conversion else False
        dialect_code_value = dialect_code if dialect_code and dialect_code != "standardni" else None
        try:
            dialect_intensity_value = float(dialect_intensity) if dialect_intensity else 1.0
        except (ValueError, TypeError):
            dialect_intensity_value = 1.0

        # Dočasně změnit ENABLE_AUDIO_ENHANCEMENT pokud je zadáno v requestu
        original_enhancement = ENABLE_AUDIO_ENHANCEMENT
        original_preset = AUDIO_ENHANCEMENT_PRESET

        try:
            # Dočasně změnit globální nastavení
            import backend.config as config_module
            config_module.ENABLE_AUDIO_ENHANCEMENT = use_enhancement
            config_module.AUDIO_ENHANCEMENT_PRESET = enhancement_preset_value

            # Generování řeči
            if job_id:
                ProgressManager.update(job_id, percent=1, stage="tts", message="Generuji řeč…")
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
                multi_pass=use_multi_pass,
                multi_pass_count=multi_pass_count_value,
                enable_batch=use_batch,
                enable_vad=use_vad,
                use_hifigan=use_hifigan_value,
                enable_normalization=use_normalization,
                enable_denoiser=use_denoiser,
                enable_compressor=use_compressor,
                enable_deesser=use_deesser,
                enable_eq=use_eq,
                enable_trim=use_trim,
                enable_dialect_conversion=use_dialect,
                dialect_code=dialect_code_value,
                dialect_intensity=dialect_intensity_value,
                job_id=job_id
            )
        finally:
            # Obnovit původní nastavení
            config_module.ENABLE_AUDIO_ENHANCEMENT = original_enhancement
            config_module.AUDIO_ENHANCEMENT_PRESET = original_preset

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


def get_demo_voice_path(demo_voice_name: str) -> Optional[str]:
    """
    Vrátí cestu k demo hlasu nebo None pokud neexistuje

    Podporuje názvy s podtržítky, pomlčkami, velkými písmeny a mezerami.
    Vyhledávání je case-insensitive a ignoruje mezery na začátku/konci.

    Args:
        demo_voice_name: Název demo hlasu (např. "buchty01", "Pohadka_muz", "Klepl-Bolzakov-rusky")

    Returns:
        Cesta k WAV souboru nebo None
    """
    if not demo_voice_name:
        return None

    # Odstraň mezery na začátku/konci
    demo_voice_name = demo_voice_name.strip()

    # Nejdříve zkus přesný název (case-sensitive)
    demo_path = DEMO_VOICES_DIR / f"{demo_voice_name}.wav"
    if demo_path.exists():
        return str(demo_path)

    # Pak zkus case-insensitive vyhledávání
    # Projdeme všechny WAV soubory a porovnáme názvy (bez přípony)
    for wav_file in DEMO_VOICES_DIR.glob("*.wav"):
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
            demo_path = get_demo_voice_path(default_demo_voice)
            if demo_path:
                default_speaker_wav = demo_path
            else:
                # Zkus najít jakýkoliv WAV soubor v demo-voices
                available_voices = list(DEMO_VOICES_DIR.glob("*.wav"))
                if available_voices:
                    default_speaker_wav = str(available_voices[0])
                    print(f"Demo voice '{default_demo_voice}' not found, using: {default_speaker_wav}")
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Demo hlas '{default_demo_voice}' neexistuje a žádné demo hlasy nejsou k dispozici."
                    )
        else:
            # Zkus použít první dostupný demo hlas
            available_voices = list(DEMO_VOICES_DIR.glob("*.wav"))
            if available_voices:
                default_speaker_wav = str(available_voices[0])
                print(f"Žádný výchozí hlas zadán, používám: {default_speaker_wav}")
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Musí být zadán buď default_voice_file nebo default_demo_voice, nebo musí existovat demo hlasy"
                )

        # Parsuj speaker mapping
        # Nejdříve automaticky zkus najít demo hlasy podle názvů v textu
        speaker_map = {}
        import re
        multi_lang_pattern = re.compile(r'\[(\w+)(?::([^\]]+))?\]')
        speaker_ids_from_text = set()
        for match in multi_lang_pattern.finditer(text):
            speaker_id = match.group(2)
            if speaker_id:
                speaker_ids_from_text.add(speaker_id)

        # Automaticky mapuj demo hlasy podle jejich názvů
        for sid in speaker_ids_from_text:
            demo_path = get_demo_voice_path(sid)
            if demo_path:
                speaker_map[sid] = demo_path
                print(f"🎤 Auto-mapování: Speaker '{sid}' -> demo hlas: {demo_path}")
            elif Path(sid).exists():
                speaker_map[sid] = sid
                print(f"🎤 Auto-mapování: Speaker '{sid}' -> soubor: {sid}")

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
                        demo_path = get_demo_voice_path(voice_ref)
                        if demo_path:
                            speaker_map[speaker_id] = demo_path
                        else:
                            print(f"[WARN] Speaker '{speaker_id}': voice '{voice_ref}' neexistuje, použije se výchozí hlas")
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
        enable_norm = (enable_normalization.lower() == "true") if isinstance(enable_normalization, str) else True
        enable_den = (enable_denoiser.lower() == "true") if isinstance(enable_denoiser, str) else True
        enable_comp = (enable_compressor.lower() == "true") if isinstance(enable_compressor, str) else True
        enable_deess = (enable_deesser.lower() == "true") if isinstance(enable_deesser, str) else True
        enable_eq_flag = (enable_eq.lower() == "true") if isinstance(enable_eq, str) else True
        enable_trim_flag = (enable_trim.lower() == "true") if isinstance(enable_trim, str) else True

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
            enable_normalization=enable_norm,
            enable_denoiser=enable_den,
            enable_compressor=enable_comp,
            enable_deesser=enable_deess,
            enable_eq=enable_eq_flag,
            enable_trim=enable_trim_flag,
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


@app.post("/api/voice/record")
async def record_voice(
    audio_blob: str = Form(...),
    filename: str = Form(None)
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
        output_path = DEMO_VOICES_DIR / filename
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
                print(f"Warning: Recorded audio is short ({duration:.1f}s), recommended minimum is {MIN_VOICE_DURATION}s")
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
        audio_url = f"/api/audio/demo/{filename}"

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
async def get_demo_voices():
    """Vrátí seznam dostupných demo hlasů"""
    demo_voices = []

    for voice_file in DEMO_VOICES_DIR.glob("*.wav"):
        voice_id = voice_file.stem
        # Zkus určit pohlaví z názvu
        gender = "unknown"
        if "male" in voice_id.lower() or "muž" in voice_id.lower() or "demo1" in voice_id:
            gender = "male"
        elif "female" in voice_id.lower() or "žena" in voice_id.lower() or "demo2" in voice_id:
            gender = "female"

        demo_voices.append({
            "id": voice_id,
            "name": voice_id.replace("_", " ").title(),
            "gender": gender,
            "preview_url": f"/api/audio/demo/{voice_file.name}"
        })

    return {"voices": demo_voices}


@app.get("/api/models/status")
async def get_model_status():
    """Vrátí status modelu"""
    return tts_engine.get_status()


@app.get("/api/audio/{filename}")
async def get_audio(filename: str):
    """Vrátí audio soubor"""
    file_path = OUTPUTS_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio soubor neexistuje")

    return FileResponse(
        str(file_path),
        media_type="audio/wav",
        filename=filename
    )


@app.get("/api/audio/demo/{filename}")
async def get_demo_audio(filename: str):
    """Vrátí demo audio soubor"""
    file_path = DEMO_VOICES_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Demo audio neexistuje")

    return FileResponse(
        str(file_path),
        media_type="audio/wav",
        filename=filename
    )


@app.post("/api/voice/youtube")
async def download_youtube_voice(
    url: str = Form(...),
    start_time: float = Form(None),
    duration: float = Form(None),
    filename: str = Form(None)
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
        output_path = DEMO_VOICES_DIR / filename

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
        audio_url = f"/api/audio/demo/{filename}"

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
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True
    )

