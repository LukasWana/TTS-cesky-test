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

**Automatická instalace (doporučeno)**
```bash
run.bat
```

Skript automaticky:
- Vyhledá Python 3.11, 3.10 nebo 3.9 (v tomto pořadí)
- Vytvoří virtual environment s kompatibilní verzí
- Nainstaluje všechny závislosti

### Windows (spuštění jedním příkazem)

Po instalaci (nebo klidně rovnou místo ručního spouštění) použijte:

```bash
start_all.bat
```

Tento skript:
- vybere kompatibilní Python (3.11/3.10/3.9)
- vytvoří/aktivuje `venv`
- doinstaluje backend závislosti jen když chybí
- doinstaluje frontend závislosti jen když chybí
- spustí backend i frontend ve dvou oknech a otevře `http://localhost:3000`

Ukončení obou procesů:

```bash
stop_all.bat
```

**Alternativní skript**
```bash
run_python311.bat
```

Pokud nemáte kompatibilní verzi Pythonu, stáhněte si Python 3.10 nebo 3.11 z [python.org](https://www.python.org/downloads/).

### Linux/Mac

Spusťte instalační skript:

```bash
chmod +x run.sh
./run.sh
```

### Manuální instalace

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

### 1. Spuštění backendu

```bash
# Aktivace virtual environment
source venv/bin/activate  # Windows: venv\Scripts\activate.bat

# Spuštění serveru
cd backend
python main.py
```

Backend poběží na `http://localhost:8000`

### 2. Spuštění frontendu

V novém terminálu:

```bash
cd frontend
npm run dev
```

Frontend poběží na `http://localhost:3000`

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

## 🎤 Demo hlasy

### Příprava demo hlasů

Pro nejlepší výsledky použijte utility scripty pro přípravu audio vzorků:

#### Metoda 1: Python script (doporučeno)

```bash
# Základní konverze
python scripts/prepare_demo_voice.py input.mp3 frontend/assets/demo-voices/male_cz.wav

# Ořez na 10 sekund od 5. sekundy
python scripts/prepare_demo_voice.py input.mp3 frontend/assets/demo-voices/male_cz.wav --trim 5 10

# S pokročilým zpracováním (noise reduction + high-pass filter)
python scripts/prepare_demo_voice.py input.mp3 frontend/assets/demo-voices/male_cz.wav --noise-reduction --highpass

# Automaticky do demo-voices složky
python scripts/prepare_demo_voice.py input.mp3 --demo-dir
```

#### Metoda 2: Batch script (Windows)

```bash
# Základní použití
scripts\prepare_demo_voice.bat input.mp3 output.wav
```

#### Metoda 3: FFmpeg (pokud máte FFmpeg nainstalovaný)

```bash
# Z MP3 na WAV, 22050 Hz, mono
ffmpeg -i input.mp3 -ar 22050 -ac 1 output.wav

# S normalizací
ffmpeg -i input.mp4 -ar 22050 -ac 1 -af "loudnorm" output.wav

# Ořez na 10 sekund od 5. sekundy
ffmpeg -i input.wav -ss 5 -t 10 -ar 22050 -ac 1 output.wav
```

### Testování kvality vzorku

Po přípravě vzorku ho otestujte:

```bash
# Python script
python scripts/test_voice_quality.py frontend/assets/demo-voices/male_cz.wav

# S vlastním testovacím textem
python scripts/test_voice_quality.py frontend/assets/demo-voices/male_cz.wav --text "Vlastní testovací text"

# Batch script (Windows)
scripts\test_voice_quality.bat frontend/assets/demo-voices/male_cz.wav
```

### Požadavky na demo hlasy

- **Délka:** Minimálně 6 sekund (doporučeno 10-30 sekund)
- **Formát:** WAV, 22050 Hz, mono
- **Kvalita:** Studiová kvalita, tichá místnost, dobrý mikrofon
- **Obsah:** Přirozený mluvený projev, různorodá intonace, celé věty

📖 **Více informací:** Viz `frontend/assets/demo-voices/README.md`

## 🏗️ Struktura projektu

```
xtts-v2-demo/
├── backend/
│   ├── main.py              # FastAPI aplikace
│   ├── tts_engine.py         # XTTS-v2 wrapper
│   ├── audio_processor.py    # Audio utilities
│   └── config.py             # Konfigurace
├── backend/
│   ├── main.py              # FastAPI aplikace
│   ├── tts_engine.py         # XTTS-v2 wrapper
│   ├── audio_processor.py    # Audio utilities (s FFmpeg fallback)
│   └── config.py             # Konfigurace
├── frontend/
│   ├── src/
│   │   ├── App.jsx           # Hlavní komponenta
│   │   ├── components/        # React komponenty
│   │   └── services/          # API client
│   └── assets/
│       └── demo-voices/       # Demo audio soubory + README.md
├── scripts/
│   ├── prepare_demo_voice.py  # Utility pro přípravu demo hlasů
│   ├── test_voice_quality.py  # Test kvality voice vzorku
│   ├── prepare_demo_voice.bat # Windows wrapper
│   └── test_voice_quality.bat # Windows wrapper
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
- `POST /api/voice/upload` - Upload audio souboru (automaticky zpracuje s pokročilým post-processing)
- `POST /api/voice/record` - Nahrání z mikrofonu
- `GET /api/voices/demo` - Seznam demo hlasů
- `GET /api/models/status` - Status modelu
- `GET /api/audio/{filename}` - Stáhnutí audio

## 🛠️ Utility Scripty

Projekt obsahuje utility scripty pro práci s audio vzorky:

### `scripts/prepare_demo_voice.py`
Připraví audio vzorek pro XTTS-v2 voice cloning:
- Konverze na 22050 Hz, mono
- Normalizace hlasitosti
- Ořez ticha
- Volitelné: noise reduction, high-pass filter
- Ořez na konkrétní časový úsek

### `scripts/test_voice_quality.py`
Otestuje kvalitu voice vzorku:
- Načte XTTS-v2 model
- Vygeneruje testovací řeč
- Uloží výstup pro poslech

**Všechny utility scripty podporují FFmpeg fallback** - pokud librosa selže, automaticky použije FFmpeg (pokud je nainstalovaný).

## ⚡ Performance

- **CPU only**: 5-15 sekund na generování (1-2 věty)
- **GPU (4GB)**: 1-3 sekundy na generování
- **GPU (6GB, RTX 3060)**: 1-2 sekundy na generování (s optimalizacemi)
- **GPU (8GB+)**: < 1 sekunda

### GPU akcelerace a přepínání Device

Pro použití GPU (NVIDIA) místo CPU:

1. **Zkontrolujte CUDA dostupnost:**
   ```bash
   python -c "import torch; print(torch.cuda.is_available())"
   ```

2. **Pokud je False, nainstalujte PyTorch s CUDA:**
   ```bash
   # Pro RTX 3060 (CUDA 11.8)
   pip uninstall torch torchaudio -y
   pip install torch==2.1.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cu118
   ```

   Nebo použijte automatický skript:
   ```bash
   install_pytorch_gpu.bat
   ```

3. **Pro GPU s 6GB VRAM (RTX 3060) použijte optimalizace:**
   ```bash
   # Před spuštěním backendu
   set SUNO_USE_SMALL_MODELS=True
   set SUNO_OFFLOAD_CPU=True
   ```

4. **Restartujte backend** - model se automaticky načte na GPU

**Výhody GPU:**
- 5-10x rychlejší generování než CPU
- Reálný čas pro krátké texty
- Lepší uživatelský zážitek

#### Přepínání mezi CPU a GPU

Můžete vynutit použití CPU nebo GPU přes environment variable `FORCE_DEVICE`:

**Vynutit CPU:**
```bash
set FORCE_DEVICE=cpu
start_all.bat
```

**Vynutit GPU:**
```bash
set FORCE_DEVICE=cuda
start_all.bat
```

**Automatická detekce (výchozí):**
```bash
set FORCE_DEVICE=auto
start_all.bat
# nebo jednoduše bez nastavení proměnné
start_all.bat
```

**Poznámky:**
- Pokud vynutíte GPU (`FORCE_DEVICE=cuda`) ale GPU není dostupné, automaticky se použije CPU
- Pokud vynutíte CPU (`FORCE_DEVICE=cpu`), GPU se nepoužije ani když je dostupné
- Aktuální device je zobrazen v UI (v hlavičce aplikace)
- Pro změnu device je potřeba restartovat backend server

## 🐛 Řešení problémů

### Model se nenačítá

- Zkontrolujte, zda máte dostatek místa na disku (model je ~2GB)
- První spuštění stáhne model automaticky
- Zkontrolujte internetové připojení pro stažení modelu

### Chyba při generování

- Zkontrolujte, zda je text v češtině
- Ujistěte se, že audio soubor má minimálně 6 sekund
- Zkontrolujte logy v terminálu backendu

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

