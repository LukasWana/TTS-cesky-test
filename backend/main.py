"""
FastAPI aplikace pro XTTS-v2 Demo
"""
import os
import base64
import uuid
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn
import aiofiles
try:
    from backend.tts_engine import XTTSEngine
    from backend.audio_processor import AudioProcessor
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
        MIN_VOICE_DURATION
    )
except ImportError:
    # Fallback pro spuštění z backend/ adresáře
    from tts_engine import XTTSEngine
    from audio_processor import AudioProcessor
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
        MIN_VOICE_DURATION
    )

# Inicializace FastAPI
app = FastAPI(title="XTTS-v2 Demo", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializace engine
tts_engine = XTTSEngine()

# Serve static files (frontend)
frontend_path = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")


@app.on_event("startup")
async def startup_event():
    """Načte model při startu aplikace"""
    try:
        await tts_engine.load_model()
        # Warmup s demo hlasem pokud existuje
        demo_voices = list(DEMO_VOICES_DIR.glob("*.wav"))
        if demo_voices:
            await tts_engine.warmup(str(demo_voices[0]))
    except Exception as e:
        print(f"Startup error: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "XTTS-v2 Demo API", "version": "1.0.0"}


@app.post("/api/tts/generate")
async def generate_speech(
    text: str = Form(...),
    voice_file: UploadFile = File(None),
    demo_voice: str = Form(None)
):
    """
    Generuje řeč z textu

    Body:
        text: Text k syntéze (max 500 znaků)
        voice_file: Nahraný audio soubor (volitelné)
        demo_voice: Název demo hlasu (volitelné)
    """
    try:
        # Validace textu
        if not text or len(text.strip()) == 0:
            raise HTTPException(status_code=400, detail="Text je prázdný")

        if len(text) > MAX_TEXT_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"Text je příliš dlouhý (max {MAX_TEXT_LENGTH} znaků)"
            )

        # Zpracování hlasu
        speaker_wav = None

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

        # Generování řeči
        output_path = await tts_engine.generate(
            text=text,
            speaker_wav=speaker_wav,
            language="cs"
        )

        # Vytvoření URL
        filename = Path(output_path).name
        audio_url = f"/api/audio/{filename}"

        return {
            "audio_url": audio_url,
            "filename": filename,
            "success": True
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při generování: {str(e)}")


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

        return {
            "voice_id": voice_id,
            "processed": True,
            "file_path": processed_path
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

        # Zpracování pomocí AudioProcessor (22050 Hz, mono, pokročilé zpracování)
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

        return {
            "success": True,
            "filename": filename,
            "audio_url": audio_url,
            "file_path": str(output_path)
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


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True
    )

