# Plán projektu 2025-voice-assistent

Hlavní plán a místo pro předávku mezi sessions (rozhodnutí uživatele 2026-11-12). Soubor se **přepisuje**, ne připisuje;
limit 25 KB. Historie je v gitu.

## Stav

- Repo: `origin` = `github.com/LukasWana/TTS-cesky-test`, větev `main`, HEAD `15ce062` je pushnutý, pracovní strom čistý.
- `backend/api/routers/realtime.py` používá `XTTSEngine` (třída existuje v `backend/tts_engine.py:78`, metoda
  `_split_text_by_commas_and_words` na ř. 160; jiný odkaz na staré jméno `TTSEngine` v `backend/*.py` grep nenašel).
  Ověřeno jen čtením kódu, backend spuštěn nebyl.

## Otevřené

1. **Integrace Applio odkazuje na smazaný adresář.** Commit `15ce062` odstranil z gitu celý `backend/applio`
   (255 souborů; na disku adresář neexistoval už před commitem). Na adresář dál odkazují:
   - `backend/api/routers/applio.py:44` — `from backend.applio.applio_client import ApplioGradioClient` (import je
     v `try`, `ImportError` se jen zaloguje);
   - `start_all.bat:415-416` — spouští `backend\applio\sync-voices.ps1` a `backend\applio\env\python.exe app.py`;
   - `backend/main.py:70,146` — router `applio` se registruje (LITE režim ho podle ř. 52 přeskakuje);
   - `.gitignore:91-110` — pravidla pro `backend/applio/*`;
   - celkem `grep -i applio` = 317 výskytů v 19 souborech (včetně dokumentace, testů `test_applio*.bat`,
     `backend/test_applio.py` a frontendu `AudioEditor.jsx`, `History.jsx`, `services/api.js`).

   Neověřeno: zda bylo smazání adresáře záměr a zda se má Applio vrátit (např. jako externí instalace mimo repo),
   nebo se má integrace z kódu odstranit. **Čeká na rozhodnutí uživatele.**
2. Backend ani frontend nebyly po commitu `15ce062` spuštěny; žádné testy neběžely.

## Rozhodnutí

- 2026-11-12: předávka se ukládá sem do `docs/PLAN.md` (uživatel zvolil na dotaz při ukončení session).

## Předávka

```
Projekt 2025-voice-assistent (C:/work/projects/2025-voice-assistent), větev main, HEAD pushnutý na origin.
Přečti docs/PLAN.md, sekce Stav a Otevřené.

Minulá session (2026-11-12) jen commitla a pushla rozpracovaný stav: commit 15ce062 (smazání backend/applio,
TTSEngine -> XTTSEngine v backend/api/routers/realtime.py, 3 nové WAV v "assets/czech voices").
Nic se nespouštělo ani netestovalo.

Otevřené, čeká na rozhodnutí uživatele: adresář backend/applio je z repa pryč, ale kód na něj dál odkazuje
(backend/api/routers/applio.py:44, start_all.bat:415-416, backend/main.py:70 a 146, .gitignore:91-110).
Nejdřív se uživatele zeptej, jestli se má Applio vrátit, nebo integrace odstranit; bez odpovědi nic z toho neměň.

Ověření stavu: git status -sb (čekej "## main...origin/main" bez změn), git log --oneline -1 (15ce062 nebo novější).
```
