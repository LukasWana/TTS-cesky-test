# Integrace Lookup Tabulky pro Zlepšení Kvality XTTS-v2

## Přehled

Byla provedena integrace lookup tabulek z adresáře `lookup_tables` do systému pro zlepšení kvality syntézy řeči XTTS-v2.

## Vytvořené moduly

### 1. `backend/lookup_tables_loader.py`
Modul pro načítání a správu lookup tabulek:
- Načítá všechny JSON soubory z `lookup_tables/`
- Poskytuje metody pro přístup k jednotlivým pravidlům
- Singleton pattern pro efektivní použití

**Hlavní metody:**
- `get_prejata_slova_dict()` - vrací slovník přejatých slov pro fonetický přepis
- `get_znele_neznele_pary()` - vrací mapování znělých/neznělých souhlásek
- `get_souhlsakove_skupiny_rules()` - vrací pravidla pro souhláskové skupiny
- `get_prosodicke_pravidla()` - vrací prosodická pravidla
- `get_raz_pravidla()` - vrací pravidla pro vkládání rázu

### 2. `backend/czech_text_processor.py`
Modul pro pokročilé předzpracování českého textu:
- Aplikuje pravidla z lookup tabulek
- Normalizuje text pro lepší zpracování TTS
- Připraveno pro budoucí rozšíření (spodoba znělosti, ráz, souhláskové skupiny)

## Integrace do existujících modulů

### 1. `backend/phonetic_translator.py`
- **Rozšířeno:** Načítá přejatá slova z lookup tabulek při inicializaci
- **Výhoda:** Automatická oprava výslovnosti problematických přejatých slov
- **Příklad:** "benzín" → správná výslovnost podle lookup tabulek

### 2. `backend/prosody_processor.py`
- **Rozšířeno:** Načítá prosodická pravidla z lookup tabulek
- **Výhoda:** Přístup k strukturovaným prosodickým pravidlům pro budoucí rozšíření
- **Poznámka:** Prosodická pravidla jsou připravena pro budoucí použití

### 3. `backend/tts_engine.py`
- **Rozšířeno:** Integrace českého text processoru do předzpracování textu
- **Konfigurace:** Nová možnost `ENABLE_CZECH_TEXT_PROCESSING` v `config.py`
- **Místo:** V metodě `_preprocess_text_for_czech()` po fonetickém přepisu

## Konfigurace

V `backend/config.py` byla přidána nová možnost:

```python
# Czech Text Processing (pokročilé předzpracování pomocí lookup tabulek)
ENABLE_CZECH_TEXT_PROCESSING = os.getenv("ENABLE_CZECH_TEXT_PROCESSING", "True").lower() == "true"
```

Můžete ji vypnout pomocí environment variable:
```bash
ENABLE_CZECH_TEXT_PROCESSING=False
```

## Načtené lookup tabulky

1. **foneticka_abeceda.json** - Kompletní fonetická abeceda (44 fonémů)
2. **spodoba_znelosti.json** - Pravidla spodoby znělosti
3. **prejata_slova_vyjimky.json** - Slovník problematických přejatých slov (36 slov)
4. **prosodicke_pravidla.json** - Prosodická pravidla (přízvuk, intonace, pauzy)
5. **raz_pozice.json** - Pravidla pro vkládání rázu
6. **souhlsakove_skupiny.json** - Problematické souhláskové skupiny

## Jak to funguje

1. **Při startu:** `LookupTablesLoader` načte všechny JSON soubory z `lookup_tables/`
2. **Při inicializaci PhoneticTranslator:** Automaticky načte přejatá slova a přidá je do slovníku
3. **Při předzpracování textu v TTS:**
   - Nejdříve se aplikuje fonetický přepis (včetně přejatých slov z lookup tabulek)
   - Pak se aplikuje český text processor (normalizace)
   - Nakonec se aplikuje prosody processing

## Výhody

1. **Automatická oprava výslovnosti** - Přejatá slova se automaticky přepisují podle lookup tabulek
2. **Strukturovaná pravidla** - Všechna pravidla jsou v JSON formátu, snadno se aktualizují
3. **Rozšiřitelnost** - Modulární struktura umožňuje snadné přidávání nových pravidel
4. **Konfigurovatelnost** - Všechny funkce lze zapnout/vypnout přes config

## Budoucí rozšíření

Moduly jsou připraveny pro budoucí implementaci:
- Aplikace spodoby znělosti na textové úrovni (pokud by bylo potřeba)
- Vkládání rázu pomocí SSML značek
- Oprava souhláskových skupin (mě → mňe) na fonetické úrovni
- Pokročilé prosodické značení podle lookup tabulek

## Testování

Lookup tabulky byly úspěšně načteny a testovány:
```
[OK] Lookup tabulky uspesne nacteny
[OK] Lookup tables loader OK
Prejata slova: 36
```

## Poznámky

- Spodoba znělosti a ráz jsou fonetické jevy, které XTTS model by měl zvládnout automaticky při správném tréninku
- Lookup tabulky primárně zlepšují výslovnost přejatých slov, která model nemusí znát
- Prosodická pravidla jsou připravena pro budoucí rozšíření prosody control funkcionality

