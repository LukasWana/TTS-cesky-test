"""
Konvertor: textový slovník hantecu (formát "HANTEC ~ význam") -> JSON pro lookup_tables/hantec_slovnik.json

Použití (Windows/Unix):
  python scripts/convert_hantec_raw_to_json.py --in lookup_tables/hantec_slovnik_raw.txt --out lookup_tables/hantec_slovnik.json

Poznámka:
- Vstup má typicky řádky jako: "bakule ~ peníze"
  což znamená HANTEC -> standardní význam.
- Pro převod v TTS potřebujeme opačný směr: standardní -> hantec.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import DefaultDict, List


HEADER_RE = re.compile(r"^[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ]{1,3}$")


def _clean_text(s: str) -> str:
    s = s.strip()
    # pryč poznámky v závorkách
    s = re.sub(r"\([^)]*\)", "", s).strip()
    # sjednotit mezery
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _split_variants(left: str) -> List[str]:
    # "buk; bukál; bukva" -> ["buk", "bukál", "bukva"]
    parts = re.split(r"\s*;\s*", left.strip())
    out = []
    for p in parts:
        p = _clean_text(p)
        if p:
            out.append(p)
    return out


def _split_meanings(right: str) -> List[str]:
    # "vědomost, znalost" -> ["vědomost", "znalost"]
    # zachováme i víceslovné výrazy; dělíme jen na , a ;
    parts = re.split(r"\s*[,;]\s*", right.strip())
    out = []
    for p in parts:
        p = _clean_text(p)
        if p:
            out.append(p)
    return out


def parse_raw_to_standard_to_hantec(raw: str) -> dict:
    standard_to_hantec: DefaultDict[str, List[str]] = defaultdict(list)

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        # komentáře
        if line.startswith("#"):
            continue
        # ignorovat sekce (A, B, Č, ...)
        if HEADER_RE.match(line):
            continue
        delim = None
        if "~" in line:
            delim = "~"
        elif " - " in line:
            delim = " - "
        if delim is None:
            continue

        left, right = line.split(delim, 1)
        left = _clean_text(left)
        right = _clean_text(right)
        if not left or not right:
            continue

        hantec_variants = _split_variants(left)
        meanings = _split_meanings(right)
        if not hantec_variants or not meanings:
            continue

        for meaning in meanings:
            key = meaning.lower()
            for hv in hantec_variants:
                # ukládáme hantec varianty v původní podobě (kvůli diakritice)
                standard_to_hantec[key].append(hv)

    # dedup listů se zachováním pořadí
    normalized = {}
    for k, vals in standard_to_hantec.items():
        seen = set()
        uniq = []
        for v in vals:
            lv = v.lower()
            if lv in seen:
                continue
            seen.add(lv)
            uniq.append(v)
        if uniq:
            normalized[k] = uniq

    return {
        "description": "Slovník brněnského hantecu (standardní čeština -> hantec). Vygenerováno ze zdrojového textu.",
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "standard_to_hantec": normalized,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True, help="Vstupní raw text (HANTEC ~ význam)")
    ap.add_argument("--out", dest="out_path", required=True, help="Výstupní JSON")
    args = ap.parse_args()

    in_path = Path(args.in_path)
    out_path = Path(args.out_path)

    raw = in_path.read_text(encoding="utf-8")
    data = parse_raw_to_standard_to_hantec(raw)

    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] Vygenerováno: {out_path} (položek: {len(data.get('standard_to_hantec', {}))})")


if __name__ == "__main__":
    main()


