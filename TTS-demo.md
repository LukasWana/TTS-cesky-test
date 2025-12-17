Technické zadání: Offline XTTS-v2 Demo Aplikace
Přehled projektu
Lokální webová aplikace pro testování XTTS-v2 TTS a voice cloningu v češtině. Běží kompletně offline na vlastním počítači.

1. Cíle projektu
Primární cíle

✅ Funkční offline TTS demo s XTTS-v2
✅ Podpora češtiny (cs)
✅ Voice cloning z audio vzorku
✅ Jednoduchý web interface
✅ Bez závislosti na externích API

Success criteria

Aplikace funguje lokálně bez internetu
Generování audio < 10 sekund pro krátký text
Kvalitní český TTS výstup
Intuitivní UI pro netechnické uživatele


2. Funkční požadavky
2.1 Core funkce
Text-to-Speech

Input: Text v češtině (max 500 znaků)
Output: Audio soubor (WAV/MP3)
Přehrání přímo v browseru
Download generovaného audio

Voice Cloning

Upload audio souboru (WAV, MP3)
Nebo nahrání z mikrofonu (min 6 sekund)
Automatická konverze na správný formát (22050 Hz, mono)
Preview nahraného audio před použitím

Předpřipravené hlasy

3-5 demo hlasů (muž/žena/dítě)
Možnost přepínat mezi demo hlasy
Export/import vlastních hlasů

2.2 User Interface
┌─────────────────────────────────────┐
│  XTTS-v2 Czech TTS Demo             │
├─────────────────────────────────────┤
│                                     │
│  [Tab: Quick Demo] [Tab: Custom Voice] │
│                                     │
│  ┌─ Voice Selection ───────────────┐│
│  │ ○ Demo Voice 1 (Male)           ││
│  │ ○ Demo Voice 2 (Female)         ││
│  │ ● Custom Voice (upload/record)  ││
│  │                                  ││
│  │ [Upload Audio] [🎤 Record]      ││
│  └──────────────────────────────────┘│
│                                     │
│  ┌─ Text Input ────────────────────┐│
│  │ Zadejte text česky...           ││
│  │                                  ││
│  │ (500/500 characters)            ││
│  └──────────────────────────────────┘│
│                                     │
│  [🔊 Generate Speech]               │
│                                     │
│  ┌─ Output ────────────────────────┐│
│  │ [▶️ Play] [⬇️ Download]         ││
│  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   ││
│  └──────────────────────────────────┘│
│                                     │
│  Status: Ready | Model: XTTS-v2    │
└─────────────────────────────────────┘
2.3 Technické features
Model Management

Automatické stažení XTTS-v2 při prvním spuštění
Progress bar při stahování modelu
Cache models lokálně (žádné opakované stahování)

Audio Processing

Automatická konverze formátů
Noise reduction (optional)
Normalizace hlasitosti
Validace audio kvality

Performance

Inference na GPU (pokud dostupné)
Fallback na CPU
Optimalizace pro rychlost
Progress indicator při generování


3. Technický stack
3.1 Backend
Framework: Flask nebo FastAPI
python# Preference: FastAPI pro async support
fastapi==0.109.0
uvicorn[standard]==0.27.0
TTS Engine:
pythonTTS==0.22.0  # Coqui TTS with XTTS-v2
torch==2.1.0
torchaudio==2.1.0
Audio Processing:
pythonsoundfile==0.12.1
librosa==0.10.1
pydub==0.25.1
numpy==1.24.0
scipy==1.11.0
Utilities:
pythonpython-multipart==0.0.6  # File upload
aiofiles==23.2.1  # Async file handling
3.2 Frontend
Framework: Vanilla JavaScript nebo React (jednodušší)
Audio:
javascript// Web APIs
- MediaRecorder API (nahrávání z mikrofonu)
- Web Audio API (přehrávání)
- FileReader API (upload)
UI Components:

Tailwind CSS (styling)
Nebo Bootstrap 5
Font Awesome (ikony)

Optional:
- Wavesurfer.js (audio waveform visualizace)

4. Architektura
4.1 Struktur projektu
xtts-v2-demo/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── tts_engine.py        # XTTS-v2 wrapper
│   ├── audio_processor.py   # Audio utils
│   └── config.py            # Configuration
├── frontend/
│   ├── index.html
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   ├── app.js
│   │   ├── audio-recorder.js
│   │   └── api-client.js
│   └── assets/
│       └── demo-voices/     # Předpřipravené vzorky
├── models/                  # Cache pro XTTS-v2
├── uploads/                 # Temporary uploads
├── outputs/                 # Generated audio
├── requirements.txt
├── README.md
└── run.sh / run.bat
4.2 API Endpoints
POST /api/tts/generate
- Body: { text: string, voice_file?: File, use_demo_voice?: string }
- Response: { audio_url: string, duration: float }

POST /api/voice/upload
- Body: FormData with audio file
- Response: { voice_id: string, processed: true }

POST /api/voice/record
- Body: { audio_blob: base64 }
- Response: { voice_id: string }

GET /api/voices/demo
- Response: { voices: [{ id, name, gender, preview_url }] }

GET /api/models/status
- Response: { loaded: bool, downloading: bool, progress: int }

GET /api/audio/{filename}
- Response: Audio file stream
4.3 Data Flow
User Input (Text + Voice)
    ↓
Frontend (validation)
    ↓
API Request
    ↓
Backend (FastAPI)
    ↓
Audio Processor (format conversion)
    ↓
XTTS-v2 Engine (inference)
    ↓
Output Audio File
    ↓
Return URL to Frontend
    ↓
Play/Download in Browser

5. Implementační kroky
Fáze 1: Basic Setup (2-3 dny)

 Setup Python environment
 Install XTTS-v2 + dependencies
 Test basic TTS generation (CLI)
 Verify Czech language support
 Create basic Flask/FastAPI skeleton

Fáze 2: Backend API (3-4 dny)

 Implement /api/tts/generate endpoint
 Voice upload handling
 Audio format conversion
 Model loading & caching
 Error handling
 Logging

Fáze 3: Frontend UI (3-4 dny)

 HTML structure
 CSS styling (responsive)
 Text input + validation
 Voice upload UI
 Microphone recording
 Audio playback controls
 Download functionality

Fáze 4: Integration (2 dny)

 Connect frontend to backend API
 Handle async requests
 Loading states & progress
 Error messages
 Success notifications

Fáze 5: Demo Voices (1 den)

 Připravit 3-5 demo audio vzorků
 Czech male voice
 Czech female voice
 Optional: child voice
 Integrate do UI

Fáze 6: Polish & Testing (2-3 dny)

 Performance optimization
 GPU/CPU detection
 Memory management
 Cross-browser testing
 UI/UX improvements
 Documentation

Fáze 7: Deployment Package (1 den)

 Create run scripts (Windows/Linux/Mac)
 README with setup instructions
 Requirements freeze
 Docker image (optional)
 Release v1.0


6. Kód snippets
6.1 Backend (FastAPI)
python# main.py
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from tts_engine import XTTSEngine

app = FastAPI(title="XTTS-v2 Demo")
tts_engine = XTTSEngine()

# Serve frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.on_event("startup")
async def startup_event():
    """Load XTTS-v2 model on startup"""
    await tts_engine.load_model()

@app.post("/api/tts/generate")
async def generate_speech(
    text: str,
    voice_file: UploadFile = File(None),
    demo_voice: str = None
):
    """Generate speech from text"""
    try:
        # Process voice
        if voice_file:
            voice_path = await save_upload(voice_file)
        elif demo_voice:
            voice_path = f"assets/demo-voices/{demo_voice}.wav"
        else:
            return {"error": "No voice provided"}

        # Generate audio
        output_path = await tts_engine.generate(
            text=text,
            speaker_wav=voice_path,
            language="cs"
        )

        return {"audio_url": f"/api/audio/{output_path}"}

    except Exception as e:
        return {"error": str(e)}

@app.get("/api/audio/{filename}")
async def get_audio(filename: str):
    """Serve generated audio"""
    return FileResponse(f"outputs/{filename}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
python# tts_engine.py
from TTS.api import TTS
import torch

class XTTSEngine:
    def __init__(self):
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    async def load_model(self):
        """Load XTTS-v2 model"""
        print(f"Loading XTTS-v2 on {self.device}...")
        self.model = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
        self.model.to(self.device)
        print("Model loaded successfully!")

    async def generate(self, text: str, speaker_wav: str, language: str = "cs"):
        """Generate speech"""
        if not self.model:
            raise Exception("Model not loaded")

        output_path = f"outputs/{uuid.uuid4()}.wav"

        self.model.tts_to_file(
            text=text,
            speaker_wav=speaker_wav,
            language=language,
            file_path=output_path
        )

        return output_path
6.2 Frontend (JavaScript)
javascript// app.js
class TTSApp {
    constructor() {
        this.apiUrl = 'http://localhost:8000';
        this.currentVoice = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadDemoVoices();
    }

    setupEventListeners() {
        document.getElementById('generateBtn')
            .addEventListener('click', () => this.generateSpeech());

        document.getElementById('uploadVoice')
            .addEventListener('change', (e) => this.handleVoiceUpload(e));

        document.getElementById('recordBtn')
            .addEventListener('click', () => this.startRecording());
    }

    async generateSpeech() {
        const text = document.getElementById('textInput').value;

        if (!text) {
            alert('Zadejte text!');
            return;
        }

        const formData = new FormData();
        formData.append('text', text);

        if (this.currentVoice) {
            formData.append('voice_file', this.currentVoice);
        } else {
            formData.append('demo_voice', 'demo1');
        }

        try {
            this.showLoading(true);

            const response = await fetch(`${this.apiUrl}/api/tts/generate`, {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.audio_url) {
                this.playAudio(data.audio_url);
            } else {
                alert('Error: ' + data.error);
            }
        } catch (error) {
            alert('Error generating speech: ' + error);
        } finally {
            this.showLoading(false);
        }
    }

    playAudio(url) {
        const audio = new Audio(this.apiUrl + url);
        const player = document.getElementById('audioPlayer');
        player.src = audio.src;
        player.style.display = 'block';
    }

    handleVoiceUpload(event) {
        const file = event.target.files[0];
        if (file) {
            this.currentVoice = file;
            document.getElementById('voiceStatus').textContent =
                `Voice loaded: ${file.name}`;
        }
    }

    showLoading(show) {
        document.getElementById('loadingSpinner').style.display =
            show ? 'block' : 'none';
        document.getElementById('generateBtn').disabled = show;
    }
}

// Initialize app
const app = new TTSApp();
html<!-- index.html -->
<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>XTTS-v2 Czech TTS Demo</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <div class="container">
        <h1>🎤 XTTS-v2 Czech TTS Demo</h1>

        <div class="voice-section">
            <h2>Výběr hlasu</h2>
            <div class="voice-options">
                <label>
                    <input type="radio" name="voice" value="demo1" checked>
                    Demo Muž
                </label>
                <label>
                    <input type="radio" name="voice" value="demo2">
                    Demo Žena
                </label>
                <label>
                    <input type="radio" name="voice" value="custom">
                    Vlastní hlas
                </label>
            </div>

            <div id="customVoiceUpload" style="display: none;">
                <input type="file" id="uploadVoice" accept="audio/*">
                <button id="recordBtn">🎤 Nahrát z mikrofonu</button>
                <p id="voiceStatus"></p>
            </div>
        </div>

        <div class="text-section">
            <h2>Text k syntéze</h2>
            <textarea
                id="textInput"
                placeholder="Zadejte český text..."
                maxlength="500"
                rows="5"
            ></textarea>
            <span class="char-count">0/500</span>
        </div>

        <button id="generateBtn" class="btn-primary">
            🔊 Generovat řeč
        </button>

        <div id="loadingSpinner" style="display: none;">
            <p>Generuji audio...</p>
        </div>

        <div class="output-section">
            <h2>Výstup</h2>
            <audio id="audioPlayer" controls style="display: none;"></audio>
        </div>
    </div>

    <script src="js/app.js"></script>
</body>
</html>

7. Požadavky na hardware
Minimální

CPU: 4 cores (Intel i5 nebo ekvivalent)
RAM: 8 GB
Storage: 10 GB (pro model + cache)
OS: Windows 10/11, Ubuntu 20.04+, macOS 11+

Doporučené

CPU: 8+ cores
RAM: 16 GB
GPU: NVIDIA s 4+ GB VRAM (CUDA support)
Storage: 20 GB SSD

Performance očekávání

CPU only: 5-15 sekund na generování (pro 1-2 věty)
GPU (4GB): 1-3 sekundy na generování
GPU (8GB+): < 1 sekunda


8. Installation & Setup
8.1 Instalační script (run.sh)
bash#!/bin/bash

echo "🎤 XTTS-v2 Demo Setup"
echo "===================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.9+"
    exit 1
fi

# Create venv
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create directories
mkdir -p models uploads outputs frontend/assets/demo-voices

# Download demo voices (optional)
echo "Setup complete!"
echo ""
echo "To start the app:"
echo "  source venv/bin/activate"
echo "  python backend/main.py"
echo ""
echo "Then open: http://localhost:8000"
8.2 Windows batch (run.bat)
batch@echo off
echo XTTS-v2 Demo Setup
echo ==================

python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found! Please install Python 3.9+
    pause
    exit /b 1
)

echo Creating virtual environment...
python -m venv venv
call venv\Scripts\activate.bat

echo Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

mkdir models uploads outputs

echo Setup complete!
echo.
echo To start: python backend\main.py
echo Then open: http://localhost:8000
pause

9. Testing checklist
Funkční testy

 Generování TTS s demo hlasem
 Upload vlastního audio
 Nahrávání z mikrofonu
 Přehrávání generovaného audio
 Download audio souboru
 Validace textu (prázdný, příliš dlouhý)
 Validace audio formátů

Performance testy

 Inference time CPU
 Inference time GPU
 Memory usage
 Concurrent requests handling
 Large text handling

UX testy

 Responsive design (mobile/desktop)
 Loading states
 Error messages
 Browser compatibility (Chrome, Firefox, Safari, Edge)


10. Known Issues & Workarounds
XTTS-v2 specifické problémy
Issue 1: První generování je pomalé

Workaround: Warmup při startu aplikace

pythonawait tts_engine.generate(
    text="Zahřívací text",
    speaker_wav="demo.wav",
    language="cs"
)
Issue 2: Akcentové znaky

Workaround: Explicitní UTF-8 encoding

pythontext = text.encode('utf-8').decode('utf-8')
Issue 3: Audio format compatibility

Workaround: Convert to 22050 Hz mono

pythonimport soundfile as sf
import librosa

audio, sr = librosa.load(input_path, sr=22050, mono=True)
sf.write(output_path, audio, 22050)

11. Budoucí rozšíření
v2.0 Features

 Batch processing (multiple texts)
 Voice mixing (interpolace mezi hlasy)
 Emotion control
 Speed/pitch adjustment
 Fine-tuning interface
 Voice library management
 Export do různých formátů (MP3, OGG, FLAC)

v3.0 Features

 Real-time streaming TTS
 Multi-speaker support
 SSML support pro pokročilou kontrolu
 API pro externí aplikace
 Docker container
 Cloud deployment option


12. Documentation Structure
/docs
├── README.md              # Hlavní dokumentace
├── INSTALL.md             # Instalační guide
├── API.md                 # API reference
├── TROUBLESHOOTING.md     # Řešení problémů
├── DEMO_VOICES.md         # Info o demo hlasech
└── DEVELOPMENT.md         # Dev guide

13. Licence & Credits

XTTS-v2: Coqui Public Model License 1.0.0 (non-commercial use)
Demo app: MIT License (open source)
Dependencies: Viz requirements.txt


14. Timeline & Milestones
Week 1: Backend + Basic TTS

Setup environment
XTTS-v2 integration
Basic API

Week 2: Frontend + Integration

UI implementation
API connection
Testing

Week 3: Polish + Release

Bug fixes
Documentation
Package for distribution

Total estimated time: 15-20 dní (1 developer)

15. Success Metrics

✅ App runs offline without errors
✅ Czech TTS quality comparable to online demos
✅ Voice cloning works with 10s samples
✅ Inference time < 5s on decent hardware
✅ User can complete workflow in < 2 minutes
✅ Zero external API dependencies


Kontakt & Support
Developer: qWANAp
Project: XTTS-v2 Offline Demo
Version: 1.0
Date: 2024-12-17

Přílohy
A. requirements.txt
txt# Core TTS
TTS==0.22.0
torch==2.1.0
torchaudio==2.1.0

# Web framework
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6
aiofiles==23.2.1

# Audio processing
soundfile==0.12.1
librosa==0.10.1
pydub==0.25.1
numpy==1.24.0
scipy==1.11.0

# Utilities
python-dotenv==1.0.0
B. Ukázkové texty pro testování
Krátký text:
"Dobrý den, toto je test českého hlasu."

Střední text:
"Umělá inteligence dokáže generovat velmi přirozený hlas v češtině. Technologie XTTS-v2 používá pokročilé neuronové sítě."

Dlouhý text:
"V dnešní době je možné vytvářet realistické hlasové nahrávky pomocí strojového učení. Systém XTTS-v2 podporuje mnoho jazyků včetně češtiny. Kvalita syntézy je velmi vysoká a připomína přirozený lidský hlas. Aplikace najde využití v mnoha odvětvích, od asistentů až po audioknihy."
C. Demo voices preparation
Pro demo hlasy potřebuješ:

Nahrát 10-30 sekund čistého audio
Export jako WAV, 22050 Hz, mono
Očistit od šumu
Uložit do frontend/assets/demo-voices/

Názvy: demo1.wav, demo2.wav, demo3.wav