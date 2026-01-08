# Applio Integration - Implementation Complete

## Summary

Applio voice cloning has been successfully integrated into the 2025-Voice-Assistant project.

## What Was Implemented

### Backend Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/applio/start-applio.bat` | Created | Spouštěcí skript pro Applio |
| `backend/applio/gradio_client.py` | Created | Gradio Client wrapper |
| `backend/api/routers/applio.py` | Updated | API endpoints for TTS |
| `start_all.bat` | Updated | Auto-start Applio in separate window |
| `requirements.txt` | Updated | Added `gradio>=4.0.0` |

### Frontend Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/services/applio.js` | Created | Frontend API service |
| `frontend/src/components/ApplioPanel.jsx` | Created | Applio UI component |
| `frontend/src/components/ApplioPanel.css` | Created | Component styles |
| `frontend/src/App.jsx` | Updated | Added Applio sub-tab under "slovenské slovo" |
| `frontend/src/App.css` | Updated | Sub-tab styling |

## Features

### ApplioPanel Component

- **Voice Grid** - Displays voices from `assets/Aplio-voices/`
- **EdgeTTS Voice Selection** - Choose base TTS voice
- **Settings Sliders**:
  - Speed (-100% to +100%)
  - Pitch (-24 to +24)
  - Voice Similarity/Index Rate (0 to 1)
  - Autotune toggle
  - Clean audio toggle
- **Text Input** - For TTS synthesis
- **Audio Output** - Play and download generated audio

### Integration Points

- Sub-tab under "slovenské slovo" (next to F5-TTS)
- Orange color theme for differentiation
- Shared text state with other components
- Error handling when Applio is not running

## Usage

### Starting the Application

```bash
# Option 1: Using start_all.bat (recommended)
start_all.bat

# This will start:
# - Backend on port 8000
# - Frontend on port 3000
# - Applio on port 6969 (separate window)
```

### Using Applio in UI

1. Open the application at http://localhost:3000
2. Navigate to "slovenské slovo" tab
3. Switch to "Applio" sub-tab
4. Select a voice from the grid
5. Choose EdgeTTS base voice
6. Adjust settings (speed, pitch, etc.)
7. Enter text and click "Generovat"

### Manual Applio Start (if not using start_all.bat)

```bash
cd backend/applio
start-applio.bat
```

Applio will open at http://localhost:6969

## Directory Structure

```
2025-voice-assistent/
├── backend/
│   ├── applio/
│   │   ├── start-applio.bat      # NEW: Applio startup script
│   │   ├── gradio_client.py      # NEW: Gradio client wrapper
│   │   ├── config.py
│   │   ├── rvc/                  # Applio RVC models
│   │   └── models/               # RVC model storage
│   ├── api/
│   │   └── routers/
│   │       └── applio.py         # UPDATED: API endpoints
│   └── ...
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   └── ApplioPanel.jsx   # NEW: UI component
│   │   │   └── ApplioPanel.css   # NEW: Component styles
│   │   └── services/
│   │       └── applio.js         # NEW: API service
│   └── ...
├── assets/
│   └── Applio-voices/            # Your voice models
│       └── [VoiceName]/
│           ├── [Voice].pth
│           └── added_IVF..._[Voice].index
└── start_all.bat                  # UPDATED: Auto-starts Applio
```

## Requirements

- Python 3.9-3.11
- gradio>=4.0.0
- Applio running on port 6969

## Troubleshooting

### Applio not available
```
Error: "Applio neni dostupny. Spustte Applio na portu 6969."
Solution: Run backend/applio/start-applio.bat
```

### No voices found
```
Check: assets/Aplio-voices/ directory exists
Verify: Voice folders contain .pth files
```

### Gradio not installed
```bash
pip install gradio>=4.0.0
```

## Notes

- Applio runs in a separate window for better resource management
- VRAM usage: ~2-4GB when Applio is running
- Applio can be skipped if not needed (just don't start it)
- The integration uses Gradio Client for communication

## Files Modified/Created

```
CREATED:
  backend/applio/start-applio.bat
  backend/applio/gradio_client.py
  frontend/src/services/applio.js
  frontend/src/components/ApplioPanel.jsx
  frontend/src/components/ApplioPanel.css
  test_applio_integration.bat

UPDATED:
  backend/api/routers/applio.py
  start_all.bat
  requirements.txt
  frontend/src/App.jsx
  frontend/src/App.css
```

## Test Date

2026-01-07
