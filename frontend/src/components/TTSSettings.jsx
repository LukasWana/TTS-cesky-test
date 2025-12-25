import React, { useState, useEffect, useRef } from 'react'
import './TTSSettings.css'
import Section from './ui/Section'
import SliderRow from './ui/SliderRow'
import SelectRow from './ui/SelectRow'
import SegmentedControl from './ui/SegmentedControl'

// Výchozí hodnoty pro reset
const DEFAULT_TTS_SETTINGS = {
  speed: 1.0,
  temperature: 0.7,
  lengthPenalty: 1.0,
  repetitionPenalty: 2.0,
  topK: 50,
  topP: 0.85,
  seed: null
}

function TTSSettings({ settings, onChange, onReset, qualitySettings, onQualityChange, activeVariant, onVariantChange, engine = 'xtts' }) {
  const [isExpanded, setIsExpanded] = useState(true) // Hlavní panel otevřený
  const [ttsParamsExpanded, setTtsParamsExpanded] = useState(true)
  const [qualityExpanded, setQualityExpanded] = useState(true)
  const [advancedExpanded, setAdvancedExpanded] = useState(false)

  const isF5 = engine === 'f5' || engine === 'f5-slovak'
  const isSlovak = engine === 'f5-slovak'

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
    enableTrim: true,
    whisperIntensity: 1.0
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
      <Section
        title="Nastavení hlasu"
        icon="settings"
        isExpanded={isExpanded}
        onToggle={() => setIsExpanded(!isExpanded)}
      >
        <Section
          title="TTS parametry"
          icon="grid"
          isExpanded={ttsParamsExpanded}
          onToggle={() => setTtsParamsExpanded(!ttsParamsExpanded)}
          onReset={() => {
            onChange({ ...settings, ...DEFAULT_TTS_SETTINGS })
          }}
        >
          {/* Záložky pro profily přímo v TTS parametrech */}
          <div className="variants-tabs-in-params" style={{ marginBottom: '20px', paddingBottom: '15px', borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>
            <div style={{ marginBottom: '10px', fontSize: '11px', fontWeight: '600', color: 'rgba(255, 255, 255, 0.4)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Slot nastavení (Profil)
            </div>
            <SegmentedControl
              options={variants.map(v => ({ value: v.id, label: v.label.replace('Varianta ', 'P') }))}
              value={activeVariant}
              onChange={(val) => onVariantChange && onVariantChange(val)}
              className="variants-segmented-control"
            />
          </div>

          <div className="settings-grid">
            {/* Rychlost řeči - vždy zobrazit */}
            <SliderRow
              label="Rychlost řeči (Tempo)"
              value={settings.speed}
              min={0.5}
              max={1.5}
              step={0.05}
              onChange={(v) => handleChange('speed', v)}
              onReset={() => handleChange('speed', DEFAULT_TTS_SETTINGS.speed)}
              formatValue={(v) => `${v.toFixed(2)}x`}
              showTicks={true}
            />

            {!isF5 && (
              <>
                {/* Teplota */}
                <SliderRow
                  label="Teplota (Temperature)"
                  value={settings.temperature}
                  min={0.01}
                  max={1.0}
                  step={0.05}
                  onChange={(v) => handleChange('temperature', v)}
                  onReset={() => handleChange('temperature', DEFAULT_TTS_SETTINGS.temperature)}
                  formatValue={(v) => v.toFixed(2)}
                  showTicks={true}
                />

                {/* Length Penalty */}
                <SliderRow
                  label="Length Penalty"
                  value={settings.lengthPenalty}
                  min={0.5}
                  max={2.0}
                  step={0.1}
                  onChange={(v) => handleChange('lengthPenalty', v)}
                  onReset={() => handleChange('lengthPenalty', DEFAULT_TTS_SETTINGS.lengthPenalty)}
                  formatValue={(v) => v.toFixed(2)}
                  showTicks={true}
                />

                {/* Repetition Penalty */}
                <SliderRow
                  label="Repetition Penalty"
                  value={settings.repetitionPenalty}
                  min={1.0}
                  max={5.0}
                  step={0.1}
                  onChange={(v) => handleChange('repetitionPenalty', v)}
                  onReset={() => handleChange('repetitionPenalty', DEFAULT_TTS_SETTINGS.repetitionPenalty)}
                  formatValue={(v) => v.toFixed(2)}
                  showTicks={true}
                />

                {/* Top-K */}
                <SliderRow
                  label="Top-K Sampling"
                  value={settings.topK}
                  min={1}
                  max={100}
                  step={1}
                  onChange={(v) => handleChange('topK', v)}
                  onReset={() => handleChange('topK', DEFAULT_TTS_SETTINGS.topK)}
                  formatValue={(v) => v}
                  showTicks={true}
                />

                {/* Top-P */}
                <SliderRow
                  label="Top-P Sampling"
                  value={settings.topP}
                  min={0.0}
                  max={1.0}
                  step={0.05}
                  onChange={(v) => handleChange('topP', v)}
                  onReset={() => handleChange('topP', DEFAULT_TTS_SETTINGS.topP)}
                  formatValue={(v) => v.toFixed(2)}
                  showTicks={true}
                />

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
              </>
            )}
          </div>
        </Section>

        <Section
          title="Kvalita výstupu"
          icon="music"
          isExpanded={qualityExpanded}
          onToggle={() => setQualityExpanded(!qualityExpanded)}
        >
          <div className="quality-section-content">
            <SelectRow
              label="Režim kvality"
              icon="star"
              value={quality.qualityMode || ''}
              onChange={(val) => onQualityChange && onQualityChange({
                ...quality,
                qualityMode: val || null
              })}
              options={[
                { value: '', label: 'Vlastní (použít parametry výše)' },
                { value: 'high_quality', label: 'Vysoká kvalita' },
                { value: 'natural', label: 'Přirozený' },
                { value: 'fast', label: 'Rychlý' },
                { value: 'meditative', label: 'Meditativní' },
                { value: 'whisper', label: 'Šeptavý' }
              ]}
            />

            <div className="setting-description" style={{ marginTop: '-10px', marginBottom: '10px' }}>
              {quality.qualityMode === 'high_quality' && 'Nejlepší kvalita, pomalejší generování'}
              {quality.qualityMode === 'natural' && 'Vyvážená kvalita a rychlost'}
              {quality.qualityMode === 'fast' && 'Rychlé generování, základní kvalita'}
              {quality.qualityMode === 'meditative' && 'Klidný, meditativní hlas s pomalejší řečí (speed: 0.75x)'}
              {quality.qualityMode === 'whisper' && 'Šeptavý hlas s whisper efektem (speed: 0.65x)'}
              {!quality.qualityMode && 'Použijte vlastní parametry výše'}
            </div>

            {/* Whisper intensity slider (pouze pro whisper režim) */}
            {quality.qualityMode === 'whisper' && (
              <SliderRow
                label="Intenzita whisper efektu"
                value={quality.whisperIntensity !== undefined ? quality.whisperIntensity : 1.0}
                min={0.0}
                max={1.0}
                step={0.05}
                onChange={(v) => onQualityChange && onQualityChange({
                  ...quality,
                  whisperIntensity: v
                })}
                onReset={() => onQualityChange && onQualityChange({
                  ...quality,
                  whisperIntensity: 1.0
                })}
                formatValue={(v) => v.toFixed(2)}
                showTicks={true}
              />
            )}

            <SelectRow
              label="Audio enhancement preset"
              icon="wand"
              value={quality.enhancementPreset || 'natural'}
              onChange={(val) => onQualityChange && onQualityChange({
                ...quality,
                enhancementPreset: val
              })}
              options={[
                { value: 'high_quality', label: 'Vysoká kvalita' },
                { value: 'natural', label: 'Přirozený' },
                { value: 'fast', label: 'Rychlý' }
              ]}
            />

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
        </Section>

        {/* Pokročilé funkce */}
        <Section
          title="Pokročilé funkce"
          icon="settings"
          isExpanded={advancedExpanded}
          onToggle={() => setAdvancedExpanded(!advancedExpanded)}
        >
            <div className="quality-section-content">

            <div className="features-grid">
              {/* Multi-pass generování - schovat pro F5 */}
              {!isF5 && (
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
              )}

              {!isF5 && quality.multiPass && (
                <div style={{ marginTop: '-10px', marginBottom: '20px', marginLeft: '54px' }}>
                  <SliderRow
                    label="Počet variant"
                    value={quality.multiPassCount || 3}
                    min={2}
                    max={5}
                    step={1}
                    onChange={(v) => onQualityChange && onQualityChange({
                      ...quality,
                      multiPassCount: v
                    })}
                    onReset={() => onQualityChange && onQualityChange({
                      ...quality,
                      multiPassCount: 3
                    })}
                    formatValue={(v) => v}
                    showTicks={true}
                  />
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

              {/* Batch processing - schovat pro F5 */}
              {!isF5 && (
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
              )}

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

              {/* Dialect Conversion - schovat pro F5/Slovensko */}
              {!isF5 && (
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
              )}

              {!isF5 && quality.enableDialectConversion && (
                <div className="dialect-settings" style={{ marginTop: '15px', marginLeft: '54px' }}>
                  <h5 style={{ marginTop: '0', marginBottom: '15px', fontSize: '14px', fontWeight: '600' }}>Nastavení nářečí</h5>

                  <SelectRow
                    label="Vyberte nářečí"
                    icon="globe"
                    value={quality.dialectCode || 'moravske'}
                    onChange={(val) => onQualityChange && onQualityChange({
                      ...quality,
                      dialectCode: val
                    })}
                    options={[
                      { value: 'moravske', label: 'Moravské' },
                      { value: 'hanacke', label: 'Hanácké' },
                      { value: 'slezske', label: 'Slezské' },
                      { value: 'chodske', label: 'Chodské' },
                      { value: 'brnenske', label: 'Brněnské (hantec)' }
                    ]}
                  />

                  <div style={{ marginBottom: '15px' }}>
                    <SliderRow
                      label="Intenzita převodu"
                      value={quality.dialectIntensity || 1.0}
                      min={0.0}
                      max={1.0}
                      step={0.1}
                      onChange={(v) => onQualityChange && onQualityChange({
                        ...quality,
                        dialectIntensity: v
                      })}
                      onReset={() => onQualityChange && onQualityChange({
                        ...quality,
                        dialectIntensity: 1.0
                      })}
                      formatValue={(v) => (v * 100).toFixed(0)}
                      valueUnit="%"
                      showTicks={true}
                    />
                    <div className="setting-description" style={{ fontSize: '12px', marginTop: '5px' }}>
                      Jak silně se má text převést na nářečí (1.0 = plný převod)
                    </div>
                  </div>
                </div>
              )}

              {/* HiFi-GAN pokročilá nastavení */}
              {quality.useHifigan && (
                <div className="hifigan-settings" style={{ marginTop: '15px', marginLeft: '54px' }}>
                  <h5 style={{ marginTop: '0', marginBottom: '15px', fontSize: '14px', fontWeight: '600' }}>⚙️ HiFi-GAN nastavení</h5>

                  {/* Intenzita refinement */}
                  <div style={{ marginBottom: '15px' }}>
                    <SliderRow
                      label="Intenzita refinement"
                      value={quality.hifiganRefinementIntensity || 1.0}
                      min={0.0}
                      max={1.0}
                      step={0.05}
                      onChange={(v) => onQualityChange && onQualityChange({
                        ...quality,
                        hifiganRefinementIntensity: v
                      })}
                      onReset={() => onQualityChange && onQualityChange({
                        ...quality,
                        hifiganRefinementIntensity: 1.0
                      })}
                      formatValue={(v) => (v * 100).toFixed(0)}
                      valueUnit="%"
                      showTicks={true}
                    />
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
                    <div style={{ marginBottom: '15px' }}>
                      <SliderRow
                        label="Normalizační gain"
                        value={quality.hifiganNormalizeGain || 0.95}
                        min={0.5}
                        max={1.0}
                        step={0.05}
                        onChange={(v) => onQualityChange && onQualityChange({
                          ...quality,
                          hifiganNormalizeGain: v
                        })}
                        onReset={() => onQualityChange && onQualityChange({
                          ...quality,
                          hifiganNormalizeGain: 0.95
                        })}
                        formatValue={(v) => v.toFixed(2)}
                        showTicks={true}
                      />
                      <div className="setting-description" style={{ fontSize: '12px', marginTop: '5px' }}>
                        Nižší hodnota = více headroom (bezpečnější), vyšší = hlasitější
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
            </div>
        </Section>

        {/* Spodní reset tlačítko schováno na žádost uživatele */}
        {/*
        <div className="settings-actions">
          <button className="btn-reset" onClick={onReset}>
            🔄 Obnovit výchozí hodnoty pro {variants.find(v => v.id === activeVariant)?.label || 'tuto variantu'}
          </button>
        </div>
        */}
      </Section>
    </div>
  )
}

export default TTSSettings

