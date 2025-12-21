# Meditativní a šeptavý hlas - Nastavení

Tento dokument popisuje, jak nastavit model pro klidný, meditativní až šeptavý hlas.

## Dostupné presety

Systém obsahuje dva nové presety pro meditativní a šeptavý hlas:

### 1. Preset "meditative"
Klidný, meditativní hlas s pomalejší řečí:

```python
{
    "speed": 0.75,              # Pomalejší řeč
    "temperature": 0.45,        # Nižší = konzistentnější, klidnější
    "length_penalty": 1.1,      # Mírně vyšší pro plynulejší řeč
    "repetition_penalty": 2.2,
    "top_k": 35,                # Nižší = konzistentnější
    "top_p": 0.75,              # Nižší = konzistentnější
    "enhancement": {
        "enable_eq": True,
        "enable_noise_reduction": True,
        "enable_compression": True,
        "enable_deesser": False,
        "enable_whisper": False,      # Whisper efekt vypnutý
        "whisper_intensity": 0.0
    }
}
```

### 2. Preset "whisper"
Šeptavý hlas s plným whisper efektem založeným na frekvenčních charakteristikách šeptání:

```python
{
    "speed": 0.65,              # Pomalejší řeč pro autentičnost šeptání
    "temperature": 0.30,        # Velmi nízká pro konzistentní, tichý hlas bez periodické struktury
    "length_penalty": 1.2,      # Vyšší pro plynulejší řeč (šeptání má menší dynamiku)
    "repetition_penalty": 2.6,  # Vyšší pro lepší artikulaci
    "top_k": 25,                # Nižší pro konzistentnější výstup (šeptání má šumový charakter)
    "top_p": 0.65,              # Nižší pro konzistentnější výstup
    "enhancement": {
        "enable_eq": False,     # Vypnuto - whisper efekt má vlastní EQ úpravy
        "enable_noise_reduction": True,  # Zapnuto - šeptání má šumový charakter
        "enable_compression": False,  # Vypnuto - whisper efekt má vlastní kompresi
        "enable_deesser": False,  # Vypnuto - šeptání má méně sykavek
        "enable_whisper": True,  # Whisper efekt zapnutý
        "whisper_intensity": 1.0  # Plná intenzita pro autentické šeptání
    }
}
```

## Použití přes API

### Příklad 1: Meditativní hlas

```javascript
// Použití presetu "meditative"
{
  text: "Dýchejte zhluboka a uvolněte se...",
  quality_mode: "meditative"
}
```

### Příklad 2: Šeptavý hlas

```javascript
// Použití presetu "whisper"
{
  text: "Tichý hlas pro meditaci...",
  quality_mode: "whisper"
}
```

### Příklad 3: Vlastní parametry

```javascript
// Ruční nastavení pro meditativní hlas
{
  text: "Dýchejte zhluboka...",
  speed: 0.75,
  temperature: 0.45,
  length_penalty: 1.1,
  top_k: 35,
  top_p: 0.75,
  enhancement_preset: "natural"  // nebo jiný preset
}
```

## Whisper efekt - technické detaily

Whisper efekt je založen na výzkumu frekvenčních charakteristik šeptání a aplikuje se jako post-processing:

### Frekvenční charakteristiky šeptání

Šeptání je charakterizováno:
- **Absencí fundamentální frekvence (F0)** - hlasivky nevibrují, takže chybí základní tón
- **Širokopásmovým spektrem** - energie rozložená napříč frekvencemi bez dominantní frekvence
- **Hlavní energie v pásmu 200-5000 Hz** - většina energie je v tomto rozsahu
- **Formanty (rezonance hlasového traktu) v pásmu 1-3 kHz** - stále přítomné, ale bez tonální složky
- **Šumový charakter** - bez periodické struktury typické pro běžnou řeč
- **Menší dynamický rozsah** - než běžná řeč

### Implementace whisper efektu

1. **Snížení velmi nízkých frekvencí** (pod 100-150 Hz)
   - Šeptání má minimální energii pod 100 Hz (bez fundamentální frekvence)
   - High-pass filter s 15-30% redukcí basů

2. **Zvýšení středních frekvencí** (1-3 kHz) - formanty šeptání
   - Formanty (rezonance hlasového traktu) jsou stále přítomné v šeptání
   - Boost 5-10% pro lepší simulaci formantů

3. **Mírné zvýšení středně-vysokých frekvencí** (3-4 kHz)
   - Šeptání má ještě určitou energii v tomto pásmu
   - Jemné zvýraznění (2-4% boost)

4. **Snížení vysokých frekvencí** (low-pass filter na 4.0-5.5 kHz)
   - Hlavní energie je v pásmu 200-5000 Hz, nad 5 kHz výrazný pokles
   - Strmejší roll-off pro autentičnost

5. **Výraznější pokles velmi vysokých frekvencí** (nad 5-6 kHz)
   - Šeptání má téměř žádné frekvence nad 5 kHz
   - Redukce 60-85% podle intenzity

6. **Přidání jemného šumu** (0-0.5% podle intenzity)
   - Pro autentičnost šumového charakteru šeptání
   - Simuluje turbulentní proudění vzduchu

7. **Snížení dynamiky** (komprese)
   - Šeptání má menší dynamický rozsah
   - Kompresní poměr: 2.5-3.0 (podle intenzity)

**Poznámka**: Whisper efekt NESNIŽUJE celkovou hlasitost - šeptání se simuluje pouze EQ úpravami a kompresí, hlasitost zůstává na normální úrovni.

## Parametry pro různé efekty

### Klidný, meditativní hlas (bez whisper efektu)
```python
speed: 0.75-0.8
temperature: 0.4-0.5
top_k: 30-40
top_p: 0.7-0.8
```

### Šeptavý hlas (s whisper efektem)
```python
speed: 0.6-0.7
temperature: 0.25-0.35  # Nižší pro konzistentnější výstup bez periodické struktury
length_penalty: 1.15-1.25  # Vyšší pro plynulejší řeč
top_k: 20-30  # Nižší pro konzistentnější výstup (šumový charakter)
top_p: 0.6-0.7  # Nižší pro konzistentnější výstup
quality_mode: "whisper"  # Automaticky zapne whisper efekt s frekvenčními charakteristikami
```

### Velmi tichý, jemný hlas
```python
speed: 0.6
temperature: 0.3
top_k: 25
top_p: 0.65
quality_mode: "whisper"
# + možná snížit OUTPUT_HEADROOM_DB na -9.0 dB
```

## Kombinace s intonací

Pro meditativní efekt můžete použít plochou intonaci:

```
[intonation:flat]Dýchejte zhluboka a uvolněte se.[/intonation]
```

Nebo kombinaci s důrazem:

```
**Dýchejte** [intonation:flat]zhluboka a uvolněte se.[/intonation]
```

## Tipy

1. **Pro meditaci**: Použijte preset "meditative" - klidný, pomalejší hlas bez whisper efektu
2. **Pro šeptání**: Použijte preset "whisper" - plný whisper efekt s tichým, šeptavým zvukem
3. **Pro vlastní nastavení**: Kombinujte parametry podle potřeby
4. **Intenzita whisper efektu**: V presetu je nastavena na 1.0 (plná), ale může být upravena v kódu

## Technické poznámky

- Whisper efekt se aplikuje **po** EQ, kompresi a de-esseru
- Whisper efekt **před** fade in/out a normalizací
- Intenzita whisper efektu: 0.0 = žádný efekt, 1.0 = plný efekt
- Whisper efekt může mírně snížit srozumitelnost - používejte opatrně

