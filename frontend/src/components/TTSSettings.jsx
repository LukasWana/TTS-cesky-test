import React, { useState, useEffect, useRef } from 'react'
import './TTSSettings.css'

// Komponenta pro rozbalovací sekci
function CollapsibleSection({ title, icon, isExpanded, onToggle, children }) {
  return (
    <div className="collapsible-section">
      <div className="collapsible-section-header" onClick={onToggle}>
        <div className="collapsible-section-title">
          <span className="section-icon">{icon}</span>
          <h4>{title}</h4>
        </div>
        <span className="toggle-icon">{isExpanded ? '▼' : '▶'}</span>
      </div>
      {isExpanded && (
        <div className="collapsible-section-content">
          {children}
        </div>
      )}
    </div>
  )
}

function TTSSettings({ settings, onChange, onReset, qualitySettings, onQualityChange, activeVariant, onVariantChange }) {
  const [isExpanded, setIsExpanded] = useState(true) // Hlavní panel otevřený
  const [variantsExpanded, setVariantsExpanded] = useState(true)
  const [ttsParamsExpanded, setTtsParamsExpanded] = useState(true)
  const [qualityExpanded, setQualityExpanded] = useState(true)
  const [advancedExpanded, setAdvancedExpanded] = useState(false)
  const wasExpandedRef = useRef(false)

  // Zajistit, že se komponenta nezavře při změně varianty
  // Pokud byla otevřená, zůstane otevřená
  useEffect(() => {
    if (wasExpandedRef.current && !isExpanded) {
      // Pokud byla otevřená před změnou varianty, zůstane otevřená
      setIsExpanded(true)
    }
  }, [activeVariant, isExpanded])

  // Sledovat, zda byla komponenta otevřená
  useEffect(() => {
    if (isExpanded) {
      wasExpandedRef.current = true
    }
  }, [isExpanded])

  const variants = [
    { id: 'variant1', label: 'Varianta 1' },
    { id: 'variant2', label: 'Varianta 2' },
    { id: 'variant3', label: 'Varianta 3' },
    { id: 'variant4', label: 'Varianta 4' },
    { id: 'variant5', label: 'Varianta 5' }
  ]

  // Výchozí quality settings pokud nejsou zadány
  const defaultQualitySettings = {
    qualityMode: null,
    enhancementPreset: 'natural',
    enableEnhancement: true,
    enableNormalization: true,
    enableDenoiser: true,
    enableCompressor: true,
    enableDeesser: true,
    enableEq: true,
    enableTrim: true
  }

  const quality = qualitySettings || defaultQualitySettings

  const handleChange = (key, value) => {
    // Pro seed použijeme integer, pro ostatní float
    if (key === 'seed') {
      const intValue = value === '' || value === null ? null : parseInt(value)
      if (intValue === null || (!isNaN(intValue) && intValue >= 0)) {
        onChange({ ...settings, [key]: intValue })
      }
    } else {
      const numValue = parseFloat(value)
      if (!isNaN(numValue)) {
        // Validace pro temperature - musí být kladné číslo
        if (key === 'temperature' && numValue <= 0) {
          // Pokud je hodnota 0 nebo menší, nastavíme minimální hodnotu 0.01
          onChange({ ...settings, [key]: 0.01 })
        } else {
          onChange({ ...settings, [key]: numValue })
        }
      }
    }
  }

  return (
    <div className="tts-settings">
      <div className="tts-settings-header" onClick={() => setIsExpanded(!isExpanded)}>
        <h3>⚙️ Nastavení hlasu</h3>
        <span className="toggle-icon">{isExpanded ? '▼' : '▶'}</span>
      </div>

      {isExpanded && (
        <div className="tts-settings-content">
          {/* Záložky pro varianty */}
          <CollapsibleSection
            title="Varianty nastavení"
            icon="📋"
            isExpanded={variantsExpanded}
            onToggle={() => setVariantsExpanded(!variantsExpanded)}
          >
            <div className="variants-tabs">
              {variants.map((variant) => (
                <button
                  key={variant.id}
                  className={`variant-tab ${activeVariant === variant.id ? 'active' : ''}`}
                  onClick={() => onVariantChange && onVariantChange(variant.id)}
                >
                  {variant.label}
                </button>
              ))}
            </div>
          </CollapsibleSection>

          {/* TTS parametry */}
          <CollapsibleSection
            title="TTS parametry"
            icon="🎛️"
            isExpanded={ttsParamsExpanded}
            onToggle={() => setTtsParamsExpanded(!ttsParamsExpanded)}
          >
            <div className="settings-grid">
            {/* Rychlost řeči - skryto, protože degraduje kvalitu zvuku */}
            {/* <div className="setting-item">
              <label htmlFor="speed">
                Rychlost řeči (Speed)
                <span className="setting-value">{settings.speed.toFixed(2)}</span>
              </label>
              <input
                type="range"
                id="speed"
                min="0.5"
                max="2.0"
                step="0.1"
                value={settings.speed}
                onChange={(e) => handleChange('speed', e.target.value)}
              />
              <div className="setting-range">
                <span>0.5x</span>
                <span>1.0x</span>
                <span>2.0x</span>
              </div>
            </div> */}

            {/* Teplota */}
            <div className="setting-item">
              <label htmlFor="temperature">
                Teplota (Temperature)
                <span className="setting-value">{settings.temperature.toFixed(2)}</span>
              </label>
              <input
                type="range"
                id="temperature"
                min="0.01"
                max="1.0"
                step="0.05"
                value={settings.temperature}
                onChange={(e) => handleChange('temperature', e.target.value)}
              />
              <div className="setting-range">
                <span>Konzistentní (0.01)</span>
                <span>Variabilní (1.0)</span>
              </div>
            </div>

            {/* Length Penalty */}
            <div className="setting-item">
              <label htmlFor="lengthPenalty">
                Length Penalty
                <span className="setting-value">{settings.lengthPenalty.toFixed(2)}</span>
              </label>
              <input
                type="range"
                id="lengthPenalty"
                min="0.5"
                max="2.0"
                step="0.1"
                value={settings.lengthPenalty}
                onChange={(e) => handleChange('lengthPenalty', e.target.value)}
              />
              <div className="setting-range">
                <span>Krátké (0.5)</span>
                <span>Dlouhé (2.0)</span>
              </div>
            </div>

            {/* Repetition Penalty */}
            <div className="setting-item">
              <label htmlFor="repetitionPenalty">
                Repetition Penalty
                <span className="setting-value">{settings.repetitionPenalty.toFixed(2)}</span>
              </label>
              <input
                type="range"
                id="repetitionPenalty"
                min="1.0"
                max="5.0"
                step="0.1"
                value={settings.repetitionPenalty}
                onChange={(e) => handleChange('repetitionPenalty', e.target.value)}
              />
              <div className="setting-range">
                <span>Méně opakování (1.0)</span>
                <span>Více opakování (5.0)</span>
              </div>
            </div>

            {/* Top-K */}
            <div className="setting-item">
              <label htmlFor="topK">
                Top-K Sampling
                <span className="setting-value">{settings.topK}</span>
              </label>
              <input
                type="range"
                id="topK"
                min="1"
                max="100"
                step="1"
                value={settings.topK}
                onChange={(e) => handleChange('topK', parseInt(e.target.value))}
              />
              <div className="setting-range">
                <span>1</span>
                <span>50</span>
                <span>100</span>
              </div>
            </div>

            {/* Top-P */}
            <div className="setting-item">
              <label htmlFor="topP">
                Top-P Sampling
                <span className="setting-value">{settings.topP.toFixed(2)}</span>
              </label>
              <input
                type="range"
                id="topP"
                min="0.0"
                max="1.0"
                step="0.05"
                value={settings.topP}
                onChange={(e) => handleChange('topP', e.target.value)}
              />
              <div className="setting-range">
                <span>0.0</span>
                <span>0.85</span>
                <span>1.0</span>
              </div>
            </div>

            {/* Seed */}
            <div className="setting-item">
              <label htmlFor="seed">
                Seed (pro reprodukovatelnost)
                <span className="setting-value">
                  {settings.seed !== null && settings.seed !== undefined ? settings.seed : 'Auto (42)'}
                </span>
              </label>
              <input
                type="number"
                id="seed"
                min="0"
                step="1"
                value={settings.seed !== null && settings.seed !== undefined ? settings.seed : ''}
                onChange={(e) => handleChange('seed', e.target.value)}
                placeholder="Prázdné = Auto (42)"
              />
              <div className="setting-description">
                Seed pro reprodukovatelnost generování. Stejný seed + stejné parametry = stejné audio.
                Prázdné pole použije fixní seed 42.
              </div>
            </div>
            </div>
          </CollapsibleSection>

          {/* Sekce kvality výstupu */}
          <CollapsibleSection
            title="Kvalita výstupu"
            icon="🎵"
            isExpanded={qualityExpanded}
            onToggle={() => setQualityExpanded(!qualityExpanded)}
          >
            <div className="quality-section-content">

            <div className="setting-item">
              <label htmlFor="qualityMode">
                Režim kvality
              </label>
              <select
                id="qualityMode"
                value={quality.qualityMode || ''}
                onChange={(e) => onQualityChange && onQualityChange({
                  ...quality,
                  qualityMode: e.target.value || null
                })}
              >
                <option value="">Vlastní (použít parametry výše)</option>
                <option value="high_quality">Vysoká kvalita</option>
                <option value="natural">Přirozený</option>
                <option value="fast">Rychlý</option>
              </select>
              <div className="setting-description">
                {quality.qualityMode === 'high_quality' && 'Nejlepší kvalita, pomalejší generování'}
                {quality.qualityMode === 'natural' && 'Vyvážená kvalita a rychlost'}
                {quality.qualityMode === 'fast' && 'Rychlé generování, základní kvalita'}
                {!quality.qualityMode && 'Použijte vlastní parametry výše'}
              </div>
            </div>

            <div className="setting-item">
              <label htmlFor="enhancementPreset">
                Audio enhancement preset
              </label>
              <select
                id="enhancementPreset"
                value={quality.enhancementPreset || 'natural'}
                onChange={(e) => onQualityChange && onQualityChange({
                  ...quality,
                  enhancementPreset: e.target.value
                })}
                disabled={!quality.enableEnhancement}
              >
                <option value="high_quality">Vysoká kvalita</option>
                <option value="natural">Přirozený</option>
                <option value="fast">Rychlý</option>
              </select>
            </div>

            <div className="feature-checkbox-item">
              <input
                type="checkbox"
                id="enableEnhancement"
                className="large-checkbox"
                checked={quality.enableEnhancement !== false}
                onChange={(e) => onQualityChange && onQualityChange({
                  ...quality,
                  enableEnhancement: e.target.checked
                })}
              />
              <label htmlFor="enableEnhancement" className="feature-checkbox-text">
                <span className="feature-title">Zapnout audio enhancement</span>
                <span className="feature-description">Post-processing pro vylepšení kvality zvuku</span>
              </label>
            </div>

            {quality.enableEnhancement && (
              <div className="enhancement-features" style={{ marginTop: '15px', marginLeft: '54px' }}>
                <div className="features-grid">
                  <div className="feature-checkbox-item">
                    <input
                      type="checkbox"
                      id="enableNormalization"
                      className="large-checkbox"
                      checked={quality.enableNormalization !== false}
                      onChange={(e) => onQualityChange && onQualityChange({
                        ...quality,
                        enableNormalization: e.target.checked
                      })}
                    />
                    <label htmlFor="enableNormalization" className="feature-checkbox-text">
                      <span className="feature-title">Normalizace</span>
                      <span className="feature-description">Automatická normalizace zvuku na optimální úroveň</span>
                    </label>
                  </div>
                  <div className="feature-checkbox-item">
                    <input
                      type="checkbox"
                      id="enableDenoiser"
                      className="large-checkbox"
                      checked={quality.enableDenoiser !== false}
                      onChange={(e) => onQualityChange && onQualityChange({
                        ...quality,
                        enableDenoiser: e.target.checked
                      })}
                    />
                    <label htmlFor="enableDenoiser" className="feature-checkbox-text">
                      <span className="feature-title">Denoiser</span>
                      <span className="feature-description">Odstranění šumu z audio signálu</span>
                    </label>
                  </div>
                  <div className="feature-checkbox-item">
                    <input
                      type="checkbox"
                      id="enableCompressor"
                      className="large-checkbox"
                      checked={quality.enableCompressor !== false}
                      onChange={(e) => onQualityChange && onQualityChange({
                        ...quality,
                        enableCompressor: e.target.checked
                      })}
                    />
                    <label htmlFor="enableCompressor" className="feature-checkbox-text">
                      <span className="feature-title">Compressor</span>
                      <span className="feature-description">Dynamická komprese pro vyrovnání hlasitosti</span>
                    </label>
                  </div>
                  <div className="feature-checkbox-item">
                    <input
                      type="checkbox"
                      id="enableDeesser"
                      className="large-checkbox"
                      checked={quality.enableDeesser !== false}
                      onChange={(e) => onQualityChange && onQualityChange({
                        ...quality,
                        enableDeesser: e.target.checked
                      })}
                    />
                    <label htmlFor="enableDeesser" className="feature-checkbox-text">
                      <span className="feature-title">De-esser</span>
                      <span className="feature-description">Redukce sykavek a ostrých sykavých zvuků</span>
                    </label>
                  </div>
                  <div className="feature-checkbox-item">
                    <input
                      type="checkbox"
                      id="enableEq"
                      className="large-checkbox"
                      checked={quality.enableEq !== false}
                      onChange={(e) => onQualityChange && onQualityChange({
                        ...quality,
                        enableEq: e.target.checked
                      })}
                    />
                    <label htmlFor="enableEq" className="feature-checkbox-text">
                      <span className="feature-title">Equalizer</span>
                      <span className="feature-description">Úprava frekvenčního spektra pro lepší zvuk</span>
                    </label>
                  </div>
                  <div className="feature-checkbox-item">
                    <input
                      type="checkbox"
                      id="enableTrim"
                      className="large-checkbox"
                      checked={quality.enableTrim !== false}
                      onChange={(e) => onQualityChange && onQualityChange({
                        ...quality,
                        enableTrim: e.target.checked
                      })}
                    />
                    <label htmlFor="enableTrim" className="feature-checkbox-text">
                      <span className="feature-title">Ořez ticha</span>
                      <span className="feature-description">Automatické odstranění ticha na začátku a konci</span>
                    </label>
                  </div>
                </div>
              </div>
            )}
            </div>
          </CollapsibleSection>

          {/* Pokročilé funkce */}
          <CollapsibleSection
            title="Pokročilé funkce"
            icon="⚙️"
            isExpanded={advancedExpanded}
            onToggle={() => setAdvancedExpanded(!advancedExpanded)}
          >
            <div className="quality-section-content">

            <div className="features-grid">
              {/* Multi-pass generování */}
              <div className="feature-checkbox-item">
                <input
                  type="checkbox"
                  id="multiPass"
                  className="large-checkbox"
                  checked={quality.multiPass || false}
                  onChange={(e) => onQualityChange && onQualityChange({
                    ...quality,
                    multiPass: e.target.checked
                  })}
                />
                <label htmlFor="multiPass" className="feature-checkbox-text">
                  <span className="feature-title">Multi-pass generování (více variant)</span>
                  <span className="feature-description">Vygeneruje více variant a umožní výběr nejlepší</span>
                </label>
              </div>

              {quality.multiPass && (
                <div className="setting-item multi-pass-count" style={{ marginTop: '-10px', marginBottom: '20px', marginLeft: '54px' }}>
                  <label htmlFor="multiPassCount">
                    Počet variant
                    <span className="setting-value">{quality.multiPassCount || 3}</span>
                  </label>
                  <input
                    type="range"
                    id="multiPassCount"
                    min="2"
                    max="5"
                    step="1"
                    value={quality.multiPassCount || 3}
                    onChange={(e) => onQualityChange && onQualityChange({
                      ...quality,
                      multiPassCount: parseInt(e.target.value)
                    })}
                  />
                  <div className="setting-range">
                    <span>2</span>
                    <span>3</span>
                    <span>5</span>
                  </div>
                </div>
              )}

              {/* Voice Activity Detection */}
              <div className="feature-checkbox-item">
                <input
                  type="checkbox"
                  id="enableVad"
                  className="large-checkbox"
                  checked={quality.enableVad !== false}
                  onChange={(e) => onQualityChange && onQualityChange({
                    ...quality,
                    enableVad: e.target.checked
                  })}
                />
                <label htmlFor="enableVad" className="feature-checkbox-text">
                  <span className="feature-title">Voice Activity Detection (VAD)</span>
                  <span className="feature-description">Lepší detekce řeči vs. ticho pro přesnější ořez</span>
                </label>
              </div>

              {/* Batch processing */}
              <div className="feature-checkbox-item">
                <input
                  type="checkbox"
                  id="enableBatch"
                  className="large-checkbox"
                  checked={quality.enableBatch !== false}
                  onChange={(e) => onQualityChange && onQualityChange({
                    ...quality,
                    enableBatch: e.target.checked
                  })}
                />
                <label htmlFor="enableBatch" className="feature-checkbox-text">
                  <span className="feature-title">Batch processing (pro dlouhé texty)</span>
                  <span className="feature-description">Automaticky rozdělí dlouhé texty na části a spojí je</span>
                </label>
              </div>

              {/* HiFi-GAN vocoder */}
              <div className="feature-checkbox-item">
                <input
                  type="checkbox"
                  id="useHifigan"
                  className="large-checkbox"
                  checked={quality.useHifigan || false}
                  onChange={(e) => onQualityChange && onQualityChange({
                    ...quality,
                    useHifigan: e.target.checked
                  })}
                />
                <label htmlFor="useHifigan" className="feature-checkbox-text">
                  <span className="feature-title">Použít HiFi-GAN vocoder (vyžaduje model)</span>
                  <span className="feature-description">Pokročilejší vocoder pro lepší kvalitu zvuku (volitelné)</span>
                </label>
              </div>

              {/* Dialect Conversion */}
              <div className="feature-checkbox-item">
                <input
                  type="checkbox"
                  id="enableDialectConversion"
                  className="large-checkbox"
                  checked={quality.enableDialectConversion || false}
                  onChange={(e) => onQualityChange && onQualityChange({
                    ...quality,
                    enableDialectConversion: e.target.checked,
                    // Pokud se vypne, vymaž dialect_code
                    dialectCode: e.target.checked ? (quality.dialectCode || 'moravske') : null
                  })}
                />
                <label htmlFor="enableDialectConversion" className="feature-checkbox-text">
                  <span className="feature-title">Převod na nářečí</span>
                  <span className="feature-description">Převede text ze standardní češtiny na zvolené nářečí před syntézou</span>
                </label>
              </div>

              {quality.enableDialectConversion && (
                <div className="dialect-settings" style={{ marginTop: '15px', marginLeft: '54px', padding: '15px', backgroundColor: 'rgba(0, 0, 0, 0.05)', borderRadius: '8px', border: '1px solid rgba(0, 0, 0, 0.1)' }}>
                  <h5 style={{ marginTop: '0', marginBottom: '15px', fontSize: '14px', fontWeight: '600' }}>🌍 Nastavení nářečí</h5>

                  <div className="setting-item" style={{ marginBottom: '15px' }}>
                    <label htmlFor="dialectCode">
                      Vyberte nářečí
                    </label>
                    <select
                      id="dialectCode"
                      value={quality.dialectCode || 'moravske'}
                      onChange={(e) => onQualityChange && onQualityChange({
                        ...quality,
                        dialectCode: e.target.value
                      })}
                    >
                      <option value="moravske">Moravské</option>
                      <option value="hanacke">Hanácké</option>
                      <option value="slezske">Slezské</option>
                      <option value="chodske">Chodské</option>
                      <option value="brnenske">Brněnské (hantec)</option>
                    </select>
                    <div className="setting-description" style={{ fontSize: '12px', marginTop: '5px' }}>
                      Vyberte nářečí, na které se má text převést
                    </div>
                  </div>

                  <div className="setting-item" style={{ marginBottom: '15px' }}>
                    <label htmlFor="dialectIntensity">
                      Intenzita převodu
                      <span className="setting-value">{(quality.dialectIntensity || 1.0).toFixed(2)}</span>
                    </label>
                    <input
                      type="range"
                      id="dialectIntensity"
                      min="0.0"
                      max="1.0"
                      step="0.1"
                      value={quality.dialectIntensity || 1.0}
                      onChange={(e) => onQualityChange && onQualityChange({
                        ...quality,
                        dialectIntensity: parseFloat(e.target.value)
                      })}
                    />
                    <div className="setting-range">
                      <span>0% (žádný převod)</span>
                      <span>50%</span>
                      <span>100% (plný převod)</span>
                    </div>
                    <div className="setting-description" style={{ fontSize: '12px', marginTop: '5px' }}>
                      Jak silně se má text převést na nářečí (1.0 = plný převod)
                    </div>
                  </div>
                </div>
              )}

              {/* HiFi-GAN pokročilá nastavení */}
              {quality.useHifigan && (
                <div className="hifigan-settings" style={{ marginTop: '15px', marginLeft: '54px', padding: '15px', backgroundColor: 'rgba(0, 0, 0, 0.05)', borderRadius: '8px', border: '1px solid rgba(0, 0, 0, 0.1)' }}>
                  <h5 style={{ marginTop: '0', marginBottom: '15px', fontSize: '14px', fontWeight: '600' }}>⚙️ HiFi-GAN nastavení</h5>

                  {/* Intenzita refinement */}
                  <div className="setting-item" style={{ marginBottom: '15px' }}>
                    <label htmlFor="hifiganRefinementIntensity">
                      Intenzita refinement
                      <span className="setting-value">{(quality.hifiganRefinementIntensity || 1.0).toFixed(2)}</span>
                    </label>
                    <input
                      type="range"
                      id="hifiganRefinementIntensity"
                      min="0.0"
                      max="1.0"
                      step="0.05"
                      value={quality.hifiganRefinementIntensity || 1.0}
                      onChange={(e) => onQualityChange && onQualityChange({
                        ...quality,
                        hifiganRefinementIntensity: parseFloat(e.target.value)
                      })}
                    />
                    <div className="setting-range">
                      <span>0% (pouze originál)</span>
                      <span>50%</span>
                      <span>100% (plný refinement)</span>
                    </div>
                    <div className="setting-description" style={{ fontSize: '12px', marginTop: '5px' }}>
                      {quality.hifiganRefinementIntensity === 1.0
                        ? 'Použije se pouze HiFi-GAN výstup'
                        : quality.hifiganRefinementIntensity === 0.0
                        ? 'Použije se pouze originální audio'
                        : `Blend: ${(quality.hifiganRefinementIntensity * 100).toFixed(0)}% HiFi-GAN + ${((1 - quality.hifiganRefinementIntensity) * 100).toFixed(0)}% originál`}
                    </div>
                  </div>

                  {/* Normalizace výstupu */}
                  <div className="feature-checkbox-item" style={{ marginBottom: '15px' }}>
                    <input
                      type="checkbox"
                      id="hifiganNormalizeOutput"
                      className="large-checkbox"
                      checked={quality.hifiganNormalizeOutput !== false}
                      onChange={(e) => onQualityChange && onQualityChange({
                        ...quality,
                        hifiganNormalizeOutput: e.target.checked
                      })}
                    />
                    <label htmlFor="hifiganNormalizeOutput" className="feature-checkbox-text">
                      <span className="feature-title">Normalizovat výstup HiFi-GAN</span>
                      <span className="feature-description">Automaticky normalizuje výstupní audio na optimální úroveň</span>
                    </label>
                  </div>

                  {/* Normalize gain (pouze pokud je normalizace zapnutá) */}
                  {quality.hifiganNormalizeOutput && (
                    <div className="setting-item" style={{ marginBottom: '15px' }}>
                      <label htmlFor="hifiganNormalizeGain">
                        Normalizační gain
                        <span className="setting-value">{(quality.hifiganNormalizeGain || 0.95).toFixed(2)}</span>
                      </label>
                      <input
                        type="range"
                        id="hifiganNormalizeGain"
                        min="0.5"
                        max="1.0"
                        step="0.05"
                        value={quality.hifiganNormalizeGain || 0.95}
                        onChange={(e) => onQualityChange && onQualityChange({
                          ...quality,
                          hifiganNormalizeGain: parseFloat(e.target.value)
                        })}
                      />
                      <div className="setting-range">
                        <span>0.5</span>
                        <span>0.95</span>
                        <span>1.0</span>
                      </div>
                      <div className="setting-description" style={{ fontSize: '12px', marginTop: '5px' }}>
                        Nižší hodnota = více headroom (bezpečnější), vyšší = hlasitější
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
            </div>
          </CollapsibleSection>

          <div className="settings-actions">
            <button className="btn-reset" onClick={onReset}>
              🔄 Obnovit výchozí hodnoty pro {variants.find(v => v.id === activeVariant)?.label || 'tuto variantu'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default TTSSettings

