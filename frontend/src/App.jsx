import React, { useState, useEffect } from 'react'
import VoiceSelector from './components/VoiceSelector'
import TextInput from './components/TextInput'
import AudioRecorder from './components/AudioRecorder'
import AudioPlayer from './components/AudioPlayer'
import LoadingSpinner from './components/LoadingSpinner'
import { generateSpeech, getDemoVoices, getModelStatus } from './services/api'
import './App.css'

function App() {
  const [selectedVoice, setSelectedVoice] = useState('demo1')
  const [voiceType, setVoiceType] = useState('demo') // 'demo' | 'upload' | 'record' | 'youtube'
  const [uploadedVoice, setUploadedVoice] = useState(null)
  const [text, setText] = useState('')
  const [generatedAudio, setGeneratedAudio] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [demoVoices, setDemoVoices] = useState([])
  const [modelStatus, setModelStatus] = useState(null)

  useEffect(() => {
    // Načtení demo hlasů
    loadDemoVoices()
    // Kontrola statusu modelu
    checkModelStatus()
  }, [])

  const loadDemoVoices = async () => {
    try {
      const data = await getDemoVoices()
      setDemoVoices(data.voices || [])
      if (data.voices && data.voices.length > 0) {
        setSelectedVoice(data.voices[0].id)
      }
    } catch (err) {
      console.error('Chyba při načítání demo hlasů:', err)
    }
  }

  const checkModelStatus = async () => {
    try {
      const status = await getModelStatus()
      setModelStatus(status)
    } catch (err) {
      console.error('Chyba při kontrole statusu modelu:', err)
    }
  }

  const handleGenerate = async () => {
    if (!text.trim()) {
      setError('Zadejte text k syntéze')
      return
    }

    setLoading(true)
    setError(null)
    setGeneratedAudio(null)

    try {
      let voiceFile = null
      let demoVoice = null

      if (voiceType === 'upload' && uploadedVoice) {
        voiceFile = uploadedVoice
      } else if (voiceType === 'demo') {
        demoVoice = selectedVoice
      } else {
        setError('Vyberte nebo nahrajte hlas')
        setLoading(false)
        return
      }

      const result = await generateSpeech(text, voiceFile, demoVoice)
      setGeneratedAudio(result.audio_url)
    } catch (err) {
      setError(err.message || 'Chyba při generování řeči')
      console.error('Generate error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleVoiceUpload = (file) => {
    setUploadedVoice(file)
    setVoiceType('upload')
  }

  const handleVoiceRecord = async (result) => {
    try {
      // Obnovit seznam demo hlasů
      await loadDemoVoices()

      // Automaticky přepnout na demo hlas a vybrat nově nahraný hlas
      setVoiceType('demo')

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

      // Počkat na načtení demo hlasů a pak vybrat nový
      setTimeout(() => {
        const filename = result.filename.replace('.wav', '')
        setSelectedVoice(filename)
      }, 500)

    } catch (err) {
      console.error('Chyba při importu z YouTube:', err)
      setError('Chyba při načítání staženého hlasu')
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>🎤 XTTS-v2 Czech TTS Demo</h1>
        {modelStatus && (
          <div className="model-status">
            <span className={`status-indicator ${modelStatus.loaded ? 'loaded' : 'loading'}`}>
              {modelStatus.loaded ? '✓ Model načten' : '⏳ Načítání modelu...'}
            </span>
            <span className="device-info">
              Device: <strong>{modelStatus.device.toUpperCase()}</strong>
              {modelStatus.gpu_name && ` (${modelStatus.gpu_name})`}
              {modelStatus.device_forced && (
                <span className="device-forced"> [vynuceno: {modelStatus.force_device}]</span>
              )}
            </span>
          </div>
        )}
      </header>

      <main className="app-main">
        <div className="container">
          <VoiceSelector
            demoVoices={demoVoices}
            selectedVoice={selectedVoice}
            voiceType={voiceType}
            onVoiceSelect={setSelectedVoice}
            onVoiceTypeChange={setVoiceType}
            onVoiceUpload={handleVoiceUpload}
            onVoiceRecord={handleVoiceRecord}
            onYouTubeImport={handleYouTubeImport}
          />

          <TextInput
            value={text}
            onChange={setText}
            maxLength={500}
          />

          <div className="generate-section">
            <button
              className="btn-primary"
              onClick={handleGenerate}
              disabled={loading || !text.trim()}
            >
              {loading ? '⏳ Generuji...' : '🔊 Generovat řeč'}
            </button>
          </div>

          {loading && <LoadingSpinner />}

          {error && (
            <div className="error-message">
              ⚠️ {error}
            </div>
          )}

          {generatedAudio && !loading && (
            <AudioPlayer audioUrl={generatedAudio} />
          )}
        </div>
      </main>
    </div>
  )
}

export default App

