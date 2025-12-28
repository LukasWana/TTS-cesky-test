import React, { useEffect, useRef, useState } from 'react'
import { useSectionColor } from '../contexts/SectionColorContext'
import './MusicGen.css'
import LoadingSpinner from './LoadingSpinner'
import AudioPlayer from './AudioPlayer'
import Section from './ui/Section'
import SliderRow from './ui/SliderRow'
import SelectRow from './ui/SelectRow'
import { generateMusic, getMusicProgress, subscribeToMusicProgress, getAmbienceList } from '../services/api'

function MusicGen({ prompt: promptProp, setPrompt: setPromptProp }) {
  const { color, rgb } = useSectionColor()
  const style = {
    '--section-color': color,
    '--section-color-rgb': rgb
  }
  const [internalPrompt, setInternalPrompt] = useState('ambient cinematic pads, 90 BPM, no vocals, warm, slow build')

  // Synchronizace s propsem (pro obnovu z historie)
  const prompt = promptProp !== undefined ? promptProp : internalPrompt
  const setPrompt = setPromptProp !== undefined ? setPromptProp : setInternalPrompt
  const [model, setModel] = useState('small')
  const [precision, setPrecision] = useState('auto') // auto|fp32|fp16|bf16
  const [offload, setOffload] = useState(false)
  const [maxVramGb, setMaxVramGb] = useState('6')
  const [duration, setDuration] = useState(12)
  const [temperature, setTemperature] = useState(1.0)
  const [topK, setTopK] = useState(250)
  const [topP, setTopP] = useState(0.0)
  const [seed, setSeed] = useState('')
  const [ambience, setAmbience] = useState('stream') // none|stream|birds|both
  const [ambienceGainDb, setAmbienceGainDb] = useState(-18)
  const [ambienceSeed, setAmbienceSeed] = useState('')
  const [ambienceFileStream, setAmbienceFileStream] = useState('random')
  const [ambienceFileBirds, setAmbienceFileBirds] = useState('random')
  const [ambienceList, setAmbienceList] = useState({ stream: [], birds: [] })
  const [preset, setPreset] = useState('med_stream')
  const [presetCategory, setPresetCategory] = useState('meditation') // meditation | ambient | nature | urban | abstract

  // Stavy pro rozbalení sekcí (konzistence s TTS)
  const [mainExpanded, setMainExpanded] = useState(true)
  const [ambienceExpanded, setAmbienceExpanded] = useState(true)
  const [advancedExpanded, setAdvancedExpanded] = useState(false)

  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState(null)
  const [error, setError] = useState(null)
  const [warning, setWarning] = useState(null)
  const [audioUrl, setAudioUrl] = useState(null)

  const progressEventSourceRef = useRef(null)
  const progressPollIntervalRef = useRef(null)
  const progressStoppedRef = useRef(false)

  useEffect(() => {
    const loadAmbience = async () => {
      try {
        const list = await getAmbienceList()
        setAmbienceList(list)
      } catch (e) {
        console.error('Chyba při načítání ambience:', e)
      }
    }
    loadAmbience()

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
      setError('Zadej prompt')
      return
    }
    if (loading) return

    setLoading(true)
    setError(null)
    setWarning(null)
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

    const eventSource = subscribeToMusicProgress(
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
            const p = await getMusicProgress(jobId)
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
      const result = await generateMusic(
        prompt,
        {
          model,
          precision,
          offload,
          maxVramGb: offload ? (maxVramGb === '' ? null : Number(maxVramGb)) : null,
          duration,
          temperature,
          topK,
          topP,
          seed: seed === '' ? null : Number(seed),
          ambience,
          ambienceGainDb,
          ambienceSeed: ambienceSeed === '' ? null : Number(ambienceSeed),
          ambienceFileStream,
          ambienceFileBirds
        },
        jobId
      )
      setAudioUrl(result.audio_url)
      if (result.warning) {
        setWarning(result.warning)
      }

      try {
        const p = await getMusicProgress(jobId)
        setProgress(p)
      } catch (_e) {
        // ignore
      }
    } catch (e) {
      setError(e.message || 'Chyba při generování hudby')
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

  const ambientPresets = {
    meditation: [
      {
        value: 'med_stream',
        label: 'Meditace + potůček',
        prompt: 'very calm meditative ambient drone, warm pads, slow evolution, no drums, no vocals, no melody hooks, relaxing',
        temperature: 0.85,
        topK: 180,
        topP: 0.0,
        duration: 18,
        ambience: 'stream',
        ambienceGainDb: -18
      },
      {
        value: 'med_birds',
        label: 'Meditace + ptáci',
        prompt: 'calm airy ambient, gentle drones, soft harmonics, slow and spacious, no drums, no vocals, relaxing morning mood',
        temperature: 0.9,
        topK: 200,
        topP: 0.0,
        duration: 16,
        ambience: 'birds',
        ambienceGainDb: -20
      },
      {
        value: 'forest_both',
        label: 'Lesní ráno (voda + ptáci)',
        prompt: 'peaceful forest meditation ambient, soft pads, subtle textures, very slow, no drums, no vocals, calming',
        temperature: 0.9,
        topK: 200,
        topP: 0.0,
        duration: 18,
        ambience: 'both',
        ambienceGainDb: -20
      },
      {
        value: 'deep_drone',
        label: 'Deep drone (bez ambience)',
        prompt: 'deep meditation drone, extremely slow evolving, dark warm pads, no percussion, no vocals, minimal',
        temperature: 0.75,
        topK: 140,
        topP: 0.0,
        duration: 20,
        ambience: 'none',
        ambienceGainDb: -18
      }
    ],
    ambient: [
      {
        value: 'rain_ambient',
        label: 'Déšť a atmosféra',
        prompt: 'gentle rain soundscape, ambient textures, soft atmospheric pads, no music, no melody, natural rain ambience',
        temperature: 0.8,
        topK: 160,
        topP: 0.0,
        duration: 15,
        ambience: 'none',
        ambienceGainDb: -18
      },
      {
        value: 'wind_ambient',
        label: 'Vítr a prostor',
        prompt: 'windy atmospheric soundscape, airy textures, spacious ambient, no music, no melody, natural wind ambience',
        temperature: 0.85,
        topK: 180,
        topP: 0.0,
        duration: 16,
        ambience: 'none',
        ambienceGainDb: -18
      },
      {
        value: 'ocean_ambient',
        label: 'Oceánské vlny',
        prompt: 'ocean waves, gentle water sounds, ambient textures, no music, no melody, natural ocean ambience',
        temperature: 0.8,
        topK: 170,
        topP: 0.0,
        duration: 18,
        ambience: 'none',
        ambienceGainDb: -18
      },
      {
        value: 'fire_ambient',
        label: 'Oheň a teplo',
        prompt: 'crackling fire, warm ambient textures, cozy atmosphere, no music, no melody, natural fire ambience',
        temperature: 0.75,
        topK: 150,
        topP: 0.0,
        duration: 15,
        ambience: 'none',
        ambienceGainDb: -18
      },
      {
        value: 'thunder_ambient',
        label: 'Bouřka a déšť',
        prompt: 'distant thunder, rain ambience, atmospheric textures, no music, no melody, natural storm ambience',
        temperature: 0.85,
        topK: 180,
        topP: 0.0,
        duration: 16,
        ambience: 'none',
        ambienceGainDb: -18
      }
    ],
    nature: [
      {
        value: 'forest_deep',
        label: 'Hluboký les',
        prompt: 'deep forest ambience, natural sounds, organic textures, no music, no melody, immersive forest soundscape',
        temperature: 0.9,
        topK: 200,
        topP: 0.0,
        duration: 20,
        ambience: 'both',
        ambienceGainDb: -22
      },
      {
        value: 'mountain_air',
        label: 'Horský vzduch',
        prompt: 'mountain air, high altitude ambience, crisp textures, no music, no melody, natural mountain soundscape',
        temperature: 0.85,
        topK: 180,
        topP: 0.0,
        duration: 18,
        ambience: 'birds',
        ambienceGainDb: -20
      },
      {
        value: 'meadow_peace',
        label: 'Klidná louka',
        prompt: 'peaceful meadow, gentle nature sounds, soft textures, no music, no melody, natural meadow ambience',
        temperature: 0.9,
        topK: 200,
        topP: 0.0,
        duration: 16,
        ambience: 'birds',
        ambienceGainDb: -20
      },
      {
        value: 'night_forest',
        label: 'Noční les',
        prompt: 'night forest ambience, nocturnal sounds, dark textures, no music, no melody, natural night soundscape',
        temperature: 0.8,
        topK: 170,
        topP: 0.0,
        duration: 18,
        ambience: 'none',
        ambienceGainDb: -18
      }
    ],
    urban: [
      {
        value: 'city_rain',
        label: 'Město v dešti',
        prompt: 'urban rain ambience, city sounds, wet textures, no music, no melody, natural city rain soundscape',
        temperature: 0.85,
        topK: 180,
        topP: 0.0,
        duration: 15,
        ambience: 'none',
        ambienceGainDb: -18
      },
      {
        value: 'cafe_ambient',
        label: 'Kavárna',
        prompt: 'cafe ambience, background chatter, warm textures, no music, no melody, natural cafe soundscape',
        temperature: 0.9,
        topK: 200,
        topP: 0.0,
        duration: 14,
        ambience: 'none',
        ambienceGainDb: -18
      },
      {
        value: 'library_quiet',
        label: 'Tichá knihovna',
        prompt: 'library ambience, quiet atmosphere, soft textures, no music, no melody, natural library soundscape',
        temperature: 0.75,
        topK: 150,
        topP: 0.0,
        duration: 16,
        ambience: 'none',
        ambienceGainDb: -18
      }
    ],
    abstract: [
      {
        value: 'space_void',
        label: 'Vesmírná prázdnota',
        prompt: 'space void ambience, cosmic textures, ethereal sounds, no music, no melody, abstract space soundscape',
        temperature: 0.8,
        topK: 170,
        topP: 0.0,
        duration: 18,
        ambience: 'none',
        ambienceGainDb: -18
      },
      {
        value: 'digital_glitch',
        label: 'Digitální textury',
        prompt: 'digital glitch ambience, electronic textures, synthetic sounds, no music, no melody, abstract digital soundscape',
        temperature: 0.9,
        topK: 200,
        topP: 0.0,
        duration: 15,
        ambience: 'none',
        ambienceGainDb: -18
      },
      {
        value: 'mechanical_hum',
        label: 'Mechanický šum',
        prompt: 'mechanical hum, industrial textures, machine sounds, no music, no melody, abstract industrial soundscape',
        temperature: 0.85,
        topK: 180,
        topP: 0.0,
        duration: 16,
        ambience: 'none',
        ambienceGainDb: -18
      }
    ]
  }

  const applyPreset = (v) => {
    setPreset(v)
    // Najdi preset ve všech kategoriích
    for (const category of Object.keys(ambientPresets)) {
      const found = ambientPresets[category].find(p => p.value === v)
      if (found) {
        setPresetCategory(category)
        setPrompt(found.prompt)
        setTemperature(found.temperature)
        setTopK(found.topK)
        setTopP(found.topP)
        setDuration(found.duration)
        setAmbience(found.ambience)
        setAmbienceGainDb(found.ambienceGainDb)
        break
      }
    }
  }

  const getCurrentPresets = () => {
    return ambientPresets[presetCategory] || []
  }

  return (
    <div className="musicgen" style={style}>
      <div className="musicgen-header">
        <h2>MusicGen (hudba a ambientní zvuky)</h2>
        <p className="musicgen-hint">
          Generování instrumentální hudby a ambientních zvukových scén. Presety pro meditaci, přírodu, město a abstraktní zvuky.
          Volitelně lze přidat potůček/ptáci z <code>assets/nature</code>.
        </p>
      </div>

      <div className="musicgen-grid">
        <div className="musicgen-controls">
          <Section
            title="🎶 Generování hudby"
            isExpanded={mainExpanded}
            onToggle={() => setMainExpanded(!mainExpanded)}
          >
            <div className="settings-grid">
              <SelectRow
                label="Velikost modelu"
                icon="cpu"
                value={model}
                onChange={setModel}
                infoIcon="large má výrazně vyšší nároky na VRAM. Pokud padá, zkus fp16 + offload."
                options={[
                  { value: 'small', label: 'Small (rychlejší, méně VRAM)' },
                  { value: 'medium', label: 'Medium (střední kvalita/VRAM)' },
                  { value: 'large', label: 'Large (nejvyšší kvalita, nejvíc VRAM)' }
                ]}
              />

              <SelectRow
                label="Kategorie presetů"
                icon="📁"
                value={presetCategory}
                onChange={(v) => {
                  setPresetCategory(v)
                  // Reset preset na první z kategorie
                  const presets = ambientPresets[v] || []
                  if (presets.length > 0) {
                    applyPreset(presets[0].value)
                  }
                }}
                options={[
                  { value: 'meditation', label: '🧘 Meditace' },
                  { value: 'ambient', label: '🌧️ Atmosférické zvuky' },
                  { value: 'nature', label: '🌲 Příroda' },
                  { value: 'urban', label: '🏙️ Městské' },
                  { value: 'abstract', label: '🌀 Abstraktní' }
                ]}
              />

              <SelectRow
                label="Ambientní preset"
                icon="🪄"
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
                    <div className="preset-description">
                      <div className="preset-description-label">📝 Popis presetu:</div>
                      <div className="preset-description-text">{currentPreset.prompt}</div>
                      <div className="preset-description-params">
                        <span>Temp: {currentPreset.temperature}</span>
                        <span>Top-K: {currentPreset.topK}</span>
                        <span>Délka: {currentPreset.duration}s</span>
                        {currentPreset.ambience !== 'none' && (
                          <span>Ambience: {currentPreset.ambience === 'stream' ? 'Potůček' : currentPreset.ambience === 'birds' ? 'Ptáci' : 'Oboje'}</span>
                        )}
                      </div>
                    </div>
                  )
                }
                return null
              })()}

              <SliderRow
                label="Délka skladby (s)"
                value={duration}
                min={1}
                max={30}
                step={1}
                onChange={setDuration}
                formatValue={(v) => `${v}s`}
                showTicks={true}
              />

              <div className="setting-item">
                <label className="musicgen-label">Textový prompt (popis hudby)</label>
                <textarea
                  className="musicgen-textarea"
                  rows={4}
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="např. ambient lo-fi beat, 90 BPM, no vocals"
                />
              </div>
            </div>
          </Section>

          <Section
            title="🍃 Ambientní zvuky (Nature)"
            icon="🕊️"
            isExpanded={ambienceExpanded}
            onToggle={() => setAmbienceExpanded(!ambienceExpanded)}
          >
            <div className="settings-grid">
              <SelectRow
                label="Druh ambience"
                icon="🌳"
                value={ambience}
                onChange={setAmbience}
                options={[
                  { value: 'none', label: 'Žádná' },
                  { value: 'stream', label: 'Pouze potůček' },
                  { value: 'birds', label: 'Pouze ptáci' },
                  { value: 'both', label: 'Potůček i ptáci' }
                ]}
              />

              {(ambience === 'stream' || ambience === 'both') && (
                <SelectRow
                  label="Konkrétní potůček"
                  icon="💧"
                  value={ambienceFileStream}
                  onChange={setAmbienceFileStream}
                  options={[
                    { value: 'random', label: '🎲 Náhodný výběr' },
                    ...ambienceList.stream.map(f => ({ value: f, label: f.replace('stream_', '').replace('.wav', '') }))
                  ]}
                />
              )}

              {(ambience === 'birds' || ambience === 'both') && (
                <SelectRow
                  label="Konkrétní ptáci"
                  icon="🐦"
                  value={ambienceFileBirds}
                  onChange={setAmbienceFileBirds}
                  options={[
                    { value: 'random', label: '🎲 Náhodný výběr' },
                    ...ambienceList.birds.map(f => ({ value: f, label: f.replace('birds_', '').replace('.wav', '') }))
                  ]}
                />
              )}

              {ambience !== 'none' && (
                <SliderRow
                  label="Hlasitost přírody"
                  value={ambienceGainDb}
                  min={-40}
                  max={-6}
                  step={1}
                  onChange={setAmbienceGainDb}
                  formatValue={(v) => `${v} dB`}
                  showTicks={true}
                />
              )}

              <div className="setting-description">
                Vzorky se berou z <code>assets/nature/</code>. Můžete tam přidat vlastní WAVy s předponou <code>stream_</code> nebo <code>birds_</code>.
              </div>
            </div>
          </Section>

          <Section
            title="⚙️ Pokročilé parametry"
            icon="🛠️"
            isExpanded={advancedExpanded}
            onToggle={() => setAdvancedExpanded(!advancedExpanded)}
          >
            <div className="settings-grid">
              <SelectRow
                label="Precision (VRAM)"
                icon="settings"
                value={precision}
                onChange={setPrecision}
                infoIcon="auto = fp32 (původní chování). Pro CUDA typicky doporučeno fp16 (méně VRAM, často rychlejší)."
                options={[
                  { value: 'auto', label: 'Auto (fp32 – kompatibilní)' },
                  { value: 'fp16', label: 'FP16 (méně VRAM)' },
                  { value: 'bf16', label: 'BF16 (pokud GPU podporuje)' },
                  { value: 'fp32', label: 'FP32 (nejvyšší přesnost)' }
                ]}
              />

              <div className="setting-item">
                <label className="musicgen-label">Offload (device_map)</label>
                <label className="musicgen-toggle">
                  <input
                    type="checkbox"
                    checked={offload}
                    onChange={(e) => setOffload(e.target.checked)}
                  />
                  <span>Povolit offload na CPU (šetří VRAM, zpomalí)</span>
                </label>
                <div className="setting-description">
                  Pokud ti <strong>medium/large</strong> padá na VRAM, offload často pomůže. Vyžaduje <code>accelerate</code>; backend má fallback.
                </div>
              </div>

              {offload && (
                <div className="setting-item">
                  <label className="musicgen-label">Max VRAM (GiB)</label>
                  <input
                    className="musicgen-input"
                    type="number"
                    min="1"
                    step="1"
                    value={maxVramGb}
                    onChange={(e) => setMaxVramGb(e.target.value)}
                    placeholder="např. 6"
                  />
                  <div className="setting-description">
                    Limit pro offload režim. Pokud necháš prázdné, nechá se to na automatice.
                  </div>
                </div>
              )}

              <SliderRow
                label="Temperature (kreativita)"
                value={temperature}
                min={0.1}
                max={1.5}
                step={0.05}
                onChange={setTemperature}
                formatValue={(v) => v.toFixed(2)}
                showTicks={true}
              />

              <SliderRow
                label="Top-K"
                value={topK}
                min={0}
                max={500}
                step={10}
                onChange={setTopK}
                formatValue={(v) => v}
                showTicks={true}
              />

              <SliderRow
                label="Top-P"
                value={topP}
                min={0.0}
                max={1.0}
                step={0.05}
                onChange={setTopP}
                formatValue={(v) => v.toFixed(2)}
                showTicks={true}
              />

              <div className="setting-item">
                <label className="musicgen-label">Seed (volitelný)</label>
                <input
                  className="musicgen-input"
                  type="number"
                  value={seed}
                  onChange={(e) => setSeed(e.target.value)}
                  placeholder="např. 42"
                />
              </div>
            </div>
          </Section>

          <div className="generate-section" style={{ marginTop: '20px' }}>
            <button className="btn-primary" onClick={handleGenerate} disabled={loading || !prompt.trim()}>
              {loading ? '⏳ Generuji…' : '🎶 Generovat hudbu'}
            </button>
          </div>

          {loading && <LoadingSpinner progress={progress} />}
          {error && <div className="error-message">⚠️ {error}</div>}
          {warning && <div className="error-message" style={{ borderColor: 'rgba(234, 179, 8, 0.3)', color: '#fbbf24' }}>⚠️ {warning}</div>}
        </div>

        <div className="musicgen-output">
          <Section title="🎧 Výsledek" isExpanded={true}>
            {audioUrl ? (
              <div className="musicgen-result">
                <AudioPlayer audioUrl={audioUrl} />
                <div className="result-hint">Hudba byla automaticky zacyklena (seamless loop).</div>
              </div>
            ) : (
              <div className="musicgen-empty">Zatím nebyla vygenerována žádná hudba.</div>
            )}
          </Section>
        </div>
      </div>
    </div>
  )
}

export default MusicGen


