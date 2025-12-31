import React from 'react'

export function XTTSHelpContent() {
  return (
    <>
      <p>
        XTTS model podporuje pokročilé značky pro kontrolu prosody (důraz, rychlost, výška hlasu, intonace, pauzy) a multi-jazyčné/multi-speaker funkce.
      </p>

      <h3>Důraz (Emphasis)</h3>
      <p>Zvýrazní část textu zvýšením hlasitosti a boostem středních frekvencí.</p>

      <h4>SSML syntaxe</h4>
      <pre><code>{`<emphasis level="strong">Toto je silný důraz</emphasis>
<emphasis level="moderate">Toto je mírný důraz</emphasis>
<emphasis>Toto je výchozí důraz (mírný)</emphasis>`}</code></pre>

      <h4>Jednoduché značky</h4>
      <pre><code>{`**Toto je silný důraz**     (dvě hvězdičky)
*Toto je mírný důraz*        (jedna hvězdička)
__Toto je silný důraz__      (dvě podtržítka)
_Toto je mírný důraz_        (jedno podtržítko)`}</code></pre>

      <div className="help-example">
        <strong>Příklad:</strong><br />
        <code>**Důležité upozornění!** Prosím, přečtěte si to.</code>
      </div>

      <h3>Rychlost řeči (Rate)</h3>
      <pre><code>{`<prosody rate="slow">Pomalá řeč</prosody>
<prosody rate="fast">Rychlá řeč</prosody>
<prosody rate="x-slow">Velmi pomalá řeč</prosody>
<prosody rate="x-fast">Velmi rychlá řeč</prosody>`}</code></pre>

      <h3>Výška hlasu (Pitch)</h3>
      <pre><code>{`<prosody pitch="high">Vysoký hlas</prosody>
<prosody pitch="low">Nízký hlas</prosody>
<prosody pitch="x-high">Velmi vysoký hlas</prosody>
<prosody pitch="x-low">Velmi nízký hlas</prosody>`}</code></pre>

      <h3>Intonace</h3>
      <p>Systém automaticky detekuje intonaci podle interpunkce, nebo můžete použít explicitní značky:</p>

      <pre><code>{`[intonation:fall]Klesavá intonace[/intonation]
[intonation:rise]Stoupavá intonace[/intonation]
[intonation:flat]Plochá intonace[/intonation]
[intonation:wave]Vlnitá intonace[/intonation]
[intonation:half_fall]Polokadence[/intonation]`}</code></pre>

      <div className="help-tip">
        <strong>Automatická detekce:</strong><br />
        <code>Přijde zítra?</code> → automaticky stoupavá<br />
        <code>Přijde zítra.</code> → automaticky klesavá<br />
        <code>Když přijde,</code> → automaticky polokadence
      </div>

      <h3>Pauzy</h3>
      <pre><code>{`[pause]              Střední pauza (~300ms)
[pause:500]          Vlastní pauza 500ms
[pause:200ms]        Vlastní pauza 200ms (s jednotkou)
...                  Krátká pauza (~200ms)`}</code></pre>

      <div className="help-example">
        <strong>Příklad:</strong><br />
        <code>Dobrý den [pause] jak se máte?</code>
      </div>

      <h3>Multi-lang a Multi-speaker</h3>
      <p>Použití více jazyků a mluvčích v jednom textu:</p>

      <pre><code>{`[lang:speaker]text[/lang]    S mluvčím
[lang]text[/lang]            Bez mluvčího (výchozí hlas)`}</code></pre>

      <h4>Podporované jazyky</h4>
      <ul>
        <li><code>cs</code> - Čeština (výchozí)</li>
        <li><code>en</code> - Angličtina</li>
        <li><code>de</code> - Němčina</li>
        <li><code>es</code> - Španělština</li>
        <li><code>fr</code> - Francouzština</li>
        <li><code>it</code> - Italština</li>
        <li><code>pl</code> - Polština</li>
        <li><code>pt</code> - Portugalština</li>
        <li><code>ru</code> - Ruština</li>
        <li><code>tr</code> - Turečtina</li>
        <li><code>zh</code> - Čínština</li>
        <li><code>ja</code> - Japonština</li>
      </ul>

      <div className="help-example">
        <strong>Příklad:</strong><br />
        <code>[cs:buchty01]Dobrý den v češtině.[/cs] [en:Pohadka_muz]Hello in English.[/en]</code>
      </div>

      <h3>Kombinace značek</h3>
      <p>Všechny značky lze kombinovat:</p>

      <div className="help-example">
        <strong>Komplexní příklad:</strong><br />
        <code>[cs:buchty01]**Dobrý den!**[/cs] [pause:200] [en:Pohadka_muz]Hello[/en] [cs:buchty01][intonation:rise]Jak se máte?[/intonation][/cs]</code>
      </div>

      <div className="help-tip">
        <strong>💡 Tipy:</strong>
        <ul>
          <li>Kombinujte značky pro komplexnější efekty</li>
          <li>Používejte automatickou detekci intonace podle interpunkce</li>
          <li>Testujte s různými hlasy - některé hlasy reagují lépe na určité efekty</li>
          <li>Pauzy pomáhají vytvářet přirozenější rytmus řeči</li>
        </ul>
      </div>
    </>
  )
}

export function F5TTSHelpContent() {
  return (
    <>
      <p>
        F5-TTS slovenský model generuje řeč ze slovenského textu. Model nepodporuje speciální značky v promptu - používejte normální slovenský text.
      </p>

      <h3>Formát promptu</h3>
      <p>Jednoduše zadejte slovenský text, který chcete nechat namluvit:</p>

      <div className="help-example">
        <strong>Příklad:</strong><br />
        <code>Dobrý deň, ako sa máte? Dnes je krásny deň.</code>
      </div>

      <h3>Ref_text parametr (volitelné)</h3>
      <p>
        Pole "Přepis referenčního audia" (ref_text) není součást promptu, ale může výrazně zlepšit kvalitu výslovnosti,
        zejména u vlastních hlasů (upload/record/YouTube).
      </p>

      <div className="help-tip">
        <strong>💡 Tip:</strong> Zadejte do ref_text pole přesný text toho, co je namluveno v referenčním audiu.
        Když ref_text sedí s audiodatem, často to zlepší výslovnost a stabilitu hlasu.
      </div>

      <div className="help-warning">
        <strong>⚠️ Upozornění:</strong> Pokud ref_text nesedí k referenci, může kvalitu naopak zhoršit.
        Používejte ho pouze pokud máte přesný přepis referenčního audia.
      </div>

      <h3>Automatický přepis</h3>
      <p>
        Můžete použít tlačítko "Přepsat referenci" nebo zapnout "Auto přepis po nahrání" -
        systém automaticky přepíše referenční audio pomocí ASR (Automatic Speech Recognition) a vyplní pole ref_text.
      </p>

      <div className="help-tip">
        <strong>💡 Tip:</strong> Nejvíce pomáhá u vlastních hlasů (upload/record/YouTube).
        U demo hlasů obvykle není nutné.
      </div>
    </>
  )
}

export function BarkHelpContent() {
  return (
    <>
      <p>
        Bark (Suno AI) generuje realistickou řeč, hudbu a zvuky z textu. Používá speciální tokeny v hranatých závorkách pro různé typy obsahu.
      </p>

      <h3>Formát promptu</h3>

      <h4>Hudba</h4>
      <p>Pro generování hudby použijte token <code>[music]</code> následovaný popisem hudby:</p>

      <div className="help-example">
        <strong>Příklad:</strong><br />
        <code>[music] calm piano melody</code><br />
        <code>[music] upbeat electronic dance music, 120 BPM</code>
      </div>

      <h4>SFX zvuky</h4>
      <p>Pro zvukové efekty rozdělte zvuky do samostatných segmentů v hranatých závorkách. Používejte jednoduché, konkrétní popisy:</p>

      <div className="help-example">
        <strong>Příklad:</strong><br />
        <code>[water stream] [water over rocks] [brook sounds]</code><br />
        <code>[footsteps on gravel] [door creaking] [wind howling]</code>
      </div>

      <div className="help-tip">
        <strong>💡 Tip:</strong> Pro SFX zvuky používejte jednoduché, konkrétní popisy.
        Rozdělte různé zvuky do samostatných segmentů: <code>[zvuk1] [zvuk2] [zvuk3]</code>
      </div>

      <h4>Řeč</h4>
      <p>Pro normální řeč jednoduše napište text bez speciálních tokenů:</p>

      <div className="help-example">
        <strong>Příklad:</strong><br />
        <code>Ahoj! Jak se máte dnes?</code>
      </div>

      <h3>Speciální tokeny</h3>
      <p>Bark podporuje různé speciální tokeny pro efekty v řeči:</p>

      <ul>
        <li><code>[laughter]</code> - smích</li>
        <li><code>[coughs]</code> - kašel</li>
        <li><code>[sighs]</code> - povzdech</li>
        <li><code>[gasps]</code> - vzdech</li>
        <li><code>[clears throat]</code> - odkašlání</li>
        <li>A další...</li>
      </ul>

      <div className="help-example">
        <strong>Příklad kombinace:</strong><br />
        <code>Ahoj! [laughter] Jak se máte? [music] calm background music</code>
      </div>

      <h3>Kombinace různých typů</h3>
      <p>Můžete kombinovat řeč, hudbu a SFX v jednom promptu:</p>

      <div className="help-example">
        <strong>Příklad:</strong><br />
        <code>Dobrý den! [pause] [water stream] [birds chirping] [music] peaceful ambient</code>
      </div>

      <div className="help-tip">
        <strong>💡 Tipy:</strong>
        <ul>
          <li>Pro hudbu vždy začněte s <code>[music]</code> tokenem</li>
          <li>Pro SFX zvuky používejte jednoduché, konkrétní popisy</li>
          <li>Speciální tokeny jako <code>[laughter]</code> fungují nejlépe v řeči</li>
          <li>Delší než ~14s se zacyklí - doporučená délka je do 14 sekund</li>
        </ul>
      </div>
    </>
  )
}

export function MusicGenHelpContent() {
  return (
    <>
      <p>
        MusicGen (AudioCraft) generuje hudbu z textového popisu. Používá prostý anglický text popisující styl, tempo, náladu a další vlastnosti hudby.
      </p>

      <h3>Formát promptu</h3>
      <p>Zadejte anglický text popisující hudbu, kterou chcete generovat:</p>

      <div className="help-example">
        <strong>Příklady:</strong><br />
        <code>ambient cinematic pads, 90 BPM, no vocals, warm, slow build</code><br />
        <code>calm meditative ambient drone, warm pads, slow evolution, no drums, no vocals, relaxing</code><br />
        <code>upbeat electronic dance music, 128 BPM, energetic, driving bass</code>
      </div>

      <h3>Klíčové složky popisu</h3>

      <h4>Styl a žánr</h4>
      <ul>
        <li><code>ambient</code> - ambientní hudba</li>
        <li><code>cinematic</code> - filmová hudba</li>
        <li><code>electronic</code> - elektronická hudba</li>
        <li><code>piano</code> - klavír</li>
        <li><code>orchestral</code> - orchestrální</li>
        <li>A další žánry...</li>
      </ul>

      <h4>Tempo (BPM)</h4>
      <p>Můžete specifikovat tempo v BPM (beats per minute):</p>

      <div className="help-example">
        <code>90 BPM</code> - pomalejší tempo<br />
        <code>120 BPM</code> - střední tempo<br />
        <code>128 BPM</code> - rychlejší tempo
      </div>

      <h4>Nálada a charakter</h4>
      <ul>
        <li><code>calm</code>, <code>peaceful</code> - klidná</li>
        <li><code>energetic</code>, <code>driving</code> - energická</li>
        <li><code>warm</code>, <code>mellow</code> - teplá, jemná</li>
        <li><code>dark</code>, <code>mysterious</code> - temná, tajemná</li>
        <li><code>uplifting</code> - povznášející</li>
      </ul>

      <h4>Vlastnosti</h4>
      <ul>
        <li><code>no vocals</code> - bez vokálů</li>
        <li><code>no drums</code> - bez bicích</li>
        <li><code>slow build</code> - pomalý náběh</li>
        <li><code>driving bass</code> - výrazný bas</li>
        <li><code>soft pads</code> - měkké pad syntezátory</li>
      </ul>

      <div className="help-example">
        <strong>Komplexní příklad:</strong><br />
        <code>very calm meditative ambient drone, warm pads, slow evolution, no drums, no vocals, no melody hooks, relaxing</code>
      </div>

      <h3>Ambience overlay (volitelné)</h3>
      <p>
        Můžete přidat ambientní zvuky (potůček, ptáci) k vygenerované hudbě pomocí nastavení "Ambience".
        Tyto zvuky se mixují s hudbou v pozadí.
      </p>

      <div className="help-tip">
        <strong>💡 Tipy:</strong>
        <ul>
          <li>Buďte konkrétní - specifikujte žánr, tempo a náladu</li>
          <li>Použijte <code>no vocals</code> nebo <code>no drums</code> pro instrumentální hudbu</li>
          <li>Pro meditační hudbu použijte: <code>calm</code>, <code>ambient</code>, <code>slow evolution</code></li>
          <li>Kombinujte více vlastností pro přesnější výsledek</li>
        </ul>
      </div>
    </>
  )
}

