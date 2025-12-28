import React, { useEffect, useRef, useState } from 'react'
import { useSectionColor } from '../contexts/SectionColorContext'
import './Bark.css'
import LoadingSpinner from './LoadingSpinner'
import AudioPlayer from './AudioPlayer'
import Section from './ui/Section'
import SliderRow from './ui/SliderRow'
import SelectRow from './ui/SelectRow'
import { generateBark, getBarkProgress, subscribeToBarkProgress } from '../services/api'

function ensureBracketedBarkPresetPrompt(raw) {
  const s = (raw ?? '').trim()
  if (!s) return ''

  // Pokud prompt začíná jedním tokenem [..] a za ním je "holý" text,
  // obal tento zbytek do dalších hranatých závorek: "[music] text" -> "[music] [text]".
  const m = s.match(/^(\[[^\]]+\])\s*(.+)$/)
  if (!m) return s

  const firstToken = m[1]
  const rest = (m[2] ?? '').trim()
  if (!rest) return firstToken
  if (rest.startsWith('[')) return `${firstToken} ${rest}`

  return `${firstToken} [${rest}]`
}

function Bark({ prompt: promptProp, setPrompt: setPromptProp }) {
  const { color, rgb } = useSectionColor()
  const style = {
    '--section-color': color,
    '--section-color-rgb': rgb
  }

  const [internalPrompt, setInternalPrompt] = useState(() =>
    ensureBracketedBarkPresetPrompt('[music] calm meditative ambient music, soft pads, slow evolving, no drums, no vocals, peaceful and relaxing')
  )

  // Synchronizace s propsem (pro obnovu z historie)
  const prompt = promptProp !== undefined ? promptProp : internalPrompt
  const setPrompt = setPromptProp !== undefined ? setPromptProp : setInternalPrompt
  const [temperature, setTemperature] = useState(0.7)
  const [seed, setSeed] = useState('')
  const [duration, setDuration] = useState(14) // Výchozí délka (Bark generuje ~14s)
  const [modelSize, setModelSize] = useState('small') // small|large
  const [mode, setMode] = useState('auto') // auto|full|mixed|small
  const [offloadCpu, setOffloadCpu] = useState(false)
  const [presetCategory, setPresetCategory] = useState('meditation')
  const [preset, setPreset] = useState('med_calm')

  // Stavy pro rozbalení sekcí
  const [mainExpanded, setMainExpanded] = useState(true)
  const [presetsExpanded, setPresetsExpanded] = useState(true)

  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState(null)
  const [error, setError] = useState(null)
  const [audioUrl, setAudioUrl] = useState(null)

  const progressEventSourceRef = useRef(null)
  const progressPollIntervalRef = useRef(null)
  const progressStoppedRef = useRef(false)

  useEffect(() => {
    return () => {
      if (progressEventSourceRef.current) {
        progressEventSourceRef.current.close()
        progressEventSourceRef.current = null
      }
      if (progressPollIntervalRef.current) {
        clearInterval(progressPollIntervalRef.current)
        progressPollIntervalRef.current = null
      }
      progressStoppedRef.current = true
    }
  }, [])

  const handleGenerate = async () => {
    if (!prompt.trim()) {
      setError('Zadej textový prompt')
      return
    }
    if (loading) return

    setLoading(true)
    setError(null)
    setAudioUrl(null)

    const jobId =
      (typeof crypto !== 'undefined' && crypto.randomUUID && crypto.randomUUID()) ||
      `${Date.now()}-${Math.random().toString(16).slice(2)}`

    setProgress({ percent: 0, message: 'Odesílám požadavek…', eta_seconds: null })

    // zruš staré
    if (progressEventSourceRef.current) {
      progressEventSourceRef.current.close()
      progressEventSourceRef.current = null
    }
    if (progressPollIntervalRef.current) {
      clearInterval(progressPollIntervalRef.current)
      progressPollIntervalRef.current = null
    }
    progressStoppedRef.current = false

    const eventSource = subscribeToBarkProgress(
      jobId,
      (p) => {
        if (progressStoppedRef.current) return
        setProgress(p)
        if (p.status === 'done' || p.status === 'error') {
          progressStoppedRef.current = true
          if (progressPollIntervalRef.current) {
            clearInterval(progressPollIntervalRef.current)
            progressPollIntervalRef.current = null
          }
        }
      },
      () => {
        // fallback polling
        if (progressStoppedRef.current) return
        if (progressPollIntervalRef.current) return

        const poll = async () => {
          if (progressStoppedRef.current) return
          try {
            const p = await getBarkProgress(jobId)
            setProgress(p)
            if (
              p?.status === 'done' ||
              p?.status === 'error' ||
              (typeof p?.percent === 'number' && p.percent >= 100)
            ) {
              progressStoppedRef.current = true
              if (progressPollIntervalRef.current) {
                clearInterval(progressPollIntervalRef.current)
                progressPollIntervalRef.current = null
              }
            }
          } catch (_e) {
            // ignore
          }
        }

        poll()
        progressPollIntervalRef.current = setInterval(poll, 500)
      }
    )

    progressEventSourceRef.current = eventSource

    try {
      const result = await generateBark(
        prompt,
        {
          modelSize,
          mode,
          offloadCpu,
          temperature,
          seed: seed === '' ? null : Number(seed),
          duration: duration
        },
        jobId
      )
      setAudioUrl(result.audio_url)

      try {
        const p = await getBarkProgress(jobId)
        setProgress(p)
      } catch (_e) {
        // ignore
      }
    } catch (e) {
      setError(e.message || 'Chyba při generování Bark audia')
    } finally {
      progressStoppedRef.current = true
      if (progressEventSourceRef.current) {
        progressEventSourceRef.current.close()
        progressEventSourceRef.current = null
      }
      if (progressPollIntervalRef.current) {
        clearInterval(progressPollIntervalRef.current)
        progressPollIntervalRef.current = null
      }
      setLoading(false)
    }
  }

  // Presety pro Bark
  const barkPresets = {
    meditation: [
      {
        value: 'med_calm',
        label: 'Klidná meditativní hudba',
        prompt: '[music] calm meditative ambient music, soft pads, slow evolving, no drums, no vocals, peaceful and relaxing',
        temperature: 0.7
      },
      {
        value: 'med_deep',
        label: 'Hluboká meditační hudba',
        prompt: '[music] deep meditation music, warm drones, very slow, minimal, no vocals, spiritual atmosphere',
        temperature: 0.65
      },
      {
        value: 'med_binaural',
        label: 'Binaurální meditace',
        prompt: '[music] binaural meditation tones, calm frequencies, ambient background, no vocals, healing sounds',
        temperature: 0.7
      },
      {
        value: 'med_singing_bowls',
        label: 'Zpívající mísy',
        prompt: '[music] tibetan singing bowls, crystal bowls, resonant tones, peaceful meditation sounds, no vocals',
        temperature: 0.7
      }
    ],
    nature: [
      {
        value: 'forest_deep',
        label: 'Hluboký les - realistické zvuky',
        prompt: '[birds chirping] [wind through trees] [leaves rustling] [forest ambience]',
        temperature: 0.8
      },
      {
        value: 'forest_morning',
        label: 'Lesní ráno s ptáky',
        prompt: '[morning birds] [forest ambience] [wind sounds] [nature sounds]',
        temperature: 0.75
      },
      {
        value: 'forest_night',
        label: 'Noční les',
        prompt: '[owls hooting] [crickets chirping] [night forest] [rustling leaves]',
        temperature: 0.8
      },
      {
        value: 'forest_rain',
        label: 'Les v dešti',
        prompt: '[rain on leaves] [forest rain] [water dripping] [wet nature sounds]',
        temperature: 0.75
      }
    ],
    stream: [
      {
        value: 'stream_gentle',
        label: 'Jemný potůček',
        prompt: '[water stream] [water over rocks] [brook sounds] [water ambience]',
        temperature: 0.7
      },
      {
        value: 'stream_forest',
        label: 'Potůček v lese',
        prompt: '[forest stream] [water sounds] [birds in background] [nature ambience]',
        temperature: 0.75
      },
      {
        value: 'stream_rocky',
        label: 'Potůček přes kameny',
        prompt: '[water over rocks] [stream sounds] [splashing water] [water flow]',
        temperature: 0.8
      },
      {
        value: 'stream_waterfall',
        label: 'Vodopád',
        prompt: '[waterfall] [cascading water] [water sounds] [waterfall ambience]',
        temperature: 0.75
      }
    ],
    birds: [
      {
        value: 'birds_forest',
        label: 'Ptáci v lese',
        prompt: '[forest birds] [birds chirping] [bird calls] [forest ambience]',
        temperature: 0.8
      },
      {
        value: 'birds_dawn',
        label: 'Ranní ptáci',
        prompt: '[dawn birds] [morning birds] [birds chirping] [bird chorus]',
        temperature: 0.75
      },
      {
        value: 'birds_garden',
        label: 'Ptáci na zahradě',
        prompt: '[garden birds] [sparrows chirping] [robins chirping] [bird sounds]',
        temperature: 0.8
      },
      {
        value: 'birds_water',
        label: 'Ptáci u vody',
        prompt: '[water birds] [ducks quacking] [geese honking] [seagulls calling]',
        temperature: 0.75
      }
    ],
    nature_sfx: [
      {
        value: 'nature_ocean',
        label: 'Oceánské vlny',
        prompt: '[ocean waves] [seagulls] [beach ambience] [water on shore]',
        temperature: 0.75
      },
      {
        value: 'nature_rain',
        label: 'Déšť',
        prompt: '[rain] [raindrops] [rain sounds] [water dripping]',
        temperature: 0.7
      },
      {
        value: 'nature_thunder',
        label: 'Bouřka',
        prompt: '[thunder] [rain] [storm sounds] [rumbling]',
        temperature: 0.8
      },
      {
        value: 'nature_fire',
        label: 'Praskající oheň',
        prompt: '[crackling fire] [wood burning] [fireplace sounds] [fire ambience]',
        temperature: 0.75
      },
      {
        value: 'nature_wind',
        label: 'Vítr',
        prompt: '[wind through trees] [rustling leaves] [wind sounds] [breeze]',
        temperature: 0.7
      },
      {
        value: 'nature_meadow',
        label: 'Louka',
        prompt: '[meadow ambience] [grass rustling] [bees buzzing] [field sounds]',
        temperature: 0.75
      }
    ]
  }

  const applyPreset = (value) => {
    setPreset(value)
    // Najdi preset ve všech kategoriích
    for (const category of Object.keys(barkPresets)) {
      const found = barkPresets[category].find(p => p.value === value)
      if (found) {
        setPresetCategory(category)
        setPrompt(ensureBracketedBarkPresetPrompt(found.prompt))
        if (found.temperature !== undefined) {
          setTemperature(found.temperature)
        }
        break
      }
    }
  }

  const getCurrentPresets = () => {
    return barkPresets[presetCategory] || []
  }

  return (
    <div className="bark" style={style}>
      <div className="bark-header">
        <h2>Bark (Suno AI) - Text-to-Speech a audio generování</h2>
        <p className="bark-hint">
          Generuje realistickou řeč, hudbu a zvuky z textu. Použijte <code>[music]</code> pro hudbu, <code>[zvuk1] [zvuk2]</code> pro SFX zvuky (jednoduché, konkrétní popisy).
          Podporuje speciální tokeny jako <code>[laughter]</code>, <code>[coughs]</code> atd.
        </p>
      </div>

      <div className="bark-grid">
        <div className="bark-controls">
          <Section
            title="🪄 Presety"
            isExpanded={presetsExpanded}
            onToggle={() => setPresetsExpanded(!presetsExpanded)}
          >
            <div className="settings-grid">
              <SelectRow
                label="Kategorie presetů"
                icon="📁"
                value={presetCategory}
                onChange={(v) => {
                  setPresetCategory(v)
                  // Reset preset na první z kategorie
                  const presets = barkPresets[v] || []
                  if (presets.length > 0) {
                    applyPreset(presets[0].value)
                  }
                }}
                options={[
                  { value: 'meditation', label: '🧘 Meditativní hudba' },
                  { value: 'nature', label: '🌲 Lesní zvuky' },
                  { value: 'stream', label: '💧 Potůček' },
                  { value: 'birds', label: '🐦 Ptáci' },
                  { value: 'nature_sfx', label: '🌿 Přírodní SFX' }
                ]}
              />

              <SelectRow
                label="Vyber preset"
                icon="🎵"
                value={preset}
                onChange={applyPreset}
                options={getCurrentPresets().map(p => ({
                  value: p.value,
                  label: p.label
                }))}
              />

              {(() => {
                const currentPreset = getCurrentPresets().find(p => p.value === preset)
                if (currentPreset) {
                  return (
                    <div className="preset-description" style={{
                      padding: '12px',
                      borderRadius: '12px',
                      background: 'rgba(0, 0, 0, 0.2)',
                      marginTop: '8px'
                    }}>
                      <div style={{
                        fontWeight: '600',
                        marginBottom: '8px',
                        color: 'rgba(255, 255, 255, 0.9)',
                        fontSize: '0.9rem'
                      }}>📝 Prompt:</div>
                      <div style={{
                        color: 'rgba(255, 255, 255, 0.8)',
                        fontSize: '0.85rem',
                        fontFamily: 'monospace',
                        wordBreak: 'break-word'
                      }}>{currentPreset.prompt}</div>
                      {currentPreset.temperature !== undefined && (
                        <div style={{
                          marginTop: '8px',
                          fontSize: '0.8rem',
                          color: 'rgba(255, 255, 255, 0.6)',
                          display: 'flex',
                          gap: '12px'
                        }}>
                          <span>Temp: {currentPreset.temperature}</span>
                        </div>
                      )}
                    </div>
                  )
                }
                return null
              })()}
            </div>
          </Section>

          <Section
            title="🎤 Generování Bark"
            isExpanded={mainExpanded}
            onToggle={() => setMainExpanded(!mainExpanded)}
          >
            <div className="settings-grid">
              <SelectRow
                label="Velikost modelu"
                icon="cpu"
                value={modelSize}
                onChange={setModelSize}
                infoIcon="large má vyšší nároky na VRAM; pokud padá na paměť, použij 'Režim modelu' = mixed nebo zapni offload."
                options={[
                  { value: 'small', label: 'Small (nižší VRAM, rychlejší)' },
                  { value: 'large', label: 'Large (vyšší kvalita, vyšší VRAM)' }
                ]}
              />

              <SelectRow
                label="Režim modelu (VRAM)"
                icon="settings"
                value={mode}
                onChange={setMode}
                infoIcon="auto = původní chování (small->small, large->full). mixed často drží kvalitu, ale výrazně šetří VRAM."
                options={[
                  { value: 'auto', label: 'Auto (původní chování)' },
                  { value: 'full', label: 'Full (vše large)' },
                  { value: 'mixed', label: 'Mixed (text large + zbytek small)' },
                  { value: 'small', label: 'Small (vše small)' }
                ]}
              />

              <div className="setting-item">
                <label className="bark-label">CPU offload</label>
                <label className="bark-toggle">
                  <input
                    type="checkbox"
                    checked={offloadCpu}
                    onChange={(e) => setOffloadCpu(e.target.checked)}
                  />
                  <span>Zapnout offload na CPU (šetří VRAM, zpomalí)</span>
                </label>
                <small style={{ opacity: 0.7, fontSize: '0.85rem', marginTop: '6px', display: 'block' }}>
                  Doporučeno, pokud <strong>large</strong> padá na paměť. V kombinaci s <strong>mixed</strong> je to nejšetrnější.
                </small>
              </div>

              <div>
                <label className="bark-label">Textový prompt</label>
                <textarea
                  className="bark-textarea"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Pro hudbu: [music] popis hudby&#10;Pro SFX: [zvuk1] [zvuk2] [zvuk3]&#10;Pro řeč: normální text&#10;&#10;Příklady:&#10;[music] calm piano melody&#10;[water stream] [water over rocks] [brook sounds]&#10;Ahoj! [laughter]"
                  rows={8}
                />
                <small style={{ opacity: 0.7, fontSize: '0.85rem', marginTop: '6px', display: 'block' }}>
                  <strong>Speciální tokeny:</strong> <code>[music]</code> pro hudbu, <code>[laughter]</code> <code>[coughs]</code> atd. pro efekty. Pro SFX zvuky rozdělte do samostatných segmentů: <code>[zvuk1] [zvuk2] [zvuk3]</code> - používejte jednoduché, konkrétní popisy.
                </small>
              </div>

              <div>
                <label className="bark-label">Seed (volitelné)</label>
                <input
                  type="text"
                  className="bark-input"
                  value={seed}
                  onChange={(e) => setSeed(e.target.value)}
                  placeholder="Prázdné = náhodné"
                />
                <small style={{ opacity: 0.7, fontSize: '0.85rem', marginTop: '4px', display: 'block' }}>
                  Číslo pro reprodukovatelnost generování
                </small>
              </div>

              <SliderRow
                label="Temperature"
                icon="🌡️"
                value={temperature}
                onChange={setTemperature}
                min={0.0}
                max={1.0}
                step={0.05}
                tooltip="Vyšší = kreativnější generování"
              />

              <SliderRow
                label="Délka (sekundy)"
                icon="⏱️"
                value={duration}
                onChange={setDuration}
                min={1}
                max={120}
                step={1}
                formatValue={(v) => `${v}s`}
                tooltip="Délka výsledného audio (1-120s). Delší než ~14s se zacyklí."
              />
            </div>
          </Section>


          <div className="generate-section">
            <button
              className="btn-primary"
              onClick={handleGenerate}
              disabled={loading || !prompt.trim()}
            >
              {loading ? '⏳ Generuji...' : '🔊 Generovat Bark audio'}
            </button>
          </div>

          {loading && <LoadingSpinner progress={progress} />}

          {error && (
            <div className="error-message">
              ⚠️ {error}
            </div>
          )}
        </div>

        <div className="bark-result">
          <h3>Výsledek</h3>
          {audioUrl ? (
            <AudioPlayer audioUrl={audioUrl} />
          ) : (
            <div className="bark-empty">
              {loading ? 'Generuji...' : 'Vygenerované audio se zobrazí zde'}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Bark

