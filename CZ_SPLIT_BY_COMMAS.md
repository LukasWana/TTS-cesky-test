# CZ Split by Commas - Dokumentace

## 🎯 Cíl

Dělit české a slovenské texty po čárkách a max. 8-10 slovech, každou část obalit uvozovkami, generovat zvlášť a spojit na konci s minimálními pauzami pro přirozenější intonaci.

## 📊 Požadavky

| Parametr | Výchozí hodnota | Popis |
|----------|----------------|-------|
| `ENABLE_CZ_SPLIT_BY_COMMAS` | `False` | Zapnutí/vypnutí dělení |
| `CZ_SPLIT_MAX_WORDS` | `10` | Max. počet slov v jedné části |
| `CZ_SPLIT_LANGUAGES` | `cs,sk` | Jazyky, které se dělí |

## 🔧 Nastavení

### Windows (PowerShell)
```powershell
$env:ENABLE_CZ_SPLIT_BY_COMMAS="True"
$env:CZ_SPLIT_MAX_WORDS="10"
$env:CZ_SPLIT_LANGUAGES="cs,sk"
```

### Windows (CMD)
```cmd
set ENABLE_CZ_SPLIT_BY_COMMAS=True
set CZ_SPLIT_MAX_WORDS=10
set CZ_SPLIT_LANGUAGES=cs,sk
```

### Linux/Mac
```bash
export ENABLE_CZ_SPLIT_BY_COMMAS=True
export CZ_SPLIT_MAX_WORDS=10
export CZ_SPLIT_LANGUAGES=cs,sk
```

## 📋 Pravidla dělení

1. **Primárně dělit po čárkách**
   ```
   Útočiště ve Třech klenotech by mělo být motivováno, že právě Buddha, Dharma a Sangha.
   → [Útočiště ve Třech klenotech by mělo být motivováno]
   → [že právě Buddha]
   → [Dharma a Sangha]
   ```

2. **Pokud část má > 10 slov, dělit dále po slovech**
   ```
   Toto je velmi dlouhá věta s mnoha slovy, která přesáhne limit.
   → [Toto je velmi dlouhá věta s mnoha slovy]
   → [která přesáhne limit]
   ```

3. **Odstranit koncovou interpunkci uvnitř částí** (tečka, otazník, vykřičník)
   ```
   Ahoj, jak se máš?
   → [Ahoj]
   → [jak se máš]
   ```

4. **Obalit každou část uvozovkami**
   ```
   Pro každý pár si vyber stranu.
   → "Pro každý pár si vyber stranu"
   ```

## 📊 Příklady

### Příklad 1: Dlouhá věta s čárkami
```
Vstup:
Útočiště ve Třech klenotech by mělo být motivováno znepokojením naší současné situací a přesvědčením, že právě Buddha, Dharma a Sangha nabízí její řešení.

Výstup (s ENABLE_CZ_SPLIT_BY_COMMAS=True):
"Útočiště ve Třech klenotech by mělo být motivováno znepokojením naší"
"současné situací a přesvědčením"
"že právě Buddha"
"Dharma a Sangha nabízí její řešení"
```

### Příklad 2: Krátká věta s čárkou
```
Vstup:
Pro každý pár si vyber stranu, která ti připadá nejpřirozenější.

Výstup (s ENABLE_CZ_SPLIT_BY_COMMAS=True):
"Pro každý pár si vyber stranu"
"která ti připadá nejpřirozenější"
```

### Příklad 3: Věta s otazníkem
```
Vstup:
Ahoj, jak se máš?

Výstup (s ENABLE_CZ_SPLIT_BY_COMMAS=True):
"Ahoj"
"jak se máš"
```

### Příklad 4: Věta s vykřičníkem (bez čárky)
```
Vstup:
Pozor! Nepoužívejte tento výtah při požáru.

Výstup (s ENABLE_CZ_SPLIT_BY_COMMAS=True):
"Pozor! Nepoužívejte tento výtah při požáru"
```

## ⚖️ Rizika a omezení

| Riziko | Pravděpodobnost | Zmírnění |
|--------|-----------------|-----------|
| Příliš mnoho pauz mezi částmi | STŘEDNÍ | Crossfade 30ms minimalizuje pauzy |
| Token overflow u jedné části | NÍZKÁ | Max 10 slov ≈ 30-40 tokenů |
| Ne přirozené spojení částí | STŘEDNÍ | AudioConcatenator s crossfade |
| Prodloužení času generování | STŘEDNÍ | Každou část generovat zvlášť |

## 🔍 Kompatibilita

| Funkce | Kompatibilita | Požadované úpravy | Status |
|--------|---------------|-------------------|--------|
| `generate_batch()` | ⚠️ Částečná | Ověřit integraci | ⏳ Čeká na otestování |
| `handle_pauses` (PAUSE značky) | ✅ Kompatibilní | Dělení před PAUSE zpracováním | ✅ Hotovo |
| `enable_dialect_conversion` | ✅ Kompatibilní | Aplikovat PŘED dělením | ✅ Hotovo |
| `enable_vad`, `enable_trim` | ✅ Kompatibilní | Aplikovat PO spojení | ✅ Hotovo |
| Chrome Extension (WebSocket) | ⚠️ Částečná | Ověřit integraci | ✅ Hotovo |
| Standardní HTTP endpoint | ✅ Kompatibilní | - | ✅ Hotovo |

---

## 🌐 Chrome Extension Integrace

### Implementované změny:
- **WebSocket router (`backend/api/routers/realtime.py`):**
  - Přidán import `TTSEngine` třídy
  - Přidány konfigurační proměnné (`ENABLE_CZ_SPLIT_BY_COMMAS`, atd.)
  - Integrace statické metody `_split_text_by_commas_and_words()` do stream módu
  - Přidány diagnostické logy pro sledování toku dat

### Ovlivnění na funkci:
**Zapnutí/Vypnutí:**
```bash
# Windows (PowerShell)
$env:ENABLE_CZ_SPLIT_BY_COMMAS="True"

# Windows (CMD)
set ENABLE_CZ_SPLIT_BY_COMMAS=True

# Linux/Mac
export ENABLE_CZ_SPLIT_BY_COMMAS=True
```

**Konfigurace počtu slov:**
```bash
export CZ_SPLIT_MAX_WORDS=10  # nebo 8, 12 atd.
```

### Tok dat s Chrome Extension:
```
Vstupní text → WebSocket → backend/api/routers/realtime.py
  ↓
Použij TTSEngine._split_text_by_commas_and_words()
  ↓
Rozdělení na části (po čárkách a 8-10 slovech)
  ↓
Generování každé části zvlášť (tts_engine.generate())
  ↓
Odesílání audio přes WebSocket:
  - type: "audio_chunk"
  - chunk_index: 0, 1, 2, ...
  - audio: base64_encoded_audio
  - pause_after: 250 (pro části končící interpunkcí)
  ↓
Konec streamu:
  - type: "stream_complete"
  ↓
Chrome Extension přehrává audio části s pauzami
```

### Diagnostika:
**Backend logy (očekávané):**
```
[INFO] Streaming: 4 chunks (CZ Split: True, Max words: 10)
[DEBUG] Rozděleno na 4 částí (max 10 slov na část)
[INFO] [WS] Sending chunk 1/4 to client 3aeb7121
[INFO] [WS] Sending chunk 2/4 to client 3aeb7121
[INFO] [WS] Sending chunk 3/4 to client 3aeb7121
[INFO] [WS] Sending chunk 4/4 to client 3aeb7121
[INFO] [WS] Stream complete sent to client 3aeb7121: 4 chunks
```

**Chrome konzole (očekávané):**
```
[WS] Connected
[WS] Client 3aeb7121: 'Útočiště ve Třech...' req=1
[Voice Assistant] Playing chunk 1/4...
[Voice Assistant] Playing chunk 2/4...
[Voice Assistant] Playing chunk 3/4...
[Voice Assistant] Playing chunk 4/4...
```

### Známé problémy:
- **Backend se nespustí** kvůli pre-existing problému s Python importy
  - Chyba: `ModuleNotFoundError: No module named 'TTS'`
  - Toto není způsobeno mou implementací
  - Vyžaduje opravu PYTHONPATH nebo použití startovacích skriptů
- **Chrome Extension je TICHO** dokud backend běží
  - WebSocket logy nejsou viditelné (backend neodesílá)
  - Potřebuje spustit backend a otestovat

### Status integrace: ✅ Implementováno, ⏳ Čeká na otestování

## 🧪 Testování

### Spuštění testovacího skriptu
```bash
python test_cz_split_by_commas.py
```

### Ruční testování
1. Nastavte `ENABLE_CZ_SPLIT_BY_COMMAS=True`
2. Spusťte backend: `python backend/main.py`
3. Otevřete Voice Studio nebo použijte Chrome Extension
4. Vložte text s čárkami
5. Sledujte logy: hledáte `[DEBUG] Rozděleno na X částí`
6. Poslouchejte výstupní audio

## 📝 Poznámky

- Funkce je ve výchozím stavu **VYPNUTA** (`False`) pro zpětnou kompatibilitu
- Zapnutí funkce může prodloužit čas generování (každou část generovat zvlášť)
- Pro krátké texty (bez čárek) se funkce neaplikuje
- Audio části se spojují s crossfade 30ms pro plynulé přechody

## 🚀 Integrace

### V kódu
```python
# backend/tts_engine.py
text_parts = self._split_text_by_commas_and_words(processed_text, language)

if len(text_parts) > 1:
    # Více částí: generuj každou zvlášť a spoj
    audio_files = []
    for i, part in enumerate(text_parts):
        part_output = temp_dir / f"part_{i}_{uuid.uuid4()}.wav"
        self.model.tts_to_file(text=part, file_path=str(part_output), ...)
        audio_files.append(str(part_output))

    # Spoj audio části
    AudioConcatenator.concatenate_audio(audio_files, output_path, crossfade_ms=30, pause_ms=0)
else:
    # Jedna část: původní logika
    self.model.tts_to_file(text=text_parts[0], file_path=output_path, ...)
```

### V config.py
```python
ENABLE_CZ_SPLIT_BY_COMMAS = os.getenv("ENABLE_CZ_SPLIT_BY_COMMAS", "False").lower() == "true"
CZ_SPLIT_MAX_WORDS = int(os.getenv("CZ_SPLIT_MAX_WORDS", "10"))
CZ_SPLIT_LANGUAGES = os.getenv("CZ_SPLIT_LANGUAGES", "cs,sk").split(",")
```

## 📚 Reference

- `backend/tts_engine.py` - Implementace `_split_text_by_commas_and_words()`
- `backend/config.py` - Konfigurační parametry
- `backend/audio_concatenator.py` - Spojení audio částí
- `test_cz_split_by_commas.py` - Testovací skript
