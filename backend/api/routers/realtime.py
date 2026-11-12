"""
Real-time WebSocket Router for TTS
Ports logic from main_xtts_ws.py to main FastAPI app
"""

import uuid
import json
import re
import base64
import os
import logging
from pathlib import Path
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from colorama import Fore, Style

from backend.config import (
    API_HOST,
    API_PORT,
    DEMO_VOICES_CS_DIR,
    DEMO_VOICES_SK_DIR,
    ENABLE_CZ_SPLIT_BY_COMMAS,
    CZ_SPLIT_MAX_WORDS,
    CZ_SPLIT_LANGUAGES,
)
from backend.api.helpers import get_demo_voice_path
from backend.api.dependencies import tts_engine
from backend.tts_engine import XTTSEngine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["realtime"])

# ============== WEBSOCKET MANAGER =============


class TTSWebSocketManager:
    def __init__(self):
        self.connections = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.connections[client_id] = websocket
        logger.info(f"WS Client {client_id} connected")

    def disconnect(self, client_id: str):
        if client_id in self.connections:
            del self.connections[client_id]
            logger.info(f"WS Client {client_id} disconnected")

    async def send_json(self, client_id: str, data: dict):
        if client_id in self.connections:
            try:
                await self.connections[client_id].send_json(data)
            except Exception as e:
                logger.error(f"WS JSON send error to {client_id}: {e}")


ws_manager = TTSWebSocketManager()

# ============== HELPER FUNCTIONS =============


async def handle_tts_request(client_id: str, data: dict):
    """Handle TTS generation request with request_id tracking"""
    text = data.get("text", "").strip()
    voice_id = data.get("voice", "ai-speakato-Vlasta-female")
    params = data.get("params", {})
    lang = data.get("lang", "cs")
    request_id = data.get("request_id", 0)

    if not text:
        await ws_manager.send_json(
            client_id,
            {"type": "error", "message": "Empty text", "request_id": request_id},
        )
        return

    # Inject explicit pauses after punctuation to force natural prosody
    # XTTS engine handles [pause:N] tags
    # DISABLED: Normalization causes numbers to be read aloud. Using manual pause_after in streaming instead.
    # text = re.sub(r'([.?!])\s+', r'\1 [pause:250] ', text)

    logger.info(f"WS Client {client_id}: '{text[:50]}...' req={request_id}")

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
    top_k = int(params.get("top_k", 100))
    top_p = float(params.get("top_p", 1.00))
    seed = int(params.get("seed", 12))

    try:
        # Check if loaded (lazy proxy handles this internally mostly, but explicit check doesn't hurt)
        if not tts_engine.is_loaded:
            await ws_manager.send_json(
                client_id,
                {
                    "type": "status",
                    "message": "Loading model...",
                    "progress": 5,
                    "request_id": request_id,
                },
            )

            # Helper to read file as base64

        def read_file_base64(path):
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")

        # STREAMING MODE
        if data.get("stream", False):
            # Použij dělení po čárkách, pokud je zapnuté
            if lang in CZ_SPLIT_LANGUAGES and ENABLE_CZ_SPLIT_BY_COMMAS:
                # Volat statickou metodu z XTTSEngine
                chunks = XTTSEngine._split_text_by_commas_and_words(text, lang)
                logger.info(
                    f"Streaming: {len(chunks)} chunks (CZ Split enabled, Max words: {CZ_SPLIT_MAX_WORDS})"
                )
            else:
                # Původní logika (fast_sentence_split) pro zpětnou kompatibilitu
                # Use simple sentence splitting for latency optimization
                # This ensures first chunk is small (one sentence) and returned quickly.
                # XTTS native splitter aggregates tokens up to 400, which causes delay.
                def fast_sentence_split(t):
                    # 1. First split by major punctuation (. ? ! newline)
                    parts = re.split(r"([.?!]+[\s\r\n]+)", t)

                # 1. First split by major punctuation (. ? ! newline)
                parts = re.split(r"([.?!]+[\s\r\n]+)", t)

                sentences = []
                current = ""

                for p in parts:
                    # Check if adding p would exceed limit significantly (if p is just delimiter, it's fine)
                    # But if 'current' is already big, we should have flushed it.

                    # If p is a delimiter
                    is_delimiter = bool(re.match(r"^[.?!]+[\s\r\n]+$", p))

                    if is_delimiter:
                        current += p
                        if current.strip():
                            sentences.append(current)
                        current = ""
                        continue

                    # If p is content
                    # If adding p fits in limit? (Try to keep under 150)
                    if len(current) + len(p) < 150:
                        current += p
                    else:
                        # 'p' itself might be huge, or current + p is huge.
                        # a) If current has content, flush it first (if it's a valid break point? No, p might be the rest of sentence)
                        # ideally we split 'p' further if it is long

                        # Combine what we have so far
                        temp_full = current + p

                        # If temp_full is > 150, we need to split it by secondary delimiters (comma, semi-colon)
                        # recursively or iteratively

                        sub_parts = re.split(r"([,;:]\s+)", temp_full)
                        sub_current = ""
                        for sub in sub_parts:
                            if len(sub_current) + len(sub) > 150:
                                if sub_current.strip():
                                    sentences.append(sub_current)
                                sub_current = sub
                            else:
                                sub_current += sub

                        current = sub_current

                if current.strip():
                    sentences.append(current)

                # Final safety pass: Hard split if any chunk > 160 chars (allow slight overflow for words)
                final_sentences = []
                for s in sentences:
                    if len(s) > 160:
                        # Split by space
                        words = s.split(" ")
                        tmp_s = ""
                        for w in words:
                            if len(tmp_s) + len(w) + 1 > 160:
                                if tmp_s.strip():
                                    final_sentences.append(tmp_s)
                                tmp_s = w + " "
                            else:
                                tmp_s += w + " "
                        if tmp_s.strip():
                            final_sentences.append(tmp_s)
                    else:
                        final_sentences.append(s)

                return final_sentences

            chunks = fast_sentence_split(text)
            # Fallback if split failed (no punctuation)
            if not chunks:
                chunks = [text]

            logger.info(f"Streaming: {len(chunks)} chunks (Latencified)")

            await ws_manager.send_json(
                client_id,
                {
                    "type": "status",
                    "message": f"Streaming {len(chunks)} chunks...",
                    "request_id": request_id,
                },
            )

            # --- COMPUTE CONDITIONING LATENTS ONCE ---
            gpt_cond_latent = None
            speaker_embedding = None
            try:
                from backend.speaker_adapter import get_speaker_adapter

                if tts_engine.is_loaded and hasattr(tts_engine, "model"):
                    adapter = get_speaker_adapter()
                    # Pass the underlying CoquiTTS model instance
                    latents = adapter.get_conditioning_latents(
                        voice_path, tts_engine.model
                    )
                    if latents:
                        gpt_cond_latent, speaker_embedding = latents
                        logger.info("✅ Conditioning latents cached for stream.")
            except Exception as e:
                logger.warning(f"Failed to cache latents: {e}")
            # -----------------------------------------

            for i, chunk in enumerate(chunks):
                # Skip empty chunks
                if not chunk.strip():
                    continue

                try:
                    # Force disable enhancements for speed in streaming
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
                        target_headroom_db=-12.0,
                        enable_normalization=False,
                        enable_denoiser=False,
                        enable_compressor=False,
                        enable_deesser=False,
                        enable_eq=False,
                        enable_trim=False,
                        gpt_cond_latent=gpt_cond_latent,
                        speaker_embedding=speaker_embedding,
                    )

                    # Setup raw audio data
                    b64_audio = read_file_base64(chunk_path)

                    # Send chunk
                    # Determine silence based on if chunk ends with punctuation
                    pause_ms = 0
                    if re.search(r"[.?!]\s*$", chunk):
                        pause_ms = 250

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

                    # Diagnostický log pro sledování odesílání
                    logger.info(
                        f"[WS] Sending chunk {i + 1}/{len(chunks)} to client {client_id}"
                    )

                    # Cleanup chunk file immediatey
                    try:
                        os.remove(chunk_path)
                    except:
                        pass

                except Exception as chunk_err:
                    logger.error(f"Streaming chunk {i} failed: {chunk_err}")

            # Done
            await ws_manager.send_json(
                client_id,
                {
                    "type": "stream_complete",
                    "total_chunks": len(chunks),
                    "request_id": request_id,
                },
            )

            # Diagnostický log
            logger.info(
                f"[WS] Stream complete sent to client {client_id}: {len(chunks)} chunks"
            )
            return

        # STANDARD MODE (Legacy)
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
            target_headroom_db=-12.0,
            enable_normalization=False,
            enable_denoiser=False,
            enable_compressor=False,
            enable_deesser=False,
            enable_eq=False,
            enable_trim=False,
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

        # Construct URL using the same logic as main.py serving /api/audio
        # The main app serves /api/audio from audio.router
        audio_url = f"/api/audio/{Path(output_path).name}"

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

        # Diagnostický log
        logger.info(f"[WS] Sending done to client {client_id}: {audio_url}")

    except Exception as e:
        error_msg = str(e)
        logger.error(f"WS Client {client_id} error: {error_msg} req={request_id}")
        await ws_manager.send_json(
            client_id, {"type": "error", "message": error_msg, "request_id": request_id}
        )


# ============== WEBSOCKET ENDPOINTS =============


@router.websocket("/ws/tts")
async def websocket_tts(websocket: WebSocket):
    """Main TTS generation endpoint"""
    client_id = str(uuid.uuid4())[:8]

    try:
        await ws_manager.connect(websocket, client_id)

        while True:
            message = await websocket.receive_text()
            try:
                data = json.loads(message)
                if data.get("type") == "generate":
                    await handle_tts_request(client_id, data)
                elif data.get("type") == "stop":
                    # Just break loop? Or just stop generation?
                    # Existing logic just breaks, which disconnects.
                    # Ideally we might want to support keeping connection open,
                    # but let's stick to original behavior for now.
                    break
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(client_id)


@router.websocket("/ws/voices")
async def websocket_voices(websocket: WebSocket):
    """
    Legacy endpoint for voices.
    The extension now uses HTTP /api/voices/demo, but we keep this if needed.
    """
    await websocket.accept()
    await websocket.close()
