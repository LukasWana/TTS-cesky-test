# Voice Assistant Reader - Chrome Extension

Doplněk do prohlížeče Chrome pro čtení označeného textu pomocí lokálního Voice Assistenta (XTTS-v2).

## Novinky ve verzi 1.1

- **Inteligentní dělení textu** - Automatické dělení podle vět (200-500 znaků na chunk)
- **Konfigurovatelné parametry** - Nastavení rychlosti, teploty, Top-K, Top-P a dalších
- **Lepší error handling** - Jasnější indikace stavu backendu

## Instalace

1. Otevřete Chrome a přejděte na `chrome://extensions`.
2. Vpravo nahoře zapněte **Režim pro vývojáře** (Developer mode).
3. Klikněte na tlačítko **Načíst rozbalené** (Load unpacked).
4. Vyberte složku `c:\work\projects\2025-voice-assistent\chrome_extension`.

## Použití

1. **Ujistěte se, že běží backend** (spusťte `start_gpu.bat` nebo `start_all.bat`).
2. Vyberte libovolný text na webové stránce.
3. Klikněte pravým tlačítkem a zvolte **Přečíst nahlas (Voice Assistant)**.
4. Pro dlouhé texty (články) bude text automaticky rozdělen na sentence-based chunks.

## Nastavení

Klikněte na ikonu rozšíření v liště prohlížeče:

### Hlas
- Výběr z dostupných hlasů (načítají se z backendu)

### Parametry generování
- **Rychlost** - 0.5 až 2.0 (výchozí: 1.0)
- **Teplota** - 0.1 až 1.5 (výchozí: 0.96)
- **Top-K** - 1 až 100 (výchozí: 1)
- **Top-P** - 0.1 až 1.0 (výchozí: 1.00)
- **Length Penalty** - 0.1 až 1.0 (výchozí: 0.50)
- **Repetition Penalty** - 1.0 až 2.0 (výchozí: 1.00)
- **Seed** - libovolné celé číslo (výchozí: 12)

## Jak funguje sentence-based chunking

1. Text je nejprve očištěn od speciálních znaků
2. Text je rozdělen na věty podle interpunkce (. ! ?)
3. Věty jsou seskupovány do chunků o velikosti 200-500 znaků
4. Každý chunk je odeslán k TTS generování
5. Výsledky jsou přehrávány v pořadí pro plynulé poslouchání

## Řešení problémů

- **"Backend nedostupný"** - Zkontrolujte, že běží `start_backend.bat`
- **"Chyba generování"** - Zkontrolujte logy backendu
- **Přerušované přehrávání** - Zkuste snížit rychlost na 0.8-0.9
