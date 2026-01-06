import React, { useState, useEffect, useRef } from 'react'
import { useSectionColor } from '../contexts/SectionColorContext'
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
  seed: null,
  cfgStrength: 2.0,
  swaySamplingCoef: -1.0,
  nfeStep: 32
}

function TTSSettings({ settings, onChange, onReset, qualitySettings, onQualityChange, activeVariant, onVariantChange, engine = 'xtts', onCopySettings, onPasteSettings }) {
  const [isExpanded, setIsExpanded] = useState(true) // Hlavní panel otevřený
  const [ttsParamsExpanded, setTtsParamsExpanded] = useState(true)
  const [qualityExpanded, setQualityExpanded] = useState(true)
  const [advancedExpanded, setAdvancedExpanded] = useState(false)
  const [copyNotification, setCopyNotification] = useState(null)

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
    whisperIntensity: 1.0,
    targetHeadroomDb: -15.0
  }

  const quality = qualitySettings || defaultQualitySettings

  // Automaticky zapnout enableEnhancement a enableTrim
  useEffect(() => {
    if (qualitySettings && onQualityChange) {
      const needsUpdate =
        qualitySettings.enableEnhancement === false ||
        qualitySettings.enableTrim === false ||
        qualitySettings.enableEnhancement === undefined ||
        qualitySettings.enableTrim === undefined

      if (needsUpdate) {
        onQualityChange({
          ...qualitySettings,
          enableEnhancement: true,
          enableTrim: true
        })
      }
    }
  }, [qualitySettings, onQualityChange])

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

  const { color, rgb } = useSectionColor()
  const style = {
    '--section-color': color,
    '--section-color-rgb': rgb
  }

  return (
    <div className="tts-settings" style={style}>
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
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '10px'
            }}>
              <div style={{ fontSize: '11px', fontWeight: '600', color: 'rgba(255, 255, 255, 0.4)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Slot nastavení (Profil)
              </div>
              <div style={{ display: 'flex', gap: '6px' }}>
                {/* Copy Settings Button */}
                <button
                  onClick={() => {
                    console.log('🔵 KLIK NA KOPÍROVAT - tlačítko funguje!')
                    if (onCopySettings) {
                      console.log('🔵 Volám onCopySettings...')
                      onCopySettings()
                      setCopyNotification('copied')
                      setTimeout(() => setCopyNotification(null), 3000)
                      console.log('🔵 Notifikace nastavena na: copied')
                    } else {
                      console.error('❌ onCopySettings není definováno!')
                      alert('CHYBA: Funkce kopírování není připojena!')
                    }
                  }}
                  title="Kopírovat nastavení z tohoto profilu"
                  style={{
                    padding: '4px 8px',
                    fontSize: '10px',
                    fontWeight: '500',
                    background: 'rgba(33, 150, 243, 0.15)',
                    border: '1px solid rgba(33, 150, 243, 0.3)',
                    borderRadius: '4px',
                    color: '#2196f3',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'rgba(33, 150, 243, 0.25)'
                    e.currentTarget.style.borderColor = 'rgba(33, 150, 243, 0.5)'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'rgba(33, 150, 243, 0.15)'
                    e.currentTarget.style.borderColor = 'rgba(33, 150, 243, 0.3)'
                  }}
                >
                  <span style={{ fontSize: '11px' }}>📋</span>
                  <span>Kopírovat</span>
                </button>

                {/* Paste Settings Button */}
                <button
                  onClick={() => {
                    console.log('🟢 KLIK NA VLOŽIT - tlačítko funguje!')
                    if (onPasteSettings) {
                      console.log('🟢 Volám onPasteSettings...')
                      const success = onPasteSettings()
                      console.log('🟢 Výsledek vložení:', success)
                      if (success) {
                        setCopyNotification('pasted')
                        setTimeout(() => setCopyNotification(null), 3000)
                        console.log('🟢 Notifikace nastavena na: pasted')
                      } else {
                        console.warn('⚠️ Vložení vrátilo false - možná nejsou data')
                        alert('VAROVÁNÍ: Nejsou žádná zkopírovaná data!\n\nNejdřív klikněte na "Kopírovat".')
                      }
                    } else {
                      console.error('❌ onPasteSettings není definováno!')
                      alert('CHYBA: Funkce vkládání není připojena!')
                    }
                  }}
                  title="Vložit nastavení do tohoto profilu"
                  style={{
                    padding: '4px 8px',
                    fontSize: '10px',
                    fontWeight: '500',
                    background: 'rgba(76, 175, 80, 0.15)',
                    border: '1px solid rgba(76, 175, 80, 0.3)',
                    borderRadius: '4px',
                    color: '#4caf50',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'rgba(76, 175, 80, 0.25)'
                    e.currentTarget.style.borderColor = 'rgba(76, 175, 80, 0.5)'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'rgba(76, 175, 80, 0.15)'
                    e.currentTarget.style.borderColor = 'rgba(76, 175, 80, 0.3)'
                  }}
                >
                  <span style={{ fontSize: '11px' }}>📥</span>
                  <span>Vložit</span>
                </button>
              </div>
            </div>

            {/* Notification banner */}
            {copyNotification && (
              <div style={{
                marginBottom: '12px',
                padding: '10px 14px',
                borderRadius: '6px',
                fontSize: '13px',
                fontWeight: '600',
                background: copyNotification === 'copied' ? 'rgba(33, 150, 243, 0.25)' : 'rgba(76, 175, 80, 0.25)',
                border: `2px solid ${copyNotification === 'copied' ? 'rgba(33, 150, 243, 0.6)' : 'rgba(76, 175, 80, 0.6)'}`,
                color: copyNotification === 'copied' ? '#2196f3' : '#4caf50',
                animation: 'slideDown 0.3s ease-out',
                boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
                textAlign: 'center'
              }}>
                {copyNotification === 'copied' ? '✓ ZKOPÍROVÁNO!' : '✓ VLOŽENO!'}
                <div style={{ fontSize: '11px', marginTop: '4px', opacity: 0.9 }}>
                  {copyNotification === 'copied' ? 'Nastavení uloženo do schránky' : 'Nastavení aplikováno na tento profil'}
                </div>
              </div>
            )}

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
              tooltip="Určuje rychlost generované řeči. Vyšší hodnota = rychlejší mluvení. Rozsah 0.5x až 1.5x."
            />

            {isF5 ? (
              <>
                {/* NFE Steps */}
                <SliderRow
                  label="Počet kroků (NFE Steps)"
                  value={settings.nfeStep !== undefined ? settings.nfeStep : (isSlovak ? 32 : 32)}
                  min={16}
                  max={128}
                  step={4}
                  onChange={(v) => handleChange('nfeStep', v)}
                  onReset={() => handleChange('nfeStep', DEFAULT_TTS_SETTINGS.nfeStep)}
                  formatValue={(v) => v}
                  showTicks={true}
                  tooltip="Počet kroků pro odebrání šumu (diffusion). Více kroků = vyšší kvalita, ale pomalejší generování. Doporučeno 32-64."
                />

                {/* CFG Strength */}
                <SliderRow
                  label="Síla navádění (CFG Strength)"
                  value={settings.cfgStrength !== undefined ? settings.cfgStrength : 2.0}
                  min={0.1}
                  max={5.0}
                  step={0.1}
                  onChange={(v) => handleChange('cfgStrength', v)}
                  onReset={() => handleChange('cfgStrength', DEFAULT_TTS_SETTINGS.cfgStrength)}
                  formatValue={(v) => v.toFixed(1)}
                  showTicks={true}
                  tooltip="Classifier-Free Guidance. Vyšší hodnota více dbá na podobnost s textem a referencí, ale příliš vysoká může sytit zvuk."
                />

                {/* Sway Sampling Coefficient */}
                <SliderRow
                  label="Sway Sampling Coef"
                  value={settings.swaySamplingCoef !== undefined ? settings.swaySamplingCoef : -1.0}
                  min={-1.0}
                  max={1.0}
                  step={0.1}
                  onChange={(v) => handleChange('swaySamplingCoef', v)}
                  onReset={() => handleChange('swaySamplingCoef', DEFAULT_TTS_SETTINGS.swaySamplingCoef)}
                  formatValue={(v) => v.toFixed(1)}
                  showTicks={true}
                  tooltip="Ovlivňuje dynamiku vzorkování. Záporné hodnoty (-1.0) jsou standard pro F5-TTS a často znějí nejlépe."
                />
              </>
            ) : (
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
                  tooltip="Ovlivňuje náhodnost a kreativitu hlasu. Vyšší = emotivnější, nižší = stabilnější, robotičtější."
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
                  tooltip="Penalizace délky. Ovlivňuje tendenci modelu generovat delší nebo kratší pauzy a protažení slov."
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
                  tooltip="Penalizace opakování. Zabraňuje modelu 'zaseknout se' v nekonečné smyčce u stejných zvuků."
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
                  tooltip="Omezuje výběr dalšího slova pouze na K nejpravděpodobnějších možností."
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
                  tooltip="Nukleární vzorkování. Vybírá z nejmenší množiny slov, jejichž celková pravděpodobnost přesahuje P."
                />
              </>
            )}

            {/* Seed - vždy zobrazit */}
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

            {/* Audio enhancement UI blok je schovaný - hodnoty se automaticky nastavují */}
            {/* enableEnhancement a enableTrim jsou automaticky zapnuté */}
            {/* enhancementPreset je automaticky nastavený na 'natural' */}

            {/* Headroom nastavení */}
            <div style={{ marginTop: '20px' }}>
              <SliderRow
                label="Výstupní headroom"
                value={quality.targetHeadroomDb !== undefined ? quality.targetHeadroomDb : -15.0}
                min={-128.0}
                max={0.0}
                step={1.0}
                onChange={(v) => onQualityChange && onQualityChange({
                  ...quality,
                  targetHeadroomDb: v
                })}
                onReset={() => onQualityChange && onQualityChange({
                  ...quality,
                  targetHeadroomDb: -15.0
                })}
                formatValue={(v) => v.toFixed(1)}
                valueUnit=" dB"
                showTicks={false}
              />
              <div className="setting-description" style={{ fontSize: '12px', marginTop: '5px' }}>
                Nižší hodnota = tišší výstup (méně "přebuzelý"), vyšší = hlasitější. Doporučené: -15.0 dB
              </div>
            </div>
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

