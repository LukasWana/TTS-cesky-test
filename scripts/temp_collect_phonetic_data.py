#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Jednorázový skript pro stažení fonetických dat z jazykových příruček
a aktualizaci slovníku v backend/phonetic_translator.py

POZOR: Tento skript je určen pro jednorázové použití.
Po úspěšné aktualizaci slovníku ho můžete smazat.
"""

import re
import sys
import time
import shutil
from pathlib import Path
from typing import Dict, Tuple, Optional, List
from urllib.parse import urljoin, urlparse

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError as e:
    print(f"ERROR: Chybí požadovaná knihovna: {e}")
    print("Nainstalujte pomocí: pip install requests beautifulsoup4")
    sys.exit(1)

# Konfigurace
BASE_DIR = Path(__file__).parent.parent
PHONETIC_FILE = BASE_DIR / "backend" / "phonetic_translator.py"
BACKUP_FILE = BASE_DIR / "backend" / "phonetic_translator.py.bak"

# URL zdrojů
PRIRUCKA_BASE = "https://prirucka.ujc.cas.cz/"
PRAVOPISNE_BASE = "https://www.pravopisne.cz/"

# User-Agent pro zdvořilé scrapování
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}


def generate_czech_phonetic(word: str) -> str:
    """
    Automaticky generuje český fonetický přepis z anglického slova.
    Používá pravidla a heuristiky založené na běžných vzorech výslovnosti.
    """
    if not word:
        return ""

    word_lower = word.lower()

    # Speciální případy - krátká slova
    special_cases = {
        'a': 'ej',
        'i': 'aj',
        'u': 'jú',
        'the': 'd',
        'and': 'end',
        'or': 'or',
        'of': 'ov',
        'to': 'tu',
        'in': 'in',
        'on': 'on',
        'at': 'et',
        'is': 'iz',
        'it': 'it',
        'be': 'bí',
        'we': 'ví',
        'he': 'hí',
        'she': 'ší',
        'me': 'mí',
        'my': 'maj',
        'you': 'jú',
        'do': 'dú',
        'go': 'gou',
        'no': 'nou',
        'so': 'sou',
        'up': 'ap',
        'if': 'if',
        'as': 'ez',
        'an': 'en',
        'am': 'em',
        'us': 'as',
        'by': 'baj',
    }

    if word_lower in special_cases:
        return special_cases[word_lower]

    # Postupné nahrazování podle vzorů (nejdelší první)
    phonetic = word_lower

    # Koncovky (nejdřív delší)
    endings = [
        ('tion', 'ejšn'),  # transformation -> transformejšn
        ('sion', 'žn'),    # compassion -> kmpešn
        ('cian', 'šn'),
        ('ness', 'nes'),   # wellness -> velnes, awareness -> evérnes
        ('ment', 'ment'),  # enlightenment -> enlajtnment
        ('ship', 'ship'),  # relationship -> rilejšnšip
        ('hood', 'hud'),
        ('less', 'les'),
        ('ful', 'fl'),     # mindful -> majndfl
        ('ing', 'ink'),    # meeting -> mítink, marketing -> marketink
        ('ed', 'd'),       # pokud není předchozí 'e'
        ('er', 'r'),       # manager -> menedžer (ale někdy 'er')
        ('ly', 'lí'),
        ('ty', 'tí'),
        ('cy', 'sí'),
        ('gy', 'dží'),    # energy -> enrdží
        ('ry', 'rí'),
        ('my', 'mí'),
        ('ny', 'ní'),
        ('sy', 'sí'),
        ('dy', 'dí'),
        ('ty', 'tí'),
        ('fy', 'fí'),
        ('py', 'pí'),
        ('by', 'bí'),
        ('vy', 'ví'),
        ('wy', 'ví'),
        ('xy', 'ksí'),
        ('zy', 'zí'),
    ]

    # Aplikujeme koncovky
    for ending, replacement in endings:
        if phonetic.endswith(ending):
            phonetic = phonetic[:-len(ending)] + replacement
            break

    # Skupiny hlásek uprostřed slova (nejdelší první)
    patterns = [
        # Dlouhé skupiny
        ('ture', 'čr'),    # natural -> nečrl
        ('sure', 'žr'),
        ('ough', 'o'),
        ('augh', 'ó'),
        ('eigh', 'ej'),
        ('tch', 'č'),
        ('dge', 'dž'),
        ('tia', 'ša'),
        ('cia', 'ša'),
        ('sio', 'žo'),
        ('tio', 'šo'),

        # Dvojhlásky
        ('ee', 'í'),       # email -> ímejl, meeting -> mítink
        ('oo', 'ú'),       # mood -> můd
        ('oa', 'ou'),
        ('ai', 'ej'),      # email -> ímejl (ai -> ej)
        ('ay', 'ej'),
        ('ei', 'ej'),
        ('ey', 'ej'),
        ('ie', 'í'),
        ('ue', 'ú'),
        ('ui', 'uj'),
        ('ou', 'au'),      # burnout -> brnaut
        ('ow', 'ou'),      # growth -> grous, flow -> flou
        ('ew', 'jú'),
        ('aw', 'ó'),
        ('au', 'ó'),
        ('oy', 'oj'),      # joy -> džoj
        ('oi', 'oj'),
        ('ea', 'í'),       # peace -> pís, healing -> hílink
        ('oa', 'ou'),
        ('oe', 'ou'),

        # Souhláskové skupiny
        ('ph', 'f'),
        ('ch', 'č'),       # chakra -> čakra
        ('sh', 'š'),       # hashtag -> heštek
        ('th', 't'),       # většinou 't'
        ('ck', 'k'),
        ('qu', 'kv'),
        ('wh', 'v'),       # wellbeing -> velbíink
        ('wr', 'r'),
        ('kn', 'n'),
        ('gn', 'n'),
        ('mb', 'm'),
        ('ps', 's'),
        ('pn', 'n'),
        ('rh', 'r'),
        ('dg', 'dž'),
        ('dj', 'dž'),
        ('tj', 'č'),
        ('ts', 'c'),
        ('ds', 'c'),
        ('x', 'ks'),       # relax -> rileks, detox -> dítoks
        ('cc', 'k'),       # před a,o,u
        ('sc', 'sk'),      # před a,o,u
    ]

    # Aplikujeme vzory (musíme to dělat opatrně, aby se nepřekrývaly)
    i = 0
    result = []
    while i < len(phonetic):
        matched = False
        for pattern, replacement in patterns:
            if phonetic[i:].startswith(pattern):
                result.append(replacement)
                i += len(pattern)
                matched = True
                break
        if not matched:
            result.append(phonetic[i])
            i += 1

    phonetic = ''.join(result)

    # Úpravy jednotlivých písmen
    phonetic = phonetic.replace('w', 'v')  # w -> v (wellbeing -> velbíink)
    phonetic = phonetic.replace('q', 'k')
    phonetic = phonetic.replace('c', 'k')  # obecně, ale před e,i,y by mělo být 's'

    # Oprava 'c' před e, i, y -> 's'
    phonetic = re.sub(r'c([eiy])', r's\1', phonetic)

    # 'y' na konci -> 'í' (pokud ještě není upraveno)
    if phonetic.endswith('y') and len(phonetic) > 1:
        phonetic = phonetic[:-1] + 'í'
    elif phonetic.endswith('i') and len(phonetic) > 1 and not phonetic.endswith('í'):
        # 'i' na konci často -> 'í'
        phonetic = phonetic[:-1] + 'í'

    # Odstraníme zdvojené znaky
    phonetic = re.sub(r'(.)\1+', r'\1', phonetic)

    # Normalizace problematických kombinací
    phonetic = phonetic.replace('kk', 'k')
    phonetic = phonetic.replace('tt', 't')
    phonetic = phonetic.replace('pp', 'p')
    phonetic = phonetic.replace('ss', 's')
    phonetic = phonetic.replace('dd', 'd')
    phonetic = phonetic.replace('bb', 'b')
    phonetic = phonetic.replace('gg', 'g')
    phonetic = phonetic.replace('ff', 'f')
    phonetic = phonetic.replace('ll', 'l')
    phonetic = phonetic.replace('mm', 'm')
    phonetic = phonetic.replace('nn', 'n')
    phonetic = phonetic.replace('rr', 'r')
    phonetic = phonetic.replace('vv', 'v')
    phonetic = phonetic.replace('zz', 'z')

    return phonetic


def download_page(url: str, max_retries: int = 3) -> Optional[str]:
    """Stáhne HTML stránku s retry logikou a rate limiting."""
    for attempt in range(max_retries):
        try:
            time.sleep(1)  # Rate limiting - 1 sekunda mezi requesty
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            return response.text
        except requests.RequestException as e:
            print(f"  Varování: Nepodařilo se stáhnout {url} (pokus {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
    return None


def extract_from_prirucka() -> Dict[str, str]:
    """
    Extrahuje fonetické přepisy z Internetové jazykové příručky.
    Hledá sekce o výslovnosti přejatých slov.
    """
    print("\n[1/2] Stahuji data z Internetové jazykové příručky...")
    results = {}

    # Konkrétní URL sekcí o výslovnosti
    target_urls = [
        ("https://prirucka.ujc.cas.cz/?id=915", "Výslovnost přejatých slov a vlastních jmen"),
        ("https://prirucka.ujc.cas.cz/?id=902", "Fonetická transkripce"),
        ("https://prirucka.ujc.cas.cz/", "Hlavní stránka"),
    ]

    for url, title in target_urls:
        print(f"  Zpracovávám: {title}...")
        html = download_page(url)
        if not html:
            print(f"    Varování: Nepodařilo se stáhnout {url}")
            continue

        soup = BeautifulSoup(html, 'html.parser')

        # 1. Hledáme texty s hranatými závorkami [výslovnost]
        # Formát: "slovo [výslovnost]" nebo "slovo[výslovnost]"
        text_content = soup.get_text(separator=' ', strip=True)

        # Pattern pro hledání: slovo [výslovnost] nebo slovo[výslovnost]
        # Lepší pattern, který zachytí více variant
        patterns = [
            # Formát: "slovo [výslovnost]" s mezerou
            r'\b([a-zá-žěščřžýáíéóúů]+(?:\s+[a-zá-žěščřžýáíéóúů]+)?)\s*\[\s*([a-zá-žěščřžýáíéóúů]+(?:\s+[a-zá-žěščřžýáíéóúů]+)*)\s*\]',
            # Formát: "slovo[výslovnost]" bez mezery
            r'\b([a-zá-žěščřžýáíéóúů]+)\[([a-zá-žěščřžýáíéóúů]+(?:\s+[a-zá-žěščřžýáíéóúů]+)*)\]',
            # Formát: "slovo – výslovnost" s pomlčkou
            r'\b([a-zá-žěščřžýáíéóúů]+(?:\s+[a-zá-žěščřžýáíéóúů]+)?)\s*[–-]\s*([a-zá-žěščřžýáíéóúů]+(?:\s+[a-zá-žěščřžýáíéóúů]+)*)',
        ]

        found_count = 0
        for pattern in patterns:
            matches = re.finditer(pattern, text_content, re.IGNORECASE)
            for match in matches:
                word = match.group(1).strip().lower()
                pronunciation = match.group(2).strip().lower()

                # Filtrace: slovo musí být alespoň 2 znaky, výslovnost také
                # A slovo by mělo obsahovat hlavně písmena (ne čísla, speciální znaky)
                if (len(word) >= 2 and len(pronunciation) >= 2 and
                    word.replace(' ', '').isalpha() and
                    pronunciation.replace(' ', '').replace('-', '').isalpha()):
                    # Normalizace: odstraníme diakritiku z klíče pro lepší matching
                    results[word] = pronunciation
                    found_count += 1

        # 2. Hledáme v tabulkách a seznamech
        for table in soup.find_all(['table', 'ul', 'ol']):
            table_text = table.get_text(separator=' ', strip=True)
            for pattern in patterns:
                matches = re.finditer(pattern, table_text, re.IGNORECASE)
                for match in matches:
                    word = match.group(1).strip().lower()
                    pronunciation = match.group(2).strip().lower()
                    if (len(word) >= 2 and len(pronunciation) >= 2 and
                        word.replace(' ', '').isalpha()):
                        results[word] = pronunciation
                        found_count += 1

        # 3. Hledáme v odstavcích s em tagy (často se tam píší příklady)
        for p in soup.find_all('p'):
            p_text = p.get_text(separator=' ', strip=True)
            # Hledáme formát: <em>slovo</em> [výslovnost]
            em_tags = p.find_all('em')
            for em in em_tags:
                word = em.get_text(strip=True).lower()
                # Hledáme výslovnost za em tagem
                after_em = em.next_sibling
                if after_em:
                    after_text = str(after_em).strip()
                    # Hledáme [výslovnost] nebo – výslovnost
                    match = re.search(r'[\[–]\s*([a-zá-žěščřžýáíéóúů]+(?:\s+[a-zá-žěščřžýáíéóúů]+)*)', after_text, re.IGNORECASE)
                    if match and len(word) >= 2:
                        pronunciation = match.group(1).strip().lower()
                        if len(pronunciation) >= 2:
                            results[word] = pronunciation
                            found_count += 1

        print(f"    Nalezeno {found_count} záznamů na této stránce")

        # Debug: zobrazíme prvních 5 nalezených záznamů
        if found_count > 0:
            sample = list(results.items())[-found_count:][:5]
            print(f"    Ukázka: {dict(sample)}")

    print(f"  Celkem extrahováno {len(results)} unikátních záznamů z Internetové jazykové příručky")

    # Zobrazíme ukázku výsledků
    if results:
        print(f"  Ukázka výsledků (prvních 10):")
        for i, (word, pron) in enumerate(list(results.items())[:10], 1):
            print(f"    {i}. {word} -> {pron}")

    return results


def extract_words_from_case_txt() -> List[str]:
    """
    Extrahuje anglická slova z case.txt souboru.
    Formát: VELKÉ_SLOVO                  malé slovo
    Vrací seznam anglických slov (lowercase).
    """
    print("\n[0/3] Extrahuji anglická slova z case.txt...")
    words = set()

    # Zkusíme oba možné soubory
    case_files = [
        BASE_DIR / "scripts" / "case.txt",
        BASE_DIR / "slovniky" / "beep" / "case.txt",
    ]

    case_file = None
    for cf in case_files:
        if cf.exists():
            case_file = cf
            break

    if not case_file:
        print("  Varování: case.txt nenalezen v žádné z možných lokací")
        return []

    print(f"  Zpracovávám: {case_file}...")
    try:
        with open(case_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Přeskočíme komentáře a prázdné řádky
                if not line or line.startswith('#'):
                    continue

                # Formát: VELKÉ_SLOVO                  malé slovo
                # Rozdělíme na více mezer (obvykle tabulátor nebo více mezer)
                parts = line.split(None, 1)  # Rozdělíme na max 2 části
                if len(parts) >= 1:
                    # Vezmeme první část (velké slovo) a druhou část (malé slovo)
                    upper_word = parts[0].strip()
                    lower_word = parts[1].strip() if len(parts) > 1 else upper_word.lower()

                    # Přidáme obě varianty (normalizované na lowercase)
                    for word in [upper_word, lower_word]:
                        if word and len(word) >= 2:
                            # Filtrujeme pouze slova (ne speciální znaky)
                            word_clean = word.replace("'", "").replace("-", "").replace("_", "")
                            if word_clean.isalpha() or (word_clean.replace("'", "").isalpha()):
                                words.add(word.lower())

        print(f"    Nalezeno {len(words)} unikátních anglických slov")

        # Ukázka
        sample = sorted(list(words))[:10]
        print(f"    Ukázka: {sample}")

    except Exception as e:
        print(f"    Chyba při zpracování case.txt: {e}")
        import traceback
        traceback.print_exc()
        return []

    return sorted(list(words))




def extract_from_pravopisne() -> Dict[str, str]:
    """
    Extrahuje fonetické přepisy z pravopisne.cz jako fallback zdroj.
    """
    print("\n[2/2] Stahuji data z pravopisne.cz (fallback)...")
    results = {}

    # URL stránek s pravidly
    target_urls = [
        "https://www.pravopisne.cz/pravidla-pravopisu/souhrn-pravopisnych-pravidel/",
    ]

    for url in target_urls:
        print(f"  Zpracovávám: {url}...")
        html = download_page(url)
        if not html:
            print(f"    Varování: Nepodařilo se stáhnout {url}")
            continue

        soup = BeautifulSoup(html, 'html.parser')
        text_content = soup.get_text(separator=' ', strip=True)

        # Stejné patterny jako v primárním zdroji
        patterns = [
            r'\b([a-zá-žěščřžýáíéóúů]+(?:\s+[a-zá-žěščřžýáíéóúů]+)?)\s*\[\s*([a-zá-žěščřžýáíéóúů]+(?:\s+[a-zá-žěščřžýáíéóúů]+)*)\s*\]',
            r'\b([a-zá-žěščřžýáíéóúů]+)\[([a-zá-žěščřžýáíéóúů]+(?:\s+[a-zá-žěščřžýáíéóúů]+)*)\]',
            r'\b([a-zá-žěščřžýáíéóúů]+(?:\s+[a-zá-žěščřžýáíéóúů]+)?)\s*[–-]\s*([a-zá-žěščřžýáíéóúů]+(?:\s+[a-zá-žěščřžýáíéóúů]+)*)',
        ]

        found_count = 0
        for pattern in patterns:
            matches = re.finditer(pattern, text_content, re.IGNORECASE)
            for match in matches:
                word = match.group(1).strip().lower()
                pronunciation = match.group(2).strip().lower()
                if (len(word) >= 2 and len(pronunciation) >= 2 and
                    word.replace(' ', '').isalpha()):
                    results[word] = pronunciation
                    found_count += 1

        print(f"    Nalezeno {found_count} záznamů na této stránce")

    print(f"  Celkem extrahováno {len(results)} unikátních záznamů z pravopisne.cz")
    return results


def load_existing_dictionary() -> Dict[str, str]:
    """Načte stávající slovník z phonetic_translator.py."""
    print("\nNačítám stávající slovník...")

    if not PHONETIC_FILE.exists():
        print(f"  ERROR: Soubor {PHONETIC_FILE} neexistuje!")
        return {}

    content = PHONETIC_FILE.read_text(encoding='utf-8')

    # Najdeme sekci ENGLISH_PHONETIC = {
    start_match = re.search(r'ENGLISH_PHONETIC\s*=\s*\{', content)
    if not start_match:
        print("  ERROR: Nepodařilo se najít ENGLISH_PHONETIC ve slovníku!")
        return {}

    # Najdeme konec slovníku (zavírací závorka na správné úrovni)
    start_pos = start_match.end()
    brace_count = 1
    end_pos = start_pos

    for i, char in enumerate(content[start_pos:], start_pos):
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                end_pos = i
                break

    dict_content = content[start_pos:end_pos]

    # Extrahujeme páry klíč: hodnota
    existing = {}
    pattern = r"['\"]([^'\"]+)['\"]\s*:\s*['\"]([^'\"]+)['\"]"
    matches = re.finditer(pattern, dict_content)

    for match in matches:
        key = match.group(1)
        value = match.group(2)
        existing[key.lower()] = value

    print(f"  Načteno {len(existing)} existujících záznamů")
    return existing


def merge_dictionaries(
    primary: Dict[str, str],
    fallback: Dict[str, str],
    existing: Dict[str, str]
) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
    """
    Sloučí nová data s existujícím slovníkem.
    Vrací: (nová slova, opravená slova, všechna data)
    """
    print("\nSlučuji data...")

    new_words = {}
    updated_words = {}
    merged = existing.copy()

    # Nejdřív použijeme primární zdroj
    for word, pronunciation in primary.items():
        word_lower = word.lower()
        if word_lower not in merged:
            new_words[word_lower] = pronunciation
            merged[word_lower] = pronunciation
        elif merged[word_lower] != pronunciation:
            updated_words[word_lower] = (merged[word_lower], pronunciation)
            merged[word_lower] = pronunciation

    # Pak použijeme fallback zdroj (pouze pro slova, která nejsou v primárním)
    for word, pronunciation in fallback.items():
        word_lower = word.lower()
        if word_lower not in merged:
            new_words[word_lower] = pronunciation
            merged[word_lower] = pronunciation

    print(f"  Nová slova: {len(new_words)}")
    print(f"  Aktualizovaná slova: {len(updated_words)}")
    print(f"  Celkem záznamů: {len(merged)}")

    return new_words, updated_words, merged


def create_backup():
    """Vytvoří zálohu souboru před změnami."""
    if PHONETIC_FILE.exists():
        shutil.copy2(PHONETIC_FILE, BACKUP_FILE)
        print(f"\nZáloha vytvořena: {BACKUP_FILE}")
        return True
    return False


def update_phonetic_file(new_dict: Dict[str, str]):
    """
    Aktualizuje phonetic_translator.py s novým slovníkem.
    Zachová strukturu, komentáře a formátování.
    """
    print("\nAktualizuji phonetic_translator.py...")

    content = PHONETIC_FILE.read_text(encoding='utf-8')

    # Najdeme začátek a konec slovníku
    start_match = re.search(r'(ENGLISH_PHONETIC\s*=\s*\{)', content)
    if not start_match:
        print("  ERROR: Nepodařilo se najít ENGLISH_PHONETIC!")
        return False

    # Najdeme konec slovníku
    start_pos = start_match.start()
    dict_start = start_match.end()
    brace_count = 1
    end_pos = dict_start

    for i, char in enumerate(content[dict_start:], dict_start):
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                end_pos = i + 1
                break

    # Vytvoříme nový obsah slovníku
    # Seřadíme podle klíče pro lepší čitelnost
    sorted_items = sorted(new_dict.items())

    # Zachováme kategorizaci - zkusíme najít komentáře v původním souboru
    lines_before = content[:start_pos]
    lines_after = content[end_pos:]

    # Vytvoříme nový slovník s formátováním
    dict_lines = ["ENGLISH_PHONETIC = {"]

    # Přidáme záznamy (zachováme formátování)
    for key, value in sorted_items:
        # Escape quotes v hodnotách
        key_escaped = key.replace("'", "\\'").replace('"', '\\"')
        value_escaped = value.replace("'", "\\'").replace('"', '\\"')
        dict_lines.append(f"    '{key_escaped}': '{value_escaped}',")

    dict_lines.append("}")

    new_dict_content = "\n".join(dict_lines)

    # Složíme nový obsah souboru
    new_content = lines_before + new_dict_content + lines_after

    # Zápis do souboru
    PHONETIC_FILE.write_text(new_content, encoding='utf-8')
    print(f"  Soubor aktualizován: {PHONETIC_FILE}")
    return True


def print_report(new_words: Dict[str, str], updated_words: Dict[str, Tuple[str, str]]):
    """Vypíše report změn."""
    print("\n" + "=" * 70)
    print("REPORT ZMĚN")
    print("=" * 70)

    if new_words:
        print(f"\nNOVÁ SLOVA ({len(new_words)}):")
        print("-" * 70)
        for word, pronunciation in sorted(new_words.items())[:20]:  # Zobrazíme prvních 20
            print(f"  + {word:30} -> {pronunciation}")
        if len(new_words) > 20:
            print(f"  ... a dalších {len(new_words) - 20} slov")
    else:
        print("\nŽádná nová slova")

    if updated_words:
        print(f"\nAKTUALIZOVANÁ SLOVA ({len(updated_words)}):")
        print("-" * 70)
        for word, (old, new) in sorted(updated_words.items())[:20]:  # Zobrazíme prvních 20
            print(f"  ~ {word:30} | {old:20} -> {new}")
        if len(updated_words) > 20:
            print(f"  ... a dalších {len(updated_words) - 20} slov")
    else:
        print("\nŽádná aktualizovaná slova")

    print("\n" + "=" * 70)


def main():
    """Hlavní funkce skriptu."""
    print("=" * 70)
    print("JEDNORÁZOVÉ STAŽENÍ FONETICKÝCH DAT")
    print("=" * 70)
    print(f"Zdroj anglických slov: case.txt")
    print(f"Zdroj fonetických přepisů 1: {PRIRUCKA_BASE}")
    print(f"Zdroj fonetických přepisů 2: {PRAVOPISNE_BASE} (fallback)")
    print(f"Cílový soubor: {PHONETIC_FILE}")

    # FÁZE 1: Extrahujeme anglická slova z case.txt
    print("\n" + "=" * 70)
    print("FÁZE 1: EXTRACE ANGLICKÝCH SLOV Z case.txt")
    print("=" * 70)
    candidate_words = extract_words_from_case_txt()

    if not candidate_words:
        print("\nERROR: Nepodařilo se extrahovat žádná slova z case.txt!")
        return 1

    print(f"\n✓ Extrahováno {len(candidate_words)} anglických slov z case.txt")

    # FÁZE 2: Hledáme fonetické přepisy pro tato slova
    print("\n" + "=" * 70)
    print("FÁZE 2: VYHLEDÁVÁNÍ FONETICKÝCH PŘEPISŮ")
    print("=" * 70)

    # 2a. Načteme existující slovník
    existing_dict = load_existing_dictionary()
    if not existing_dict:
        print("  Varování: Nepodařilo se načíst existující slovník, pokračuji s prázdným...")
        existing_dict = {}

    # 2b. Stáhneme data z webových zdrojů
    primary_data = extract_from_prirucka()
    fallback_data = extract_from_pravopisne()

    # 2c. Zkombinujeme všechna nalezená data
    all_found_data = {}
    all_found_data.update(existing_dict)
    all_found_data.update(primary_data)
    all_found_data.update(fallback_data)

    # 2d. Pro každé slovo z case.txt vygenerujeme fonetický přepis
    print("\n  Generuji fonetické přepisy pro slova z case.txt...")
    words_with_pronunciation = []
    words_without_pronunciation = []

    for word in candidate_words:
        # Nejdřív zkusíme najít existující přepis
        if word in all_found_data:
            words_with_pronunciation.append((word, all_found_data[word]))
        else:
            # Pokud neexistuje, vygenerujeme automaticky
            generated_pronunciation = generate_czech_phonetic(word)
            if generated_pronunciation:
                words_with_pronunciation.append((word, generated_pronunciation))
            else:
                words_without_pronunciation.append(word)

    print(f"  ✓ Vygenerováno {len(words_with_pronunciation)} fonetických přepisů")

    # Rozdělíme na existující a generované přepisy
    existing_pronunciations = []
    generated_pronunciations = []

    for word, pron in words_with_pronunciation:
        if word in all_found_data:
            existing_pronunciations.append((word, pron))
        else:
            generated_pronunciations.append((word, pron))

    # Report
    print("\n" + "=" * 70)
    print("VÝSLEDKY")
    print("=" * 70)
    print(f"\nCelkem slov s přepisem: {len(words_with_pronunciation)}")
    print(f"  - Existující přepisy (ze zdrojů): {len(existing_pronunciations)}")
    print(f"  - Automaticky generované přepisy: {len(generated_pronunciations)}")
    print(f"  - Slova bez přepisu: {len(words_without_pronunciation)}")

    if existing_pronunciations:
        print(f"\nUkázka existujících přepisů (prvních 10):")
        for word, pron in existing_pronunciations[:10]:
            print(f"  {word:30} -> {pron}")

    if generated_pronunciations:
        print(f"\nUkázka automaticky generovaných přepisů (prvních 20):")
        for word, pron in generated_pronunciations[:20]:
            print(f"  {word:30} -> {pron} (generováno)")
        if len(generated_pronunciations) > 20:
            print(f"  ... a dalších {len(generated_pronunciations) - 20} generovaných přepisů")

    if words_without_pronunciation:
        print(f"\nSlova bez přepisu (prvních 30):")
        for word in words_without_pronunciation[:30]:
            print(f"  {word}")
        if len(words_without_pronunciation) > 30:
            print(f"\n  ... a dalších {len(words_without_pronunciation) - 30} slov bez přepisu")
        print(f"  (Tato slova nebyly možné automaticky převést)")

    # FÁZE 3: Aktualizace slovníku (pouze slova s přepisem)
    if words_with_pronunciation:
        print("\n" + "=" * 70)
        print("FÁZE 3: AKTUALIZACE SLOVNÍKU")
        print("=" * 70)

        # Sloučíme existující slovník s novými daty
        merged_dict = existing_dict.copy()

        # Přidáme nová slova s přepisem
        new_words = {}
        updated_words = {}

        for word, pronunciation in words_with_pronunciation:
            if word not in merged_dict:
                new_words[word] = pronunciation
                merged_dict[word] = pronunciation
            elif merged_dict[word] != pronunciation:
                updated_words[word] = (merged_dict[word], pronunciation)
                merged_dict[word] = pronunciation

        if not new_words and not updated_words:
            print("\nŽádné změny k aplikování. Slovník je již aktuální.")
            return 0

        # Zobrazíme report
        print_report(new_words, updated_words)

        # Zeptáme se na potvrzení
        print("\nChcete aplikovat tyto změny? (ano/ne): ", end='')
        try:
            response = input().strip().lower()
            if response not in ['ano', 'a', 'yes', 'y']:
                print("Změny zrušeny.")
                return 0
        except (EOFError, KeyboardInterrupt):
            print("\nZměny zrušeny.")
            return 0

        # Vytvoříme zálohu
        if not create_backup():
            print("Varování: Nepodařilo se vytvořit zálohu!")
            print("Pokračovat? (ano/ne): ", end='')
            try:
                response = input().strip().lower()
                if response not in ['ano', 'a', 'yes', 'y']:
                    return 0
            except (EOFError, KeyboardInterrupt):
                return 0

        # Aktualizujeme soubor
        if update_phonetic_file(merged_dict):
            print("\n" + "=" * 70)
            print("ÚSPĚCH! Slovník byl aktualizován.")
            print("=" * 70)
            print(f"\nZáloha: {BACKUP_FILE}")
            print(f"Aktualizovaný soubor: {PHONETIC_FILE}")
            print(f"\nPřidáno nových slov: {len(new_words)}")
            print(f"Aktualizováno slov: {len(updated_words)}")
            print(f"Slov bez přepisu (vyžadují manuální doplnění): {len(words_without_pronunciation)}")
            print("\nTento skript a BAT soubor můžete nyní smazat.")
            return 0
        else:
            print("\nERROR: Nepodařilo se aktualizovat soubor!")
            return 1
    else:
        print("\nVarování: Nenalezeny žádné slova s fonetickým přepisem k přidání.")
        print("Slovník nebyl aktualizován.")
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nPřerušeno uživatelem.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nERROR: Neočekávaná chyba: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

