import React, { useState, useEffect, useRef } from 'react'
import './TTSSettings.css'

function TTSSettings({ settings, onChange, onReset, qualitySettings, onQualityChange, activeVariant, onVariantChange }) {
  const [isExpanded, setIsExpanded] = useState(false)
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
        onChange({ ...settings, [key]: numValue })
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
          <div className="variants-section">
            <h4>Varianty nastavení:</h4>
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
          </div>

          <div className="settings-grid">
            {/* Rychlost řeči */}
            <div className="setting-item">
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
            </div>

            {/* Teplota */}
            <div className="setting-item">
              <label htmlFor="temperature">
                Teplota (Temperature)
                <span className="setting-value">{settings.temperature.toFixed(2)}</span>
              </label>
              <input
                type="range"
                id="temperature"
                min="0.0"
                max="1.0"
                step="0.05"
                value={settings.temperature}
                onChange={(e) => handleChange('temperature', e.target.value)}
              />
              <div className="setting-range">
                <span>Konzistentní (0.0)</span>
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

          {/* Sekce kvality výstupu */}
          <div className="quality-section">
            <h4>Kvalita výstupu</h4>

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

            <div className="setting-item">
              <label htmlFor="enableEnhancement">
                <input
                  type="checkbox"
                  id="enableEnhancement"
                  checked={quality.enableEnhancement !== false}
                  onChange={(e) => onQualityChange && onQualityChange({
                    ...quality,
                    enableEnhancement: e.target.checked
                  })}
                />
                Zapnout audio enhancement
              </label>
              <div className="setting-description">
                Post-processing pro vylepšení kvality zvuku
              </div>
            </div>

            {quality.enableEnhancement && (
              <div className="enhancement-features" style={{ marginTop: '15px', paddingLeft: '20px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div className="feature-checkbox-item small">
                  <input
                    type="checkbox"
                    id="enableNormalization"
                    checked={quality.enableNormalization !== false}
                    onChange={(e) => onQualityChange && onQualityChange({
                      ...quality,
                      enableNormalization: e.target.checked
                    })}
                  />
                  <label htmlFor="enableNormalization">Normalizace</label>
                </div>
                <div className="feature-checkbox-item small">
                  <input
                    type="checkbox"
                    id="enableDenoiser"
                    checked={quality.enableDenoiser !== false}
                    onChange={(e) => onQualityChange && onQualityChange({
                      ...quality,
                      enableDenoiser: e.target.checked
                    })}
                  />
                  <label htmlFor="enableDenoiser">Denoiser</label>
                </div>
                <div className="feature-checkbox-item small">
                  <input
                    type="checkbox"
                    id="enableCompressor"
                    checked={quality.enableCompressor !== false}
                    onChange={(e) => onQualityChange && onQualityChange({
                      ...quality,
                      enableCompressor: e.target.checked
                    })}
                  />
                  <label htmlFor="enableCompressor">Compressor</label>
                </div>
                <div className="feature-checkbox-item small">
                  <input
                    type="checkbox"
                    id="enableDeesser"
                    checked={quality.enableDeesser !== false}
                    onChange={(e) => onQualityChange && onQualityChange({
                      ...quality,
                      enableDeesser: e.target.checked
                    })}
                  />
                  <label htmlFor="enableDeesser">De-esser</label>
                </div>
                <div className="feature-checkbox-item small">
                  <input
                    type="checkbox"
                    id="enableEq"
                    checked={quality.enableEq !== false}
                    onChange={(e) => onQualityChange && onQualityChange({
                      ...quality,
                      enableEq: e.target.checked
                    })}
                  />
                  <label htmlFor="enableEq">Equalizer</label>
                </div>
                <div className="feature-checkbox-item small">
                  <input
                    type="checkbox"
                    id="enableTrim"
                    checked={quality.enableTrim !== false}
                    onChange={(e) => onQualityChange && onQualityChange({
                      ...quality,
                      enableTrim: e.target.checked
                    })}
                  />
                  <label htmlFor="enableTrim">Ořez ticha</label>
                </div>
              </div>
            )}
          </div>

          {/* Pokročilé funkce */}
          <div className="quality-section">
            <h4>Pokročilé funkce</h4>

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
            </div>
          </div>

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

