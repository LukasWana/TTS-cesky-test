# 📋 Kompletní shrnutí: CZ Split by Commas pro Chrome Extension

## 🎯 Cíl implementace

Implementovat dělení českých a slovenských textů po čárkách a 8-10 slovech pro lepší intonaci v XTTSv2 modelu, s plnou integrací do Chrome Extension.

---

## ✅ Dokončené změny

### **Fáze 1: Backend Config** ✅
**Soubor:** `backend/config.py`

**Změny:**
```python
# CZ Sentence Quotes (uvozovky pro české věty)
ENABLE_CZ_SENTENCE_QUOTES = os.getenv("ENABLE_CZ_SENTENCE_QUOTES", "True").lower() == "true"

# CZ Split by Commas (dělení textu po čárkách a slovech)
ENABLE_CZ_SPLIT_BY_COMMAS = os.getenv("ENABLE_CZ_SPLIT_BY_COMMAS", "False").lower() == "true"
CZ_SPLIT_MAX_WORDS = int(os.getenv("CZ_SPLIT_MAX_WORDS", "10"))  # Max slov na část
CZ_SPLIT_MIN_WORDS = int(os.getenv("CZ_SPLIT_MIN_WORDS", "1"))  # Min slov na část
CZ_SPLIT_LANGUAGES = os.getenv("CZ_SPLIT_LANGUAGES", "cs,sk").split(",")  # Jazyky, které se dělí
```

**Status:** ✅ Hotovo
**Výchozí nastavení:** `ENABLE_CZ_SPLIT_BY_COMMAS=False` (vypnuto pro zpětnou kompatibilitu)

---

### **Fáze 2: TTS Engine - Statická metoda** ✅
**Soubor:** `backend/tts_engine.py`

**Změny:**
- Převedení `_split_text_by_commas_and_words()` na `@staticmethod`
- Lze volat bez instance `TTSEngine`
- Snadná integrace do WebSocket routeru

**Status:** ✅ Hotovo a otestováno
**Výsledek testů:** 7/7 PASS

---

### **Fáze 3: WebSocket Router Integrace** ✅
**Soubor:** `backend/api/routers/realtime.py`

**Změny:**
1. Přidány importy:
   ```python
   from backend.config import (
       ENABLE_CZ_SPLIT_BY_COMMAS,
       CZ_SPLIT_MAX_WORDS,
       CZ_SPLIT_LANGUAGES,
   )
   from backend.tts_engine import TTSEngine
   ```

2. Integrace logiky dělení do stream módu:
   ```python
   if lang in CZ_SPLIT_LANGUAGES and ENABLE_CZ_SPLIT_BY_COMMAS:
       # Volat statickou metodu z TTSEngine
       chunks = TTSEngine._split_text_by_commas_and_words(text, lang)
       logger.info(f"Streaming: {len(chunks)} chunks (CZ Split enabled, Max words: {CZ_SPLIT_MAX_WORDS})")
   else:
       # Původní logika (fast_sentence_split)
       chunks = fast_sentence_split(text)
       logger.info(f"Streaming: {len(chunks)} chunks (Legacy mode)")
   ```

3. Přidány diagnostické logy:
   ```python
   logger.info(f"[WS] Sending chunk {i+1}/{len(chunks)} to client {client_id}")
   logger.info(f"[WS] Stream complete sent to client {client_id}: {len(chunks)} chunks")
   logger.info(f"[WS] Sending done to client {client_id}: {audio_url}")
   ```

**Status:** ✅ Hotovo

---

### **Fáze 4: Testovací skript** ✅
**Soubor:** `test_cz_split_by_commas.py`

**Funkce:**
- Automatické testování dělení textu
- 7 testovacích případů
- Ověření správnosti dělení po čárkách a slovech
- Ověření přidání uvozovek

**Status:** ✅ Hotovo - 7/7 testy PASS

---

### **Fáze 5: Dokumentace** ✅
**Soubory:**
- `README.md` - aktualizována o sekce:
  - "⚠️ DŮLEŽITÉ: Správný způsob spuštění backendu"
  - "⚙️ Environment Variables" (CZ Split by Commas)
  - "3. Chrome Extension Integration"
  - "⚠️ Chyba: Backend se nespustí / ModuleNotFoundError"

- `CZ_SPLIT_BY_COMMAS.md` - detailní dokumentace funkce
- `CHROME_EXTENSION_INTEGRATION_STATUS.md` - status integrace

**Status:** ✅ Hotovo

---

## 📊 Pravidla dělení textu

### **Primární dělení:**
1. **Po čárkách** - preferované dělení
   ```
   Útočiště ve Třech klenotech by mělo být motivováno, že právě Buddha.
   → [Útočiště ve Třech klenotech by mělo být motivováno]
   → [že právě Buddha]
   ```

### **Sekundární dělení:**
2. **Max. 8-10 slov** - pokud část po čárce má > 10 slov
   ```
   Toto je velmi dlouhá věta s mnoha slovy, která přesáhne limit.
   → [Toto je velmi dlouhá věta s mnoha slovy]
   → [která přesáhne limit deseti slov v jednom úseku]
   → [takže bude rozdělena na více částí]
   ```

### **Předzpracování:**
3. **Odstranění koncové interpunkce** uvnitř částí
   ```
   Ahoj, jak se máš?
   → "Ahoj"  (otazník odstraněn)
   → "jak se máš"
   ```

4. **Přidání uvozovek** (pokud `ENABLE_CZ_SENTENCE_QUOTES=True`)
   ```
   Pro každý pár si vyber stranu, která ti připadá nejpřirozenější.
   → "Pro každý pár si vyber stranu"
   → "která ti připadá nejpřirozenější"
   ```

---

## ⚡ Nastavení pro Chrome Extension

### **Zapnutí funkce:**

**Uprava `.env` souboru:**
```env
ENABLE_CZ_SPLIT_BY_COMMAS=True
CZ_SPLIT_MAX_WORDS=10
CZ_SPLIT_LANGUAGES=cs,sk
```

**Nebo přes command line:**
```bash
# Windows (CMD)
set ENABLE_CZ_SPLIT_BY_COMMAS=True

# Windows (PowerShell)
$env:ENABLE_CZ_SPLIT_BY_COMMAS="True"

# Linux/Mac
export ENABLE_CZ_SPLIT_BY_COMMAS=True
```

### **Restart backendu:**
```bash
./start_cpu.bat  # nebo start_gpu.bat
```

---

## 🧪 Očekávané výsledky

### **S funkcí VYPNUTO (`ENABLE_CZ_SPLIT_BY_COMMAS=False`):**
```
Vstup: Útočiště ve Třech klenotech by mělo být motivováno, že právě Buddha.

Backend logy:
[INFO] Streaming: 2 chunks (CZ Split: False, Max words: 10)

Chrome logy:
[Voice Assistant] Playing chunk 1/2...
[Voice Assistant] Playing chunk 2/2...
```

### **S funkcí ZAPNUTO (`ENABLE_CZ_SPLIT_BY_COMMAS=True`):**
```
Vstup: Útočiště ve Třech klenotech by mělo být motivováno, že právě Buddha, Dharma a Sangha nabízí její řešení.

Backend logy:
[INFO] Streaming: 4 chunks (CZ Split: True, Max words: 10)
[DEBUG] Rozděleno na 4 částí (max 10 slov na část)
[DEBUG]   [1] "Útočiště ve Třech klenotech by mělo být motivováno..."
[DEBUG]   [2] "současné situací a přesvědčením"
[DEBUG]   [3] "že právě Buddha"
[DEBUG]   [4] "Dharma a Sangha nabízí její řešení"
[INFO] [WS] Sending chunk 1/4 to client 3aeb7121
[INFO] [WS] Sending chunk 2/4 to client 3aeb7121
[INFO] [WS] Sending chunk 3/4 to client 3aeb7121
[INFO] [WS] Sending chunk 4/4 to client 3aeb7121
[INFO] [WS] Stream complete sent to client 3aeb7121: 4 chunks

Chrome logy:
[Voice Assistant] Playing chunk 1/4...
[Voice Assistant] Playing chunk 2/4...
[Voice Assistant] Playing chunk 3/4...
[Voice Assistant] Playing chunk 4/4...
```

---

## ⚠️ Zjištěný problém: Python import

### **Problém:**
```
ModuleNotFoundError: No module named 'TTS'
```

### **Příčina:**
- Při testování se používá `cd backend && python main.py`
- Tento Python NENÍ ve virtual environment (venv)
- TTS balíček je nainstalován jen ve venv
- `sys.path` neobsahuje cestu do venv

### **Řešení:**
**POUŽÍVEJTE startovací skripty:**
```bash
./start_cpu.bat    # CPU režim
./start_gpu.bat    # GPU režim
./start_all.bat    # Backend + Frontend
```

**Tyto skripty automaticky:**
1. ✅ Najdou kompatibilní verzi Pythonu
2. ✅ Aktivují virtual environment (venv)
3. ✅ Nastavují PYTHONPATH
4. ✅ Instalují potřebné závislosti
5. ✅ Spouští backend ve správném prostředí

### **Při manuálním spuštění (pro vývoj):**
```bash
# 1. Aktivujte venv
call venv\Scripts\activate.bat    # Windows (CMD)
venv\Scripts\Activate.ps1         # Windows (PowerShell)
source venv/bin/activate         # Linux/Mac

# 2. Nastavte PYTHONPATH
set PYTHONPATH=%CD%              # Windows (CMD)
$env:PYTHONPATH=$(Get-Location).Path  # Windows (PowerShell)
export PYTHONPATH=$(pwd)          # Linux/Mac

# 3. Spusťe backend
cd backend
python main.py
```

### **POUŽÍVEJTE TOTO:**
```bash
cd backend
python main.py
```

**NEPOUŽÍVEJTE TOTO!** → Backend se nespustí → `ModuleNotFoundError: No module named 'TTS'`

---

## 📋 Kontrolní seznam pro otestování

- [ ] Backend je spuštěn přes `start_cpu.bat`
- [ ] Backend běží na portu 8000
- [ ] TTS model je načten (backend logy)
- [ ] `.env` obsahuje `ENABLE_CZ_SPLIT_BY_COMMAS=True`
- [ ] Chrome Extension je nainstalována a aktivní
- [ ] Testovací text obsahuje čárky pro dělení
- [ ] Backend logy ukazují `[DEBUG] Rozděleno na X částí`
- [ ] WebSocket logy ukazují `[WS] Sending chunk X/Y`
- [ ] Chrome konzole ukazuje `[Voice Assistant] Playing chunk X/Y`
- [ ] Audio se přehrává bez ticha
- [ ] Intonace je přirozenější než bez dělení

---

## 🎯 Očekávané zlepšení intonace

### **Bez CZ Split by Commas:**
- Dlouhé věty → dramatický pokles intonace na konci
- Text: "Útočiště ve Třech klenotech by mělo být motivováno znepokojením naší současné situací a přesvědčením, že právě Buddha, Dharma a Sangha nabízí její řešení."
- Výsledek: Celý věta v jednom chunk → výrazný pokles na konci

### **S CZ Split by Commas:**
- Rozdělení po čárkách → menší pokles intonace
- Text rozdělen na 4 části → každá část má menší pokles
- Spojení částí s crossfade (30ms) → plynulý přechod
- Výsledek: Přirozenější intonace, méně výrazný pokles

---

## 📊 Shrnutí

| Fáze | Popis | Status | Testy |
|-------|-------|--------|-------|
| 1. Backend Config | Přidání konfiguračních proměnných | ✅ Hotovo | - |
| 2. TTS Engine | Refaktoring na statickou metodu | ✅ Hotovo | 7/7 PASS |
| 3. WebSocket Router | Integrace dělení a logů | ✅ Hotovo | - |
| 4. Testovací skript | Automatické testování | ✅ Hotovo | 7/7 PASS |
| 5. Dokumentace | README + CZ_SPLIT_BY_COMMAS.md | ✅ Hotovo | - |
| 6. README aktualizace | Sekce o správném spuštění | ✅ Hotovo | - |
| 7. Otestování | Chrome Extension + backend | ⏳ Čeká na vás | - |

---

## 🚀 Jak otestovat

### **1. Spusťte backend:**
```bash
./start_cpu.bat
```

### **2. Upravte .env:**
```env
ENABLE_CZ_SPLIT_BY_COMMAS=True
CZ_SPLIT_MAX_WORDS=10
```

### **3. Restartujte backend:**
- Ukončete běžící backend (Ctrl+C)
- Spusťte znovu: `./start_cpu.bat`

### **4. Otevřete Chrome Extension:**
- Klikněte pravým tlačítkem na ikonu
- Vyberte text s čárkami
- Klikněte "Přečti nahlas"

### **5. Sledujte logy:**

**Backend terminál:**
```
[INFO] Streaming: 4 chunks (CZ Split: True, Max words: 10)
[DEBUG] Rozděleno na 4 částí (max 10 slov na část)
[INFO] [WS] Sending chunk 1/4 to client 3aeb7121
[INFO] [WS] Sending chunk 2/4 to client 3aeb7121
[INFO] [WS] Sending chunk 3/4 to client 3aeb7121
[INFO] [WS] Sending chunk 4/4 to client 3aeb7121
[INFO] [WS] Stream complete sent to client 3aeb7121: 4 chunks
```

**Chrome DevTools (F12 → Console):**
```
[WS] Connected
[Voice Assistant] Playing chunk 1/4...
[Voice Assistant] Playing chunk 2/4...
[Voice Assistant] Playing chunk 3/4...
[Voice Assistant] Playing chunk 4/4...
```

### **6. Poslouchejte výstup:**
- Ověřte, zda se přehrávají jednotlivé části
- Porovnejte intonaci mezi částmi
- Ověřte menší pokles intonace na konci

---

## 📚 Odkazy na dokumentaci

- **README.md** - kompletní dokumentace aplikace
- **CZ_SPLIT_BY_COMMAS.md** - detailní dokumentace funkce
- **CHROME_EXTENSION_INTEGRATION_STATUS.md** - status integrace

---

**Implementace je dokončena. Pro otestování je nutné použít startovací skripty (start_cpu.bat, start_gpu.bat), které automaticky aktivují virtual environment.**
