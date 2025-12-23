# Přehled všech dostupných značek pro prosody control

Tento dokument obsahuje kompletní seznam všech značek, které můžete použít v textu pro kontrolu prosody (důraz, rychlost, výška hlasu, intonace, pauzy).

## 📌 Obsah

1. [Důraz (Emphasis)](#důraz-emphasis)
2. [Rychlost řeči (Rate)](#rychlost-řeči-rate)
3. [Výška hlasu (Pitch)](#výška-hlasu-pitch)
4. [Intonace](#intonace)
5. [Pauzy](#pauzy)
6. [Multi-lang a Multi-speaker](#multi-lang-a-multi-speaker)
7. [Kombinace značek](#kombinace-značek)

---

## 🎯 Důraz (Emphasis)

Zvýrazní část textu zvýšením hlasitosti, boostem středních frekvencí a případně změnou pitch.

### SSML syntaxe

```xml
<emphasis level="strong">Toto je silný důraz</emphasis>
<emphasis level="moderate">Toto je mírný důraz</emphasis>
<emphasis>Toto je výchozí důraz (mírný)</emphasis>
```

### Jednoduché značky

```
**Toto je silný důraz**     (dvě hvězdičky)
*Toto je mírný důraz*        (jedna hvězdička)
__Toto je silný důraz__      (dvě podtržítka)
_Toto je mírný důraz_        (jedno podtržítko)
```

### Úrovně důrazu

- **STRONG** (`level="strong"` nebo `**text**`):
  - Zvýšení hlasitosti: +6-12 dB
  - Boost středních frekvencí: 15-30%
  - Zvýšení pitch: +1-2 semitony
  - Dynamická komprese pro větší kontrast

- **MODERATE** (`level="moderate"` nebo `*text*`):
  - Zvýšení hlasitosti: +3-6 dB
  - Boost středních frekvencí: 8-20%

### Příklady

```
**Důležité upozornění!** Prosím, přečtěte si to.
<emphasis level="strong">Pozor!</emphasis> Toto je varování.
*Mírně důležité* sdělení pro všechny.
```

---

## ⚡ Rychlost řeči (Rate)

Mění rychlost mluvení.

### SSML syntaxe

```xml
<prosody rate="slow">Pomalá řeč</prosody>
<prosody rate="fast">Rychlá řeč</prosody>
<prosody rate="x-slow">Velmi pomalá řeč</prosody>
<prosody rate="x-fast">Velmi rychlá řeč</prosody>
```

### Úrovně rychlosti

- **SLOW** / **X_SLOW**: Zpomalení řeči (přidání mikropauz)
- **FAST** / **X_FAST**: Zrychlení řeči (odstranění mezer)

### Příklady

```
<prosody rate="slow">Pomalu a zřetelně</prosody>
<prosody rate="fast">Rychle a stručně</prosody>
<prosody rate="x-slow">Velmi pomalu pro důraz</prosody>
```

---

## 🎵 Výška hlasu (Pitch)

Mění výšku hlasu (vyšší = tenčí, nižší = hlubší).

### SSML syntaxe

```xml
<prosody pitch="high">Vysoký hlas</prosody>
<prosody pitch="low">Nízký hlas</prosody>
<prosody pitch="x-high">Velmi vysoký hlas</prosody>
<prosody pitch="x-low">Velmi nízký hlas</prosody>
```

### Úrovně výšky

- **HIGH** / **X_HIGH**: Zvýšení pitch (text se převede na velká písmena)
- **LOW** / **X_LOW**: Snížení pitch (text se převede na malá písmena)

### Příklady

```
<prosody pitch="high">Vysoký hlas pro důraz</prosody>
<prosody pitch="low">Hluboký hlas pro vážnost</prosody>
```

---

## 🎼 Intonace

Kontroluje melodii věty (klesavá, stoupavá, plochá, vlnitá).

### Automatická detekce

Systém automaticky detekuje intonaci podle interpunkce:

```
Přijde zítra?  → automaticky stoupavá (RISE)
Přijde zítra.  → automaticky klesavá (FALL)
Když přijde,   → automaticky polokadence (HALF_FALL)
Přijde zítra!  → automaticky klesavá (FALL)
```

### Explicitní značky

```
[intonation:fall]Klesavá intonace[/intonation]
[intonation:rise]Stoupavá intonace[/intonation]
[intonation:flat]Plochá intonace[/intonation]
[intonation:wave]Vlnitá intonace[/intonation]
[intonation:half_fall]Polokadence[/intonation]
```

### Typy intonace

- **fall**: Klesavá intonace (pokles o ~3 semitony)
  - Použití: oznamovací věty, rozkazy
  - Příklad: `[intonation:fall]Přijde zítra.[/intonation]`

- **rise**: Stoupavá intonace (vzestup o ~3 semitony)
  - Použití: otázky zjišťovací
  - Příklad: `[intonation:rise]Přijde zítra?[/intonation]`

- **half_fall**: Polokadence (mírný pokles o ~1.5 semitonu)
  - Použití: nedokončené věty, souvětí
  - Příklad: `[intonation:half_fall]Když přijde,[/intonation] zavolej mi.`

- **wave**: Vlnitá intonace (střídání výšky)
  - Použití: zdůraznění, emocionální projev
  - Příklad: `[intonation:wave]To je opravdu zajímavé![/intonation]`

- **flat**: Plochá intonace (žádná změna)
  - Použití: monotónní projev
  - Příklad: `[intonation:flat]Seznam položek.[/intonation]`

### SSML kontury (pokročilé)

Pro pokročilou kontrolu můžete použít SSML-like kontury:

```xml
<prosody contour="(0%,0%) (50%,0%) (100%,-3%)">Klesavá intonace</prosody>
<prosody contour="(0%,0%) (50%,0%) (100%,+3%)">Stoupavá intonace</prosody>
<prosody contour="(0%,0%) (25%,+2%) (50%,-1%) (75%,+1%) (100%,-2%)">Složitá kontura</prosody>
```

**Formát kontury:**
- `(čas%, změna_pitch%)` - čas je relativní pozice (0-100%), změna je v semitonech
- Kladné hodnoty = vyšší pitch, záporné = nižší pitch

---

## ⏸️ Pauzy

Vkládá pauzy do řeči.

### Syntaxe

```
[pause]              Střední pauza (~300ms)
[pause:500]          Vlastní pauza 500ms
[pause:200ms]        Vlastní pauza 200ms (s jednotkou)
...                  Krátká pauza (~200ms)
…                    Krátká pauza (Unicode ellipsis)
```

### Příklady

```
Dobrý den [pause] jak se máte?
Přijdu zítra [pause:500] v pět hodin.
Když přijde... zavolej mi.
```

---

## 🌍 Multi-lang a Multi-speaker

Použití více jazyků a mluvčích v jednom textu.

### Syntaxe

```
[lang:speaker]text[/lang]    S mluvčím
[lang]text[/lang]            Bez mluvčího (výchozí hlas)
```

### Podporované jazyky

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

### Demo hlasy

Dostupné demo hlasy (case-insensitive):
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

### Příklady

```
[cs:buchty01]Dobrý den v češtině.[/cs]
[en:Pohadka_muz]Hello in English.[/en]
[cs:buchty01]Jak se máte?[/cs]

[cs:ai-speakato-Antonin]Český text[/cs] [en:ai-speakato-Antonin]English text[/en]
```

---

## 🔗 Kombinace značek

Všechny značky lze kombinovat:

### Kombinace emphasis + intonace

```
**Důležité** [intonation:rise]otázka?[/intonation]
<emphasis level="strong">Důležité</emphasis> [intonation:fall]sdělení.[/intonation]
```

### Kombinace rate + pitch

```
<prosody rate="slow" pitch="low">Pomalu a hluboko</prosody>
```

### Kombinace multi-lang + pauzy + emphasis

```
[cs:buchty01]**Dobrý den!**[/cs] [pause:300]
[en:Pohadka_muz]<emphasis level="strong">Hello</emphasis>[/en] [pause:200]
[cs:buchty01][intonation:rise]Jak se máte?[/intonation][/cs]
```

### Komplexní příklad

```
[cs:buchty01]**Dobrý den!**[/cs] [pause:200]
[en:Pohadka_muz]<emphasis level="strong">Hello</emphasis>[/en] [pause:300]
[cs:buchty01][intonation:fall]Dnes je krásný den.[/intonation][/cs] [pause:500]
[cs:ai-speakato-Antonin]<prosody rate="slow" pitch="low">Meditativní hlas.</prosody>[/cs]
```

---

## 📝 Kompletní testovací text

```
<emphasis level="strong">Silný důraz.</emphasis>
<emphasis level="moderate">Mírný důraz.</emphasis>
**Silný s hvězdičkami.**
*Mírný s hvězdičkou.*

<prosody rate="slow">Pomalá řeč.</prosody>
<prosody rate="fast">Rychlá řeč.</prosody>
<prosody rate="x-slow">Velmi pomalá.</prosody>
<prosody rate="x-fast">Velmi rychlá.</prosody>

<prosody pitch="high">Vysoký hlas.</prosody>
<prosody pitch="low">Nízký hlas.</prosody>
<prosody pitch="x-high">Velmi vysoký.</prosody>
<prosody pitch="x-low">Velmi nízký.</prosody>

[intonation:fall]Klesavá intonace.[/intonation]
[intonation:rise]Stoupavá intonace?[/intonation]
[intonation:flat]Plochá intonace.[/intonation]
[intonation:wave]Vlnitá intonace.[/intonation]

[pause] Střední pauza
[pause:500] Vlastní pauza
[pause:200ms] Krátká pauza

Přijde zítra? Automaticky stoupavá.
Přijde zítra. Automaticky klesavá.

[cs:buchty01]Český text.[/cs]
[en:Pohadka_muz]English text.[/en]

[cs:buchty01]**Důraz** [pause:200] <prosody rate="slow">pomalu</prosody> [intonation:rise]otázka?[/intonation][/cs]
```

---

## ⚙️ Konfigurace

Prosody control lze zapnout/vypnout v `backend/config.py`:

```python
ENABLE_PROSODY_CONTROL = True  # Zapnout/vypnout prosody control
ENABLE_INTONATION_PROCESSING = True  # Zapnout/vypnout intonační post-processing
```

---

## 💡 Tipy

1. **Kombinujte značky** pro komplexnější efekty
2. **Používejte automatickou detekci** intonace podle interpunkce
3. **Testujte s různými hlasy** - některé hlasy reagují lépe na určité efekty
4. **Pauzy** pomáhají vytvářet přirozenější rytmus řeči
5. **Multi-lang** je užitečné pro bilingvní obsah

---

## 🐛 Řešení problémů

### Emphasis není slyšet
- Zkontrolujte, že `ENABLE_PROSODY_CONTROL = True`
- Podívejte se na debug výpisy v konzoli
- Zkuste zvýšit intenzitu (STRONG místo MODERATE)

### Intonace se neaplikuje
- Zkontrolujte, že `ENABLE_INTONATION_PROCESSING = True`
- Použijte explicitní značky místo automatické detekce

### Multi-lang nefunguje
- Zkontrolujte syntaxi: `[lang:speaker]text[/lang]`
- Ujistěte se, že demo hlas existuje
- Pro cross-language použijte hlas v jazyce textu



