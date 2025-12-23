import React, { useEffect, useRef, useState } from 'react'
import './MusicGen.css'
import LoadingSpinner from './LoadingSpinner'
import AudioPlayer from './AudioPlayer'
import Section from './ui/Section'
import SliderRow from './ui/SliderRow'
import SelectRow from './ui/SelectRow'
import { generateMusic, getMusicProgress, subscribeToMusicProgress, getAmbienceList } from '../services/api'

function MusicGen({ prompt: promptProp, setPrompt: setPromptProp }) {
  const [internalPrompt, setInternalPrompt] = useState('ambient cinematic pads, 90 BPM, no vocals, warm, slow build')

  // Synchronizace s propsem (pro obnovu z historie)
  const prompt = promptProp !== undefined ? promptProp : internalPrompt
  const setPrompt = setPromptProp !== undefined ? setPromptProp : setInternalPrompt
  const [model, setModel] = useState('small')
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

  const applyPreset = (v) => {
    setPreset(v)
    if (v === 'med_stream') {
      setPrompt('very calm meditative ambient drone, warm pads, slow evolution, no drums, no vocals, no melody hooks, relaxing')
      setTemperature(0.85)
      setTopK(180)
      setTopP(0.0)
      setDuration(18)
      setAmbience('stream')
      setAmbienceGainDb(-18)
    } else if (v === 'med_birds') {
      setPrompt('calm airy ambient, gentle drones, soft harmonics, slow and spacious, no drums, no vocals, relaxing morning mood')
      setTemperature(0.9)
      setTopK(200)
      setTopP(0.0)
      setDuration(16)
      setAmbience('birds')
      setAmbienceGainDb(-20)
    } else if (v === 'forest_both') {
      setPrompt('peaceful forest meditation ambient, soft pads, subtle textures, very slow, no drums, no vocals, calming')
      setTemperature(0.9)
      setTopK(200)
      setTopP(0.0)
      setDuration(18)
      setAmbience('both')
      setAmbienceGainDb(-20)
    } else if (v === 'deep_drone') {
      setPrompt('deep meditation drone, extremely slow evolving, dark warm pads, no percussion, no vocals, minimal')
      setTemperature(0.75)
      setTopK(140)
      setTopP(0.0)
      setDuration(20)
      setAmbience('none')
    }
  }

  return (
    <div className="musicgen">
      <div className="musicgen-header">
        <h2>MusicGen (instrumentální hudba)</h2>
        <p className="musicgen-hint">
          Specializace: klidný ambient/meditace + volitelně potůček/ptáci (mix z <code>assets/nature</code>).
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
                label="Hudební preset"
                icon="🪄"
                value={preset}
                onChange={applyPreset}
                options={[
                  { value: 'med_stream', label: 'Meditace + potůček' },
                  { value: 'med_birds', label: 'Meditace + ptáci' },
                  { value: 'forest_both', label: 'Lesní ráno (voda + ptáci)' },
                  { value: 'deep_drone', label: 'Deep drone (bez ambience)' }
                ]}
              />

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


