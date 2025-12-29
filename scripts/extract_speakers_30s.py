#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pro extrakci 20 nejkvalitnějších hlasů (10 mužů, 10 žen) z ParCzech4Speech.
Vybere mluvčí s různým věkem a nejlepší kvalitou audio.
Stahuje jen potřebné TAR archivy postupně a extrahuje jen malé segmenty.
"""

import os
import sys
import csv
import tarfile
import requests
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime
from collections import defaultdict
from tqdm import tqdm
from pydub import AudioSegment
import numpy as np

# Nastavení UTF-8 pro Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Cesty
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data" / "parczech"
DOWNLOADS_DIR = DATA_DIR / "downloads"
AUDIO_SELECTED_DIR = DATA_DIR / "audio" / "selected"
XML_DIR = DATA_DIR / "tei_ana"
METADATA_DIR = DOWNLOADS_DIR
TEMP_DIR = DOWNLOADS_DIR / "temp_extract"
PERSON_LIST_XML = XML_DIR / "ParCzech.TEI.ana" / "ParCzech-listPerson.xml"

# Konfigurace
TARGET_AUDIO_LENGTH_SEC = 30  # 30 sekund od každého mluvčího
TARGET_SPEAKERS = 20  # Celkem 20 mluvčích
TARGET_MALE = 10  # 10 mužů
TARGET_FEMALE = 10  # 10 žen
MIN_QUALITY_SCORE = 30.0  # Minimální skóre kvality pro výběr audio

# Přidat backend do cesty pro import
sys.path.insert(0, str(BASE_DIR))

def find_existing_tar_files(downloads_dir: Path) -> Set[str]:
    """Najde všechny existující TAR soubory."""
    existing = set()
    for tar_file in downloads_dir.glob("*.tar"):
        existing.add(tar_file.name)
    for subdir in downloads_dir.iterdir():
        if subdir.is_dir() and subdir.name != "temp_extract":
            for tar_file in subdir.glob("*.tar"):
                existing.add(tar_file.name)
    return existing

def find_tar_file_in_downloads(filename: str, downloads_dir: Path) -> Optional[Path]:
    """Najde TAR soubor v downloads adresáři nebo podadresářích."""
    tar_path = downloads_dir / filename
    if tar_path.exists():
        return tar_path
    for subdir in downloads_dir.iterdir():
        if subdir.is_dir() and subdir.name != "temp_extract":
            tar_path = subdir / filename
            if tar_path.exists():
                return tar_path
    return None

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

def extract_single_file_from_tar(tar_path: Path, file_path_in_tar: str, extract_to: Path) -> Optional[Path]:
    """Extrahuje jeden soubor z TAR archivu bez rozbalení celého archivu."""
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Najít soubor v archivu - zkusit přesnou cestu
            member = None
            try:
                member = tar.getmember(file_path_in_tar)
            except KeyError:
                # Zkusit najít podle názvu souboru
                filename = Path(file_path_in_tar).name
                for m in tar.getmembers():
                    if m.name.endswith(filename) or filename in m.name:
                        member = m
                        break

                if not member:
                    return None

            # Extrahovat do dočasného adresáře
            extract_to.parent.mkdir(parents=True, exist_ok=True)
            tar.extract(member, extract_to.parent)

            # Najít extrahovaný soubor
            extracted_path = extract_to.parent / member.name
            if extracted_path.exists():
                # Pokud je cesta jiná, přesunout
                if extracted_path != extract_to:
                    if extract_to.exists():
                        extract_to.unlink()
                    extract_to.parent.mkdir(parents=True, exist_ok=True)
                    extracted_path.rename(extract_to)
                return extract_to
            return extracted_path if extracted_path.exists() else None
    except Exception as e:
        print(f"⚠️  Chyba při extrakci {file_path_in_tar} z {tar_path.name}: {e}")
        return None

def load_audio_file_mapping(metadata_file: Path) -> Dict[str, str]:
    """Načte mapování audio souborů na archivy z metadata."""
    mapping = {}
    if not metadata_file.exists():
        print(f"⚠️  Metadata soubor neexistuje: {metadata_file}")
        return mapping

    print(f"📋 Načítám mapování audio souborů z {metadata_file.name}...")
    with open(metadata_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in tqdm(reader, desc="Načítám metadata"):
            file_path = row['filePath']
            archive = row['archiveFileName']
            mapping[file_path] = archive

    print(f"✅ Načteno {len(mapping)} mapování")
    return mapping

def load_quarter_archives() -> Dict[str, Dict]:
    """Načte metadata o archivech."""
    metadata_file = METADATA_DIR / "audioPSP-meta.quarterArchive.tsv"
    archives = {}

    if not metadata_file.exists():
        return archives

    with open(metadata_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            archives[row['archiveFileName']] = {
                'url': row['repositoryUrl'],
                'from_date': row['fromDate'],
                'to_date': row['toDate']
            }

    return archives

def load_speaker_metadata(person_list_xml: Path) -> Dict[str, Dict]:
    """
    Načte metadata o mluvčích z ParCzech-listPerson.xml.
    Vrací dict: person_id -> {gender, birth_date, age, name, person_id}
    """
    metadata = {}
    if not person_list_xml.exists():
        print(f"⚠️  Person list XML neexistuje: {person_list_xml}")
        return metadata

    print(f"📋 Načítám metadata o mluvčích z {person_list_xml.name}...")
    ns = {'tei': 'http://www.tei-c.org/ns/1.0'}

    try:
        tree = ET.parse(person_list_xml)
        root = tree.getroot()

        # Referenční datum pro výpočet věku (střed korpusu - 2020)
        reference_date = datetime(2020, 1, 1)

        for person in tqdm(root.findall('.//tei:person', ns), desc="Načítám osoby"):
            person_id = person.get('xml:id', '')
            if not person_id:
                continue

            # Získat pohlaví
            sex_elem = person.find('.//tei:sex', ns)
            gender = sex_elem.get('value', '') if sex_elem is not None else ''

            # Získat datum narození
            birth_elem = person.find('.//tei:birth', ns)
            birth_date_str = birth_elem.get('when', '') if birth_elem is not None else ''

            # Vypočítat věk
            age = None
            if birth_date_str:
                try:
                    birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d')
                    age = (reference_date - birth_date).days // 365
                except:
                    pass

            # Získat jméno
            pers_name = person.find('.//tei:persName', ns)
            name_parts = []
            if pers_name is not None:
                surname = pers_name.find('.//tei:surname', ns)
                forename = pers_name.find('.//tei:forename', ns)
                if surname is not None and surname.text:
                    name_parts.append(surname.text)
                if forename is not None and forename.text:
                    name_parts.append(forename.text)
            name = ' '.join(name_parts) if name_parts else person_id

            # Uložit metadata
            # Person ID je ve formátu "JménoPříjmení.rok" (např. "AdamKalous.1979")
            metadata[person_id] = {
                'gender': gender,
                'birth_date': birth_date_str,
                'age': age,
                'name': name,
                'person_id': person_id
            }

            # Také uložit pod base_id (bez roku) pro případné mapování
            base_id = person_id.split('.')[0] if '.' in person_id else person_id
            if base_id != person_id and base_id not in metadata:
                metadata[base_id] = metadata[person_id].copy()

        print(f"✅ Načteno {len(metadata)} záznamů o mluvčích")

    except Exception as e:
        print(f"❌ Chyba při načítání metadata: {e}")
        import traceback
        traceback.print_exc()

    return metadata

def map_speaker_to_person(speaker_id: str, speaker_metadata: Dict[str, Dict]) -> Optional[Dict]:
    """
    Mapuje speaker_id na metadata osoby.

    V ParCzech XML je speaker_id ve formátu "JménoPříjmení.rok" (např. "MiroslavaNemcova.1952"),
    což přímo odpovídá person_id v ParCzech-listPerson.xml.

    Pokud není přímá shoda, zkusíme najít podle různých variant.
    """
    # Přímá shoda (nejčastější případ)
    if speaker_id in speaker_metadata:
        return speaker_metadata[speaker_id]

    # Zkusit najít podle base_id (bez roku)
    base_id = speaker_id.split('.')[0] if '.' in speaker_id else speaker_id
    if base_id in speaker_metadata:
        return speaker_metadata[base_id]

    # Zkusit najít podle části ID
    # Speaker ID může obsahovat person ID nebo naopak
    for person_id, person_data in speaker_metadata.items():
        if person_id in speaker_id or speaker_id in person_id:
            return person_data

    # Zkusit najít podle jména v ID
    # Speaker ID může obsahovat jméno (např. "AdamKalous" v nějakém formátu)
    for person_id, person_data in speaker_metadata.items():
        name = person_data.get('name', '').replace(' ', '')
        if name and name.lower() in speaker_id.lower():
            return person_data

    return None

def parse_xml_for_speakers(xml_file: Path) -> Dict[str, List[Dict]]:
    """
    Parsuje XML soubor a najde všechny mluvčí s jejich audio segmenty.
    Vrací: {speaker_id: [{'audio_url': str, 'start_ms': int, 'end_ms': int, 'text': str}, ...]}
    """
    ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
    speaker_segments = {}

    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        # Najít všechny audio soubory a jejich timeline
        audio_timelines = {}
        for timeline in root.findall('.//tei:timeline', ns):
            timeline_id = timeline.get('xml:id', '')
            for when in timeline.findall('.//tei:when', ns):
                when_id = when.get('xml:id', '')
                interval = float(when.get('interval', 0))  # v milisekundách

                # Uložit časovou značku
                if timeline_id not in audio_timelines:
                    audio_timelines[timeline_id] = {}
                audio_timelines[timeline_id][when_id] = interval

        # Najít všechny media elementy
        audio_media = {}
        for media in root.findall('.//tei:media', ns):
            media_id = media.get('xml:id', '')
            url = media.get('url', '')
            if url:
                audio_media[media_id] = url

        # Najít všechny mluvčí a jejich segmenty
        for u in root.findall('.//tei:u', ns):
            speaker_id = u.get('who', '').lstrip('#')
            if not speaker_id:
                continue

            if speaker_id not in speaker_segments:
                speaker_segments[speaker_id] = []

            # Najít první anchor pro začátek segmentu
            first_anchor = u.find('.//tei:anchor', ns)
            if first_anchor is None:
                continue

            synch_start = first_anchor.get('synch', '').lstrip('#')
            if not synch_start:
                continue

            # Najít audio soubor pro tento segment
            audio_url = None
            # Zkusit najít podle corresp na pb nebo div
            for pb in root.findall('.//tei:pb', ns):
                corresp = pb.get('corresp', '')
                if corresp:
                    audio_ref = corresp.lstrip('#').split('.')[0]
                    if audio_ref in audio_media:
                        audio_url = audio_media[audio_ref]
                        break

            if not audio_url and audio_media:
                # Zkusit najít první audio soubor
                audio_url = list(audio_media.values())[0]

            if audio_url:
                # Získat časové značky z timeline
                start_ms = 0
                end_ms = TARGET_AUDIO_LENGTH_SEC * 1000  # 30 sekund

                # Zkusit najít přesné časy z timeline
                for timeline_id, timeline in audio_timelines.items():
                    if synch_start in timeline:
                        start_ms = int(timeline[synch_start])
                        end_ms = start_ms + (TARGET_AUDIO_LENGTH_SEC * 1000)
                        break

                # Získat text (prvních pár slov)
                text_parts = []
                for w in u.findall('.//tei:w', ns)[:10]:  # Prvních 10 slov
                    if w.text:
                        text_parts.append(w.text)
                text = ' '.join(text_parts)

                speaker_segments[speaker_id].append({
                    'audio_url': audio_url,
                    'start_ms': start_ms,
                    'end_ms': end_ms,
                    'text': text,
                    'xml_file': str(xml_file.relative_to(XML_DIR))
                })

    except Exception as e:
        # Tichá chyba - některé XML soubory mohou být poškozené
        pass

    return speaker_segments

def find_speakers_in_all_xml(xml_dir: Path, max_files: Optional[int] = None) -> Dict[str, List[Dict]]:
    """Najde všechny mluvčí ve všech XML souborech."""
    all_speaker_segments = {}
    xml_files = list(xml_dir.rglob("*.ana.xml"))

    if max_files:
        xml_files = xml_files[:max_files]

    print(f"🔍 Prohledávám {len(xml_files)} XML souborů...")

    for xml_file in tqdm(xml_files, desc="Parsuji XML"):
        segments = parse_xml_for_speakers(xml_file)
        for speaker_id, segs in segments.items():
            if speaker_id not in all_speaker_segments:
                all_speaker_segments[speaker_id] = []
            all_speaker_segments[speaker_id].extend(segs)

    # Pro každého mluvčího vezmeme nejlepší segment (pokud je více možností)
    # Pozn.: Výběr nejkvalitnějšího se provede později při extrakci, když máme přístup k archivům
    result = {}
    for speaker_id, segs in all_speaker_segments.items():
        if segs:
            # Pokud má mluvčí více segmentů, uložíme všechny pro pozdější výběr
            # Pokud má jen jeden, použijeme ho
            result[speaker_id] = segs

    return result

def extract_audio_segment(audio_path: Path, start_ms: int, end_ms: int, output_path: Path) -> bool:
    """Extrahuje segment z audio souboru."""
    try:
        audio = AudioSegment.from_mp3(str(audio_path))
        # Omezit délku na TARGET_AUDIO_LENGTH_SEC
        actual_end = min(end_ms, start_ms + (TARGET_AUDIO_LENGTH_SEC * 1000))
        segment = audio[start_ms:actual_end]
        segment.export(str(output_path), format="wav")
        return True
    except Exception as e:
        print(f"⚠️  Chyba při extrakci segmentu z {audio_path.name}: {e}")
        return False

def calculate_quality_score(quality_analysis: Dict) -> float:
    """
    Vypočítá celkové skóre kvality audio souboru.
    Kombinuje různé metriky do jednoho čísla (čím vyšší, tím lepší).

    Args:
        quality_analysis: Výsledek AudioProcessor.analyze_audio_quality()

    Returns:
        Skóre 0-100 (100 = nejlepší kvalita)
    """
    snr = quality_analysis.get('snr', 0)
    clipping_ratio = quality_analysis.get('clipping_ratio', 1.0)
    duration = quality_analysis.get('duration', 0)
    speech_ratio = quality_analysis.get('speech_ratio', 0)
    audio_type = quality_analysis.get('audio_type', 'unknown')
    has_music = quality_analysis.get('has_music', False)

    # 1. SNR skóre (0-40 bodů)
    # SNR > 30 dB = 40 bodů, SNR < 10 dB = 0 bodů
    snr_score = min(40, max(0, (snr - 10) / 20 * 40))

    # 2. Clipping skóre (0-20 bodů)
    # Žádné clipping = 20 bodů, > 5% clipping = 0 bodů
    clipping_score = max(0, 20 * (1 - clipping_ratio / 0.05))

    # 3. Speech ratio skóre (0-20 bodů)
    # 100% řeč = 20 bodů, < 50% řeč = 0 bodů
    speech_score = min(20, speech_ratio * 20)

    # 4. Audio type skóre (0-10 bodů)
    # speech = 10, mixed = 5, music/unknown = 0
    type_score = 10 if audio_type == 'speech' else (5 if audio_type == 'mixed' else 0)

    # 5. Duration skóre (0-10 bodů)
    # 10-30 sekund = 10 bodů, < 6 sekund = 0 bodů
    if 10 <= duration <= 30:
        duration_score = 10
    elif 6 <= duration < 10:
        duration_score = 5 + (duration - 6) / 4 * 5  # 5-10 bodů
    elif duration > 30:
        duration_score = max(5, 10 - (duration - 30) / 30 * 5)  # 5-10 bodů
    else:
        duration_score = 0

    # Penalizace za hudbu v pozadí
    music_penalty = -5 if has_music else 0

    # Celkové skóre
    total_score = snr_score + clipping_score + speech_score + type_score + duration_score + music_penalty

    return max(0, min(100, total_score))

def analyze_audio_quality_simple(audio_path: Path) -> Dict:
    """
    Jednoduchá analýza kvality audio souboru bez závislosti na backend modulu.
    Používá pouze librosa a numpy.
    """
    try:
        import librosa
        audio, sr = librosa.load(str(audio_path), sr=None)

        # SNR estimation (zjednodušené)
        rms_total = np.sqrt(np.mean(audio**2))
        if rms_total == 0:
            snr = 0
        else:
            win_length = 2048
            hop_length = 512
            if len(audio) < win_length:
                snr = 20.0
            else:
                rms_windows = librosa.feature.rms(y=audio, frame_length=win_length, hop_length=hop_length)[0]
                noise_floor = np.percentile(rms_windows, 10)
                if noise_floor == 0:
                    snr = 50.0
                else:
                    snr = 20 * np.log10(rms_total / (noise_floor + 1e-10))
                    snr = max(0, snr)

        # Clipping detection
        clipping_ratio = np.sum(np.abs(audio) >= 0.99) / len(audio)

        # Duration
        duration = librosa.get_duration(y=audio, sr=sr)

        # Speech ratio estimation (zjednodušené - pomocí spektrálních vlastností)
        # Řeč má typicky více energie v pásmu 1-4 kHz
        spectral_centroids = librosa.feature.spectral_centroid(y=audio, sr=sr)[0]
        mean_centroid = np.mean(spectral_centroids)
        zcr = librosa.feature.zero_crossing_rate(audio)[0]
        mean_zcr = np.mean(zcr)

        # Heuristika: pokud je ZCR vysoké a centroid je v rozsahu řeči, je to pravděpodobně řeč
        is_speech_like = (
            mean_zcr > 0.05 and
            mean_centroid > 500 and mean_centroid < 3000
        )

        speech_ratio = 0.8 if is_speech_like else 0.3
        audio_type = 'speech' if is_speech_like else 'mixed'

        return {
            'snr': float(snr),
            'clipping_ratio': float(clipping_ratio),
            'duration': float(duration),
            'speech_ratio': speech_ratio,
            'audio_type': audio_type,
            'has_music': False,
            'classification_available': False
        }
    except Exception as e:
        return {
            'snr': 0,
            'clipping_ratio': 1.0,
            'duration': 0,
            'speech_ratio': 0,
            'audio_type': 'unknown',
            'has_music': False,
            'classification_available': False,
            'error': str(e)
        }

def select_best_segment_for_speaker(segments: List[Dict], audio_mapping: Dict[str, str],
                                    archives_metadata: Dict, downloads_dir: Path) -> Optional[Dict]:
    """
    Vybere nejkvalitnější audio segment pro mluvčího z více možností.

    Args:
        segments: Seznam segmentů pro mluvčího
        audio_mapping: Mapování audio souborů na archivy
        archives_metadata: Metadata o archivech
        downloads_dir: Adresář se staženými archivy

    Returns:
        Nejlepší segment nebo None
    """
    if not segments:
        return None

    if len(segments) == 1:
        return segments[0]

    # Analyzovat kvalitu všech segmentů
    results = []

    for seg in segments:
        audio_url = seg['audio_url']
        archive_name = audio_mapping.get(audio_url)

        if not archive_name:
            continue

        # Zkusit najít archiv
        tar_path = find_tar_file_in_downloads(archive_name, downloads_dir)
        if not tar_path or not tar_path.exists():
            # Archiv není stažený - přeskočit (nebudeme stahovat jen pro analýzu)
            continue

        # Extrahovat audio dočasně pro analýzu
        temp_audio_path = TEMP_DIR / f"quality_check_{hash(audio_url)}_{Path(audio_url).name}"

        try:
            audio_file = extract_single_file_from_tar(tar_path, audio_url, temp_audio_path)

            if audio_file and audio_file.exists():
                # Extrahovat segment do dočasného WAV
                temp_segment = TEMP_DIR / f"segment_{hash(audio_url)}.wav"

                if extract_audio_segment(audio_file, seg['start_ms'], seg['end_ms'], temp_segment):
                    # Analyzovat kvalitu
                    quality = analyze_audio_quality_simple(temp_segment)
                    score = calculate_quality_score(quality)

                    results.append({
                        'segment': seg,
                        'score': score,
                        'quality': quality,
                        'archive': archive_name
                    })

                    # Smazat dočasné soubory
                    if temp_segment.exists():
                        temp_segment.unlink()

                # Smazat dočasný audio soubor
                if temp_audio_path.exists():
                    temp_audio_path.unlink()
                if audio_file != temp_audio_path and audio_file.exists():
                    try:
                        if audio_file.parent != TEMP_DIR:
                            audio_file.unlink()
                    except:
                        pass
        except Exception as e:
            # Tichá chyba - přeskočit tento segment
            continue

    if not results:
        # Pokud se nepodařilo analyzovat žádný segment, vrátit první
        return segments[0]

    # Seřadit podle skóre (nejlepší první)
    results.sort(key=lambda x: x['score'], reverse=True)

    # Filtrovat podle minimální kvality
    valid_results = [r for r in results if r['score'] >= MIN_QUALITY_SCORE]

    if not valid_results:
        # Pokud žádný nesplňuje minimální kvalitu, použít nejlepší dostupný
        valid_results = results

    best = valid_results[0]

    return best['segment']

def select_best_speakers(
    all_speaker_segments: Dict[str, List[Dict]],
    speaker_metadata_dict: Dict[str, Dict],
    audio_mapping: Dict[str, str],
    archives_metadata: Dict,
    downloads_dir: Path
) -> List[Tuple[str, Dict, float, Dict]]:
    """
    Vybere 20 nejkvalitnějších mluvčích (10 mužů, 10 žen) s různým věkem.

    Vrací seznam: [(speaker_id, best_segment, quality_score, person_metadata), ...]
    """
    print("\n🎯 Vybírám nejkvalitnější mluvčí...")
    print("   ⚠️  Tento krok může trvat dlouho - analyzuji kvalitu všech segmentů...")

    # 1. Extrahovat všechny segmenty s kvalitou
    print("📊 Extrahuji a analyzuji kvalitu všech segmentů...")
    speaker_candidates = []  # [(speaker_id, segment, quality_score, person_metadata), ...]

    # Nejdříve zjistit, které archivy jsou potřeba
    needed_archives = set()
    for speaker_id, segs in all_speaker_segments.items():
        for seg in segs:
            audio_url = seg['audio_url']
            archive_name = audio_mapping.get(audio_url)
            if archive_name:
                needed_archives.add(archive_name)

    print(f"📦 Potřebných archivů pro analýzu: {len(needed_archives)}")

    # Stáhnout archivy pokud nejsou stažené (jen pro analýzu)
    existing_tars = find_existing_tar_files(downloads_dir)
    for archive_name in sorted(needed_archives):
        tar_path = find_tar_file_in_downloads(archive_name, downloads_dir)
        if not tar_path or not tar_path.exists():
            if archive_name in archives_metadata:
                url = archives_metadata[archive_name]['url']
                tar_path = downloads_dir / archive_name
                print(f"📥 Stahuji {archive_name} pro analýzu kvality...")
                if not download_file(url, tar_path):
                    print(f"⚠️  Nepodařilo se stáhnout {archive_name}, přeskakuji...")
                    continue

    # Analyzovat každého mluvčího
    for speaker_id, segments in tqdm(all_speaker_segments.items(), desc="Analyzuji mluvčí"):
        # Mapovat speaker_id na metadata osoby
        person_meta = map_speaker_to_person(speaker_id, speaker_metadata_dict)

        if not person_meta:
            # Pokud nemáme metadata, přeskočit (nebo použít výchozí hodnoty)
            continue

        gender = person_meta.get('gender', '')
        if gender not in ['M', 'F']:
            # Pokud není pohlaví známé, přeskočit
            continue

        # Vybrat nejlepší segment pro tohoto mluvčího
        best_seg = select_best_segment_for_speaker(
            segments, audio_mapping, archives_metadata, downloads_dir
        )

        if not best_seg:
            continue

        # Analyzovat kvalitu segmentu (pokud ještě není analyzována)
        if 'quality_score' not in best_seg:
            # Musíme stáhnout a analyzovat audio
            audio_url = best_seg['audio_url']
            archive_name = audio_mapping.get(audio_url)

            if archive_name:
                tar_path = find_tar_file_in_downloads(archive_name, downloads_dir)
                if tar_path and tar_path.exists():
                    temp_audio_path = TEMP_DIR / f"quality_{hash(audio_url)}_{Path(audio_url).name}"
                    audio_file = extract_single_file_from_tar(tar_path, audio_url, temp_audio_path)

                    if audio_file and audio_file.exists():
                        temp_segment = TEMP_DIR / f"segment_{hash(audio_url)}.wav"
                        if extract_audio_segment(audio_file, best_seg['start_ms'], best_seg['end_ms'], temp_segment):
                            try:
                                quality = analyze_audio_quality_simple(temp_segment)
                                quality_score = calculate_quality_score(quality)
                                best_seg['quality_score'] = quality_score
                                best_seg['quality_analysis'] = quality
                            except:
                                quality_score = 0

                            # Smazat dočasné soubory
                            if temp_segment.exists():
                                temp_segment.unlink()

                        if temp_audio_path.exists():
                            temp_audio_path.unlink()
                        if audio_file != temp_audio_path and audio_file.exists():
                            try:
                                if audio_file.parent != TEMP_DIR:
                                    audio_file.unlink()
                            except:
                                pass

        quality_score = best_seg.get('quality_score', 0)

        # Přidat do kandidátů pouze pokud má minimální kvalitu
        if quality_score >= MIN_QUALITY_SCORE:
            speaker_candidates.append((
                speaker_id,
                best_seg,
                quality_score,
                person_meta
            ))

    # 2. Rozdělit podle pohlaví
    male_candidates = [(sid, seg, score, meta) for sid, seg, score, meta in speaker_candidates
                       if meta.get('gender') == 'M']
    female_candidates = [(sid, seg, score, meta) for sid, seg, score, meta in speaker_candidates
                         if meta.get('gender') == 'F']

    print(f"📊 Nalezeno {len(male_candidates)} mužů a {len(female_candidates)} žen s dostatečnou kvalitou")

    # 3. Seřadit podle kvality
    male_candidates.sort(key=lambda x: x[2], reverse=True)
    female_candidates.sort(key=lambda x: x[2], reverse=True)

    # 4. Vybrat s různým věkem (rozdělit do věkových skupin)
    def select_diverse_by_age(candidates: List[Tuple], target_count: int) -> List[Tuple]:
        """Vybere kandidáty s různým věkem."""
        if len(candidates) <= target_count:
            return candidates[:target_count]

        # Rozdělit do věkových skupin
        age_groups = defaultdict(list)
        for cand in candidates:
            age = cand[3].get('age')
            if age is not None:
                # Věkové skupiny: 20-30, 31-40, 41-50, 51-60, 61+
                if age < 31:
                    age_groups['20-30'].append(cand)
                elif age < 41:
                    age_groups['31-40'].append(cand)
                elif age < 51:
                    age_groups['41-50'].append(cand)
                elif age < 61:
                    age_groups['51-60'].append(cand)
                else:
                    age_groups['61+'].append(cand)
            else:
                age_groups['unknown'].append(cand)

        # Vybrat z každé skupiny
        selected = []
        per_group = max(1, target_count // max(1, len(age_groups) - 1))  # -1 pro unknown

        # Nejdříve vybrat z věkových skupin
        for group_name in ['20-30', '31-40', '41-50', '51-60', '61+']:
            if group_name in age_groups and len(selected) < target_count:
                group_candidates = age_groups[group_name]
                group_candidates.sort(key=lambda x: x[2], reverse=True)  # Seřadit podle kvality
                selected.extend(group_candidates[:per_group])
                if len(selected) >= target_count:
                    break

        # Pokud ještě nemáme dost, doplnit nejkvalitnějšími
        if len(selected) < target_count:
            remaining = [c for c in candidates if c not in selected]
            remaining.sort(key=lambda x: x[2], reverse=True)
            selected.extend(remaining[:target_count - len(selected)])

        return selected[:target_count]

    selected_males = select_diverse_by_age(male_candidates, TARGET_MALE)
    selected_females = select_diverse_by_age(female_candidates, TARGET_FEMALE)

    selected = selected_males + selected_females

    print(f"✅ Vybráno {len(selected_males)} mužů a {len(selected_females)} žen")

    # Zobrazit statistiky
    if selected:
        print("\n📊 Statistiky vybraných mluvčích:")
        male_ages = [c[3].get('age') for c in selected_males if c[3].get('age')]
        female_ages = [c[3].get('age') for c in selected_females if c[3].get('age')]
        if male_ages:
            print(f"   Muži - věk: min={min(male_ages)}, max={max(male_ages)}, průměr={sum(male_ages)/len(male_ages):.1f}")
        if female_ages:
            print(f"   Ženy - věk: min={min(female_ages)}, max={max(female_ages)}, průměr={sum(female_ages)/len(female_ages):.1f}")
        avg_quality = sum(c[2] for c in selected) / len(selected)
        print(f"   Průměrná kvalita: {avg_quality:.1f}")

    return selected

def main():
    """Hlavní funkce."""
    print("=" * 60)
    print("🎤 ParCzech4Speech - Extrakce 20 nejkvalitnějších hlasů")
    print(f"   Cíl: {TARGET_MALE} mužů + {TARGET_FEMALE} žen = {TARGET_SPEAKERS} mluvčích")
    print("=" * 60)

    # 1. Načíst metadata mapování
    print("\n📋 Načítám metadata...")
    audio_mapping = load_audio_file_mapping(METADATA_DIR / "audioPSP-meta.audioFile.tsv")
    archives_metadata = load_quarter_archives()
    speaker_metadata_dict = load_speaker_metadata(PERSON_LIST_XML)

    if not audio_mapping:
        print("❌ Nepodařilo se načíst mapování audio souborů")
        return

    # 2. Najít všechny mluvčí v XML
    print("\n📋 Hledám mluvčí v XML souborech...")
    if not XML_DIR.exists():
        print(f"❌ XML adresář neexistuje: {XML_DIR}")
        return

    speaker_segments = find_speakers_in_all_xml(XML_DIR, max_files=None)
    print(f"✅ Nalezeno {len(speaker_segments)} unikátních mluvčích")

    # 3. Vybrat 20 nejkvalitnějších s různým věkem
    selected_speakers = select_best_speakers(
        speaker_segments,
        speaker_metadata_dict,
        audio_mapping,
        archives_metadata,
        DOWNLOADS_DIR
    )

    if not selected_speakers:
        print("❌ Nepodařilo se vybrat žádné mluvčí")
        return

    print(f"\n✅ Vybráno {len(selected_speakers)} mluvčích pro extrakci")

    # Vytvořit mapu vybraných mluvčích pro rychlé vyhledávání
    selected_speaker_ids = {sid for sid, _, _, _ in selected_speakers}
    selected_speaker_map = {sid: (seg, score, meta) for sid, seg, score, meta in selected_speakers}

    # 4. Určit, které archivy jsou potřeba pro vybrané mluvčí
    print("\n📦 Určuji potřebné TAR archivy pro vybrané mluvčí...")
    needed_archives = set()
    speaker_archive_map = {}  # speaker_id -> [(archive_name, segment), ...]

    for speaker_id, seg, score, meta in selected_speakers:
        audio_url = seg['audio_url']
        archive_name = audio_mapping.get(audio_url)
        if archive_name:
            needed_archives.add(archive_name)
            if speaker_id not in speaker_archive_map:
                speaker_archive_map[speaker_id] = []
            speaker_archive_map[speaker_id].append((archive_name, seg))

    print(f"✅ Potřebných archivů: {len(needed_archives)}")
    for arch in sorted(needed_archives):
        print(f"   - {arch}")

    # 5. Stáhnout a zpracovat archivy postupně
    print("\n📥 Stahuji a zpracovávám archivy postupně...")
    existing_tars = find_existing_tar_files(DOWNLOADS_DIR)

    AUDIO_SELECTED_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    speakers_metadata = {}
    processed_speakers = set()

    for archive_name in sorted(needed_archives):
        print(f"\n{'='*60}")
        print(f"📦 Zpracovávám: {archive_name}")
        print(f"{'='*60}")

        # Stáhnout archiv pokud není stažený
        tar_path = find_tar_file_in_downloads(archive_name, DOWNLOADS_DIR)
        if not tar_path or not tar_path.exists():
            if archive_name in archives_metadata:
                url = archives_metadata[archive_name]['url']
                tar_path = DOWNLOADS_DIR / archive_name
                print(f"📥 Stahuji {archive_name}...")
                if not download_file(url, tar_path):
                    print(f"❌ Nepodařilo se stáhnout {archive_name}")
                    continue
            else:
                print(f"⚠️  Metadata pro {archive_name} nejsou k dispozici")
                continue
        else:
            print(f"✓ Archiv již stažen: {archive_name}")

        # Zpracovat audio soubory z tohoto archivu (jen vybrané mluvčí)
        archive_speakers = [s for s in selected_speaker_ids
                           if s in speaker_archive_map and
                           any(a == archive_name for a, _ in speaker_archive_map[s])]

        for speaker_id in archive_speakers:
            if speaker_id in processed_speakers:
                continue

            # Použít již vybraný segment (už jsme ho vybrali v select_best_speakers)
            if speaker_id not in selected_speaker_map:
                continue

            best_seg, quality_score, person_meta = selected_speaker_map[speaker_id]

            # Ověřit, že tento segment je v tomto archivu
            audio_url = best_seg['audio_url']
            archive_name_for_seg = audio_mapping.get(audio_url)
            if archive_name_for_seg != archive_name:
                continue

            audio_url = best_seg['audio_url']

            # Extrahovat audio soubor z TAR
            temp_audio_path = TEMP_DIR / f"{speaker_id}_{Path(audio_url).name}"

            print(f"  📂 Extrahuji {Path(audio_url).name} pro {speaker_id}...")
            audio_file = extract_single_file_from_tar(tar_path, audio_url, temp_audio_path)

            if audio_file and audio_file.exists():
                # Extrahovat 30 sekund segment
                output_audio = AUDIO_SELECTED_DIR / f"{speaker_id}.wav"

                if extract_audio_segment(audio_file, best_seg['start_ms'], best_seg['end_ms'], output_audio):
                    # Analyzovat kvalitu finálního segmentu (pokud ještě není analyzována)
                    if 'quality_analysis' not in best_seg:
                        try:
                            quality = analyze_audio_quality_simple(output_audio)
                            quality_score = calculate_quality_score(quality)
                        except:
                            quality = best_seg.get('quality_analysis', {})
                            quality_score = best_seg.get('quality_score', 0)
                    else:
                        quality = best_seg.get('quality_analysis', {})
                        quality_score = best_seg.get('quality_score', 0)

                    # person_meta je už definováno výše z selected_speaker_map
                    speakers_metadata[speaker_id] = {
                        'audio_file': str(output_audio.relative_to(DATA_DIR)),
                        'start_ms': best_seg['start_ms'],
                        'end_ms': best_seg['end_ms'],
                        'duration_sec': TARGET_AUDIO_LENGTH_SEC,
                        'text': best_seg['text'],
                        'source_xml': best_seg['xml_file'],
                        'original_audio_url': audio_url,
                        'source_archive': archive_name,
                        'quality_score': quality_score,
                        'quality_analysis': quality,
                        'speaker_name': person_meta.get('name', '') if person_meta else '',
                        'gender': person_meta.get('gender', '') if person_meta else '',
                        'age': person_meta.get('age') if person_meta else None,
                        'birth_date': person_meta.get('birth_date', '') if person_meta else ''
                    }
                    processed_speakers.add(speaker_id)
                    speaker_name = person_meta.get('name', speaker_id) if person_meta else speaker_id
                    print(f"  ✅ Extrahováno: {speaker_name} ({output_audio.name}, kvalita: {quality_score:.1f})")

                # Smazat dočasný soubor
                if temp_audio_path.exists():
                    temp_audio_path.unlink()
                # Také smazat extrahovaný soubor pokud je jinde
                if audio_file != temp_audio_path and audio_file.exists():
                    # Smazat celý adresář pokud je potřeba
                    try:
                        if audio_file.parent != TEMP_DIR:
                            audio_file.unlink()
                    except:
                        pass
            else:
                print(f"  ⚠️  Nepodařilo se extrahovat audio pro {speaker_id}")

        # Smazat archiv po zpracování (pro úsporu místa)
        if tar_path.exists() and archive_name not in existing_tars:
            print(f"🗑️  Mažu archiv {archive_name} (ušetří místo)...")
            try:
                tar_path.unlink()
            except Exception as e:
                print(f"⚠️  Nepodařilo se smazat archiv: {e}")

    # 6. Uložit metadata
    metadata_file = DATA_DIR / "speakers_30s_metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(speakers_metadata, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Metadata uložena do {metadata_file}")
    print(f"✅ Celkem extrahováno {len(speakers_metadata)} mluvčích")

    # Zobrazit statistiky
    if speakers_metadata:
        male_count = sum(1 for m in speakers_metadata.values() if m.get('gender') == 'M')
        female_count = sum(1 for m in speakers_metadata.values() if m.get('gender') == 'F')
        avg_quality = sum(m.get('quality_score', 0) for m in speakers_metadata.values()) / len(speakers_metadata)
        print(f"📊 Statistiky: {male_count} mužů, {female_count} žen, průměrná kvalita: {avg_quality:.1f}")

    # 6. Vyčistit dočasné soubory
    if TEMP_DIR.exists():
        print(f"🧹 Čistím dočasné soubory...")
        for f in TEMP_DIR.glob("*"):
            try:
                if f.is_file():
                    f.unlink()
                elif f.is_dir():
                    import shutil
                    shutil.rmtree(f)
            except:
                pass

    print("\n" + "=" * 60)
    print("✅ Hotovo!")
    print(f"📁 Audio soubory: {AUDIO_SELECTED_DIR}")
    print(f"📊 Metadata: {metadata_file}")
    print(f"💾 Celková velikost: {sum(f.stat().st_size for f in AUDIO_SELECTED_DIR.glob('*.wav')) / (1024**2):.1f} MB")
    print("=" * 60)

if __name__ == "__main__":
    main()


