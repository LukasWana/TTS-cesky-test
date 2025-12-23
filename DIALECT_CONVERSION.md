# Převod Textu na Česká Nářečí

## Přehled

Byla přidána funkcionalita pro převod standardní češtiny na různá česká nářečí. Tato funkcionalita umožňuje syntetizovat řeč v různých nářečních variantách pomocí XTTS-v2.

## Podporovaná nářečí

1. **Moravské** (`moravske`) - Východomoravské nářečí
2. **Hanácké** (`hanacke`) - Středomoravské hanácké nářečí
3. **Slezské** (`slezske`) - Slezské nářečí s polskými vlivy
4. **Chodské** (`chodske`) - Západní české nářečí z Chodska
5. **Brněnské** (`brnenske`) - Městské brněnské nářečí (hantec)

## Jak to funguje

### 1. Lookup tabulka s pravidly

Pravidla pro převod jsou uložena v `lookup_tables/ceska_nareci.json`. Každé nářečí má:
- Pravidla pro samohlásky (např. e na konci → y)
- Pravidla pro souhlásky (např. h → ch)
- Slovní základy (např. jsem → sem)
- Koncovky
- Specifická slova

### 2. Dialect Converter modul

Modul `backend/dialect_converter.py` obsahuje třídu `DialectConverter`, která:
- Načítá pravidla z lookup tabulky
- Aplikuje pravidla na text podle zvoleného nářečí
- Podporuje intenzitu převodu (0.0-1.0)

### 3. Integrace do TTS

Převod na nářečí je integrován do `tts_engine.py` a aplikuje se během předzpracování textu před syntézou.

## Konfigurace

### Environment Variables

```bash
# Zapnout převod na nářečí
ENABLE_DIALECT_CONVERSION=True

# Zvolit nářečí (standardni, moravske, hanacke, slezske, chodske, brnenske)
DIALECT_CODE=moravske

# Intenzita převodu (0.0-1.0, kde 1.0 = plný převod)
DIALECT_INTENSITY=1.0
```

### V config.py

```python
# Dialect Conversion (převod textu na nářečí)
ENABLE_DIALECT_CONVERSION = os.getenv("ENABLE_DIALECT_CONVERSION", "False").lower() == "true"
DIALECT_CODE = os.getenv("DIALECT_CODE", "standardni")
DIALECT_INTENSITY = float(os.getenv("DIALECT_INTENSITY", "1.0"))
```

## Použití

### Programově

```python
from backend.dialect_converter import get_dialect_converter

converter = get_dialect_converter()

# Získat seznam dostupných nářečí
dialects = converter.get_available_dialects()
print(dialects)  # ['moravske', 'hanacke', 'slezske', 'chodske', 'brnenske']

# Převést text na moravské nářečí
text = "Dobrý den, jsem rád, že jsem tady."
moravske_text = converter.convert_to_dialect(text, "moravske", intensity=1.0)
print(moravske_text)  # "Dobrý den, sem rád, že sem tady."

# Částečný převod (50% intenzita)
partial = converter.convert_to_dialect(text, "moravske", intensity=0.5)
```

### Automaticky v TTS

Když je `ENABLE_DIALECT_CONVERSION=True` a `DIALECT_CODE` je nastaveno na jiné než "standardni", text se automaticky převede před syntézou.

## Příklady převodů

### Moravské nářečí

```
Standardní: "Dobrý den, jsem rád, že jsem tady."
Moravské:   "Dobrý den, sem rád, že sem tady."

Standardní: "Dělám to dobře."
Moravské:   "Dělám to dobry."
```

### Hanácké nářečí

```
Standardní: "Dobrý den, jsem rád."
Hanácké:    "Dobrý den, sem rád."
```

## Pravidla převodu

### Moravské nářečí

1. **Slovní základy:**
   - jsem → sem
   - jsme → sme
   - jste → ste
   - jsou → su

2. **Samohlásky:**
   - E na konci slov → y (dobře → dobry, krásně → krásny)

3. **Souhlásky:**
   - H → ch (v některých oblastech)

### Hanácké nářečí

1. **Slovní základy:** (stejné jako moravské)
2. **Samohlásky:**
   - E na konci → y
   - OU → uo (v některých případech)

### Slezské nářečí

1. **Slovní základy:** (stejné jako moravské)
2. **Souhlásky:**
   - H → ch (v některých oblastech)

## Rozšíření pravidel

Pravidla lze snadno rozšířit úpravou `lookup_tables/ceska_nareci.json`:

```json
{
  "nareci": {
    "moravske": {
      "pravidla": {
        "slovni_zaklad": {
          "priklady": {
            "jsem": "sem",
            "novy_slovni_zaklad": "nova_nahrada"
          }
        }
      }
    }
  }
}
```

## Brněnský hantec – velký slovník (doporučené)

Pro brněnské nářečí (`brnenske`) je praktické držet velký slovník mimo `ceska_nareci.json` (kvůli velikosti a údržbě) v samostatném souboru:

- `lookup_tables/hantec_slovnik_raw.txt` – zdrojový text ve formátu `HANTEC ~ význam`
- `scripts/convert_hantec_raw_to_json.py` – převod do JSON (standardní → hantec)
- `lookup_tables/hantec_slovnik.json` – výstupní lookup tabulka, kterou runtime načítá

V konvertoru se pro `brnenske` aplikuje:
- nejdřív **fráze** (delší shody mají přednost),
- potom **jednotlivá slova**,
- a nakonec existující pravidla z `ceska_nareci.json` (místopis, činnosti, specifická slova…).

## Intenzita převodu

Parametr `intensity` (0.0-1.0) určuje, jak silně se pravidla aplikují:

- **1.0** - Plný převod (všechna pravidla se aplikují)
- **0.5** - Částečný převod (pouze část pravidel se aplikuje náhodně)
- **0.0** - Žádný převod

## Omezení

1. **Přibližnost:** Převod je přibližný a zjednodušený. Skutečná nářečí mají mnohem složitější pravidla.

2. **Regionální varianty:** Každé nářečí má mnoho regionálních variant, které nejsou všechny pokryty.

3. **Kontext:** Některá pravidla závisí na kontextu, který není vždy správně rozpoznán.

4. **Význam:** Některé převody mohou změnit význam slova (i když se to snažíme minimalizovat).

## Budoucí rozšíření

- Přidání více nářečí
- Rozšíření pravidel pro existující nářečí
- Kontextově závislé převody
- Podpora pro více intenzit převodu
- Uživatelské definované pravidla

## Testování

```python
from backend.dialect_converter import get_dialect_converter

converter = get_dialect_converter()

# Test všech nářečí
test_text = "Dobrý den, jsem rád, že jsem tady a dělám to dobře."

for dialect in converter.get_available_dialects():
    converted = converter.convert_to_dialect(test_text, dialect)
    print(f"{dialect}: {converted}")
```

## Poznámky

- Převod se aplikuje **před** syntézou řeči, takže XTTS model syntetizuje již převedený text
- Pro nejlepší výsledky použijte intenzitu 1.0
- Pravidla lze snadno rozšířit úpravou JSON souboru
- Některé převody mohou být nepřesné - vždy testujte výsledky



