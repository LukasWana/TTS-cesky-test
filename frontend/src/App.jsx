import React, { useState, useEffect, useRef } from 'react'
import VoiceSelector from './components/VoiceSelector'
import TextInput from './components/TextInput'
import AudioRecorder from './components/AudioRecorder'
import AudioPlayer from './components/AudioPlayer'
import LoadingSpinner from './components/LoadingSpinner'
import TTSSettings from './components/TTSSettings'
import History from './components/History'
import Tabs from './components/Tabs'
import { generateSpeech, getDemoVoices, getModelStatus } from './services/api'
import './App.css'

// Výchozí hodnoty TTS parametrů
const DEFAULT_TTS_SETTINGS = {
  speed: 1.0,
  temperature: 0.7,
  lengthPenalty: 1.0,
  repetitionPenalty: 2.0,
  topK: 50,
  topP: 0.85,
  seed: null
}

const DEFAULT_QUALITY_SETTINGS = {
  qualityMode: null,
  enhancementPreset: 'natural',
  enableEnhancement: true,
  // Nové možnosti:
  multiPass: false,
  multiPassCount: 3,
  enableVad: true,
  enableBatch: true,
  useHifigan: false
}

// Klíče pro localStorage - varianty jsou vázané na konkrétní hlas (id)
const getVariantStorageKey = (voiceId, variantId) => `xtts_voice_${voiceId}_variant_${variantId}`

// Pomocné funkce pro localStorage
const saveVariantSettings = (voiceId, variantId, settings) => {
  try {
    localStorage.setItem(getVariantStorageKey(voiceId, variantId), JSON.stringify(settings))
  } catch (err) {
    console.error('Chyba při ukládání nastavení:', err)
  }
}

const loadVariantSettings = (voiceId, variantId) => {
  try {
    const stored = localStorage.getItem(getVariantStorageKey(voiceId, variantId))
    if (stored) {
      return JSON.parse(stored)
    }
  } catch (err) {
    console.error('Chyba při načítání nastavení:', err)
  }
  return null
}

function App() {
  const [activeVariant, setActiveVariant] = useState('variant1') // 'variant1' | 'variant2' | ... | 'variant5'
  const [activeTab, setActiveTab] = useState('generate') // 'generate' | 'history'

  // Nastavení hlasu
  const [selectedVoice, setSelectedVoice] = useState('demo1')
  const [voiceType, setVoiceType] = useState('demo') // 'demo' | 'upload' | 'record' | 'youtube'
  const [uploadedVoice, setUploadedVoice] = useState(null)
  const [uploadedVoiceFileName, setUploadedVoiceFileName] = useState(null)
  const [text, setText] = useState('')
  const [generatedAudio, setGeneratedAudio] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [demoVoices, setDemoVoices] = useState([])
  const [modelStatus, setModelStatus] = useState(null)

  // Nastavení pro aktuální variantu (vázané na vybraný hlas)
  const [ttsSettings, setTtsSettings] = useState(DEFAULT_TTS_SETTINGS)
  const [qualitySettings, setQualitySettings] = useState(DEFAULT_QUALITY_SETTINGS)

  const tabs = [
    { id: 'generate', label: 'Generovat', icon: '🎤' },
    { id: 'history', label: 'Historie', icon: '📜' }
  ]

  // Ref pro sledování, zda se právě načítá nastavení (aby se neukládalo při načítání)
  const isLoadingSettingsRef = useRef(false)

  // Ref pro aktuální nastavení - vždy obsahuje nejnovější hodnoty
  const currentSettingsRef = useRef({
    ttsSettings: DEFAULT_TTS_SETTINGS,
    qualitySettings: DEFAULT_QUALITY_SETTINGS
  })

  // Aktualizovat ref při každé změně nastavení
  useEffect(() => {
    currentSettingsRef.current = {
      ttsSettings: { ...ttsSettings },
      qualitySettings: { ...qualitySettings }
    }
  }, [ttsSettings, qualitySettings])

  // Debounce timer pro ukládání
  const saveTimeoutRef = useRef(null)

  const saveCurrentVariantNow = () => {
    // Ukládat pouze pro demo hlasy a když je selectedVoice skutečný hlas (ne 'demo1')
    if (!selectedVoice || selectedVoice === 'demo1') return
    if (voiceType !== 'demo') return
    if (isLoadingSettingsRef.current) return

    // Použít hodnoty z ref (vždy aktuální)
    const settings = {
      ttsSettings: { ...currentSettingsRef.current.ttsSettings },
      qualitySettings: { ...currentSettingsRef.current.qualitySettings }
    }

    try {
      saveVariantSettings(selectedVoice, activeVariant, settings)
      console.log('💾 Ukládám nastavení pro:', selectedVoice, activeVariant, settings) // Debug
    } catch (err) {
      console.error('Chyba při ukládání nastavení:', err)
    }
  }

  const handleVariantChange = (nextVariant) => {
    if (nextVariant === activeVariant) return

    // Zrušit případný pending debounce
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current)
      saveTimeoutRef.current = null
    }

    // Než přepneme variantu, ulož aktuální stav synchronně (bez debounce)
    saveCurrentVariantNow()

    // Změnit variantu
    setActiveVariant(nextVariant)
  }

  // Uložení nastavení aktuální varianty do localStorage (vázané na hlas)
  // Ukládá se s debounce při změně nastavení, ale ne při načítání nebo změně varianty
  useEffect(() => {
    if (isLoadingSettingsRef.current) return
    if (!selectedVoice || selectedVoice === 'demo1') return
    if (voiceType !== 'demo') return

    // Zrušit předchozí timeout
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current)
    }

    // Nastavit nový timeout pro debounce (300ms)
    saveTimeoutRef.current = setTimeout(() => {
      saveCurrentVariantNow()
      saveTimeoutRef.current = null
    }, 300)

    // Cleanup - zrušit timeout při unmount nebo změně závislostí
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current)
        saveTimeoutRef.current = null
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ttsSettings, qualitySettings, selectedVoice, voiceType])

  // Načtení nastavení při změně varianty nebo hlasu
  useEffect(() => {
    // Načítat pouze pro demo hlasy a když je selectedVoice skutečný hlas
    if (!selectedVoice || selectedVoice === 'demo1') return
    if (voiceType !== 'demo') return

    // Zrušit případný pending debounce pro ukládání
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current)
      saveTimeoutRef.current = null
    }

    // Reset generovaného audio při změně varianty
    setGeneratedAudio(null)
    setError(null)

    // Nastav flag, že se právě načítá (aby se neukládalo)
    isLoadingSettingsRef.current = true

    // Načíst nastavení
    const saved = loadVariantSettings(selectedVoice, activeVariant)
    console.log('📖 Načítám nastavení pro:', selectedVoice, activeVariant, saved) // Debug

    // Validace a načtení nastavení atomicky
    let loadedTts, loadedQuality

    if (saved && saved.ttsSettings && saved.qualitySettings) {
      // Validace a načtení TTS nastavení s fallback na výchozí hodnoty
      loadedTts = {
        speed: typeof saved.ttsSettings.speed === 'number' && !isNaN(saved.ttsSettings.speed)
          ? saved.ttsSettings.speed
          : DEFAULT_TTS_SETTINGS.speed,
        temperature: typeof saved.ttsSettings.temperature === 'number' && !isNaN(saved.ttsSettings.temperature)
          ? saved.ttsSettings.temperature
          : DEFAULT_TTS_SETTINGS.temperature,
        lengthPenalty: typeof saved.ttsSettings.lengthPenalty === 'number' && !isNaN(saved.ttsSettings.lengthPenalty)
          ? saved.ttsSettings.lengthPenalty
          : DEFAULT_TTS_SETTINGS.lengthPenalty,
        repetitionPenalty: typeof saved.ttsSettings.repetitionPenalty === 'number' && !isNaN(saved.ttsSettings.repetitionPenalty)
          ? saved.ttsSettings.repetitionPenalty
          : DEFAULT_TTS_SETTINGS.repetitionPenalty,
        topK: typeof saved.ttsSettings.topK === 'number' && !isNaN(saved.ttsSettings.topK)
          ? saved.ttsSettings.topK
          : DEFAULT_TTS_SETTINGS.topK,
        topP: typeof saved.ttsSettings.topP === 'number' && !isNaN(saved.ttsSettings.topP)
          ? saved.ttsSettings.topP
          : DEFAULT_TTS_SETTINGS.topP,
        seed: saved.ttsSettings.seed !== undefined && saved.ttsSettings.seed !== null
          ? (typeof saved.ttsSettings.seed === 'number' ? saved.ttsSettings.seed : null)
          : DEFAULT_TTS_SETTINGS.seed
      }

      // Validace a načtení quality nastavení s fallback na výchozí hodnoty
      loadedQuality = {
        qualityMode: saved.qualitySettings.qualityMode !== undefined
          ? saved.qualitySettings.qualityMode
          : DEFAULT_QUALITY_SETTINGS.qualityMode,
        enhancementPreset: typeof saved.qualitySettings.enhancementPreset === 'string'
          ? saved.qualitySettings.enhancementPreset
          : DEFAULT_QUALITY_SETTINGS.enhancementPreset,
        enableEnhancement: typeof saved.qualitySettings.enableEnhancement === 'boolean'
          ? saved.qualitySettings.enableEnhancement
          : DEFAULT_QUALITY_SETTINGS.enableEnhancement
      }
    } else {
      // Výchozí nastavení pro novou variantu
      loadedTts = { ...DEFAULT_TTS_SETTINGS }
      loadedQuality = { ...DEFAULT_QUALITY_SETTINGS }
    }

    // Aktualizuj state atomicky (všechno najednou)
    setTtsSettings(loadedTts)
    setQualitySettings(loadedQuality)

    // Aktualizuj také ref
    currentSettingsRef.current = {
      ttsSettings: { ...loadedTts },
      qualitySettings: { ...loadedQuality }
    }

    // Po načtení resetuj flag (v cleanup funkci pro jistotu)
    const timeoutId = setTimeout(() => {
      isLoadingSettingsRef.current = false
    }, 0)

    // Cleanup funkce
    return () => {
      clearTimeout(timeoutId)
      // Zajistit, že se flag resetuje i při unmount
      isLoadingSettingsRef.current = false
    }
  }, [activeVariant, selectedVoice, voiceType])

  useEffect(() => {
    // Načtení demo hlasů
    loadDemoVoices()
    // Kontrola statusu modelu
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

      // Převod nastavení na formát pro API
      const ttsParams = {
        speed: ttsSettings.speed,
        temperature: ttsSettings.temperature,
        lengthPenalty: ttsSettings.lengthPenalty,
        repetitionPenalty: ttsSettings.repetitionPenalty,
        topK: ttsSettings.topK,
        topP: ttsSettings.topP,
        seed: ttsSettings.seed,
        qualityMode: qualitySettings.qualityMode,
        enhancementPreset: qualitySettings.enhancementPreset,
        enableEnhancement: qualitySettings.enableEnhancement,
        // Nové parametry:
        multiPass: qualitySettings.multiPass,
        multiPassCount: qualitySettings.multiPassCount,
        enableVad: qualitySettings.enableVad,
        enableBatch: qualitySettings.enableBatch,
        useHifigan: qualitySettings.useHifigan
      }

      const result = await generateSpeech(text, voiceFile, demoVoice, ttsParams)

      // Pokud je multi-pass, zobrazit varianty
      if (result.variants && result.variants.length > 0) {
        // Prozatím použijeme první variantu
        // V budoucnu můžete přidat VariantSelector komponent
        setGeneratedAudio(result.variants[0].audio_url)
        console.log('Multi-pass: vygenerováno', result.variants.length, 'variant')
      } else {
        setGeneratedAudio(result.audio_url)
      }
    } catch (err) {
      setError(err.message || 'Chyba při generování řeči')
      console.error('Generate error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleVoiceUpload = (file) => {
    setUploadedVoice(file)
    setUploadedVoiceFileName(file.name)
    setVoiceType('upload')
  }

  const handleVoiceRecord = async (result) => {
    try {
      // Obnovit seznam demo hlasů
      await loadDemoVoices()

      // Automaticky přepnout na demo hlas a vybrat nově nahraný hlas
      setVoiceType('demo')
      setUploadedVoice(null)
      setUploadedVoiceFileName(null)

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
          {/* Záložky Generovat/Historie */}
          <Tabs activeTab={activeTab} onTabChange={setActiveTab} tabs={tabs} />

          {activeTab === 'generate' && (
            <>
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
              />

              <TextInput
                value={text}
                onChange={setText}
                maxLength={500}
              />

          <TTSSettings
            settings={ttsSettings}
            onChange={setTtsSettings}
            onReset={() => {
              // Resetovat nastavení pro aktuální variantu
              const resetTts = { ...DEFAULT_TTS_SETTINGS }
              const resetQuality = { ...DEFAULT_QUALITY_SETTINGS }

              setTtsSettings(resetTts)
              setQualitySettings(resetQuality)

              // Aktualizovat ref okamžitě
              currentSettingsRef.current = {
                ttsSettings: { ...resetTts },
                qualitySettings: { ...resetQuality }
              }

              // Uložit resetované hodnoty do localStorage pro tuto variantu
              if (selectedVoice && selectedVoice !== 'demo1' && voiceType === 'demo') {
                const resetSettings = {
                  ttsSettings: { ...resetTts },
                  qualitySettings: { ...resetQuality }
                }
                saveVariantSettings(selectedVoice, activeVariant, resetSettings)
              }
            }}
            qualitySettings={qualitySettings}
            onQualityChange={setQualitySettings}
            activeVariant={activeVariant}
            onVariantChange={handleVariantChange}
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
            </>
          )}

          {activeTab === 'history' && (
            <History />
          )}
        </div>
      </main>
    </div>
  )
}

export default App

