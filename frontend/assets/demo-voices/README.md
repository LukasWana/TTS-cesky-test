# Demo Voice Samples pro XTTS-v2

Tato složka obsahuje demo audio vzorky pro voice cloning v XTTS-v2.

## 📋 Požadavky na audio vzorky

### ✅ Délka vzorku
- **Minimum:** 6 sekund (funkční, ale méně přesné)
- **Optimum:** 10-15 sekund
- **Nejlepší kvalita:** 20-30 sekund

### ✅ Obsah vzorku
- **Přirozený mluvený projev** (ne čtení)
- **Různorodá intonace** (otázky, výroky, emoce)
- **Celé věty** (ne jednotlivá slova)
- **Čistá výslovnost** bez překážek

### ✅ Kvalita nahrávky
- **Studiová kvalita** nejlepší
- **Minimálně dobrý mikrofon**
- **Tichá místnost** bez echo
- **Bez pozadí** (minimální background noise)

## 🎯 Formát souborů

Všechny demo hlasy musí být:
- **Formát:** WAV
- **Sample rate:** 22050 Hz
- **Kanály:** Mono (1 kanál)
- **Bitrate:** 16-bit nebo vyšší

## 🛠️ Příprava demo hlasů

### Metoda 1: Použití utility scriptu (doporučeno)

```bash
# Základní konverze
python scripts/prepare_demo_voice.py input.mp3 demo-voices/male_cz.wav

# Ořez na 10 sekund od 5. sekundy
python scripts/prepare_demo_voice.py input.mp3 demo-voices/male_cz.wav --trim 5 10

# S pokročilým zpracováním (noise reduction + high-pass filter)
python scripts/prepare_demo_voice.py input.mp3 demo-voices/male_cz.wav --noise-reduction --highpass

# Automaticky do demo-voices složky
python scripts/prepare_demo_voice.py input.mp3 --demo-dir
```

### Metoda 2: FFmpeg konverze

```bash
# Z MP3 na WAV, 22050 Hz, mono
ffmpeg -i input.mp3 -ar 22050 -ac 1 output.wav

# Z jakéhokoliv formátu + normalizace
ffmpeg -i input.mp4 -ar 22050 -ac 1 -af "loudnorm" output.wav

# Ořez na 10 sekund od 5. sekundy
ffmpeg -i input.wav -ss 5 -t 10 -ar 22050 -ac 1 output.wav
```

### Metoda 3: Python script (librosa)

```python
import librosa
import soundfile as sf

def prepare_voice_sample(input_path, output_path):
    # Load audio
    audio, sr = librosa.load(input_path, sr=22050, mono=True)

    # Normalize audio
    audio = audio / max(abs(audio))

    # Save
    sf.write(output_path, audio, 22050)
    print(f"✅ Připraveno: {output_path}")

# Použití
prepare_voice_sample("raw_audio.mp3", "voice_sample.wav")
```

## 🧪 Testování kvality vzorku

Po přípravě vzorku ho otestujte:

```bash
python scripts/test_voice_quality.py demo-voices/male_cz.wav
```

Script:
1. Načte XTTS-v2 model
2. Vygeneruje testovací řeč s vaším vzorkem
3. Uloží výstup do `outputs/` složky
4. Zobrazí informace o kvalitě

**Co kontrolovat:**
- ✅ Přirozenost hlasu
- ✅ Shoda s originálním hlasem
- ✅ Kvalita výslovnosti
- ✅ Absence artefaktů

## 📝 Ukázkový text pro nahrávku

Pro nejlepší výsledky použijte tento text při nahrávání:

```
"Umělá inteligence dokáže dnes generovat velmi přirozený hlas
v češtině. Tato technologie využívá pokročilé neuronové sítě
a strojové učení. Kvalita syntézy je překvapivě vysoká
a neustále se zlepšuje."
```

**Tip:** Nahrajte text přirozeně, jako byste mluvili s přáteli, ne jako byste četli z papíru.

## 🎨 Post-processing tipy

### Noise Reduction (Audacity)
1. Otevřete audio v Audacity
2. Vyberte tichou část (jen šum)
3. Effect → Noise Reduction → Get Noise Profile
4. Vyberte celý track
5. Effect → Noise Reduction → OK

### Normalizace hlasitosti
- Automaticky provedeno v `prepare_demo_voice.py`
- Nebo v Audacity: Effect → Normalize

### High-pass Filter
- Odfiltruje hluboké frekvence pod 80 Hz
- Automaticky v `prepare_demo_voice.py` s `--highpass`
- Nebo v Audacity: Effect → High-pass Filter (80 Hz)

## 📁 Struktura souborů

Doporučené názvy souborů:
```
demo-voices/
├── male_cz.wav           # Mužský hlas
├── female_cz.wav         # Ženský hlas
├── young_cz.wav          # Mladší hlas
└── README.md              # Tento soubor
```

## ⚠️ Časté chyby

1. **Příliš krátký vzorek** (< 6s)
   - ❌ Model nemá dostatek dat pro klonování
   - ✅ Použijte alespoň 10 sekund

2. **Špatná kvalita nahrávky**
   - ❌ Echo, šum, špatný mikrofon
   - ✅ Použijte tichou místnost a dobrý mikrofon

3. **Nepřirozený projev**
   - ❌ Čtení z papíru, monotónní
   - ✅ Přirozená konverzace, různorodá intonace

4. **Špatný formát**
   - ❌ Nesprávná sample rate, stereo
   - ✅ 22050 Hz, mono, WAV

## 🔗 Užitečné odkazy

- [XTTS-v2 Dokumentace](https://github.com/coqui-ai/TTS)
- [Hugging Face XTTS-v2](https://huggingface.co/coqui/XTTS-v2)
- [FFmpeg Dokumentace](https://ffmpeg.org/documentation.html)
- [Librosa Dokumentace](https://librosa.org/doc/latest/index.html)




