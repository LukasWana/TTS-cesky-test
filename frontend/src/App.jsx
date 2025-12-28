import React, { useState, useEffect } from 'react'
import VoiceSelector from './components/VoiceSelector'
import TextInput from './components/TextInput'
import AudioRecorder from './components/AudioRecorder'
import AudioPlayer from './components/AudioPlayer'
import LoadingSpinner from './components/LoadingSpinner'
import TTSSettings from './components/TTSSettings'
import History from './components/History'
import MusicGen from './components/MusicGen'
import Bark from './components/Bark'
import F5TTS from './components/F5TTS'
import AudioEditor from './components/AudioEditor'
import Sidebar from './components/Sidebar'
import Alert from './components/Alert'
import Button from './components/ui/Button'
import Icon from './components/ui/Icons'
import { getDemoVoices, getModelStatus } from './services/api'
import { useTTSSettings } from './hooks/useTTSSettings'
import { useVariantManager } from './hooks/useVariantManager'
import { useTextVersions } from './hooks/useTextVersions'
import { useTTSProgress } from './hooks/useTTSProgress'
import { useTTSGeneration } from './hooks/useTTSGeneration'
import { getDefaultSlotSettings } from './constants/ttsDefaults'
import './App.css'

function App() {
  const [activeTab, setActiveTab] = useState('generate')
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [selectedVoice, setSelectedVoice] = useState('demo1')
  const [voiceType, setVoiceType] = useState('demo')
  const [uploadedVoice, setUploadedVoice] = useState(null)
  const [uploadedVoiceFileName, setUploadedVoiceFileName] = useState(null)
  const [demoVoices, setDemoVoices] = useState([])
  const [modelStatus, setModelStatus] = useState(null)
  const [voiceQuality, setVoiceQuality] = useState(null)
  const [showSettings, setShowSettings] = useState(true)

  // Hooks - useVariantManager musí být před useTTSSettings, protože useTTSSettings potřebuje activeVariant
  const { activeVariant, handleVariantChange, setSaveCurrentVariantNow } = useVariantManager()
  const { ttsSettings, setTtsSettings, qualitySettings, setQualitySettings, saveCurrentVariantNow } = useTTSSettings(
    selectedVoice,
    voiceType,
    activeVariant
  )

  // Propojit saveCurrentVariantNow s useVariantManager
  useEffect(() => {
    setSaveCurrentVariantNow(saveCurrentVariantNow)
  }, [saveCurrentVariantNow, setSaveCurrentVariantNow])
  const { text, setText, textVersions, saveTextVersion, deleteTextVersion } = useTextVersions(activeTab)
  const { ttsProgress, startProgressTracking, stopProgressTracking } = useTTSProgress()
  const {
    loading,
    error,
    setError,
    generatedAudio,
    setGeneratedAudio,
    generatedVariants,
    handleGenerate: handleGenerateBase
  } = useTTSGeneration(
    text,
    selectedVoice,
    voiceType,
    uploadedVoice,
    ttsSettings,
    qualitySettings,
    startProgressTracking
  )

  // Wrapper pro handleGenerate s saveTextVersion
  const handleGenerate = () => {
    handleGenerateBase(saveTextVersion)
  }

  const tabs = [
    { id: 'generate', label: 'české slovo', icon: 'microphone' },
    { id: 'f5tts', label: 'slovenské slovo', icon: 'speaker' },
    { id: 'musicgen', label: 'hudba', icon: 'music' },
    { id: 'bark', label: 'FX & English', icon: 'speaker' },
    { id: 'audioeditor', label: 'Audio Editor', icon: 'sliders' },
    { id: 'history', label: 'Historie', icon: 'scroll' }
  ]

  // Reset generovaného audio při změně varianty
  useEffect(() => {
    setGeneratedAudio(null)
    setError(null)
  }, [activeVariant, setGeneratedAudio, setError])

  // Načtení demo hlasů a statusu modelu
  useEffect(() => {
    loadDemoVoices()
    checkModelStatus()
  }, [])

  const loadDemoVoices = async () => {
    try {
      const data = await getDemoVoices()
      const voices = data.voices || []
      setDemoVoices(voices)
      // Nastav první dostupný hlas, pokud je selectedVoice stále 'demo1'
      if (selectedVoice === 'demo1' && voices.length > 0) {
        setSelectedVoice(voices[0].id)
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


  const handleVoiceUpload = async (file) => {
    setUploadedVoice(file)
    setUploadedVoiceFileName(file.name)
    setVoiceType('upload')
    setVoiceQuality(null) // Reset quality for new upload

    // Poznámka: uploadVoice API zatím nevoláme přímo zde,
    // ale až v handleGenerate pokud je voiceType 'upload'.
    // Pro okamžitou analýzu bychom museli volat uploadVoice dříve.
  }

  const handleVoiceRecord = async (result) => {
    try {
      // Obnovit seznam demo hlasů
      await loadDemoVoices()

      // Automaticky přepnout na demo hlas a vybrat nově nahraný hlas
      setVoiceType('demo')
      setUploadedVoice(null)
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
      setUploadedVoice(null)
      setUploadedVoiceFileName(null)
      setVoiceQuality(result.quality || null)

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
      <Sidebar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        tabs={tabs}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        modelStatus={modelStatus}
      />

      <div className={`app-content ${sidebarOpen ? 'sidebar-open' : ''}`}>
        <header className="app-header">
          <button
            className="app-menu-toggle"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            aria-label="Otevřít menu"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="3" y1="12" x2="21" y2="12"></line>
              <line x1="3" y1="6" x2="21" y2="6"></line>
              <line x1="3" y1="18" x2="21" y2="18"></line>
            </svg>
          </button>
        </header>

        {error && (
          <Alert
            type="error"
            message={error}
            onClose={() => setError(null)}
          />
        )}

        <main className="app-main">
        <div className="container">
          <div className="main-header-row">

            {activeTab === 'generate' && (
              <button
                className={`btn-toggle-settings ${!showSettings ? 'collapsed' : ''}`}
                onClick={() => setShowSettings(!showSettings)}
                title={showSettings ? "Skrýt nastavení" : "Zobrazit nastavení"}
              >
                {showSettings ? (
                  <>
                    <Icon name="close" size={14} style={{ display: 'inline-block', marginRight: '6px', verticalAlign: 'middle' }} />
                    Skrýt nastavení
                  </>
                ) : (
                  <>
                    <Icon name="settings" size={14} style={{ display: 'inline-block', marginRight: '6px', verticalAlign: 'middle' }} />
                    Nastavení
                  </>
                )}
              </button>
            )}
          </div>

          {activeTab === 'generate' && (
            <div className={`generate-layout ${!showSettings ? 'full-width' : ''}`}>
              <div className="generate-content">
                <VoiceSelector
                  demoVoices={demoVoices}
                  selectedVoice={selectedVoice}
                  voiceType={voiceType}
                  uploadedVoiceFileName={uploadedVoiceFileName}
                  onVoiceSelect={setSelectedVoice}
                  onVoiceTypeChange={setVoiceType}
                  onVoiceUpload={handleVoiceUpload}
                  onVoiceRecord={handleVoiceRecord}
                  onYouTubeImport={handleYouTubeImport}
                  voiceQuality={voiceQuality}
                  language="cs"
                />

                <TextInput
                  value={text}
                  onChange={setText}
                  maxLength={100000}
                  versions={textVersions}
                  onSaveVersion={() => saveTextVersion(text)}
                  onDeleteVersion={deleteTextVersion}
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
                    {loading ? 'Generuji...' : 'Generovat řeč'}
                  </Button>
                </div>

                {loading && <LoadingSpinner progress={ttsProgress} />}

                {generatedVariants && generatedVariants.length > 0 && !loading ? (
                  <div className="variants-output-list">
                    <div className="variants-header">
                      <h3>✨ Vygenerované varianty ({generatedVariants.length})</h3>
                      <button
                        className="btn-download-all"
                        onClick={() => {
                          generatedVariants.forEach((variant, index) => {
                            const link = document.createElement('a')
                            link.href = `http://localhost:8000${variant.audio_url}`
                            link.download = variant.filename || `varianta-${index + 1}.wav`
                            document.body.appendChild(link)
                            link.click()
                            document.body.removeChild(link)
                            // Malé zpoždění mezi stahováním, aby se soubory stáhly správně
                            setTimeout(() => {}, 100 * index)
                          })
                        }}
                        title="Stáhnout všechny varianty"
                      >
                        💾 Stáhnout všechny
                      </button>
                    </div>
                    <div className="variants-grid">
                      {generatedVariants.map((variant, index) => (
                        <div key={index} className="variant-output-item">
                          <div className="variant-label">Varianta {index + 1}</div>
                          <AudioPlayer audioUrl={variant.audio_url} />
                          <div className="variant-meta-info">
                            Seed: {variant.seed} | Temp: {variant.temperature?.toFixed(2)}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  generatedAudio && !loading && (
                    <AudioPlayer audioUrl={generatedAudio} />
                  )
                )}
              </div>

              {showSettings && (
                <div className="settings-panel">
                  <TTSSettings
                    settings={ttsSettings}
                    onChange={setTtsSettings}
                    onReset={() => {
                      // Resetovat nastavení pro aktuální variantu na slot-specifické defaultní hodnoty
                      const defaultSlot = getDefaultSlotSettings(activeVariant)
                      const resetTts = { ...defaultSlot.ttsSettings }
                      const resetQuality = { ...defaultSlot.qualitySettings }

                      setTtsSettings(resetTts)
                      setQualitySettings(resetQuality)

                      // Uložit resetované hodnoty do localStorage pro tuto variantu
                      // saveCurrentVariantNow se zavolá automaticky přes debounce v useTTSSettings
                    }}
                    qualitySettings={qualitySettings}
                    onQualityChange={setQualitySettings}
                    activeVariant={activeVariant}
                    onVariantChange={handleVariantChange}
                  />
                </div>
              )}
            </div>
          )}

          {activeTab === 'history' && (
            <History
              onRestoreText={(restoredText) => {
                setText(restoredText)
                setActiveTab('generate')
                window.scrollTo({ top: 0, behavior: 'smooth' })
              }}
              onRestorePrompt={(prompt) => {
                setText(prompt)
                window.scrollTo({ top: 0, behavior: 'smooth' })
              }}
              onSwitchTab={(tab) => {
                setActiveTab(tab)
                window.scrollTo({ top: 0, behavior: 'smooth' })
              }}
            />
          )}

          {activeTab === 'musicgen' && (
            <MusicGen prompt={text} setPrompt={setText} />
          )}

          {activeTab === 'f5tts' && (
            <F5TTS text={text} setText={setText} />
          )}

          {activeTab === 'bark' && (
            <Bark prompt={text} setPrompt={setText} />
          )}

          {activeTab === 'audioeditor' && (
            <AudioEditor />
          )}
        </div>
      </main>
      </div>
    </div>
  )
}

export default App

