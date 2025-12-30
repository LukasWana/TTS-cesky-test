import React, { useEffect, useRef, useState } from 'react'
import './SfxGen.css'
import LoadingSpinner from './LoadingSpinner'
import AudioPlayer from './AudioPlayer'
import Section from './ui/Section'
import SliderRow from './ui/SliderRow'
import SelectRow from './ui/SelectRow'
import { generateSfx, getSfxProgress, subscribeToSfxProgress } from '../services/api'

function SfxGen({ prompt: promptProp, setPrompt: setPromptProp }) {
  const [internalPrompt, setInternalPrompt] = useState('laser zap sound, sci-fi, clean, no music')

  // Synchronizace s propsem (pro obnovu z historie)
  const prompt = promptProp !== undefined ? promptProp : internalPrompt
  const setPrompt = setPromptProp !== undefined ? setPromptProp : setInternalPrompt
  const [model, setModel] = useState('medium')
  const [duration, setDuration] = useState(3)
  const [temperature, setTemperature] = useState(1.0)
  const [topK, setTopK] = useState(250)
  const [topP, setTopP] = useState(0.0)
  const [cfgCoef, setCfgCoef] = useState(3.0)
  const [seed, setSeed] = useState('')

  // Stavy pro rozbalení sekcí
  const [mainExpanded, setMainExpanded] = useState(true)
  const [advancedExpanded, setAdvancedExpanded] = useState(false)

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
      setError('Zadej prompt')
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

    const eventSource = subscribeToSfxProgress(
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
            const p = await getSfxProgress(jobId)
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
      const result = await generateSfx(
        prompt,
        {
          model,
          duration,
          temperature,
          topK,
          topP,
          cfgCoef,
          seed: seed === '' ? null : Number(seed),
        },
        jobId
      )
      setAudioUrl(result.audio_url)
    } catch (e) {
      const errorMsg = e.message || 'Chyba při generování SFX'
      setError(errorMsg)

      // Pokud je to chyba o chybějící audiocraft, zobrazit instrukce
      if (errorMsg.includes('audiocraft') || errorMsg.includes('AudioGen závislosti')) {
        setError(
          errorMsg + '\n\n' +
          'Pro použití SFX generování nainstalujte:\n' +
          '  pip install audiocraft\n\n' +
          'Pozn.: TTS a MusicGen fungují i bez této závislosti.'
        )
      }
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

  return (
    <div className="sfxgen">
      <div className="sfxgen-header">
        <h2>SFX (AudioGen) – Zvukové efekty</h2>
        <p className="sfxgen-hint">
          Generování zvukových efektů na základě textového popisu. Optimalizováno pro RTX 3060 6GB VRAM (doporučeno 2–4s délka).
        </p>
      </div>

      <div className="sfxgen-grid">
        <div className="sfxgen-controls">
          <Section
            title="🔊 Generování SFX"
            isExpanded={mainExpanded}
            onToggle={() => setMainExpanded(!mainExpanded)}
          >
            <div className="settings-grid">
              <SelectRow
                label="Velikost modelu"
                icon="🤖"
                value={model}
                onChange={setModel}
                options={[
                  { value: 'small', label: 'Small (menší VRAM)' },
                  { value: 'medium', label: 'Medium (doporučeno pro 6GB VRAM)' }
                ]}
              />

              <SliderRow
                label="Délka efektu (s)"
                value={duration}
                min={1}
                max={8}
                step={0.5}
                onChange={setDuration}
                formatValue={(v) => `${v}s`}
                showTicks={true}
              />

              <div className="setting-item">
                <label className="sfxgen-label">Textový prompt (popis zvukového efektu)</label>
                <textarea
                  className="sfxgen-textarea"
                  rows={4}
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="např. laser zap sound, sci-fi, clean, no music"
                />
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

              <SliderRow
                label="CFG Coefficient"
                value={cfgCoef}
                min={1.0}
                max={10.0}
                step={0.5}
                onChange={setCfgCoef}
                formatValue={(v) => v.toFixed(1)}
                showTicks={true}
              />

              <div className="setting-item">
                <label className="sfxgen-label">Seed (volitelný)</label>
                <input
                  className="sfxgen-input"
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
              {loading ? '⏳ Generuji…' : '🔊 Generovat SFX'}
            </button>
          </div>

          {loading && <LoadingSpinner progress={progress} />}
          {error && (
            <div className="error-message" style={{ whiteSpace: 'pre-line' }}>
              ⚠️ {error}
            </div>
          )}
        </div>

        <div className="sfxgen-output">
          <Section title="🎧 Výsledek" isExpanded={true}>
            {audioUrl ? (
              <div className="sfxgen-result">
                <AudioPlayer audioUrl={audioUrl} />
              </div>
            ) : (
              <div className="sfxgen-empty">Zatím nebyl vygenerován žádný SFX efekt.</div>
            )}
          </Section>
        </div>
      </div>
    </div>
  )
}

export default SfxGen












