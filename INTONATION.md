# Systém modelování intonace

Tento dokument popisuje systém pro modelování intonace vět v TTS systému.

## Přehled

Systém umožňuje kontrolu intonace (výšky hlasu) pomocí:
1. **Automatické detekce** - podle typu věty (otázka, oznamovací, atd.)
2. **Explicitních značek** - `[intonation:type]text[/intonation]`
3. **SSML kontur** - `<prosody contour="...">text</prosody>`

## Automatická detekce

Systém automaticky detekuje intonaci podle interpunkce:

- **`?`** → Stoupavá intonace (RISE) - pro otázky
- **`.`** → Klesavá intonace (FALL) - pro oznamovací věty
- **`,`** → Polokadence (HALF_FALL) - pro nedokončené věty
- **`!`** → Klesavá intonace (FALL) - pro rozkazy/výkřiky

### Příklad

```
Přijde zítra?  → automaticky stoupavá intonace
Přijde zítra.  → automaticky klesavá intonace
Když přijde,   → automaticky polokadence
```

## Explicitní značky

Můžete explicitně zadat typ intonace pomocí značek:

### Syntaxe

```
[intonation:fall]text[/intonation]     - klesavá intonace
[intonation:rise]text[/intonation]     - stoupavá intonace
[intonation:flat]text[/intonation]      - plochá intonace
[intonation:wave]text[/intonation]      - vlnitá intonace
[intonation:half_fall]text[/intonation] - polokadence
```

### Typy intonace

- **`fall`** - Klesavá intonace (pokles o ~3 semitony na konci)
  - Použití: oznamovací věty, rozkazy
  - Příklad: `[intonation:fall]Přijde zítra.[/intonation]`

- **`rise`** - Stoupavá intonace (vzestup o ~3 semitony na konci)
  - Použití: otázky zjišťovací
  - Příklad: `[intonation:rise]Přijde zítra?[/intonation]`

- **`half_fall`** - Polokadence (mírný pokles o ~1.5 semitonu)
  - Použití: nedokončené věty, souvětí
  - Příklad: `[intonation:half_fall]Když přijde,[/intonation] zavolej mi.`

- **`wave`** - Vlnitá intonace (střídání výšky)
  - Použití: zdůraznění, emocionální projev
  - Příklad: `[intonation:wave]To je opravdu zajímavé![/intonation]`

- **`flat`** - Plochá intonace (žádná změna)
  - Použití: monotónní projev
  - Příklad: `[intonation:flat]Seznam položek.[/intonation]`

## SSML kontury

Pro pokročilou kontrolu můžete použít SSML-like kontury:

### Syntaxe

```
<prosody contour="(0%,0%) (50%,+10%) (100%,-20%)">text</prosody>
```

### Formát kontury

Kontura se zadává jako seznam bodů: `(čas%, změna_pitch%)`

- **čas%** - Relativní pozice ve větě (0-100%)
- **změna_pitch** - Změna výšky v semitonech (kladné = vyšší, záporné = nižší)

### Příklady

```xml
<!-- Klesavá intonace -->
<prosody contour="(0%,0%) (50%,0%) (100%,-3%)">Přijde zítra.</prosody>

<!-- Stoupavá intonace -->
<prosody contour="(0%,0%) (50%,0%) (100%,+3%)">Přijde zítra?</prosody>

<!-- Složitá kontura -->
<prosody contour="(0%,0%) (25%,+2%) (50%,-1%) (75%,+1%) (100%,-2%)">Komplexní intonace</prosody>
```

## Kombinace s dalšími značkami

Intonační značky lze kombinovat s důrazem a dalšími prosody značkami:

```
**To je** [intonation:rise]opravdu zajímavé?[/intonation]
<emphasis level="strong">Důležité</emphasis> [intonation:fall]sdělení.[/intonation]
```

## Technické detaily

### Post-processing

Intonace se aplikuje jako post-processing na vygenerované audio pomocí:
- **librosa.effects.pitch_shift** - pro změnu výšky hlasu
- **Segmentace** - audio se rozdělí na segmenty podle intonačních značek
- **Vyhlazení** - přechody mezi segmenty jsou vyhlazeny pro přirozený zvuk

### Konfigurace

V `backend/config.py`:

```python
ENABLE_PROSODY_CONTROL = True  # Zapnout/vypnout prosody control
ENABLE_INTONATION_PROCESSING = True  # Zapnout/vypnout intonační post-processing
```

### Omezení

1. **Přesnost mapování** - Mapování text→audio není 100% přesné, používá se aproximace podle délky
2. **Výkon** - Pitch shifting může být výpočetně náročné pro dlouhé texty
3. **Kvalita** - Extrémní změny pitch (>5 semitonů) mohou způsobit artefakty

## Příklady použití

### Příklad 1: Jednoduchá otázka

```
Přijde zítra?
```

Automaticky se aplikuje stoupavá intonace.

### Příklad 2: Explicitní kontrola

```
[intonation:fall]Přijde zítra.[/intonation] [intonation:rise]Opravdu?[/intonation]
```

První část má klesavou, druhá stoupavou intonaci.

### Příklad 3: SSML kontura

```xml
<prosody contour="(0%,0%) (50%,+2%) (100%,-3%)">
  To je velmi zajímavé.
</prosody>
```

Složitá kontura s vzestupem uprostřed a poklesem na konci.

### Příklad 4: Kombinace s multi-lang

```
[cs:buchty01][intonation:fall]Dobrý den.[/intonation][/cs]
[en:Pohadka_muz][intonation:rise]How are you?[/intonation][/en]
```

Intonace funguje i s multi-lang syntaxí.

## Řešení problémů

### Intonace se neaplikuje

1. Zkontrolujte, že `ENABLE_INTONATION_PROCESSING = True` v configu
2. Zkontrolujte, že `ENABLE_PROSODY_CONTROL = True`
3. Zkontrolujte, že máte nainstalovanou knihovnu `librosa`

### Artefakty v audio

1. Snižte intenzitu změn (menší hodnoty v kontuře)
2. Použijte méně agresivní intonační profily
3. Zkontrolujte, že audio není příliš krátké (< 0.1s)

### Intonace není přirozená

1. Použijte automatickou detekci místo explicitních značek
2. Upravte intonační profily v `IntonationProcessor.INTONATION_PROFILES`
3. Experimentujte s různými hodnotami intenzity

