import React, { useState, useRef, useEffect } from 'react'
import VoiceSelector from './VoiceSelector'
import TextInput from './TextInput'
import AudioPlayer from './AudioPlayer'
import LoadingSpinner from './LoadingSpinner'
import TTSSettings from './TTSSettings'
import Button from './ui/Button'
import Icon from './ui/Icons'
import { generateF5TTS, generateF5TTSSlovak, getDemoVoices, subscribeToTtsProgress, uploadVoice, recordVoice, downloadYouTubeVoice } from '../services/api'
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
  const [language, setLanguage] = useState('cs') // 'cs' nebo 'sk'
  const [uploadedVoiceFileName, setUploadedVoiceFileName] = useState(null)
  const [voiceQuality, setVoiceQuality] = useState(null)

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
        const data = await getDemoVoices()
        const voices = data.voices || data || [] // Podpora obou formátů response
        setDemoVoices(voices)
        if (voices.length > 0 && !selectedVoice) {
          // Použít voice.id (stejně jako v App.jsx)
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
      const data = await getDemoVoices()
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
        refText: null // Můžeme přidat UI pro ref_text později
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

      // Použít správný endpoint podle jazyka
      const result = language === 'sk'
        ? await generateF5TTSSlovak(text, voiceFile, demoVoice, ttsParams, jobId)
        : await generateF5TTS(text, voiceFile, demoVoice, ttsParams, jobId)

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
          Pokročilý TTS engine s flow matching. Podporuje češtinu i slovenštinu.
        </p>
        <div className="language-selector" style={{ marginTop: '10px' }}>
          <label style={{ marginRight: '10px' }}>Jazyk:</label>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            style={{ padding: '5px 10px', fontSize: '14px' }}
          >
            <option value="cs">Čeština</option>
            <option value="sk">Slovenština</option>
          </select>
        </div>
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
          />

          <div className="generate-section">
            <Button
              variant="primary"
              size="lg"
              onClick={handleGenerate}
              disabled={loading || !text.trim()}
              fullWidth
              icon={loading ? <Icon name="clock" size={16} /> : <Icon name="speaker" size={16} />}
            >
              {loading ? 'Generuji...' : `Generovat řeč (F5-TTS ${language === 'sk' ? 'Slovak' : ''})`}
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

