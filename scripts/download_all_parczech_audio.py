#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pro stažení všech audio souborů z ParCzech4Speech korpusu.
Stáhne všechny TAR archivy, rozbalí je a připraví audio soubory pro použití.
"""

import os
import sys
import csv
import tarfile
import requests
from pathlib import Path
from typing import Dict, List, Set, Optional
from tqdm import tqdm
import json

# Nastavení UTF-8 pro Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Cesty
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data" / "parczech"
DOWNLOADS_DIR = DATA_DIR / "downloads"
AUDIO_EXTRACTED_DIR = DATA_DIR / "audio" / "extracted"
AUDIO_SELECTED_DIR = DATA_DIR / "audio" / "selected"
METADATA_DIR = DOWNLOADS_DIR

# URL základna pro LINDAT
LINDAT_BASE_URL = "https://lindat.mff.cuni.cz/repository/xmlui/bitstream/handle/11234/1-5404"

def find_existing_tar_files(downloads_dir: Path) -> Set[str]:
    """Najde všechny existující TAR soubory v downloads adresáři a podadresářích."""
    existing = set()

    # Hledat v hlavním adresáři
    for tar_file in downloads_dir.glob("*.tar"):
        existing.add(tar_file.name)

    # Hledat v podadresářích (např. audio_psp_raw)
    for subdir in downloads_dir.iterdir():
        if subdir.is_dir():
            for tar_file in subdir.glob("*.tar"):
                existing.add(tar_file.name)

    return existing

def download_file(url: str, dest_path: Path, chunk_size: int = 8192) -> bool:
    """Stáhne soubor s progress barem."""
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))

        dest_path.parent.mkdir(parents=True, exist_ok=True)

        with open(dest_path, 'wb') as f, tqdm(
            desc=f"Stahuji {dest_path.name}",
            total=total_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024
        ) as pbar:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))

        return True
    except Exception as e:
        print(f"❌ Chyba při stahování {url}: {e}")
        return False

def extract_tar(tar_path: Path, extract_dir: Path) -> bool:
    """Rozbalí TAR archiv."""
    try:
        print(f"📦 Rozbaluji {tar_path.name}...")
        with tarfile.open(tar_path, 'r:*') as tar:
            # Získat seznam souborů pro progress
            members = tar.getmembers()
            total = len(members)

            for member in tqdm(members, desc=f"Rozbaluji {tar_path.name}", total=total):
                tar.extract(member, extract_dir)

        print(f"✅ Rozbaleno: {tar_path.name}")
        return True
    except Exception as e:
        print(f"❌ Chyba při rozbalování {tar_path.name}: {e}")
        return False

def find_tar_file_in_downloads(filename: str, downloads_dir: Path) -> Optional[Path]:
    """Najde TAR soubor v downloads adresáři nebo podadresářích."""
    # Zkusit hlavní adresář
    tar_path = downloads_dir / filename
    if tar_path.exists():
        return tar_path

    # Zkusit podadresáře
    for subdir in downloads_dir.iterdir():
        if subdir.is_dir():
            tar_path = subdir / filename
            if tar_path.exists():
                return tar_path

    return None

def load_quarter_archives() -> List[Dict[str, str]]:
    """Načte seznam všech TAR archivů z metadata."""
    metadata_file = METADATA_DIR / "audioPSP-meta.quarterArchive.tsv"

    if not metadata_file.exists():
        print(f"❌ Metadata soubor neexistuje: {metadata_file}")
        return []

    archives = []
    with open(metadata_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            archives.append({
                'filename': row['archiveFileName'],
                'url': row['repositoryUrl'],
                'from_date': row['fromDate'],
                'to_date': row['toDate'],
                'file_count': int(row['cntFiles'])
            })

    return archives

def download_all_archives(archives: List[Dict[str, str]], downloads_dir: Path, force_redownload: bool = False) -> List[Path]:
    """Stáhne všechny TAR archivy, které ještě nejsou stažené."""
    downloaded = []
    existing_files = find_existing_tar_files(downloads_dir)

    print(f"📋 Nalezeno {len(existing_files)} již stažených souborů:")
    for f in sorted(existing_files):
        print(f"   ✓ {f}")

    for archive in tqdm(archives, desc="Kontroluji archivy"):
        filename = archive['filename']

        # Zkontrolovat, jestli už není stažený
        if filename in existing_files:
            tar_path = find_tar_file_in_downloads(filename, downloads_dir)
            if tar_path and tar_path.exists():
                file_size = tar_path.stat().st_size
                if file_size > 0:
                    print(f"⏭️  Přeskočeno (již staženo): {filename} ({file_size / (1024**3):.2f} GB)")
                    downloaded.append(tar_path)
                    continue

        # Stáhnout do hlavního downloads adresáře
        url = archive['url']
        tar_path = downloads_dir / filename

        print(f"📥 Stahuji {filename}...")
        if download_file(url, tar_path):
            downloaded.append(tar_path)
        else:
            print(f"⚠️  Nepodařilo se stáhnout {filename}")

    return downloaded

def extract_all_archives(tar_files: List[Path], extract_dir: Path, downloads_dir: Path) -> bool:
    """Rozbalí všechny TAR archivy."""
    extract_dir.mkdir(parents=True, exist_ok=True)

    success_count = 0
    for tar_path in tar_files:
        # Zkontrolovat, jestli už není rozbalený
        archive_name = tar_path.stem  # bez .tar
        archive_extract_dir = extract_dir / archive_name

        if archive_extract_dir.exists() and any(archive_extract_dir.iterdir()):
            print(f"⏭️  Přeskočeno (již rozbaleno): {tar_path.name}")
            success_count += 1
            continue

        if extract_tar(tar_path, extract_dir):
            success_count += 1

    # Také zkontrolovat existující TAR soubory, které nebyly v seznamu
    existing_files = find_existing_tar_files(downloads_dir)
    for filename in existing_files:
        tar_path = find_tar_file_in_downloads(filename, downloads_dir)
        if tar_path and tar_path not in tar_files:
            archive_name = tar_path.stem
            archive_extract_dir = extract_dir / archive_name

            if not (archive_extract_dir.exists() and any(archive_extract_dir.iterdir())):
                print(f"📦 Rozbaluji existující soubor: {filename}")
                if extract_tar(tar_path, extract_dir):
                    success_count += 1

    print(f"\n✅ Rozbaleno {success_count} archivů")
    return True

def create_audio_index(extract_dir: Path) -> Dict[str, List[Path]]:
    """Vytvoří index audio souborů podle cesty."""
    audio_index = {}

    print("🔍 Indexuji audio soubory...")
    for audio_file in tqdm(extract_dir.rglob("*.mp3")):
        # Cesta relativní k extract_dir
        rel_path = audio_file.relative_to(extract_dir)
        path_str = str(rel_path).replace('\\', '/')

        if path_str not in audio_index:
            audio_index[path_str] = []
        audio_index[path_str].append(audio_file)

    print(f"✅ Nalezeno {len(audio_index)} unikátních audio cest")
    return audio_index

def find_speakers_in_xml(xml_dir: Path) -> Dict[str, Set[str]]:
    """Najde všechny mluvčí a jejich audio soubory z XML souborů."""
    import xml.etree.ElementTree as ET

    speaker_audio_map = {}
    ns = {'tei': 'http://www.tei-c.org/ns/1.0'}

    print("🔍 Prohledávám XML soubory pro mluvčí a audio...")
    xml_files = list(xml_dir.rglob("*.ana.xml"))

    for xml_file in tqdm(xml_files, desc="Zpracovávám XML"):
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            # Najít všechny audio soubory
            audio_urls = []
            for media in root.findall('.//tei:media', ns):
                url_attr = media.get('url')
                if url_attr:
                    audio_urls.append(url_attr)

            # Najít všechny mluvčí
            for u in root.findall('.//tei:u', ns):
                speaker_id = u.get('who', '').lstrip('#')
                if speaker_id and audio_urls:
                    if speaker_id not in speaker_audio_map:
                        speaker_audio_map[speaker_id] = set()
                    speaker_audio_map[speaker_id].update(audio_urls)

        except Exception as e:
            print(f"⚠️  Chyba při zpracování {xml_file.name}: {e}")
            continue

    # Převést sety na seznamy pro JSON serializaci
    return {k: list(v) for k, v in speaker_audio_map.items()}

def main():
    """Hlavní funkce."""
    print("=" * 60)
    print("🎤 ParCzech4Speech - Stažení všech audio souborů")
    print("=" * 60)

    # 1. Načíst metadata
    print("\n📋 Načítám metadata...")
    archives = load_quarter_archives()
    if not archives:
        print("❌ Nepodařilo se načíst metadata. Ujistěte se, že máte stažený soubor audioPSP-meta.quarterArchive.tsv")
        return

    print(f"✅ Nalezeno {len(archives)} archivů v metadatech")

    # 2. Stáhnout všechny archivy (kromě těch, co už jsou stažené)
    print("\n📥 Kontroluji a stahuji TAR archivy...")
    tar_files = download_all_archives(archives, DOWNLOADS_DIR, force_redownload=False)

    if not tar_files:
        print("❌ Nepodařilo se stáhnout žádné archivy")
        return

    print(f"✅ Celkem {len(tar_files)} archivů k dispozici (včetně již stažených)")

    # 3. Rozbalit archivy
    print("\n📦 Rozbaluji archivy...")
    extract_dir = DOWNLOADS_DIR / "audio_psp_extracted"
    if not extract_all_archives(tar_files, extract_dir, DOWNLOADS_DIR):
        print("⚠️  Některé archivy se nepodařilo rozbalit")

    # 4. Vytvořit index audio souborů
    print("\n🔍 Vytvářím index audio souborů...")
    audio_index = create_audio_index(extract_dir)

    # Uložit index
    index_file = DATA_DIR / "audio_index.json"
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump({k: [str(p) for p in paths] for k, paths in audio_index.items()},
                 f, ensure_ascii=False, indent=2)
    print(f"✅ Index uložen do {index_file}")

    # 5. Najít mluvčí z XML
    print("\n🔍 Hledám mluvčí v XML souborech...")
    xml_dir = DATA_DIR / "tei_ana"
    if xml_dir.exists():
        speaker_audio_map = find_speakers_in_xml(xml_dir)

        # Uložit mapování
        mapping_file = DATA_DIR / "speaker_audio_mapping.json"
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(speaker_audio_map, f, ensure_ascii=False, indent=2)
        print(f"✅ Mapování mluvčí->audio uloženo do {mapping_file}")
        print(f"   Nalezeno {len(speaker_audio_map)} unikátních mluvčích")
    else:
        print(f"⚠️  XML adresář neexistuje: {xml_dir}")

    print("\n" + "=" * 60)
    print("✅ Hotovo! Všechny audio soubory jsou stažené a rozbalené.")
    print(f"📁 Audio soubory: {extract_dir}")
    print(f"📊 Index: {index_file}")
    if xml_dir.exists():
        print(f"🗣️  Mapování mluvčích: {mapping_file}")
    print("=" * 60)

if __name__ == "__main__":
    main()



