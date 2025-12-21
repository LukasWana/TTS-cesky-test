# Lookup tabulky pro český TTS systém

Tento adresář obsahuje strukturované lookup tabulky pro rychlý přístup k výslovnostním a prosodickým pravidlům.

## Struktura

### `spodoba_znelosti.json`
Kompletní pravidla pro spodobu znělosti:
- Párové souhlásky (p/b, t/d, k/g, f/v, s/z, š/ž, ch/h, c/dz, č/dž)
- Pravidla pro konec slova
- Regresivní asimilace (před neznělými)
- Progresivní asimilace (před znělými)
- Zvláštní případy (v, ř, sh)
- Konkrétní příklady s transformacemi

### `raz_pozice.json`
Pravidla pro vkládání rázu (glottální okluze [ʔ]):
- Na začátku slova po pauze
- Mezi dvěma samohláskami
- Po předponách
- Dopad na asimilaci znělosti

### `prejata_slova_vyjimky.json`
Slovník problematických přejatých slov:
- Samohlásková délka (kolísání in/ín, on/ón, or/ór, ura/úra)
- Souhlásková znělost (s/z, k/g)
- Skupiny di, ti, ni (měkké vs. tvrdé)
- Vlastní jména s různými výslovnostmi podle původu
- Konkrétní příklady s variantami

### `souhlsakove_skupiny.json`
Problematické souhláskové skupiny:
- mě [mňe] (nespravně [mje])
- šťk [šťk/štk]
- cts (redukce na [c])
- nk/ng → [ŋ] (závazné)
- mv/mf → [ɱ] (fakultativní)
- tň/dň, nť/nď (fakultativní asimilace)
- ts/ds asimilace
- nsk asimilace

### `foneticka_abeceda.json`
Kompletní fonetická abeceda:
- Samohlásky (krátké, dlouhé, diftongy)
- Souhlásky (závěrové, úžinové, polozávěrové, kmitavé, bokové, klouzavé)
- IPA symboly
- Znělostní páry
- Jedinečné souhlásky
- Varianty fonémů ([ɱ], [ŋ], [r̝̊], [ɣ])
- Celkem 44 fonémů (13 vokálů + 31 konsonantů)

### `prosodicke_pravidla.json`
Prosodická pravidla:
- Slabika (slabikotvorné souhlásky, pobočná slabika)
- Slovní přízvuk (na první slabice)
- Větný přízvuk (na obsahově nejdůležitějším slově)
- Melodémy (klesavý, stoupavý, neukončující)
- Tempo řeči (průměrně 5 slabik/s)
- Pauzy (členicí, důrazové, formulační, hezitace)
- Frázování
- SSML tagy pro prosodické značení

### `../test_data/testovaci_slova.json`
Testovací sada problematických slov:
- Spodoba znělosti (konec slova, před neznělými/znělými)
- Ráz (pozice)
- Přejatá slova (samohlásková délka, souhlásková znělost, di/ti/ni)
- Souhláskové skupiny
- Vypouštění a vkládání hlásek
- Spojení stejných souhlásek
- Vlastní jména
- Značky, čísla a číslice
- Prosodické jevy

## Použití

### Python příklad

```python
import json

# Načtení lookup tabulky
with open('sources/lookup_tables/spodoba_znelosti.json', 'r', encoding='utf-8') as f:
    spodoba = json.load(f)

# Získání pravidel pro konec slova
pravidla_konec = spodoba['pravidla']['konec_slova']
print(pravidla_konec['priklady'])

# Kontrola párových souhlásek
znele_neznele = spodoba['znele_neznele_pary']
print(f"Párová souhláska k 'b': {znele_neznele['b']}")  # 'p'
```

### Validace výslovnosti

```python
# Načtení testovacích slov
with open('sources/test_data/testovaci_slova.json', 'r', encoding='utf-8') as f:
    testy = json.load(f)

# Test spodoby znělosti na konci slova
for priklad in testy['kategorie']['spodoba_znelosti']['konec_slova']:
    print(f"{priklad['slovo']}: {priklad['spravne']}")
```

### Prosodické značení

```python
# Načtení prosodických pravidel
with open('sources/lookup_tables/prosodicke_pravidla.json', 'r', encoding='utf-8') as f:
    prosodie = json.load(f)

# Získání melodémů
melodemy = prosodie['melodémy']
for nazev, popis in melodemy.items():
    print(f"{nazev}: {popis['popis']}")
    print(f"  Příklady: {popis['priklady']}")
```

## Aktualizace

Při aktualizaci pravidel:
1. Aktualizujte příslušný JSON soubor
2. Zvyšte číslo verze
3. Aktualizujte datum v `source` poli
4. Otestujte pomocí `testovaci_slova.json`

## Formát

Všechny soubory jsou v JSON formátu s UTF-8 encoding:
- Strukturovaná hierarchie
- Konkrétní příklady
- Implementační poznámky
- Odkazy na zdroje

