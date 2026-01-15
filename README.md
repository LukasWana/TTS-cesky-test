# XTTS-v2 Czech TTS Demo

Offline webová aplikace pro testování XTTS-v2 Text-to-Speech a voice cloningu v češtině. Aplikace běží kompletně lokálně bez závislosti na externích API.

## 🎯 Funkce

- ✅ **Text-to-Speech**: Generování českého hlasu z textu
- ✅ **Voice Cloning**: Klonování hlasu z audio vzorku (6+ sekund)
- ✅ **Demo hlasy**: Předpřipravené hlasy pro rychlé testování
- ✅ **Nahrávání z mikrofonu**: Nahrání hlasu přímo z prohlížeče
- ✅ **Offline provoz**: Vše běží lokálně, žádné externí API

## 📋 Požadavky

### Minimální
- **CPU**: 4 cores (Intel i5 nebo ekvivalent)
- **RAM**: 8 GB
- **Storage**: 10 GB (pro model + cache)
- **OS**: Windows 10/11, Ubuntu 20.04+, macOS 11+

### Doporučené
- **CPU**: 8+ cores
- **RAM**: 16 GB
- **GPU**: NVIDIA s 4+ GB VRAM (CUDA support)
- **Storage**: 20 GB SSD

### Software
- **Python**: 3.9, 3.10, nebo 3.11 (TTS nepodporuje Python 3.12+)
- **Node.js**: 18+
- **CUDA**: 11.8+ (volitelné, pro GPU inference)

**DŮLEŽITÉ**:
- TTS balíček není kompatibilní s Python 3.12+
- Instalační skripty automaticky vyhledají kompatibilní verzi Pythonu (3.9, 3.10, nebo 3.11)
- Pokud máte více verzí Pythonu, skript použije nejnovější kompatibilní verzi

## 🚀 Instalace

### Windows

**DŮLEŽITÉ**: TTS vyžaduje Python 3.9-3.11. Pokud máte Python 3.12+, použijte `run_python311.bat` nebo nainstalujte Python 3.11.

**Možnost 1: Automatická instalace (Python 3.11)**
```bash
run_python311.bat
```

**Možnost 2: Standardní instalace**
```bash
run.bat
```

Pokud máte Python 3.12+, skript vás upozorní a musíte nainstalovat Python 3.11 z [python.org](https://www.python.org/downloads/).

### Linux/Mac

Spusťte instalační skript:

```bash
chmod +x run.sh
./run.sh
```

### Manuální instalace

**⚠️ DŮLEŽITÉ:** Pokud spouštíte backend ručně (bez startovacích skriptů), **musíte aktivovat venv**:

```bash
# 1. Aktivujte virtual environment
source venv/bin/activate  # Windows: venv\Scripts\activate.bat

# 2. Nastavte PYTHONPATH
export PYTHONPATH=$(pwd)  # Linux/Mac
set PYTHONPATH=%CD%  # Windows (CMD)
$env:PYTHONPATH=$(Get-Location).Path  # Windows (PowerShell)

# 3. Spusťe backend
python main.py
```

**❌ NEPOUŽÍVEJTE TOTO:**
```bash
cd backend
python main.py
```

**Příčina:** Tento příkaz NEAKTIVUJE venv → Python nemůže najít modul TTS → `ModuleNotFoundError: No module named 'TTS'`

**Řešení:** Použijte startovací skripty (`start_cpu.bat`, `start_gpu.bat`, `start_all.bat`), které automaticky aktivují venv a nastavují PYTHONPATH. Více viz sekce [▶️ Spuštění](#-spuštění) níže.

---

1. **Backend setup:**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate.bat
pip install -r requirements.txt
```

2. **Frontend setup:**
```bash
cd frontend
npm install
cd ..
```

3. **Vytvoření adresářů:**
```bash
mkdir -p models uploads outputs frontend/assets/demo-voices
```

## ▶️ Spuštění

### ⚠️ DŮLEŽITÉ: Správný způsob spuštění backendu

**NEPOUŽÍVEJTE TOTO:**
```bash
cd backend
python main.py
```

**POUŽIJTE TOTO:**
```bash
# CPU režim
.\start_cpu.bat

# GPU režim (pokud máte NVIDIA GPU)
.\start_gpu.bat

# Vše (backend + frontend)
.\start_all.bat
```

**Příčina:**
- Při použití `cd backend && python main.py` se **NEAKTIVUJE** virtual environment (venv)
- Python nemůže najít modul `TTS` → `ModuleNotFoundError: No module named 'TTS'`
- Startovací skripty (`start_cpu.bat`, `start_gpu.bat`) automaticky aktivují venv a nastavují PYTHONPATH

---

### 1. Spuštění backendu (použijte startovací skripty)

**VÝCHOZÍ ZPŮSOB:**
```bash
# CPU režim
.\start_cpu.bat
```

**SKRIPTY automaticky:**
1. ✅ Najdou kompatibilní verzi Pythonu (3.9, 3.10, nebo 3.11)
2. ✅ Aktivují virtual environment (`venv`)
3. ✅ Nastavují PYTHONPATH
4. ✅ Nastavují UTF-8 kódování
5. ✅ Instalují potřebné závislosti (pokud chybí)
6. ✅ Spouštějí backend ve správném prostředí
7. ✅ Otevírají prohlížeč na http://localhost:3000

**Alternativa: Aktivace venv ručně (pokud potřebujete debugovat)**
```bash
# 1. Aktivujte venv
call venv\Scripts\activate.bat

# 2. Nastavte PYTHONPATH (přidá kořenový adresář projektu)
set PYTHONPATH=%CD%

# 3. Spusťe backend
cd backend
python main.py
```

**NEPOUŽÍVEJTE PRODUKČNÍ POUŽITÍ:**
```bash
cd backend
python main.py
```

Tento příkaz NEAKTIVUJE venv → Python nemůže najít TTS modul → Backend se nespustí.

---

### 2. Spuštění frontendu

**Při použití `start_all.bat` nebo `start_cpu.bat` se frontend spouští automaticky.**

**Ruční spuštění (pokud běží jen backend):**
```bash
cd frontend
npm run dev
```

Frontend poběží na `http://localhost:3000`

---

### 3. Otevření aplikace

Otevřete prohlížeč a přejděte na: **http://localhost:3000**

## 📖 Použití

### Generování řeči s demo hlasem

1. Vyberte "Demo hlas" v sekci výběru hlasu
2. Zadejte český text (max 500 znaků)
3. Klikněte na "🔊 Generovat řeč"
4. Počkejte na dokončení generování
5. Přehrát nebo stáhnout vygenerované audio

### Voice Cloning z audio souboru

1. Vyberte "Nahrát soubor"
2. Klikněte na "📁 Vybrat audio soubor"
3. Vyberte audio soubor (WAV, MP3) - minimálně 6 sekund
4. Zadejte text k syntéze
5. Klikněte na "🔊 Generovat řeč"

### Voice Cloning z mikrofonu

1. Vyberte "Nahrát z mikrofonu"
2. Klikněte na "🎤 Začít nahrávat"
3. Povolte přístup k mikrofonu
4. Nahrajte minimálně 6 sekund čistého audio
5. Klikněte na "⏹ Zastavit"
6. Zadejte text a generujte řeč

### 3. Chrome Extension Integration

**POUŽÍVE TOTO:** Při použití Chrome Extension se backend spouští automaticky přes startovací skripty.

**Spouštění Chrome Extension:**
1. Ujistěte se, že backend běží na portu 8000 (použijte `start_cpu.bat`)
2. Otevřete Chrome Extension
3. Vyberte text s čárkami pro lepší testování
4. Klikněte na "Přečti nahlas"

**Zapnutí CZ Split by Commas pro Chrome Extension:**

Upravte `.env` soubor:
```env
# Zapnutí dělení textu po čárkách a slovech
ENABLE_CZ_SPLIT_BY_COMMAS=True

# Maximální počet slov v jedné části (výchozí: 10)
CZ_SPLIT_MAX_WORDS=10

# Jazyky, které se dělí (výchozí: cs,sk)
CZ_SPLIT_LANGUAGES=cs,sk
```

Nebo nastavte přes command line:
```bash
# Windows (CMD)
set ENABLE_CZ_SPLIT_BY_COMMAS=True

# Windows (PowerShell)
$env:ENABLE_CZ_SPLIT_BY_COMMAS="True"

# Linux/Mac
export ENABLE_CZ_SPLIT_BY_COMMAS=True
```

**Restart backendu po změně nastavení:**
```bash
# Ukončete stávající backend (Ctrl+C)
# Spusťte znovu
.\start_cpu.bat
```

**Očekávané chování s CZ Split by Commas zapnutým:**
- Text se rozdělí po čárkách a 8-10 slovech
- Každá část se obalí uvozovkami pro lepší intonaci
- Menší pokles intonace na konci každé části
- Přirozenější spojení mezi částmi

---

## 🎤 Demo hlasy

Pro přidání demo hlasů:

1. Připravte audio soubory (WAV, 22050 Hz, mono)
2. Uložte je do `frontend/assets/demo-voices/`
3. Pojmenujte je např. `demo1.wav`, `demo2.wav`
4. Restartujte backend

## 🏗️ Struktura projektu

```
xtts-v2-demo/
├── backend/
│   ├── main.py              # FastAPI aplikace
│   ├── tts_engine.py         # XTTS-v2 wrapper
│   ├── audio_processor.py    # Audio utilities
│   └── config.py             # Konfigurace
├── frontend/
│   ├── src/
│   │   ├── App.jsx           # Hlavní komponenta
│   │   ├── components/        # React komponenty
│   │   └── services/          # API client
│   └── assets/
│       └── demo-voices/       # Demo audio soubory
├── models/                    # Cache pro XTTS-v2 modely
├── uploads/                   # Nahrané audio soubory
├── outputs/                   # Generované audio
├── requirements.txt
└── README.md
```

## 📦 Model načítání

Aplikace podporuje načítání XTTS-v2 modelu z několika zdrojů:

1. **Hugging Face (výchozí)**: Model se automaticky stáhne z [coqui/XTTS-v2](https://huggingface.co/coqui/XTTS-v2)
2. **TTS Registry**: Použití modelu z TTS model registry
3. **Lokální cache**: Pokud je model již stažen, použije se z cache

Model se ukládá do `models/` adresáře a při dalším spuštění se použije z cache.

Pro změnu zdroje modelu nastavte environment variable:
```bash
export XTTS_MODEL_NAME="coqui/XTTS-v2"  # Hugging Face (výchozí)
# nebo
export XTTS_MODEL_NAME="tts_models/multilingual/multi-dataset/xtts_v2"  # TTS registry
```

## 🔧 API Endpoints

- `POST /api/tts/generate` - Generování TTS
- `POST /api/voice/upload` - Upload audio souboru
- `POST /api/voice/record` - Nahrání z mikrofonu
- `GET /api/voices/demo` - Seznam demo hlasů
- `GET /api/models/status` - Status modelu
- `GET /api/audio/{filename}` - Stáhnutí audio

## ⚡ Performance

- **CPU only**: 5-15 sekund na generování (1-2 věty)
- **GPU (4GB)**: 1-3 sekundy na generování
- **GPU (8GB+)**: < 1 sekunda

## ⚙️ Environment Variables

Pro pokročilou konfiguraci můžete použít environment variables:

### CZ Sentence Quotes (Uvozovky pro české věty)
```bash
# Zapnutí/Vypnutí přidávání uvozovek pro lepší intonaci českých vět
# Výchozí: True (zapnuto)
ENABLE_CZ_SENTENCE_QUOTES=True  # nebo False pro vypnutí
```

### CZ Split by Commas (Dělení textu po čárkách a slovech)
```bash
# Zapnutí/Vypnutí dělení textu po čárkách a 8-10 slovech pro lepší intonaci
# Výchozí: False (vypnuto)
ENABLE_CZ_SPLIT_BY_COMMAS=True  # nebo False pro vypnutí

# Maximální počet slov v jedné části (výchozí: 10)
CZ_SPLIT_MAX_WORDS=10  # nebo 8, 12 atd.

# Jazyky, které se dělí (výchozí: cs,sk)
CZ_SPLIT_LANGUAGES=cs,sk  # nebo jen cs, nebo cs,sk,en
```

### Jiné konfigurační proměnné
Viz `backend/config.py` pro kompletní seznam možných nastavení.

## 🐛 Řešení problémů

### Model se nenačítá

- Zkontrolujte, zda máte dostatek místa na disku (model je ~2GB)
- První spuštění stáhne model automaticky
- Zkontrolujte internetové připojení pro stažení modelu

### Chyba při generování

- Zkontrolujte, zda je text v češtině
- Ujistěte se, že audio soubor má minimálně 6 sekund
- Zkontrolujte logy v terminálu backendu

### Chyba při generování

- Zkontrolujte, zda je text v češtině
- Ujistěte se, že audio soubor má minimálně 6 sekund
- Zkontrolujte logy v terminálu backendu

### ⚠️ Chyba: Backend se nespustí / ModuleNotFoundError

**Příznaky:**
```
ModuleNotFoundError: No module named 'TTS'
```
**Příčina:** Backend není spuštěn ve virtual environment (venv) a Python nemůže najít modul TTS.

**Řešení: POUŽIJTE startovací skripty**
```bash
# POŽIJTE TOTO:
cd backend
python main.py

# POŽIJTE TOTO (správný způsob):
.\start_cpu.bat          # CPU režim
# nebo
.\start_gpu.bat          # GPU režim (pokud máte NVIDIA GPU)
# nebo
.\start_all.bat          # Backend + Frontend + Applio
```

**Proč to nastává:**
- Při použití `cd backend && python main.py` se NEAKTIVUJE virtual environment (venv)
- TTS balíček je nainstalován jen v venv
- Systémový Python nemá přístup k TTS modulu

**Co dělají startovací skripty (správně):**
1. Najdou kompatibilní verzi Pythonu (3.9-3.11)
2. Aktivují virtual environment (venv)
3. Nastavují PYTHONPATH
4. Nastavují UTF-8 kódování
5. Instalují potřebné závislosti (pokud chybí)
6. Spouštějí backend ve správném prostředí

**Pokud potřebujete debugovat backend ručně:**
```bash
# 1. Aktivujte venv
call venv\Scripts\activate.bat    # Windows (CMD)
venv\Scripts\Activate.ps1         # Windows (PowerShell)
source venv/bin/activate         # Linux/Mac

# 2. Nastavte PYTHONPATH
set PYTHONPATH=%CD%              # Windows (CMD)
$env:PYTHONPATH=$(pwd).Path      # Windows (PowerShell)
export PYTHONPATH=$(pwd)          # Linux/Mac

# 3. Spusťe backend
cd backend
python main.py
```

---

### Audio se nepřehrává

- Zkontrolujte, zda backend běží na portu 8000
- Zkontrolujte CORS nastavení
- Zkuste jiný prohlížeč

## 📝 Licence

- **XTTS-v2**: Coqui Public Model License 1.0.0 (non-commercial use)
- **Demo app**: MIT License

## 👤 Kontakt

Developer: qWANAp
Project: XTTS-v2 Offline Demo
Version: 1.0

## 🙏 Poděkování

- [Coqui TTS](https://github.com/coqui-ai/TTS) za XTTS-v2 model
- Komunita za podporu a feedback

