"""
Knihovna ambience samplů (potůček / ptáci) z assets/nature.

Souborová konvence:
- stream_*.wav  -> potůček / voda
- birds_*.wav   -> ptáci
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from backend.config import BASE_DIR


@dataclass(frozen=True)
class AmbiencePick:
    kind: str
    path: Path


def _nature_dir() -> Path:
    return (BASE_DIR / "assets" / "nature").resolve()


def list_ambience(kind: str) -> List[Path]:
    k = (kind or "").strip().lower()
    d = _nature_dir()
    if not d.exists():
        return []

    if k == "stream":
        return sorted(d.glob("stream_*.wav"))
    if k == "birds":
        return sorted(d.glob("birds_*.wav"))
    return []


def pick_ambience(kind: str, seed: Optional[int] = None) -> Optional[AmbiencePick]:
    files = list_ambience(kind)
    if not files:
        return None
    rnd = random.Random(int(seed) if seed is not None else None)
    path = rnd.choice(files)
    return AmbiencePick(kind=kind, path=path)


def pick_many(kinds: List[str], seed: Optional[int] = None) -> List[AmbiencePick]:
    """
    Pickne maximálně 1 soubor pro každý typ (deterministicky podle seed).
    Seed se pro každý typ lehce posune, aby "both" dávalo stabilně různé volby.
    """
    out: List[AmbiencePick] = []
    base_seed = int(seed) if seed is not None else None
    for idx, k in enumerate(kinds):
        s = None if base_seed is None else base_seed + (idx * 997)
        p = pick_ambience(k, seed=s)
        if p:
            out.append(p)
    return out



