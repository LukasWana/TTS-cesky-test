import React, { useState, useRef, useEffect, useMemo } from 'react'
import VoiceSelector from './VoiceSelector'
import TextInput from './TextInput'
import AudioPlayer from './AudioPlayer'
import LoadingSpinner from './LoadingSpinner'
import TTSSettings from './TTSSettings'
import Button from './ui/Button'
import Icon from './ui/Icons'
import { generateF5TTSSlovak, getDemoVoices, subscribeToTtsProgress, uploadVoice, recordVoice, downloadYouTubeVoice, transcribeReferenceAudio } from '../services/api'
import './F5TTS.css'

function F5TTS({ text: textProp, setText: setTextProp }) {
  const [internalText, setInternalText] = useState('')
  const text = textProp !== undefined ? textProp : internalText
  const setText = setTextProp !== undefined ? setTextProp : setInternalText

  const [selectedVoice, setSelectedVoice] = useState(null)
  const [voiceType, setVoiceType] = useState('demo')
  const [demoVoices, setDemoVoices] = useState([])
  const [loading, setLoading] = useState(false)
  const [ttsProgress, setTtsProgress] = useState(null)
  const [generatedAudio, setGeneratedAudio] = useState(null)
  const [error, setError] = useState(null)
  const [showSettings, setShowSettings] = useState(false)
  // F5TTS je v tomto projektu fixně pro slovenštinu (nepřepíná se do češtiny).
  const language = 'sk'
  const [uploadedVoiceFileName, setUploadedVoiceFileName] = useState(null)
  const [voiceQuality, setVoiceQuality] = useState(null)
  const [refText, setRefText] = useState('')
  const [autoTranscribe, setAutoTranscribe] = useState(true)
  const [refTextLoading, setRefTextLoading] = useState(false)

  // --- Persist ref_text per konkrétní hlas (aby po reloadu nezmizel) ---
  const persistRefText = (storageKey, value) => {
    if (!storageKey) return
    try {
      const v = (value || '').toString()
      if (v.trim() === '') {
        localStorage.removeItem(storageKey)
      } else {
        localStorage.setItem(storageKey, v)
      }
    } catch (e) {
      // localStorage může být nedostupné (privacy mode apod.) – ignoruj
      console.warn('Nelze uložit ref_text do localStorage:', e)
    }
  }

  const makeDemoRefKey = (voiceId) => `f5tts_reftext:v1:${language}:demo:${voiceId}`
  const makeUploadRefKey = (filename) => `f5tts_reftext:v1:${language}:upload:${filename}`

  const refTextStorageKey = useMemo(() => {
    // Pro demo/record/youtube používáme ID demo hlasu; pro upload jen název souboru.
    if (voiceType === 'upload') {
      return uploadedVoiceFileName ? makeUploadRefKey(uploadedVoiceFileName) : null
    }
    if (voiceType === 'demo' || voiceType === 'record' || voiceType === 'youtube') {
      return typeof selectedVoice === 'string' && selectedVoice ? makeDemoRefKey(selectedVoice) : null
    }
    return null
  }, [voiceType, selectedVoice, uploadedVoiceFileName])

  // Při změně hlasu načti uložený ref_text
  useEffect(() => {
    if (!refTextStorageKey) {
      setRefText('')
      return
    }
    try {
      const stored = localStorage.getItem(refTextStorageKey)
      setRefText(stored || '')
    } catch (e) {
      setRefText('')
    }
  }, [refTextStorageKey])

  // Průběžně ukládej ref_text (debounce) – aby se zachovalo i ruční psaní do textarea
  const refTextSaveTimeoutRef = useRef(null)
  useEffect(() => {
    if (!refTextStorageKey) return
    if (refTextSaveTimeoutRef.current) {
      clearTimeout(refTextSaveTimeoutRef.current)
    }
    refTextSaveTimeoutRef.current = setTimeout(() => {
      persistRefText(refTextStorageKey, refText)
    }, 250)
    return () => {
      if (refTextSaveTimeoutRef.current) {
        clearTimeout(refTextSaveTimeoutRef.current)
        refTextSaveTimeoutRef.current = null
      }
    }
  }, [refText, refTextStorageKey])

  // TTS nastavení (stejné jako XTTS)
  const [ttsSettings, setTtsSettings] = useState({
    speed: 1.0,
    temperature: 0.7,
    lengthPenalty: 1.0,
    repetitionPenalty: 2.0,
    topK: 50,
    topP: 0.85,
    seed: null
  })

  const [qualitySettings, setQualitySettings] = useState({
    qualityMode: null,
    enhancementPreset: 'natural',
    enableEnhancement: true,
    enableNormalization: false,
    enableDenoiser: true,
    enableCompressor: false,
    enableDeesser: true,
    enableEq: false,
    enableTrim: true,
    enableVad: true,
    useHifigan: false,
    enableDialectConversion: false,
    dialectCode: null,
    dialectIntensity: 1.0,
    whisperIntensity: 1.0
  })

  const [activeVariant, setActiveVariant] = useState('variant2') // P2 - Přirozený jako default

  const progressEventSourceRef = useRef(null)
  const currentSettingsRef = useRef({ ttsSettings, qualitySettings })

  useEffect(() => {
    const loadVoices = async () => {
      try {
        const data = await getDemoVoices(language)
        const voices = data.voices || data || [] // Podpora obou formátů response
        setDemoVoices(voices)
        // Pokud není nic vybráno, nebo aktuální výběr v novém seznamu neexistuje, vyber první.
        const hasSelected = selectedVoice && voices.some(v => (v.id || v.name) === selectedVoice)
        if (voices.length > 0 && (!selectedVoice || !hasSelected)) {
          setSelectedVoice(voices[0].id || voices[0].name)
        }
      } catch (err) {
        console.error('Chyba při načítání demo hlasů:', err)
      }
    }
    loadVoices()

    return () => {
      if (progressEventSourceRef.current) {
        progressEventSourceRef.current.close()
        progressEventSourceRef.current = null
      }
    }
  }, [])

  useEffect(() => {
    currentSettingsRef.current = { ttsSettings, qualitySettings }
  }, [ttsSettings, qualitySettings])

  const loadDemoVoices = async () => {
    try {
      const data = await getDemoVoices(language)
      const voices = data.voices || data || []
      setDemoVoices(voices)
    } catch (err) {
      console.error('Chyba při načítání demo hlasů:', err)
    }
  }

  const handleVoiceUpload = async (file) => {
    setSelectedVoice(file)
    setVoiceType('upload')
    setUploadedVoiceFileName(file.name)
    setVoiceQuality(null) // Reset quality for new upload

    if (autoTranscribe) {
      try {
        setRefTextLoading(true)
        const res = await transcribeReferenceAudio({ voiceFile: file, language })
        const txt = res.cleaned_text || res.text || ''
        setRefText(txt)
        // Ulož hned pod konkrétní upload filename (state update je async)
        persistRefText(makeUploadRefKey(file.name), txt)
      } catch (e) {
        console.error('ASR přepis selhal:', e)
      } finally {
        setRefTextLoading(false)
      }
    }
  }

  const handleVoiceRecord = async (result) => {
    try {
      // Obnovit seznam demo hlasů
      await loadDemoVoices()

      // Automaticky přepnout na demo hlas a vybrat nově nahraný hlas
      setVoiceType('demo')
      setSelectedVoice(null) // Reset před nastavením nového
      setUploadedVoiceFileName(null)
      setVoiceQuality(result.quality || null)

      // Počkat na načtení demo hlasů a pak vybrat nový
      setTimeout(() => {
        if (result && result.filename) {
          const voiceId = result.filename.replace('.wav', '')
          setSelectedVoice(voiceId)

          if (autoTranscribe) {
            ;(async () => {
              try {
                setRefTextLoading(true)
                const res = await transcribeReferenceAudio({ demoVoice: voiceId, language })
                const txt = res.cleaned_text || res.text || ''
                setRefText(txt)
                persistRefText(makeDemoRefKey(voiceId), txt)
              } catch (e) {
                console.error('ASR přepis selhal:', e)
              } finally {
                setRefTextLoading(false)
              }
            })()
          }
        }
      }, 500)
    } catch (err) {
      console.error('Chyba při načítání nahraného hlasu:', err)
      setError('Chyba při načítání nahraného hlasu')
    }
  }

  const handleYouTubeImport = async (result) => {
    try {
      // Obnovit seznam demo hlasů
      await loadDemoVoices()

      // Automaticky přepnout na demo hlas a vybrat nově stažený hlas
      setVoiceType('demo')
      setSelectedVoice(null) // Reset před nastavením nového
      setUploadedVoiceFileName(null)
      setVoiceQuality(result.quality || null)

      // Počkat na načtení demo hlasů a pak vybrat nový
      setTimeout(() => {
        if (result && result.filename) {
          const voiceId = result.filename.replace('.wav', '')
          setSelectedVoice(voiceId)

          if (autoTranscribe) {
            ;(async () => {
              try {
                setRefTextLoading(true)
                const res = await transcribeReferenceAudio({ demoVoice: voiceId, language })
                const txt = res.cleaned_text || res.text || ''
                setRefText(txt)
                persistRefText(makeDemoRefKey(voiceId), txt)
              } catch (e) {
                console.error('ASR přepis selhal:', e)
              } finally {
                setRefTextLoading(false)
              }
            })()
          }
        }
      }, 500)
    } catch (err) {
      console.error('Chyba při importu z YouTube:', err)
      setError('Chyba při načítání staženého hlasu')
    }
  }

  const handleGenerate = async () => {
    if (!text.trim()) {
      setError('Zadej text k syntéze')
      return
    }

    // Validace podle typu hlasu
    if (voiceType === 'upload') {
      if (!selectedVoice || !(selectedVoice instanceof File)) {
        setError('Vyber audio soubor k nahrání')
        return
      }
    } else if (voiceType === 'demo' || voiceType === 'record' || voiceType === 'youtube') {
      if (!selectedVoice) {
        setError('Vyber demo hlas nebo nahraj vlastní audio')
        return
      }
    } else {
      setError('Vyber typ hlasu')
      return
    }

    if (loading) return

    setLoading(true)
    setError(null)
    setGeneratedAudio(null)

    const jobId =
      (typeof crypto !== 'undefined' && crypto.randomUUID && crypto.randomUUID()) ||
      `${Date.now()}-${Math.random().toString(16).slice(2)}`

    setTtsProgress({ percent: 0, message: 'Odesílám požadavek…', eta_seconds: null })

    // Zruš staré progress tracking
    if (progressEventSourceRef.current) {
      progressEventSourceRef.current.close()
      progressEventSourceRef.current = null
    }

    try {
      // Pro upload je selectedVoice File objekt, pro ostatní typy je to string (ID hlasu)
      const voiceFile = voiceType === 'upload' ? selectedVoice : null
      const demoVoice = (voiceType === 'demo' || voiceType === 'record' || voiceType === 'youtube') ? selectedVoice : null

      // Sestavení parametrů pro F5-TTS
      const ttsParams = {
        ...ttsSettings,
        ...qualitySettings,
        // Volitelný přepis referenčního audia (zlepšuje výslovnost/stabilitu, když sedí k referenci)
        refText: refText || null
      }

      // Spuštění SSE pro progress tracking
      progressEventSourceRef.current = subscribeToTtsProgress(
        jobId,
        (progressData) => {
          setTtsProgress({
            percent: progressData.percent || 0,
            message: progressData.message || 'Generuji…',
            eta_seconds: progressData.eta_seconds
          })
        },
        (err) => {
          console.error('SSE chyba:', err)
        }
      )

      // F5TTS je fixně slovenský endpoint
      const result = await generateF5TTSSlovak(text, voiceFile, demoVoice, ttsParams, jobId)

      if (result.success) {
        setGeneratedAudio(result.audio_url)
        setTtsProgress({ percent: 100, message: 'Hotovo!', eta_seconds: null })
      } else {
        throw new Error(result.error || 'Generování selhalo')
      }
    } catch (err) {
      setError(err.message || 'Chyba při generování řeči')
      setTtsProgress(null)
    } finally {
      setLoading(false)
      if (progressEventSourceRef.current) {
        progressEventSourceRef.current.close()
        progressEventSourceRef.current = null
      }
    }
  }

  const handleVariantChange = (variant) => {
    setActiveVariant(variant)
    // Můžeme načíst uložené nastavení pro variantu (stejně jako XTTS)
  }

  return (
    <div className="f5tts-container">
      <div className="f5tts-header">
        <h2>F5-TTS Generování</h2>
        <p className="f5tts-description">
          Pokročilý TTS engine s flow matching. V této aplikaci je nastavený pouze pro slovenštinu.
        </p>
      </div>

      <div className="f5tts-content">
        <div className="f5tts-main">
          <TextInput
            value={text}
            onChange={setText}
            placeholder="Zadej text k syntéze..."
            maxLength={10000}
          />

          <VoiceSelector
            selectedVoice={selectedVoice}
            onVoiceSelect={setSelectedVoice}
            voiceType={voiceType}
            onVoiceTypeChange={setVoiceType}
            demoVoices={demoVoices}
            onVoiceUpload={handleVoiceUpload}
            onVoiceRecord={handleVoiceRecord}
            onYouTubeImport={handleYouTubeImport}
            uploadedVoiceFileName={uploadedVoiceFileName}
            voiceQuality={voiceQuality}
            language={language}
          />

          <div className="reftext-section" style={{ marginTop: '12px' }}>
            <label style={{ display: 'block', fontWeight: 600, marginBottom: '6px' }}>
              Přepis referenčního audia (ref_text) – volitelné
            </label>
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center', marginBottom: '8px' }}>
              <label style={{ display: 'flex', gap: '8px', alignItems: 'center', fontSize: '13px', opacity: 0.9 }}>
                <input
                  type="checkbox"
                  checked={autoTranscribe}
                  onChange={(e) => setAutoTranscribe(e.target.checked)}
                />
                Auto přepis po nahrání
              </label>
              <Button
                variant="secondary"
                size="sm"
                disabled={refTextLoading || (!selectedVoice && !uploadedVoiceFileName)}
                onClick={async () => {
                  try {
                    setRefTextLoading(true)
                    if (voiceType === 'upload' && selectedVoice instanceof File) {
                      const res = await transcribeReferenceAudio({ voiceFile: selectedVoice, language })
                      const txt = res.cleaned_text || res.text || ''
                      setRefText(txt)
                      if (uploadedVoiceFileName) {
                        persistRefText(makeUploadRefKey(uploadedVoiceFileName), txt)
                      }
                    } else if (selectedVoice) {
                      const res = await transcribeReferenceAudio({ demoVoice: selectedVoice, language })
                      const txt = res.cleaned_text || res.text || ''
                      setRefText(txt)
                      persistRefText(makeDemoRefKey(selectedVoice), txt)
                    }
                  } catch (e) {
                    console.error('ASR přepis selhal:', e)
                    setError(e.message || 'Chyba při přepisu audia')
                  } finally {
                    setRefTextLoading(false)
                  }
                }}
              >
                {refTextLoading ? 'Přepisuji…' : 'Přepsat referenci'}
              </Button>
            </div>
            <textarea
              value={refText}
              onChange={(e) => setRefText(e.target.value)}
              placeholder="Sem vlož přepis toho, co je namluveno v referenčním audiu. Když sedí s audiodatem, často to zlepší výslovnost."
              rows={3}
              style={{
                width: '100%',
                padding: '10px',
                borderRadius: '8px',
                border: '1px solid rgba(255,255,255,0.12)',
                background: 'rgba(0,0,0,0.15)',
                color: 'inherit',
                resize: 'vertical'
              }}
            />
            <div style={{ opacity: 0.8, fontSize: '12px', marginTop: '6px' }}>
              Tip: nejvíc pomáhá u vlastních hlasů (upload/record/YouTube). Pokud ref_text nesedí k referenci, může kvalitu naopak zhoršit.
            </div>
          </div>

          <div className="generate-section">
            <Button
              variant="primary"
              size="lg"
              onClick={handleGenerate}
              disabled={loading || !text.trim()}
              fullWidth
              icon={loading ? <Icon name="clock" size={16} /> : <Icon name="speaker" size={16} />}
            >
              {loading ? 'Generuji...' : 'Generovat řeč (F5-TTS Slovak)'}
            </Button>
          </div>

          {loading && <LoadingSpinner progress={ttsProgress} />}

          {generatedAudio && !loading && (
            <AudioPlayer audioUrl={generatedAudio} />
          )}

          {error && (
            <div className="error-message">
              {error}
            </div>
          )}
        </div>

        {showSettings && (
          <div className="settings-panel">
            <TTSSettings
              settings={ttsSettings}
              onChange={setTtsSettings}
              onReset={() => {
                setTtsSettings({
                  speed: 1.0,
                  temperature: 0.7,
                  lengthPenalty: 1.0,
                  repetitionPenalty: 2.0,
                  topK: 50,
                  topP: 0.85,
                  seed: null
                })
                setQualitySettings({
                  qualityMode: null,
                  enhancementPreset: 'natural',
                  enableEnhancement: true,
                  enableNormalization: false,
                  enableDenoiser: true,
                  enableCompressor: false,
                  enableDeesser: true,
                  enableEq: false,
                  enableTrim: true,
                  enableVad: true,
                  useHifigan: false,
                  enableDialectConversion: false,
                  dialectCode: null,
                  dialectIntensity: 1.0,
                  whisperIntensity: 1.0
                })
              }}
              qualitySettings={qualitySettings}
              onQualityChange={setQualitySettings}
              activeVariant={activeVariant}
              onVariantChange={handleVariantChange}
            />
          </div>
        )}

        <div className="settings-toggle">
          <Button
            variant="secondary"
            onClick={() => setShowSettings(!showSettings)}
            icon={<Icon name={showSettings ? "chevron-up" : "chevron-down"} size={16} />}
          >
            {showSettings ? 'Skrýt nastavení' : 'Zobrazit nastavení'}
          </Button>
        </div>
      </div>
    </div>
  )
}

export default F5TTS

