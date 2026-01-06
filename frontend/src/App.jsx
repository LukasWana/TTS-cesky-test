import React, { useState, useEffect, useMemo, useRef } from 'react'
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
import F5TTSCzech from './components/F5TTSCzech'
import AudioEditor from './components/AudioEditor'
import VoicePreparation from './components/VoicePreparation'
import Sidebar from './components/Sidebar'
import Alert from './components/Alert'
import Button from './components/ui/Button'
import Icon from './components/ui/Icons'
import SegmentedControl from './components/ui/SegmentedControl'
import { getDemoVoices, getModelStatus, transcribeReferenceAudio } from './services/api'
import { useTTSSettings } from './hooks/useTTSSettings'
import { useVariantManager } from './hooks/useVariantManager'
import { useTextVersions } from './hooks/useTextVersions'
import { useTTSProgress } from './hooks/useTTSProgress'
import { useTTSGeneration } from './hooks/useTTSGeneration'
import { getDefaultSlotSettings } from './constants/ttsDefaults'
import { SectionColorProvider } from './contexts/SectionColorContext'
import PromptsHistory from './components/PromptsHistory'
import HelpSidebar from './components/HelpSidebar'
import { XTTSHelpContent } from './components/HelpContent'
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
  const [xttsHelpOpen, setXttsHelpOpen] = useState(false)
  // Přepínač mezi XTTS a F5-TTS pro české slovo
  const [ttsEngine, setTtsEngine] = useState(() => {
    const saved = localStorage.getItem('czech_tts_engine')
    return saved || 'xtts' // výchozí XTTS
  })

  // --- States for ref_text (F5-TTS) ---
  const [refText, setRefText] = useState('')
  const [refTextLoading, setRefTextLoading] = useState(false)
  const [autoTranscribe, setAutoTranscribe] = useState(true)

  // --- Context for refText persistence ---
  const makeDemoRefKey = (voiceId, lang) => `f5tts_reftext:v1:${lang}:demo:${voiceId}`
  const makeUploadRefKey = (filename, lang) => `f5tts_reftext:v1:${lang}:upload:${filename}`

  const refTextStorageKey = useMemo(() => {
    if (ttsEngine !== 'f5tts' || activeTab !== 'generate') return null
    if (voiceType === 'upload') {
      return uploadedVoiceFileName ? makeUploadRefKey(uploadedVoiceFileName, 'cs') : null
    }
    if (voiceType === 'demo' || voiceType === 'record' || voiceType === 'youtube') {
      return typeof selectedVoice === 'string' && selectedVoice ? makeDemoRefKey(selectedVoice, 'cs') : null
    }
    return null
  }, [ttsEngine, activeTab, voiceType, selectedVoice, uploadedVoiceFileName])

  // Load refText from localStorage
  useEffect(() => {
    if (!refTextStorageKey) {
      if (ttsEngine !== 'f5tts') setRefText('')
      return
    }
    try {
      const stored = localStorage.getItem(refTextStorageKey)
      setRefText(stored || '')
    } catch (e) {
      setRefText('')
    }
  }, [refTextStorageKey, ttsEngine])

  // Save refText to localStorage (debounce)
  const refTextSaveTimeoutRef = useRef(null)
  useEffect(() => {
    if (!refTextStorageKey) return
    if (refTextSaveTimeoutRef.current) {
      clearTimeout(refTextSaveTimeoutRef.current)
    }
    refTextSaveTimeoutRef.current = setTimeout(() => {
      try {
        const v = (refText || '').toString()
        if (v.trim() === '') {
          localStorage.removeItem(refTextStorageKey)
        } else {
          localStorage.setItem(refTextStorageKey, v)
        }
      } catch (e) {
        console.warn('Nelze uložit ref_text do localStorage:', e)
      }
    }, 250)
    return () => {
      if (refTextSaveTimeoutRef.current) {
        clearTimeout(refTextSaveTimeoutRef.current)
      }
    }
  }, [refText, refTextStorageKey])

  const handleTranscribeRef = async (vFile = null, vDemo = null) => {
    try {
      setRefTextLoading(true)
      const res = await transcribeReferenceAudio({
        voiceFile: vFile || (voiceType === 'upload' ? uploadedVoice : null),
        demoVoice: vDemo || (voiceType === 'demo' ? selectedVoice : null),
        language: 'cs'
      })
      const txt = res.cleaned_text || res.text || ''
      setRefText(txt)
      if (refTextStorageKey) {
        localStorage.setItem(refTextStorageKey, txt)
      }
    } catch (e) {
      console.error('ASR přepis selhal:', e)
      setError(e.message || 'Chyba při přepisu audia')
    } finally {
      setRefTextLoading(false)
    }
  }

  // Uložit preferenci engine do localStorage při změně
  useEffect(() => {
    localStorage.setItem('czech_tts_engine', ttsEngine)
  }, [ttsEngine])


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
    startProgressTracking,
    ttsEngine // předat výběr engine
  )

  // Wrapper pro handleGenerate s saveTextVersion
  const handleGenerate = () => {
    handleGenerateBase(saveTextVersion, ttsEngine === 'f5tts' ? refText : null)
  }

  // Uložit výběr engine do localStorage při změně
  useEffect(() => {
    localStorage.setItem('czech_tts_engine', ttsEngine)
  }, [ttsEngine])

  const tabs = [
    { id: 'voicepreparation', label: 'příprava hlasů', icon: 'microphone' },
    { id: 'generate', label: 'české slovo', icon: 'speaker' },
    { id: 'f5tts-cs', label: 'F5-TTS (Czech)', icon: 'speaker' },
    { id: 'f5tts', label: 'slovenské slovo', icon: 'speaker' },
    { id: 'musicgen', label: 'hudba', icon: 'music' },
    { id: 'bark', label: 'FX & English', icon: 'speaker' },
    { id: 'audioeditor', label: 'Audio Editor', icon: 'sliders' },
    { id: 'history', label: 'Historie', icon: 'scroll' }
  ]

  // Určení jazyka na základě aktivního tabu
  const getLanguageForTab = (tabId) => {
    return tabId === 'f5tts' ? 'sk' : 'cs'
  }

  const currentLanguage = getLanguageForTab(activeTab)

  // Reset generovaného audio při změně varianty
  useEffect(() => {
    setGeneratedAudio(null)
    setError(null)
  }, [activeVariant, setGeneratedAudio, setError])

  // Načtení demo hlasů při změně jazyka (activeTab) a statusu modelu
  useEffect(() => {
    const lang = getLanguageForTab(activeTab)
    loadDemoVoices(lang)
    if (activeTab === 'generate') {
      checkModelStatus()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab])

  const loadDemoVoices = async (lang = 'cs') => {
    try {
      const data = await getDemoVoices(lang)
      const voices = data.voices || []
      setDemoVoices(voices)
      // Nastav první dostupný hlas, pokud je selectedVoice stále 'demo1' nebo pokud aktuální výběr v novém seznamu neexistuje
      const hasSelected = selectedVoice && voices.some(v => (v.id || v.name) === selectedVoice)
      if (voices.length > 0 && (!selectedVoice || selectedVoice === 'demo1' || !hasSelected)) {
        setSelectedVoice(voices[0].id || voices[0].name)
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


  const handleVoiceUpload = async (file, removeBackground = false) => {
    setUploadedVoice(file)
    setUploadedVoiceFileName(file.name)
    setVoiceType('upload')
    setVoiceQuality(null) // Reset quality for new upload

    if (autoTranscribe && activeTab === 'generate' && ttsEngine === 'f5tts') {
      handleTranscribeRef(file)
    }
  }

  const handleVoiceRecord = async (result) => {
    try {
      // Obnovit seznam demo hlasů
      await loadDemoVoices(currentLanguage)

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

          if (autoTranscribe && activeTab === 'generate' && ttsEngine === 'f5tts') {
            handleTranscribeRef(null, voiceId)
          }
        }
        // Přepnout na tab "české slovo" po úspěšném nahrání
        if (activeTab === 'voicepreparation') {
          setActiveTab('generate')
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
      await loadDemoVoices(currentLanguage)

      // Automaticky přepnout na demo hlas a vybrat nově stažený hlas
      setVoiceType('demo')
      setUploadedVoice(null)
      setUploadedVoiceFileName(null)
      setVoiceQuality(result.quality || null)

      // Počkat na načtení demo hlasů a pak vybrat nový
      setTimeout(() => {
        const filename = result.filename.replace('.wav', '')
        setSelectedVoice(filename)

        if (autoTranscribe && activeTab === 'generate' && ttsEngine === 'f5tts') {
          handleTranscribeRef(null, filename)
        }

        // Přepnout na tab "české slovo" po úspěšném nahrání
        if (activeTab === 'voicepreparation') {
          setActiveTab('generate')
        }
      }, 500)

    } catch (err) {
      console.error('Chyba při importu z YouTube:', err)
      setError('Chyba při načítání staženého hlasu')
    }
  }

  // Copy/Paste settings functionality
  const handleCopySettings = () => {
    try {
      console.log('🔵🔵🔵 COPY FUNKCE BYLA ZAVOLÁNA! 🔵🔵🔵')
      console.log('Aktuální profil:', activeVariant)
      console.log('Aktuální TTS nastavení:', ttsSettings)
      console.log('Aktuální Quality nastavení:', qualitySettings)

      const settingsToCopy = {
        ttsSettings: { ...ttsSettings },
        qualitySettings: { ...qualitySettings },
        timestamp: Date.now(),
        sourceVariant: activeVariant
      }

      sessionStorage.setItem('tts_copied_settings_xtts', JSON.stringify(settingsToCopy))
      console.log('✅ ÚSPĚŠNĚ ULOŽENO DO SESSIONSTORAGE!')
      console.log('📋 Nastavení zkopírována z varianty:', activeVariant)

      // Ověření
      const verify = sessionStorage.getItem('tts_copied_settings_xtts')
      console.log('🔍 Ověření - data v sessionStorage:', verify ? 'ANO ✓' : 'NE ✗')

    } catch (err) {
      console.error('❌ CHYBA při kopírování nastavení:', err)
      alert('CHYBA při kopírování: ' + err.message)
    }
  }

  const handlePasteSettings = () => {
    try {
      console.log('🟢🟢🟢 PASTE FUNKCE BYLA ZAVOLÁNA! 🟢🟢🟢')
      console.log('Cílový profil:', activeVariant)

      const copiedData = sessionStorage.getItem('tts_copied_settings_xtts')
      console.log('📦 Data ze sessionStorage:', copiedData ? 'NALEZENA ✓' : 'NENALEZENA ✗')

      if (!copiedData) {
        console.warn('⚠️  ŽÁDNÁ ZKOPÍROVANÁ NASTAVENÍ!')
        console.log('💡 TIP: Nejdřív musíte kliknout na "Kopírovat"')
        return false
      }

      const parsed = JSON.parse(copiedData)
      console.log('📥 Vkládám nastavení:', parsed.sourceVariant, '→', activeVariant)
      console.log('📥 TTS Settings:', parsed.ttsSettings)
      console.log('📥 Quality Settings:', parsed.qualitySettings)

      // Nastavit state - tímto se aktivuje useEffect pro uložení (automaticky přes debounce)
      console.log('🔄 Aktualizuji React state...')
      setTtsSettings({ ...parsed.ttsSettings })
      setQualitySettings({ ...parsed.qualitySettings })

      console.log('✅ ÚSPĚŠNĚ APLIKOVÁNO!')
      console.log('💾 Nastavení se automaticky uloží do localStorage přes debounce mechanismus')

      return true
    } catch (err) {
      console.error('❌ CHYBA při vkládání nastavení:', err)
      alert('CHYBA při vkládání: ' + err.message)
      return false
    }
  }

  return (
    <SectionColorProvider activeTab={activeTab}>
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

              {activeTab === 'voicepreparation' && (
                <VoicePreparation
                  onVoiceUpload={handleVoiceUpload}
                  onVoiceRecord={handleVoiceRecord}
                  onYouTubeImport={handleYouTubeImport}
                  uploadedVoiceFileName={uploadedVoiceFileName}
                  voiceQuality={voiceQuality}
                  language={currentLanguage}
                />
              )}

              {activeTab === 'generate' && (
                <div className="generate-layout">
                  <div className="generate-content">
                    <div className="section-header">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                        <h2>{ttsEngine === 'f5tts' ? 'F5-TTS' : 'XTTS'} (české slovo)</h2>
                        <button
                          onClick={() => setXttsHelpOpen(true)}
                          className="help-button"
                          title="Zobrazit nápovědu"
                          aria-label="Zobrazit nápovědu"
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: 'rgba(255, 255, 255, 0.7)',
                            cursor: 'pointer',
                            padding: '4px',
                            display: 'flex',
                            alignItems: 'center',
                            borderRadius: '4px',
                            transition: 'all 0.2s ease'
                          }}
                          onMouseEnter={(e) => {
                            e.target.style.background = 'rgba(255, 255, 255, 0.1)'
                            e.target.style.color = 'rgba(255, 255, 255, 0.9)'
                          }}
                          onMouseLeave={(e) => {
                            e.target.style.background = 'transparent'
                            e.target.style.color = 'rgba(255, 255, 255, 0.7)'
                          }}
                        >
                          <Icon name="info" size={20} />
                        </button>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '8px', marginBottom: '8px' }}>
                        <span style={{ fontSize: '14px', color: 'rgba(255, 255, 255, 0.7)' }}>Engine:</span>
                        <div style={{
                          display: 'flex',
                          gap: '4px',
                          background: 'rgba(255, 255, 255, 0.1)',
                          borderRadius: '6px',
                          padding: '2px'
                        }}>
                          <button
                            onClick={() => setTtsEngine('xtts')}
                            style={{
                              padding: '6px 12px',
                              borderRadius: '4px',
                              border: 'none',
                              background: ttsEngine === 'xtts' ? 'rgba(100, 150, 255, 0.3)' : 'transparent',
                              color: ttsEngine === 'xtts' ? '#fff' : 'rgba(255, 255, 255, 0.6)',
                              cursor: 'pointer',
                              fontWeight: ttsEngine === 'xtts' ? '600' : '400',
                              transition: 'all 0.2s ease'
                            }}
                          >
                            XTTS
                          </button>
                          <button
                            onClick={() => setTtsEngine('f5tts')}
                            style={{
                              padding: '6px 12px',
                              borderRadius: '4px',
                              border: 'none',
                              background: ttsEngine === 'f5tts' ? 'rgba(100, 150, 255, 0.3)' : 'transparent',
                              color: ttsEngine === 'f5tts' ? '#fff' : 'rgba(255, 255, 255, 0.6)',
                              cursor: 'pointer',
                              fontWeight: ttsEngine === 'f5tts' ? '600' : '400',
                              transition: 'all 0.2s ease'
                            }}
                          >
                            F5-TTS
                          </button>
                        </div>
                      </div>
                      <p className="section-hint">
                        {ttsEngine === 'f5tts'
                          ? 'Generování řeči v češtině pomocí finetunovaného F5-TTS modelu. Podporuje různé hlasy a varianty generování.'
                          : 'Generování řeči v češtině pomocí XTTS modelu. Podporuje různé hlasy a varianty generování.'}
                      </p>
                    </div>



                    <VoiceSelector
                      demoVoices={demoVoices}
                      selectedVoice={selectedVoice}
                      onVoiceSelect={setSelectedVoice}
                      voiceQuality={voiceQuality}
                      language={currentLanguage}
                    />

                    <TextInput
                      value={text}
                      onChange={setText}
                      maxLength={100000}
                      versions={textVersions}
                      onSaveVersion={() => saveTextVersion(text)}
                      onDeleteVersion={deleteTextVersion}
                    />

                    <PromptsHistory
                      modelType={ttsEngine === 'f5tts' ? 'f5tts' : 'xtts'}
                      onSelectPrompt={setText}
                    />

                    {ttsEngine === 'f5tts' && (
                      <div className="reftext-section" style={{ marginTop: '12px', marginBottom: '12px' }}>
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
                            onClick={() => handleTranscribeRef()}
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
                    )}

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
                                setTimeout(() => { }, 100 * index)
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
                      onCopySettings={handleCopySettings}
                      onPasteSettings={handlePasteSettings}
                    />
                  </div>
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
                <MusicGen
                  prompt={text}
                  setPrompt={setText}
                  versions={textVersions}
                  onSaveVersion={() => saveTextVersion(text)}
                  onDeleteVersion={deleteTextVersion}
                />
              )}

              {activeTab === 'f5tts-cs' && (
                <F5TTSCzech
                  text={text}
                  setText={setText}
                  versions={textVersions}
                  onSaveVersion={() => saveTextVersion(text)}
                  onDeleteVersion={deleteTextVersion}
                />
              )}

              {activeTab === 'f5tts' && (
                <F5TTS
                  text={text}
                  setText={setText}
                  versions={textVersions}
                  onSaveVersion={() => saveTextVersion(text)}
                  onDeleteVersion={deleteTextVersion}
                />
              )}

              {activeTab === 'bark' && (
                <Bark
                  prompt={text}
                  setPrompt={setText}
                  versions={textVersions}
                  onSaveVersion={() => saveTextVersion(text)}
                  onDeleteVersion={deleteTextVersion}
                />
              )}

              <div style={{ display: activeTab === 'audioeditor' ? 'block' : 'none' }}>
                <AudioEditor />
              </div>
            </div>
          </main>
        </div>
      </div>

      <HelpSidebar
        isOpen={xttsHelpOpen}
        onClose={() => setXttsHelpOpen(false)}
        title="Nápověda - XTTS (české slovo)"
      >
        <XTTSHelpContent />
      </HelpSidebar>
    </SectionColorProvider>
  )
}

export default App

