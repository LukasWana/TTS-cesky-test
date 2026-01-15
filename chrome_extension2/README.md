# Voice Assistant Reader v2 - Chrome Extension

Vylepšená verze rozšíření pro čtení označeného textu pomocí lokálního Voice Assistenta.

## Architektura

```
┌─────────────────────────────────────────────────────────────────┐
│  CHROME EXTENSION v2                                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ background.js                                           │   │
│  │  - splitIntoSentences() - detekce vět s podporou zkratek│   │
│  │  - splitIntoChunks() - word-boundary wrapping           │   │
│  │  - validateChunks() - kontrola integrity dat            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            ↓                                     │
│  WebSocket: ws://localhost:8000/ws/tts                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  BACKEND                                                        │
│  main_xtts_ws.py                                                │
│  - split_into_sentences() - Python ekvivalent                  │   │
│  - split_into_chunks() - Python ekvivalent                     │   │
│  - validate_chunks() - Python ekvivalent                       │
│  - Generuje audio chunky s pauzami mezi větami                 │
└─────────────────────────────────────────────────────────────────┘
```

## Novinky ve verzi 2.0

### 1. Sjednocené dělení textu
Stejná logika v Chrome extension i backendu:
- **Detekce zkratek**: např, tj, tzn, tzv, apod, č, resp, popř...
- **Sentence splitting**: správné rozdělení na věty
- **Word-boundary wrapping**: dlouhé věty se dělí na hranicích slov

### 2. Opravené Pauzy
Detekce konce věty podporuje uvozovky:
```python
# předtím: "věta." → bez pauzy
# nyní: "věta." → 250ms pauza
pause_ms = 250 if re.search(r"[.?!][\"']?\s*$", chunk) else 0
```

### 3. Validace integrity
Oba systémy kontrolují, že žádný text není vynechán nebo duplikován:
```
[WS] Validation: {'isValid': True, 'chunkCount': 12, 'totalLength': 2850, 'similarity': '95%'}
```

## Postprocessing

Veškerý postprocessing je **vypnut** pro maximální kvalitu a přirozené pauzy:

| Parametr | Hodnota | Důvod |
|----------|---------|-------|
| `enable_normalization` | False | Raw výstup z modelu |
| `enable_denoiser` | False | Žádná redukce šumu |
| `enable_compressor` | False | Žádná komprese |
| `enable_deesser` | False | Žádný de-essing |
| `enable_eq` | False | Žádný EQ |
| `enable_trim` | True | Ořez ticha na začátku/konci chunku |

### Jak fungují pauzy mezi větami

```
1. JavaScript detekuje věty a počítá pauzy (detectPause)
2. Backend generuje audio bez postprocessingu
3. Backend posílá: {chunk_index, total_chunks, audio, pause_after: 250}
4. Content.js přehrává s timing offsetem:
   source.start(nextStartTime);
   nextStartTime += buffer.duration + 0.25s;  // ← Pauza 250ms
```

### Debug logy pro pauzy

```
[Voice Assistant v2] Stream chunk 1/10 - pause: 250ms
[Voice Assistant v2] Playing chunk 1/10 with pause 250ms
[Voice Assistant v2] Stream chunk 2/10 - pause: 250ms
[Voice Assistant v2] Playing chunk 2/10 with pause 250ms
```

| Parametr | Hodnota | Popis |
|----------|---------|-------|
| minSize | 150 | Minimální délka chunku |
| maxSize | 300 | Maximální délka chunku |
| enableWordWrap | true | Dělení na hranicích slov |

## Podporované zkratky (CZ)

```javascript
const CZ_ABBREVIATIONS = new Set([
  'např', 'tj', 'tzn', 'tzv', 'apod', 'č', 'resp', 'popř',
  'event', 'max', 'min', 'například', 'takzvaný', 'čís',
  'př', 'n', 'm', 'k', 's', 'v', 'z', 'u', 'o', 'i', 'a'
]);
```

## Debug logy

### Chrome DevTools (background.js)
```
[Background v2] Original text length: 2500
[Background v2] Text processing: { sentences: 15, chunks: 12, validation: {...} }
[Background v2] Sample sentences: ['Věta 1...', 'Věta 2...', 'Věta 3...']
[Background v2] Sending 12 chunks to backend
[WS v2] Connected
[WS v2] Chunk 1/12 sent (pause: 250ms)
```

### Backend terminal
```
[WS] Client abc123: 'Text...' req=1 stream=True
[WS] Text processing: 15 sentences -> 12 chunks
[WS] Validation: {'isValid': True, 'chunkCount': 12, 'totalLength': 2850, 'similarity': '95%'}
[WS] Chunk 1/12 sent (pause: 250ms)
```

## Řešení problémů

### "Chunk failed" chyby
Zkontrolujte, že běží správný backend:
```batch
start_xtts_extension.bat
```

### Žádné pauzy mezi větami
Zkontrolujte logy - backend by měl posílat `pause_after: 250` pro věty končící na `.`, `!`, `?`

### Text se přeskakuje nebo duplikuje
Zkontrolujte validaci v logách:
```
[WS] Validation: {'isValid': True, 'similarity': '95%'}
```
Pokud `isValid: False`, něco je špatně s dělením textu.

## Instalace

1. Otevřete Chrome → `chrome://extensions`
2. Aktivujte **Režim pro vývojáře**
3. Klikněte **Načíst rozbalené**
4. Vyberte složku `chrome_extension2`

## Testování

1. Spusťte backend: `start_xtts_extension.bat`
2. V Chrome vyberte dlouhý text (několik odstavců)
3. Pravé tlačítko → **Přečti nahlas (v2)**
4. Sledujte logy pro ověření správného dělení
