# Přírodní ambience pro meditativní hudbu (potůček / ptáci)

Tahle složka je určená pro **lokální** zvukové podklady, které se budou **mixovat** do MusicGen výstupu (ambient/meditace).

Repo **neobsahuje** žádné audio (binárky) – vložte sem vlastní WAV soubory.

## Jak pojmenovat soubory

- Potůček / voda: `stream_*.wav`
  - příklady: `stream_small.wav`, `stream_forest_01.wav`
- Ptáci: `birds_*.wav`
  - příklady: `birds_morning.wav`, `birds_park_02.wav`

Podporovaný formát: **WAV** (doporučeno 44.1k/48k, mono/stereo – backend si to přizpůsobí).

## Tipy pro dobrý výsledek

- Ideální jsou **čisté field recordings** bez hlasů lidí.
- Délka 10–60s je OK (backend to umí loopovat do libovolné délky).
- Hlasitost nech radši nižší; v UI se nastavuje mix typicky kolem **-22 až -14 dB**.

## Co se stane, když tu nic není

Pokud v UI zvolíš ambience (potůček/ptáci) a tady nejsou žádné odpovídající soubory, MusicGen stále vygeneruje hudbu, ale backend vrátí `warning` a výstup bude bez ambience vrstvy.



