# Opravy fonetického přepisu - česká stop words

## Problém

V lookup tabulkách (`english_phonetic.json`) jsou některá běžná česká slova, která se přepisují foneticky, i když by se neměla. To způsobuje, že se čtou jako písmena nebo nesprávně.

## Nalezené problémy

### 1. Předložky
- **"za"** → přepisováno jako "zet á" (písmena Z a A)
- **"pod"** → přepisováno jako "pod" (může být problém v kontextu)
- **"s"** → přepisováno jako "zurič" (velmi špatně)

### 2. Spojky
- **"ale"** → přepisováno jako "ale" (může být problém v kontextu)

### 3. Zájmena
- **"ta"** → přepisováno jako "ta" (může být problém v kontextu)
- **"ten"** → přepisováno jako "ten" (může být problém v kontextu)
- **"si"** → přepisováno jako "es í" (písmena S a I)
- **"mi"** → přepisováno jako "je" (úplně špatně)

### 4. Částice
- **"ne"** → přepisováno jako "li dokonce na hřbet samotného školního sešitu" (velmi špatně)

## Řešení

Byl vytvořen rozšířený seznam českých stop words v `PhoneticTranslator`, který obsahuje:

### Kategorie stop words (celkem 186 slov):

1. **Předložky** (30+ slov)
   - Jednoslabičné: za, na, v, s, z, k, o, u
   - Dvouslabičné: pro, před, pod, nad, přes, bez, od, do, po, při
   - Více slabik: mezi, kolem, okolo, kromě, mimo, vedle, blízko, daleko, podle

2. **Spojky** (20+ slov)
   - Souřadicí: a, i, ale, nebo
   - Podřadicí: protože, když, že, aby, kdyby
   - Další: pak, tak, také, takže, proto, avšak, však, jenže, přesto, nicméně

3. **Zájmena** (80+ slov)
   - Osobní: já, ty, on, ona, ono, my, vy, oni, ony
   - Přivlastňovací: můj, tvůj, jeho, její, náš, váš, jejich
   - Ukazovací: to, ta, ten, toto, tato, tento, tam, tady, tamto
   - Tázací: kdo, co, jaký, který, kde, kam, kdy, proč, jak
   - Vztažná: který, jenž, jež
   - Neurčitá: někdo, něco, nějaký, některý, někde, někdy
   - Reflexivní: se, si, sebe, sobě, sebou
   - Krátké tvary: mi, ti, mu, jí, nám, vám, jim

4. **Částice** (15+ slov)
   - ne, ano, nechť, ať, kéž, jen, jenom, pouze, také, i, ani, nebo, či

5. **Pomocná slovesa** (15+ slov)
   - je, jsem, jsme, jste, jsou, být, mít, byl, byla, bylo, bude, budou

6. **Číslovky základní** (1-10)
   - jeden, dva, tři, čtyři, pět, šest, sedm, osm, devět, deset

7. **Číslovky řadové** (1-10)
   - první, druhý, třetí, čtvrtý, pátý, šestý, sedmý, osmý, devátý, desátý

## Implementace

V `backend/phonetic_translator.py`:

```python
self.czech_stopwords = {
    # Rozsáhlý seznam českých stop words
    ...
}

def _apply_phonetic_dict(self, text: str, phonetic_dict: Dict[str, str]) -> str:
    ...
    for foreign_word in sorted_words:
        # Přeskočit české stop words - nepřepisovat je foneticky
        if foreign_word.lower() in self.czech_stopwords:
            continue
        ...
```

## Výsledek

- Česká stop words se **nepřepisují** foneticky
- Zůstávají v původní podobě
- Cizí slova se stále přepisují správně
- Předložky, spojky, zájmena se čtou správně

## Testování

Zkuste vygenerovat texty s:
- "za domem" → mělo by se číst jako předložka "za", ne "zet á"
- "ale ne" → mělo by se číst jako spojka "ale", ne foneticky
- "si to" → mělo by se číst jako zájmeno "si", ne "es í"
- "mi řekl" → mělo by se číst jako zájmeno "mi", ne "je"

## Poznámky

- Seznam stop words lze dále rozšířit podle potřeby
- Pokud najdete další problematická slova, přidejte je do `czech_stopwords`
- Stop words se kontrolují case-insensitive (malá/velká písmena)








