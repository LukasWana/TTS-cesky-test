# Technické zadání: Real-time Voice Conversation & Voice Cloning (CZ)

## Přehled projektu
Systém pro real-time hlasové konverzace v češtině s možností voice cloningu a tuningu hlasů.

---

## 1. Funkční požadavky

### 1.1 Real-time konverzace
- **STT (Speech-to-Text)**: Rozpoznávání českého mluvení v reálném čase
- **LLM zpracování**: Generování odpovědí pomocí AI modelu
- **TTS (Text-to-Speech)**: Syntéza českého hlasu s nízkou latencí
- **Latence**: Celková odezva < 2 sekundy (ideálně < 1s)

### 1.2 Voice Cloning
- **Instant cloning**: Z krátkého audio vzorku (6-30 sekund)
- **Kvalita**: Přirozený, čitelný český hlas
- **Formáty**: Podpora WAV, MP3 jako vstup

### 1.3 Voice Tuning
- **Custom training**: Trénování vlastních hlasových modelů
- **Dataset**: 10-30 minut čistého audio materiálu
- **Konzistence**: Stabilní výstup pro dlouhodobé použití

---

## 2. Technický stack

### 2.1 Varianta A: Open-source (Full Control)

#### STT
- **Model**: Faster-Whisper (distil-large-v3)
- **Alternativa**: Whisper large-v3
- **Jazyk**: Čeština (cs)

#### LLM
- **Primary**: Claude API (Anthropic)
- **Fallback**: GPT-4 (OpenAI)
- **Local option**: Llama 3 (volitelné)

#### TTS + Voice Cloning
- **Primary**: XTTS-v2 (Coqui TTS)
  - Multilingual support
  - Voice cloning z krátkých vzorků
  - Lokální provoz

#### Voice Tuning
- **Model**: RVC (Retrieval-based Voice Conversion)
- **Repo**: RVC-Project/Retrieval-based-Voice-Conversion-WebUI
- **Training**: Custom datasets

### 2.2 Varianta B: Hybrid (Rychlý start)

#### STT
- **Service**: Deepgram nebo Azure Speech
- **Fallback**: Faster-Whisper lokálně

#### TTS + Cloning
- **Service**: ElevenLabs (instant cloning)
- **Fallback**: XTTS-v2 lokálně

---

## 3. Infrastruktura

### 3.1 Hardware požadavky

**Minimální konfigurace:**
- CPU: 8 cores+
- RAM: 16 GB
- GPU: 4 GB VRAM (pro XTTS-v2)
- Storage: 20 GB

**Doporučená konfigurace:**
- CPU: 16 cores+
- RAM: 32 GB
- GPU: 8+ GB VRAM (NVIDIA)
- Storage: 50 GB SSD

### 3.2 Software
- **OS**: Ubuntu 22.04 LTS / Windows 11
- **Python**: 3.10+
- **CUDA**: 11.8+ (pro GPU inference)
- **Node.js**: 18+ (pro web interface)

---

## 4. Architektura systému

```
[Mikrofon]
    ↓
[STT: Faster-Whisper]
    ↓
[Text Buffer]
    ↓
[LLM: Claude/GPT-4]
    ↓
[Response Text]
    ↓
[TTS: XTTS-v2 + Voice Clone]
    ↓
[Audio Stream]
    ↓
[Reproduktor]
```

### 4.1 Komponenty

#### Voice Input Module
- Audio capture (16kHz, mono)
- Noise reduction
- VAD (Voice Activity Detection)

#### STT Module
- Faster-Whisper inference
- Real-time streaming
- Czech language model

#### Conversation Module
- LLM API integration
- Context management
- Response streaming

#### TTS Module
- XTTS-v2 inference
- Voice cloning engine
- Audio output buffer

#### Voice Training Module (RVC)
- Dataset preprocessing
- Model training pipeline
- Inference engine

---

## 5. Implementační fáze

### Fáze 1: Prototyp (2-3 týdny)
- [ ] Setup Faster-Whisper STT
- [ ] Integrace Claude API
- [ ] XTTS-v2 basic TTS
- [ ] Jednoduchý voice cloning z reference audio
- [ ] Command-line interface

### Fáze 2: Voice Cloning (2 týdny)
- [ ] XTTS-v2 optimalizace
- [ ] Voice library management
- [ ] Quality testing s českými vzorky
- [ ] Web interface pro upload audio

### Fáze 3: Voice Tuning (3-4 týdny)
- [ ] RVC setup a training pipeline
- [ ] Dataset preparation tools
- [ ] Model training automation
- [ ] A/B testing trained voices

### Fáze 4: Optimalizace (2 týdny)
- [ ] Latence reduction
- [ ] GPU optimization
- [ ] Caching strategies
- [ ] Load testing

### Fáze 5: Production (1-2 týdny)
- [ ] Deployment setup
- [ ] Monitoring
- [ ] Documentation
- [ ] User testing

---

## 6. Dependencies

### Python packages
```txt
TTS==0.22.0
faster-whisper==0.10.0
torch==2.1.0
anthropic==0.18.0
openai==1.12.0
sounddevice==0.4.6
numpy==1.24.0
scipy==1.11.0
```

### RVC specific
```txt
fairseq==0.12.2
librosa==0.10.1
pyworld==0.3.4
praat-parselmouth==0.4.3
```

---

## 7. API klíče (potřebné)

- [ ] Anthropic API key (Claude)
- [ ] OpenAI API key (fallback)
- [ ] ElevenLabs API key (optional, hybrid)
- [ ] Deepgram API key (optional, hybrid)

---

## 8. Testovací kritéria

### Performance
- STT latence: < 500ms
- LLM odpověď: < 1000ms
- TTS syntéza: < 500ms
- **Celková latence: < 2s**

### Kvalita
- STT WER (Word Error Rate): < 10% pro češtinu
- TTS naturalness: MOS score > 4.0
- Voice cloning similarity: > 80%

### Stabilita
- Uptime: > 99%
- Error recovery: automatické
- Memory leaks: žádné

---

## 9. Dokumentace

### Struktura
```
/docs
  ├── setup.md          # Instalační guide
  ├── api.md            # API documentation
  ├── voice-cloning.md  # Voice cloning guide
  ├── rvc-training.md   # RVC training tutorial
  └── troubleshooting.md
```

---

## 10. Bezpečnost & Privacy

- [ ] Audio data encryption at rest
- [ ] API keys v environment variables
- [ ] Voice samples anonymizace (optional)
- [ ] GDPR compliance pro EU uživatele
- [ ] Local-first option (bez cloud API)

---

## 11. Monitoring & Logging

- [ ] Audio quality metrics
- [ ] Latency tracking
- [ ] Error logging
- [ ] Usage statistics
- [ ] Model performance metrics

---

## 12. Budget estimate

### One-time costs
- Development: 40-60 hodin
- Testing: 10-15 hodin

### Recurring costs (monthly)
- **Varianta A (Open-source)**:
  - Cloud GPU: $50-150/měsíc (optional)
  - LLM API: $20-100/měsíc

- **Varianta B (Hybrid)**:
  - ElevenLabs: $30-100/měsíc
  - Deepgram: $20-80/měsíc
  - LLM API: $20-100/měsíc

---

## 13. Rizika & Mitigace

| Riziko | Pravděpodobnost | Impact | Mitigace |
|--------|-----------------|--------|----------|
| Vysoká latence | Střední | Vysoký | GPU inference, optimalizace |
| Nízká kvalita CZ TTS | Nízká | Střední | Testování více modelů |
| API rate limits | Střední | Střední | Lokální fallback modely |
| Dataset quality (RVC) | Vysoká | Vysoký | Quality guidelines, preprocessing |

---

## 14. Success Metrics

- ✅ Fungující prototyp do 3 týdnů
- ✅ Latence < 2s v 95% případů
- ✅ Pozitivní user feedback (> 4/5)
- ✅ Stabilní voice cloning v češtině
- ✅ Custom voice training funkční

---

## Kontakt & Zodpovědnost

**Projekt manager**: qWANAp
**Tech lead**: TBD
**Timeline**: 10-14 týdnů (all phases)
**Start date**: TBD

---

## Changelog

- v1.0 (2024-12-17): Initial technical specification
