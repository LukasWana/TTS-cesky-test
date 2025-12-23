"""
Jednoduché mixování WAV: overlay ambience (potůček/ptáci) na MusicGen výstup.

Používá soundfile + librosa pro resample, takže není nutný FFmpeg.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import librosa
import soundfile as sf


@dataclass(frozen=True)
class LoadedAudio:
    y: np.ndarray  # shape: (T, C) float32
    sr: int


def _to_2d(y: np.ndarray) -> np.ndarray:
    if y.ndim == 1:
        return y[:, None]
    if y.ndim == 2:
        # soundfile vrací (T, C), librosa typicky (T,) nebo (C, T) – ošetříme níže
        return y
    raise ValueError("Neplatný tvar audio pole")


def load_audio(path: str | Path) -> LoadedAudio:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))

    try:
        y, sr = sf.read(str(p), always_2d=True, dtype="float32")
        return LoadedAudio(y=_to_2d(y).astype(np.float32, copy=False), sr=int(sr))
    except Exception:
        # fallback: librosa
        y, sr = librosa.load(str(p), sr=None, mono=False)
        if isinstance(y, np.ndarray) and y.ndim == 2:
            # librosa: (C, T) -> (T, C)
            y = y.T
        y = _to_2d(np.asarray(y, dtype=np.float32))
        return LoadedAudio(y=y, sr=int(sr))


def resample_to(audio: LoadedAudio, target_sr: int) -> LoadedAudio:
    if audio.sr == target_sr:
        return audio
    import time
    start = time.time()
    y = audio.y
    # resample po kanálech
    channels = []
    for c in range(y.shape[1]):
        channels.append(librosa.resample(y[:, c], orig_sr=audio.sr, target_sr=target_sr))
    y2 = np.stack(channels, axis=1).astype(np.float32)
    print(f"[Mixer] Resample {audio.sr}Hz -> {target_sr}Hz trval {time.time() - start:.2f}s")
    return LoadedAudio(y=y2, sr=int(target_sr))


def _loop_with_crossfade(y: np.ndarray, target_len: int, crossfade_len: int) -> np.ndarray:
    """
    Loopuje y do target_len. Na spojích použije krátký crossfade (lineární).
    y: (T, C)
    """
    if y.shape[0] <= 0:
        raise ValueError("Prázdné audio")
    if target_len <= y.shape[0]:
        return y[:target_len].copy()

    # crossfade_len nesmí být delší než polovina vzorku
    crossfade_len = min(crossfade_len, y.shape[0] // 2)

    parts = []
    current_len = 0

    # První kus
    first_chunk = y.copy()
    parts.append(first_chunk)
    current_len = first_chunk.shape[0]

    while current_len < target_len:
        # Kolik ještě potřebujeme?
        needed = target_len - current_len

        # Přidáme další loop
        chunk = y.copy()

        if crossfade_len > 0:
            # Crossfade mezi koncem parts[-1] a začátkem chunk
            n = crossfade_len

            # Konec předchozího kusu
            a = parts[-1][-n:]
            # Začátek nového kusu
            b = chunk[:n]

            # Lineární prolnutí
            t = np.linspace(0.0, 1.0, n, dtype=np.float32)[:, None]
            xf = a * (1.0 - t) + b * t

            # Upravíme konec předchozího kusu v seznamu
            parts[-1] = parts[-1][:-n]
            # Nový kus začíná prolnutím a zbytkem
            chunk = np.concatenate([xf, chunk[n:]], axis=0)

            # Přepočítáme aktuální délku (odečetli jsme n z konce parts[-1])
            current_len -= n

        # Pokud by byl nový kus delší než potřebujeme, ořízneme ho
        if chunk.shape[0] > (target_len - current_len):
            chunk = chunk[:(target_len - current_len)]

        if chunk.shape[0] <= 0:
            break

        parts.append(chunk)
        current_len += chunk.shape[0]

    out = np.concatenate(parts, axis=0)
    return out[:target_len]


def match_length_and_channels(
    audio: LoadedAudio,
    *,
    target_len: int,
    target_channels: int,
    loop: bool = True,
    crossfade_ms: int = 30,
) -> np.ndarray:
    y = audio.y

    # channels
    if y.shape[1] == 1 and target_channels == 2:
        y = np.repeat(y, 2, axis=1)
    elif y.shape[1] == 2 and target_channels == 1:
        y = np.mean(y, axis=1, keepdims=True)
    elif y.shape[1] != target_channels:
        # fallback: mixdown to mono then upmix
        y = np.mean(y, axis=1, keepdims=True)
        if target_channels == 2:
            y = np.repeat(y, 2, axis=1)

    # length
    if y.shape[0] == target_len:
        return y
    if not loop:
        out = np.zeros((target_len, y.shape[1]), dtype=np.float32)
        n = min(target_len, y.shape[0])
        out[:n] = y[:n]
        return out

    crossfade_len = int((crossfade_ms / 1000.0) * audio.sr)
    crossfade_len = max(0, min(crossfade_len, max(1, y.shape[0] // 4)))
    return _loop_with_crossfade(y, target_len=target_len, crossfade_len=crossfade_len)


def db_to_gain(db: float) -> float:
    return float(10.0 ** (float(db) / 20.0))


def overlay(
    base: LoadedAudio,
    overlay_audio: LoadedAudio,
    *,
    overlay_gain_db: float = -18.0,
    loop_overlay: bool = True,
    overlay_crossfade_ms: int = 30,
    soft_limit: bool = True,
) -> LoadedAudio:
    if base.sr != overlay_audio.sr:
        overlay_audio = resample_to(overlay_audio, base.sr)

    target_len = base.y.shape[0]
    target_channels = base.y.shape[1]

    print(f"[Mixer] Připravuji overlay (původní SR: {overlay_audio.sr}, cílová délka: {target_len} vzorků)")
    ov = match_length_and_channels(
        overlay_audio,
        target_len=target_len,
        target_channels=target_channels,
        loop=loop_overlay,
        crossfade_ms=overlay_crossfade_ms,
    )

    gain = db_to_gain(overlay_gain_db)
    print(f"[Mixer] Aplikuji mix (gain: {gain:.4f})")
    mixed = base.y + ov * gain

    if soft_limit:
        peak = float(np.max(np.abs(mixed))) if mixed.size else 0.0
        if peak > 0.99:
            print(f"[Mixer] Peak {peak:.2f} překročil limit, normalizuji...")
            mixed = mixed * (0.99 / peak)

    return LoadedAudio(y=mixed.astype(np.float32, copy=False), sr=base.sr)


def save_wav(audio: LoadedAudio, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(p), audio.y, audio.sr)


def make_loopable(audio: LoadedAudio, crossfade_ms: int = 3000) -> LoadedAudio:
    """
    Vytvoří plynulou smyčku tak, že konec skladby (crossfade_ms)
    přimíchá (fade-in) do začátku skladby (fade-out).
    Výsledná délka se zkrátí o crossfade_ms.
    """
    y = audio.y
    sr = audio.sr
    fade_samples = int((crossfade_ms / 1000.0) * sr)

    if y.shape[0] < fade_samples * 3:
        # Skladba je příliš krátká pro tak dlouhý crossfade
        return audio

    # Rozdělíme na části
    # [začátek_pro_prolnutí][střed][konec_pro_prolnutí]
    end_part = y[-fade_samples:].copy()
    main_part = y[:-fade_samples].copy()

    # Vytvoříme lineární váhy pro prolnutí
    t = np.linspace(0.0, 1.0, fade_samples, dtype=np.float32)[:, None]

    # Prolneme konec se začátkem
    # Začátek nové skladby = (původní_konec * (1-t)) + (původní_začátek * t)
    loop_start = end_part * (1.0 - t) + main_part[:fade_samples] * t

    # Složíme výsledek: [prolnutý_začátek] + [zbytek_středu]
    new_y = np.concatenate([loop_start, main_part[fade_samples:]], axis=0)

    print(f"[Mixer] Vytvořena plynulá smyčka (crossfade: {crossfade_ms}ms, nová délka: {new_y.shape[0]/sr:.2f}s)")
    return LoadedAudio(y=new_y, sr=sr)



