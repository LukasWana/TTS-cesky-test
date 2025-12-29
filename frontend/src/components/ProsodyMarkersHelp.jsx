import React, { useState, useRef, useEffect } from 'react'
import './ProsodyMarkersHelp.css'

function ProsodyMarkersHelp() {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef(null)

  // Zavřít dropdown při kliknutí mimo
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false)
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isOpen])

  return (
    <div className="prosody-help-container" ref={dropdownRef}>
      <button
        className="btn-prosody-help"
        onClick={() => setIsOpen(!isOpen)}
        title="Zobrazit dostupné značky pro kontrolu prosody"
      >
        ❓ Pomocník značek
      </button>

      {isOpen && (
        <div className="prosody-help-dropdown">
          <div className="prosody-help-header">
            <h3>📝 Dostupné značky pro kontrolu prosody</h3>
            <button className="btn-close-help" onClick={() => setIsOpen(false)}>✕</button>
          </div>

          <div className="prosody-help-content">
            {/* Pauzy */}
            <section className="prosody-section">
              <h4>⏸️ Pauzy</h4>
              <div className="prosody-examples">
                <div className="prosody-example">
                  <code>[pause]</code>
                  <span>Střední pauza (~300ms)</span>
                </div>
                <div className="prosody-example">
                  <code>[pause:500]</code>
                  <span>Vlastní pauza 500ms</span>
                </div>
                <div className="prosody-example">
                  <code>[pause:200ms]</code>
                  <span>Vlastní pauza 200ms</span>
                </div>
                <div className="prosody-example">
                  <code>...</code>
                  <span>Krátká pauza (~200ms)</span>
                </div>
              </div>
              <div className="prosody-usage">
                <strong>Příklad:</strong> <code>Dobrý den [pause] jak se máte?</code>
              </div>
            </section>

            {/* Důraz */}
            <section className="prosody-section">
              <h4>🎯 Důraz</h4>
              <div className="prosody-examples">
                <div className="prosody-example">
                  <code>**text**</code>
                  <span>Silný důraz</span>
                </div>
                <div className="prosody-example">
                  <code>*text*</code>
                  <span>Mírný důraz</span>
                </div>
                <div className="prosody-example">
                  <code>&lt;emphasis level="strong"&gt;text&lt;/emphasis&gt;</code>
                  <span>SSML silný důraz</span>
                </div>
              </div>
              <div className="prosody-usage">
                <strong>Příklad:</strong> <code>**Důležité upozornění!** Prosím, přečtěte si to.</code>
              </div>
            </section>

            {/* Rychlost */}
            <section className="prosody-section">
              <h4>⚡ Rychlost řeči</h4>
              <div className="prosody-examples">
                <div className="prosody-example">
                  <code>&lt;prosody rate="slow"&gt;text&lt;/prosody&gt;</code>
                  <span>Pomalá řeč</span>
                </div>
                <div className="prosody-example">
                  <code>&lt;prosody rate="fast"&gt;text&lt;/prosody&gt;</code>
                  <span>Rychlá řeč</span>
                </div>
                <div className="prosody-example">
                  <code>&lt;prosody rate="x-slow"&gt;text&lt;/prosody&gt;</code>
                  <span>Velmi pomalá řeč</span>
                </div>
              </div>
              <div className="prosody-usage">
                <strong>Příklad:</strong> <code>&lt;prosody rate="slow"&gt;Pomalu a zřetelně&lt;/prosody&gt;</code>
              </div>
            </section>

            {/* Výška hlasu */}
            <section className="prosody-section">
              <h4>🎵 Výška hlasu</h4>
              <div className="prosody-examples">
                <div className="prosody-example">
                  <code>&lt;prosody pitch="high"&gt;text&lt;/prosody&gt;</code>
                  <span>Vysoký hlas</span>
                </div>
                <div className="prosody-example">
                  <code>&lt;prosody pitch="low"&gt;text&lt;/prosody&gt;</code>
                  <span>Nízký hlas</span>
                </div>
              </div>
              <div className="prosody-usage">
                <strong>Příklad:</strong> <code>&lt;prosody pitch="high"&gt;Vysoký hlas&lt;/prosody&gt;</code>
              </div>
            </section>

            {/* Intonace */}
            <section className="prosody-section">
              <h4>🎼 Intonace</h4>
              <div className="prosody-examples">
                <div className="prosody-example">
                  <code>[intonation:fall]text[/intonation]</code>
                  <span>Klesavá intonace</span>
                </div>
                <div className="prosody-example">
                  <code>[intonation:rise]text[/intonation]</code>
                  <span>Stoupavá intonace</span>
                </div>
                <div className="prosody-example">
                  <code>[intonation:flat]text[/intonation]</code>
                  <span>Plochá intonace</span>
                </div>
                <div className="prosody-example">
                  <code>[intonation:wave]text[/intonation]</code>
                  <span>Vlnitá intonace</span>
                </div>
                <div className="prosody-example">
                  <code>[intonation:half_fall]text[/intonation]</code>
                  <span>Polokadence</span>
                </div>
              </div>
              <div className="prosody-usage">
                <strong>Příklad:</strong> <code>[intonation:rise]Přijde zítra?[/intonation]</code>
              </div>
            </section>

            {/* Multi-lang */}
            <section className="prosody-section">
              <h4>🌍 Více jazyků a mluvčích</h4>
              <div className="prosody-examples">
                <div className="prosody-example">
                  <code>[lang:speaker]text[/lang]</code>
                  <span>S mluvčím</span>
                </div>
                <div className="prosody-example">
                  <code>[lang]text[/lang]</code>
                  <span>Bez mluvčího (výchozí hlas)</span>
                </div>
              </div>
              <div className="prosody-usage">
                <strong>Příklad:</strong> <code>[cs:buchty01]Dobrý den[/cs] [en:Pohadka_muz]Hello[/en]</code>
              </div>
              <div className="prosody-note">
                <strong>Podporované jazyky:</strong> cs, en, de, es, fr, it, pl, pt, ru, tr, zh, ja
              </div>
            </section>

            {/* Kombinace */}
            <section className="prosody-section">
              <h4>🔗 Kombinace značek</h4>
              <div className="prosody-usage">
                <strong>Příklad:</strong>
                <code>
                  [cs:buchty01]**Dobrý den!**[/cs] [pause:200] [en:Pohadka_muz]&lt;emphasis level="strong"&gt;Hello&lt;/emphasis&gt;[/en]
                </code>
              </div>
            </section>
          </div>
        </div>
      )}
    </div>
  )
}

export default ProsodyMarkersHelp

