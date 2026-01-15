"""
Lightweight XTTS WebSocket Server for Chrome Extension
WebSocket-only architecture - fast, parallel, playlist support
"""

import sys
import os
import asyncio
import json
import uuid
import logging
import base64
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
import uvicorn
from colorama import init, Fore, Style

init(autoreset=True, strip=False)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("xtts_ws")

from backend.config import (
    API_HOST,
    API_PORT,
    DEMO_VOICES_CS_DIR,
    DEMO_VOICES_SK_DIR,
    OUTPUTS_DIR,
)
from backend.api.helpers import get_demo_voice_path
from backend.api.dependencies import tts_engine


# ============== WEBSOCKET MANAGER =============


class TTSWebSocketManager:
    def __init__(self):
        self.connections = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.connections[client_id] = websocket
        print(f"{Fore.CYAN}[WS] Client {client_id} connected{Style.RESET_ALL}")

    def disconnect(self, client_id: str):
        if client_id in self.connections:
            del self.connections[client_id]
            print(f"{Fore.CYAN}[WS] Client {client_id} disconnected{Style.RESET_ALL}")

    async def send_json(self, client_id: str, data: dict):
        if client_id in self.connections:
            try:
                await self.connections[client_id].send_json(data)
            except RuntimeError as e:
                if "close message" in str(e):
                    pass
            except Exception as e:
                print(
                    f"{Fore.RED}[WS] JSON send error to {client_id}: {e}{Style.RESET_ALL}"
                )


ws_manager = TTSWebSocketManager()


# ============== HELPER FUNCTIONS =============


async def handle_tts_request(client_id: str, data: dict):
    """Handle TTS generation request with request_id tracking"""
    text = data.get("text", "").strip()
    voice_id = data.get("voice", "ai-speakato-Vlasta-female")
    params = data.get("params", {})
    lang = data.get("lang", "cs")
    request_id = data.get("request_id", 0)
    stream_mode = data.get("stream", False)

    if not text:
        await ws_manager.send_json(
            client_id,
            {"type": "error", "message": "Empty text", "request_id": request_id},
        )
        return

    print(
        f"{Fore.CYAN}[WS] Client {client_id}: '{text[:50]}...' req={request_id} stream={stream_mode}{Style.RESET_ALL}"
    )

    voice_path = get_demo_voice_path(voice_id, lang)
    if not voice_path:
        await ws_manager.send_json(
            client_id,
            {
                "type": "error",
                "message": f"Voice not found: {voice_id}",
                "request_id": request_id,
            },
        )
        return

    speed = float(params.get("speed", 1.0))
    temperature = float(params.get("temperature", 0.96))
    length_penalty = float(params.get("length_penalty", 0.50))
    repetition_penalty = float(params.get("repetition_penalty", 1.00))
    top_k = int(params.get("top_k", 1))
    top_p = float(params.get("top_p", 1.00))
    seed = int(params.get("seed", 12))

    def read_file_base64(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    if stream_mode:
        import re as re_module

        CZ_ABBREVIATIONS_PY = {
            "např",
            "tj",
            "tzn",
            "tzv",
            "apod",
            "č",
            "resp",
            "popř",
            "event",
            "max",
            "min",
            "například",
            "takzvaný",
            "čís",
            "př",
            "n",
            "m",
            "k",
            "s",
            "v",
            "z",
            "u",
            "o",
            "i",
            "a",
        }

        def is_abbreviation(word):
            clean = word.lower().replace(".", "")
            return clean in CZ_ABBREVIATIONS_PY

        def split_into_sentences(t):
            # Přeskočit úvodní uvozovky a whitespace
            position = 0
            while position < len(t) and t[position] in ' "\n\r\t':
                position += 1

            sentences = []

            while position < len(t):
                found_end = False

                for i in range(position, len(t)):
                    char = t[i]

                    if char in ".!?":
                        is_abbrev_word = False
                        for j in range(i - 1, position - 1, -1):
                            if t[j] == " ":
                                break
                            if is_abbreviation(t[j : i + 1]):
                                is_abbrev_word = True
                                break

                        if is_abbrev_word:
                            continue

                        j = i + 1
                        while j < len(t) and t[j] in " \n\r\t":
                            j += 1

                        if j > i + 1 or i == len(t) - 1:
                            # Zkontrolovat, zda koncová uvozovka patří k větev
                            # Věta končí na: .?" nebo .? nebo ." nebo jen .
                            has_closing_quote = j < len(t) and t[j] == '"'

                            sentence = t[position:j].strip()
                            if sentence:
                                # Zabalit větu do uvozovek pro správné čtení TTS
                                if not sentence.startswith('"'):
                                    sentence = '"' + sentence + '"'
                                sentences.append(sentence)
                            position = j
                            found_end = True
                            break

                if not found_end:
                    remaining = t[position:].strip()
                    if remaining:
                        sentences.append(remaining)
                    break

            return [s for s in sentences if s]

        def wrap_sentence(sentence, max_size):
            if len(sentence) <= max_size:
                return [sentence]

            words = sentence.split(" ")
            wrapped = []
            current = ""

            for word in words:
                test = f"{current} {word}" if current else word
                if len(test) > max_size:
                    if current:
                        wrapped.append(current)
                    current = word
                else:
                    current = test
            if current:
                wrapped.append(current)
            return wrapped

        def split_into_chunks(
            sentences, min_size=150, max_size=300, enable_word_wrap=True
        ):
            chunks = []
            current_chunk = ""

            for sentence in sentences:
                wrapped_parts = (
                    wrap_sentence(sentence, max_size)
                    if enable_word_wrap
                    else [sentence]
                )

                for part in wrapped_parts:
                    test_chunk = f"{current_chunk} {part}" if current_chunk else part

                    if not current_chunk:
                        current_chunk = part
                    elif len(test_chunk) <= max_size:
                        current_chunk = test_chunk
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = part

            if current_chunk:
                chunks.append(current_chunk)
            return chunks

        def validate_chunks(chunks, original_text):
            reconstructed = " ".join(chunks).replace(r"\s+", " ").strip()
            original = original_text.replace(r"\s+", " ").strip()
            similarity = len(reconstructed) / max(len(original), 1)
            return {
                "isValid": similarity > 0.7,
                "chunkCount": len(chunks),
                "totalLength": sum(len(c) for c in chunks),
                "similarity": f"{round(similarity * 100)}%",
            }

        sentences = split_into_sentences(text)
        chunks = split_into_chunks(
            sentences, min_size=150, max_size=300, enable_word_wrap=True
        )
        validation = validate_chunks(chunks, text)

        print(
            f"{Fore.CYAN}[WS] Text processing: {len(sentences)} sentences -> {len(chunks)} chunks{Style.RESET_ALL}"
        )
        print(f"{Fore.CYAN}[WS] Validation: {validation}{Style.RESET_ALL}")
        if sentences:
            print(f"{Fore.CYAN}[WS] Sample sentences: {sentences[:3]}{Style.RESET_ALL}")

        if not chunks:
            chunks = [text]

        # Zpracovat chunks_with_pauses z JavaScriptu pokud existuje
        chunks_with_pauses = data.get("chunks_with_pauses", [])
        if chunks_with_pauses:
            # Použít pauzy z JavaScriptu
            pause_map = {c["index"]: c["pauseAfter"] for c in chunks_with_pauses}
        else:
            # Fallback: detekce pauzy v Pythonu (podpora českých uvozovek)
            pause_map = {}
            quote_chars = "\"'»«"
            for i, chunk in enumerate(chunks):
                # Ořezat uvozovky a odstranit formátování (... → .)
                cleaned = chunk.replace("...", ".").strip(quote_chars)
                # Detekovat konec věty: . ? ! nasledovane uvozovkami a whitespace
                has_pause = bool(re_module.search(r"[.?!][\"'»«]?\s*$", cleaned))
                pause_map[i] = 250 if has_pause else 0
                print(
                    f"{Fore.CYAN}[WS] Pause detection: '{cleaned[:50]}...' -> {pause_map[i]}ms{Style.RESET_ALL}"
                )

        await ws_manager.send_json(
            client_id,
            {
                "type": "status",
                "message": f"Streaming {len(chunks)} chunks...",
                "request_id": request_id,
            },
        )

        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                continue

            try:
                chunk_path = await tts_engine.generate(
                    text=chunk,
                    speaker_wav=voice_path,
                    language=lang,
                    speed=speed,
                    temperature=temperature,
                    length_penalty=length_penalty,
                    repetition_penalty=repetition_penalty,
                    top_k=top_k,
                    top_p=top_p,
                    seed=seed,
                    enable_normalization=False,
                    enable_denoiser=False,
                    enable_compressor=False,
                    enable_deesser=False,
                    enable_eq=False,
                    enable_trim=True,
                )

                b64_audio = read_file_base64(chunk_path)

                # Detekce pauzy - ořezat uvozovky, podpora českých uvozovek
                quote_chars = "\"'»«"
                cleaned_chunk = chunk.replace("...", ".").strip(quote_chars)
                has_pause = bool(re_module.search(r"[.?!][\"'»«]?\s*$", cleaned_chunk))
                pause_ms = pause_map.get(i, 250 if has_pause else 0)

                await ws_manager.send_json(
                    client_id,
                    {
                        "type": "audio_chunk",
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "audio": b64_audio,
                        "text": chunk,
                        "request_id": request_id,
                        "pause_after": pause_ms,
                    },
                )

                print(
                    f"{Fore.CYAN}[WS] Chunk {i + 1}/{len(chunks)} sent (pause: {pause_ms}ms){Style.RESET_ALL}"
                )

                try:
                    os.remove(chunk_path)
                except:
                    pass

            except Exception as chunk_err:
                print(f"{Fore.RED}[WS] Chunk {i} failed: {chunk_err}{Style.RESET_ALL}")

        await ws_manager.send_json(
            client_id,
            {
                "type": "stream_complete",
                "total_chunks": len(chunks),
                "request_id": request_id,
            },
        )
        print(f"{Fore.CYAN}[WS] Stream complete{Style.RESET_ALL}")
        return

    # STANDARD MODE (non-streaming)
    await ws_manager.send_json(
        client_id,
        {
            "type": "status",
            "message": "Generating...",
            "progress": 10,
            "request_id": request_id,
        },
    )

    try:
        output_path = await tts_engine.generate(
            text=text,
            speaker_wav=voice_path,
            language=lang,
            speed=speed,
            temperature=temperature,
            length_penalty=length_penalty,
            repetition_penalty=repetition_penalty,
            top_k=top_k,
            top_p=top_p,
            seed=seed,
        )

        await ws_manager.send_json(
            client_id,
            {
                "type": "status",
                "message": "Done",
                "progress": 90,
                "request_id": request_id,
            },
        )

        audio_url = f"http://{API_HOST}:{API_PORT}/audio/{Path(output_path).name}"

        await ws_manager.send_json(
            client_id,
            {
                "type": "done",
                "audio_url": audio_url,
                "local_path": output_path,
                "request_id": request_id,
                "text_preview": text[:100],
            },
        )

        print(
            f"{Fore.CYAN}[WS] Done sent to client {client_id}: {audio_url}{Style.RESET_ALL}"
        )

    except Exception as e:
        error_msg = str(e)
        print(
            f"{Fore.RED}[WS] Error for client {client_id}: {error_msg}{Style.RESET_ALL}"
        )
        await ws_manager.send_json(
            client_id, {"type": "error", "message": error_msg, "request_id": request_id}
        )
        return

    print(
        f"{Fore.CYAN}[WS] Client {client_id}: '{text[:50]}...' req={request_id}{Style.RESET_ALL}"
    )

    await ws_manager.send_json(
        client_id,
        {
            "type": "status",
            "message": "Generating...",
            "progress": 10,
            "request_id": request_id,
        },
    )

    voice_path = get_demo_voice_path(voice_id, lang)
    if not voice_path:
        await ws_manager.send_json(
            client_id,
            {
                "type": "error",
                "message": f"Voice not found: {voice_id}",
                "request_id": request_id,
            },
        )
        return

    speed = float(params.get("speed", 1.0))
    temperature = float(params.get("temperature", 0.96))
    length_penalty = float(params.get("length_penalty", 0.50))
    repetition_penalty = float(params.get("repetition_penalty", 1.00))
    top_k = int(params.get("top_k", 1))
    top_p = float(params.get("top_p", 1.00))
    seed = int(params.get("seed", 12))

    try:
        output_path = await tts_engine.generate(
            text=text,
            speaker_wav=voice_path,
            language=lang,
            speed=speed,
            temperature=temperature,
            length_penalty=length_penalty,
            repetition_penalty=repetition_penalty,
            top_k=top_k,
            top_p=top_p,
            seed=seed,
        )

        await ws_manager.send_json(
            client_id,
            {
                "type": "status",
                "message": "Done",
                "progress": 90,
                "request_id": request_id,
            },
        )

        audio_url = f"http://{API_HOST}:{API_PORT}/audio/{Path(output_path).name}"

        await ws_manager.send_json(
            client_id,
            {
                "type": "done",
                "audio_url": audio_url,
                "local_path": output_path,
                "request_id": request_id,
                "text_preview": text[:100],
            },
        )

        print(
            f"{Fore.GREEN}[WS] Client {client_id}: Done req={request_id}{Style.RESET_ALL}"
        )

    except Exception as e:
        error_msg = str(e)
        print(
            f"{Fore.RED}[WS] Client {client_id} error: {error_msg} req={request_id}{Style.RESET_ALL}"
        )
        await ws_manager.send_json(
            client_id, {"type": "error", "message": error_msg, "request_id": request_id}
        )


def get_voices_list(lang: str = "cs"):
    """Get list of demo voices"""
    voices_dir = DEMO_VOICES_SK_DIR if lang.startswith("sk") else DEMO_VOICES_CS_DIR

    voices = []
    for wav_file in sorted(voices_dir.glob("*.wav")):
        stem = wav_file.stem
        is_female = any(
            x in stem.lower()
            for x in [
                "female",
                "zena",
                "zeny",
                "holka",
                "divka",
                "erika",
                "evicka",
                "veronika",
                "vlasta",
            ]
        )
        voices.append(
            {
                "id": stem,
                "display_name": stem.replace("-", " ").replace("_", " ").title(),
                "gender": "female" if is_female else "male",
                "lang": lang,
            }
        )
    return voices


# ============== LIFESPAN =============


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}  XTTS WebSocket Server - Chrome Extension{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
    print()
    print(f"  WebSocket:  ws://{API_HOST}:{API_PORT}/ws/tts")
    print(f"  Voices WS:  ws://{API_HOST}:{API_PORT}/ws/voices")
    print(f"  Voices:     {DEMO_VOICES_CS_DIR}")
    print()
    print(f"{Fore.YELLOW}  Loading XTTS model...{Style.RESET_ALL}")

    try:
        await tts_engine.load_model()
        print(f"{Fore.GREEN}  ✓ Model loaded{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}  ✗ Failed: {e}{Style.RESET_ALL}")
    print()
    yield
    print(f"{Fore.YELLOW}Shutting down...{Style.RESET_ALL}")


app = FastAPI(title="XTTS WS Server", version="1.0.0", lifespan=lifespan)


# ============== WEBSOCKET ENDPOINTS =============


@app.websocket("/ws/tts")
async def websocket_tts(websocket: WebSocket):
    """Main TTS generation endpoint"""
    client_id = str(uuid.uuid4())[:8]

    try:
        await ws_manager.connect(websocket, client_id)

        while True:
            try:
                message = await websocket.receive_text()
            except RuntimeError:
                break
            data = json.loads(message)

            if data.get("type") == "generate":
                await handle_tts_request(client_id, data)
            elif data.get("type") == "stop":
                break

    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(client_id)


# ============== AUDIO SERVING =============


@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    """Serve generated audio files"""
    audio_path = OUTPUTS_DIR / filename
    if not audio_path.exists():
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(
        str(audio_path),
        media_type="audio/wav",
        headers={"Content-Disposition": f"inline; filename={filename}"},
    )


# ============== HEALTH CHECK =============


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "model_loaded": tts_engine.is_loaded,
        "voices_count": len(get_voices_list()),
    }


# ============== VOICES ENDPOINT =============


@app.get("/api/voices/demo")
async def get_demo_voices(lang: str = "cs"):
    """Get list of demo voices - HTTP endpoint"""
    voices = get_voices_list(lang)
    return {"voices": voices}


@app.get("/api/voices/demo/{voice_id}")
async def get_voice_info(voice_id: str, lang: str = "cs"):
    """Get info about a specific voice"""
    from fastapi import HTTPException

    voice_path = get_demo_voice_path(voice_id, lang)
    if not voice_path:
        raise HTTPException(status_code=404, detail="Voice not found")

    from pathlib import Path

    wav_path = Path(voice_path)
    is_female = any(
        x in voice_id.lower()
        for x in [
            "female",
            "zena",
            "zeny",
            "holka",
            "divka",
            "erika",
            "evicka",
            "veronika",
            "vlasta",
        ]
    )

    return {
        "id": voice_id,
        "display_name": voice_id.replace("-", " ").replace("_", " ").title(),
        "gender": "female" if is_female else "male",
        "lang": lang,
        "file": voice_path,
    }


# ============== MAIN =============

if __name__ == "__main__":
    print(f"{Fore.GREEN}Starting XTTS WS Server...{Style.RESET_ALL}")
    uvicorn.run(app, host=API_HOST, port=API_PORT, log_level="info", reload=False)
