# Podpora více jazyků a více mluvčích

## Přehled

Systém nyní podporuje generování řeči s více jazyky a více mluvčími v jednom textu. Můžete označit různé části textu různými jazyky a mluvčími pomocí jednoduché syntaxe.

## Syntaxe

### Základní syntaxe

```
[lang:speaker]text[/lang]
```

nebo bez specifikace mluvčího:

```
[lang]text[/lang]
```

**Důležité:**
- `speaker` může být **název demo hlasu** (např. `buchty01`, `Pohadka_muz`, `Klepl-Bolzakov-rusky`) - systém ho automaticky najde
- Názvy jsou **case-insensitive** (můžete psát `pohadka_muz` i `Pohadka_muz`)
- Podporuje názvy s podtržítky, pomlčkami a velkými písmeny
- Nebo může být cesta k WAV souboru
- Pokud není zadán `speaker`, použije se výchozí hlas
- **Výchozí jazyk je čeština (cs)**

### Příklady

#### 1. Použití skutečných názvů demo hlasů
```
[cs:buchty01]Ahoj, jak se máš?[/cs] [en:Pohadka_muz]Hello, how are you?[/en]
```
Systém automaticky najde demo hlasy `buchty01.wav` a `Pohadka_muz.wav` v adresáři `frontend/assets/demo-voices/`.

**Dostupné demo hlasy:**
- `buchty01`
- `Pohadka_muz`
- `Klepl-Bolzakov-rusky`
- `ai-speakato-Antonin`
- `ai-speakato-Erika`
- `ai-speakato-Veronika`
- `ai-speakato-Vlasta`
- `Bohumil-Klepl-CR-Radiožurnál`
- `Brodksy`
- `Klepl-drama`
- `werich-hlas`
- A další...

#### 2. Dialog mezi dvěma mluvčími
```
[cs:buchty01]Dobrý den, vítám vás.[/cs]
[cs:Pohadka_muz]Děkuji, těší mě.[/cs]
[cs:buchty01]Můžeme začít?[/cs]
```

#### 3. Mix jazyků s jedním mluvčím
```
[cs:ai-speakato-Antonin]Slovo "hello" znamená[/cs] [en:ai-speakato-Antonin]hello[/en] [cs:ai-speakato-Antonin]v češtině.[/cs]
```

#### 4. Bez uzavíracího tagu (segment končí na další tag)
```
[cs:buchty01]První věta [en:Pohadka_muz]Second sentence [cs:buchty01]třetí věta
```

#### 5. Kombinace s pauzami
```
[cs:buchty01]Ahoj[/cs] [pause:200] [en:Pohadka_muz]Hello[/en] [pause:500] [cs:buchty01]jak se máš?[/cs]
```
Systém automaticky detekuje pauzy a vloží je mezi segmenty.

#### 6. Case-insensitive názvy
```
[cs:pohadka_muz]Funguje i s malými písmeny[/cs]
[cs:Pohadka_muz]I s velkými písmeny[/cs]
```
Oba příklady najdou stejný soubor `Pohadka_muz.wav`.

#### 7. Bez specifikace mluvčího (použije se výchozí hlas)
```
[cs]Ahoj[/cs] [en]Hello[/en] [cs]jak se máš?[/cs]
```

## API Endpoint

### POST `/api/tts/generate-multi`

Generuje řeč pro text s více jazyky a mluvčími.

#### Parametry

- `text` (required): Text s anotacemi `[lang:speaker]text[/lang]`
- `default_voice_file` (optional): Nahraný audio soubor jako výchozí hlas
- `default_demo_voice` (optional): Název demo hlasu jako výchozí hlas
- `default_language` (optional, default: "cs"): Výchozí jazyk pro neanotované části
- `speaker_mapping` (optional): JSON mapování `speaker_id -> voice_path` nebo `demo_voice_name`
  - Příklad: `{"voice1": "demo1", "voice2": "/path/to/voice.wav"}`
- Ostatní parametry jako v `/api/tts/generate` (speed, temperature, atd.)

#### Příklad použití

```bash
curl -X POST "http://localhost:8000/api/tts/generate-multi" \
  -F "text=[cs:voice1]Ahoj[/cs] [en:voice2]Hello[/en]" \
  -F "default_demo_voice=demo1" \
  -F "speaker_mapping={\"voice1\": \"demo1\", \"voice2\": \"demo2\"}" \
  -F "default_language=cs"
```

#### Response

```json
{
  "audio_url": "/api/audio/abc123.wav",
  "filename": "abc123.wav",
  "success": true,
  "job_id": "job-123"
}
```

## Programové použití

### Python

```python
from backend.tts_engine import get_tts_engine

engine = get_tts_engine()
await engine.load_model()

# Text s anotacemi
text = "[cs:voice1]Ahoj[/cs] [en:voice2]Hello[/en]"

# Mapování mluvčích
speaker_map = {
    "voice1": "/path/to/voice1.wav",
    "voice2": "/path/to/voice2.wav"
}

# Generuj
output_path = await engine.generate_multi_lang_speaker(
    text=text,
    default_speaker_wav="/path/to/default.wav",
    default_language="cs",
    speaker_map=speaker_map,
    speed=1.0,
    temperature=0.7
)
```

## Podporované jazyky

**Výchozí jazyk je čeština (cs)** - pokud není zadán jiný jazyk, použije se čeština.

XTTS-v2 podporuje tyto jazyky:
- `cs` - Čeština (výchozí)
- `en` - Angličtina
- `de` - Němčina
- `es` - Španělština
- `fr` - Francouzština
- `it` - Italština
- `pl` - Polština
- `pt` - Portugalština
- `ru` - Ruština
- `tr` - Turečtina
- `zh` - Čínština
- `ja` - Japonština
- A další...

## Automatická detekce jazyka (volitelné)

Pokud chcete automaticky detekovat jazyky bez anotací, můžete použít `LanguageDetector`:

```python
from backend.language_detector import get_language_detector

detector = get_language_detector()
segments = detector.detect_segments("Hello world. Ahoj světe.")

# Výsledek: [("Hello world.", "en"), ("Ahoj světe.", "cs")]
```

**Poznámka:** Pro automatickou detekci nainstalujte: `pip install langdetect`

## Omezení

1. Každý segment se generuje samostatně, takže pro dlouhé texty může generování trvat déle
2. Mezi segmenty se automaticky vkládá 50ms crossfade pro plynulý přechod
3. Speaker mapping musí být zadán předem - nelze dynamicky měnit mluvčí během generování

## Tipy

1. **Krátké segmenty**: Pro lepší kvalitu udržujte segmenty alespoň 3-5 slov
2. **Konzistentní mluvčí**: Používejte stejného mluvčího pro stejný jazyk, pokud chcete konzistentní hlas
3. **Cross-language varování**: Použití českého hlasu pro anglický text (nebo naopak) může způsobovat chrčení a artefakty. Pro nejlepší kvalitu používejte hlas v jazyce, ve kterém generujete text
4. **Testování**: Začněte s jednoduchými příklady a postupně přidávejte složitější struktury
5. **Demo hlasy**: Použijte demo hlasy pro rychlé testování (`/api/voices/demo`)

## Příklady použití

### Příklad 1: Bilingvní prezentace s demo hlasy
```
[cs:demo1]Dobrý den, dnes vám představím nový produkt.[/cs]
[en:demo1]Good morning, today I will present you a new product.[/en]
[cs:demo1]Začneme s přehledem funkcí.[/cs]
```

### Příklad 2: Rozhovor mezi dvěma mluvčími
```
[cs:demo1]Jaký je váš názor na tuto problematiku?[/cs]
[cs:demo2]Myslím, že je to velmi důležité téma.[/cs]
[cs:demo1]Můžete to rozvést?[/cs]
```

### Příklad 3: Jazyková výuka
```
[cs:demo1]Slovo "house" se čte[/cs] [en:demo1]house[/en] [cs:demo1]a znamená dům.[/cs]
```

**Poznámka:** Názvy jako `buchty01`, `Pohadka_muz`, `Klepl-Bolzakov-rusky` jsou skutečné názvy souborů (bez přípony `.wav`) v adresáři `frontend/assets/demo-voices/`. Systém je automaticky najde a použije. Vyhledávání je case-insensitive, takže můžete psát názvy s malými i velkými písmeny.

## Řešení problémů

### Segment se negeneruje
- Zkontrolujte, že syntaxe je správná: `[lang:speaker]text[/lang]`
- Ujistěte se, že mluvčí je zaregistrován v `speaker_mapping`
- Zkontrolujte, že jazyk je podporován XTTS-v2

### Špatná výslovnost / Chrčení
- **DŮLEŽITÉ**: Použití českého hlasu pro anglický text (nebo naopak) může způsobovat:
  - Chrčení a artefakty
  - Dlouhé ticho na konci
  - Špatnou výslovnost
- **Doporučení**: Používejte hlas v jazyce, ve kterém generujete text
  - Pro angličtinu použijte anglický hlas (pokud máte)
  - Pro češtinu použijte český hlas
- Systém automaticky detekuje cross-language použití a upraví parametry, ale kvalita může být stále nižší
- Pro cizí slova použijte fonetický přepis (systém to dělá automaticky pro angličtinu)
- Zkontrolujte, že je správně nastaven jazyk segmentu

### Plynulost přechodů
- Crossfade mezi segmenty je 50ms - pro delší pauzy použijte `[pause:ms]` syntaxi
- Zkontrolujte, že audio soubory mluvčích mají podobnou hlasitost

