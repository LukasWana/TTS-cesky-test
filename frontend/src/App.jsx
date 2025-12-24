import React, { useState, useEffect, useRef } from 'react'
import VoiceSelector from './components/VoiceSelector'
import TextInput from './components/TextInput'
import AudioRecorder from './components/AudioRecorder'
import AudioPlayer from './components/AudioPlayer'
import LoadingSpinner from './components/LoadingSpinner'
import TTSSettings from './components/TTSSettings'
import History from './components/History'
import Tabs from './components/Tabs'
import MusicGen from './components/MusicGen'
import Bark from './components/Bark'
import AudioEditor from './components/AudioEditor'
import { generateSpeech, getDemoVoices, getModelStatus, getTtsProgress, subscribeToTtsProgress } from './services/api'
import './App.css'

// Výchozí hodnoty TTS parametrů (základní)
const BASE_TTS_SETTINGS = {
  speed: 1.0,
  temperature: 0.7,
  lengthPenalty: 1.0,
  repetitionPenalty: 2.0,
  topK: 50,
  topP: 0.85,
  seed: null
}

const BASE_QUALITY_SETTINGS = {
  qualityMode: null,
  enhancementPreset: 'natural',
  enableEnhancement: true,
  // Nové možnosti:
  multiPass: false,
  multiPassCount: 3,
  enableVad: true,
  enableBatch: true,
  useHifigan: false,
  // HiFi-GAN nastavení
  hifiganRefinementIntensity: 1.0,
  hifiganNormalizeOutput: true,
  hifiganNormalizeGain: 0.95,
  // Normalizace (RMS/peak + limiter) může působit "přebuzile" – necháme defaultně vypnuté
  enableNormalization: false,
  enableDenoiser: true,
  // Komprese často dělá "nalezlý/přebuzelý" pocit – necháme defaultně vypnuté
  enableCompressor: false,
  enableDeesser: true,
  // EQ (zvýraznění řečového pásma) může působit "přebuzile"/ostře – necháme defaultně vypnuté
  enableEq: false,
  enableTrim: true,
  // Dialect conversion
  enableDialectConversion: false,
  dialectCode: null,
  dialectIntensity: 1.0,
  // Whisper efekt
  whisperIntensity: 1.0
}

// Defaultní nastavení pro sloty P1-P5
const DEFAULT_SLOT_SETTINGS = {
  variant1: { // P1 - Vysoká kvalita
    ttsSettings: {
      speed: 1.0,
      temperature: 0.5,
      lengthPenalty: 1.2,
      repetitionPenalty: 2.5,
      topK: 30,
      topP: 0.8,
      seed: null
    },
    qualitySettings: {
      qualityMode: 'high_quality',
      enhancementPreset: 'high_quality',
      enableEnhancement: true,
      multiPass: false,
      multiPassCount: 3,
      enableVad: true,
      enableBatch: true,
      useHifigan: false,
      hifiganRefinementIntensity: 1.0,
      hifiganNormalizeOutput: true,
      hifiganNormalizeGain: 0.95,
      enableNormalization: true,
      enableDenoiser: true,
      enableCompressor: true,
      enableDeesser: true,
      enableEq: true,
      enableTrim: true,
      enableDialectConversion: false,
      dialectCode: null,
      dialectIntensity: 1.0,
      whisperIntensity: 1.0
    }
  },
  variant2: { // P2 - Přirozený
    ttsSettings: {
      speed: 1.0,
      temperature: 0.7,
      lengthPenalty: 1.0,
      repetitionPenalty: 2.0,
      topK: 50,
      topP: 0.85,
      seed: null
    },
    qualitySettings: {
      qualityMode: 'natural',
      enhancementPreset: 'natural',
      enableEnhancement: true,
      multiPass: false,
      multiPassCount: 3,
      enableVad: true,
      enableBatch: true,
      useHifigan: false,
      hifiganRefinementIntensity: 1.0,
      hifiganNormalizeOutput: true,
      hifiganNormalizeGain: 0.95,
      enableNormalization: false,
      enableDenoiser: false,
      enableCompressor: true,
      enableDeesser: true,
      enableEq: true,
      enableTrim: true,
      enableDialectConversion: false,
      dialectCode: null,
      dialectIntensity: 1.0,
      whisperIntensity: 1.0
    }
  },
  variant3: { // P3 - Rychlý
    ttsSettings: {
      speed: 1.0,
      temperature: 0.8,
      lengthPenalty: 1.0,
      repetitionPenalty: 2.0,
      topK: 60,
      topP: 0.9,
      seed: null
    },
    qualitySettings: {
      qualityMode: 'fast',
      enhancementPreset: 'fast',
      enableEnhancement: true,
      multiPass: false,
      multiPassCount: 3,
      enableVad: true,
      enableBatch: true,
      useHifigan: false,
      hifiganRefinementIntensity: 1.0,
      hifiganNormalizeOutput: true,
      hifiganNormalizeGain: 0.95,
      enableNormalization: false,
      enableDenoiser: false,
      enableCompressor: true,
      enableDeesser: false,
      enableEq: false,
      enableTrim: true,
      enableDialectConversion: false,
      dialectCode: null,
      dialectIntensity: 1.0,
      whisperIntensity: 1.0
    }
  },
  variant4: { // P4 - Meditativní
    ttsSettings: {
      speed: 0.75,
      temperature: 0.45,
      lengthPenalty: 1.1,
      repetitionPenalty: 2.2,
      topK: 35,
      topP: 0.75,
      seed: null
    },
    qualitySettings: {
      qualityMode: 'meditative',
      enhancementPreset: 'high_quality',
      enableEnhancement: true,
      multiPass: false,
      multiPassCount: 3,
      enableVad: true,
      enableBatch: true,
      useHifigan: false,
      hifiganRefinementIntensity: 1.0,
      hifiganNormalizeOutput: true,
      hifiganNormalizeGain: 0.95,
      enableNormalization: true,
      enableDenoiser: true,
      enableCompressor: true,
      enableDeesser: false,
      enableEq: true,
      enableTrim: true,
      enableDialectConversion: false,
      dialectCode: null,
      dialectIntensity: 1.0,
      whisperIntensity: 0.0
    }
  },
  variant5: { // P5 - Šeptavý
    ttsSettings: {
      speed: 0.65,
      temperature: 0.30,
      lengthPenalty: 1.0,
      repetitionPenalty: 2.0,
      topK: 25,
      topP: 0.7,
      seed: null
    },
    qualitySettings: {
      qualityMode: 'whisper',
      enhancementPreset: 'high_quality',
      enableEnhancement: true,
      multiPass: false,
      multiPassCount: 3,
      enableVad: true,
      enableBatch: true,
      useHifigan: false,
      hifiganRefinementIntensity: 1.0,
      hifiganNormalizeOutput: true,
      hifiganNormalizeGain: 0.95,
      enableNormalization: true,
      enableDenoiser: true,
      enableCompressor: true,
      enableDeesser: true,
      enableEq: true,
      enableTrim: true,
      enableDialectConversion: false,
      dialectCode: null,
      dialectIntensity: 1.0,
      whisperIntensity: 1.0
    }
  }
}

// Funkce pro získání defaultního nastavení pro slot
const getDefaultSlotSettings = (variantId) => {
  return DEFAULT_SLOT_SETTINGS[variantId] || {
    ttsSettings: { ...BASE_TTS_SETTINGS },
    qualitySettings: { ...BASE_QUALITY_SETTINGS }
  }
}

// Pro zpětnou kompatibilitu
const DEFAULT_TTS_SETTINGS = BASE_TTS_SETTINGS
const DEFAULT_QUALITY_SETTINGS = BASE_QUALITY_SETTINGS

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
  const [activeTab, setActiveTab] = useState('generate') // 'generate' | 'musicgen' | 'bark' | 'history'

  // Nastavení hlasu
  const [selectedVoice, setSelectedVoice] = useState('demo1')
  const [voiceType, setVoiceType] = useState('demo') // 'demo' | 'upload' | 'record' | 'youtube'
  const [uploadedVoice, setUploadedVoice] = useState(null)
  const [uploadedVoiceFileName, setUploadedVoiceFileName] = useState(null)
  const [text, setText] = useState('')
  const [generatedAudio, setGeneratedAudio] = useState(null)
  const [generatedVariants, setGeneratedVariants] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [ttsProgress, setTtsProgress] = useState(null)
  const [demoVoices, setDemoVoices] = useState([])
  const [modelStatus, setModelStatus] = useState(null)
  const [voiceQuality, setVoiceQuality] = useState(null)
  const [textVersions, setTextVersions] = useState([])
  const [showSettings, setShowSettings] = useState(true)

  // Nastavení pro aktuální variantu (vázané na vybraný hlas)
  // Použij slot-specifické defaultní hodnoty pro variant1 (P1) jako výchozí
  const defaultSlotForInit = getDefaultSlotSettings('variant1')
  const [ttsSettings, setTtsSettings] = useState(defaultSlotForInit.ttsSettings)
  const [qualitySettings, setQualitySettings] = useState(defaultSlotForInit.qualitySettings)

  const tabs = [
    { id: 'generate', label: 'mluvené slovo', icon: '🎤' },
    { id: 'musicgen', label: 'hudba', icon: '🎵' },
    { id: 'bark', label: 'FX & English', icon: '🔊' },
    { id: 'audioeditor', label: 'Audio Editor', icon: '🎚️' },
    { id: 'history', label: 'Historie', icon: '📜' }
  ]

  // Ref pro sledování, zda se právě načítá nastavení (aby se neukládalo při načítání)
  const isLoadingSettingsRef = useRef(false)

  // Ref pro aktuální nastavení - vždy obsahuje nejnovější hodnoty
  // Použij slot-specifické defaultní hodnoty pro variant1 (P1) jako výchozí
  const defaultSlotForRef = getDefaultSlotSettings('variant1')
  const currentSettingsRef = useRef({
    ttsSettings: defaultSlotForRef.ttsSettings,
    qualitySettings: defaultSlotForRef.qualitySettings
  })

  // Ref pro progress SSE connection - pro cleanup při novém spuštění nebo unmount
  const progressEventSourceRef = useRef(null)
  // Fallback polling (když SSE selže kvůli CORS/proxy apod.)
  const progressPollIntervalRef = useRef(null)
  const progressStoppedRef = useRef(false)

  // Aktualizovat ref při každé změně nastavení
  useEffect(() => {
    currentSettingsRef.current = {
      ttsSettings: { ...ttsSettings },
      qualitySettings: { ...qualitySettings }
    }
  }, [ttsSettings, qualitySettings])

  // Načtení rozpracovaného textu a historie verzí z localStorage při startu
  useEffect(() => {
    const savedText = localStorage.getItem('xtts_current_text')
    if (savedText) setText(savedText)

    const savedVersions = localStorage.getItem('xtts_text_versions')
    if (savedVersions) {
      try {
        setTextVersions(JSON.parse(savedVersions))
      } catch (e) {
        console.error('Chyba při načítání historie verzí:', e)
      }
    }
  }, [])

  // Auto-save aktuálního textu
  useEffect(() => {
    localStorage.setItem('xtts_current_text', text)
  }, [text])

  // Funkce pro uložení verze textu
  const saveTextVersion = (textToSave) => {
    if (!textToSave || !textToSave.trim()) return

    const newVersion = {
      id: Date.now(),
      text: textToSave,
      timestamp: new Date().toISOString()
    }

    const updatedVersions = [newVersion, ...textVersions.slice(0, 19)] // Max 20 verzí
    setTextVersions(updatedVersions)
    localStorage.setItem('xtts_text_versions', JSON.stringify(updatedVersions))
  }

  const deleteTextVersion = (versionId) => {
    const updatedVersions = textVersions.filter(v => v.id !== versionId)
    setTextVersions(updatedVersions)
    localStorage.setItem('xtts_text_versions', JSON.stringify(updatedVersions))
  }

  // Debounce timer pro ukládání
  const saveTimeoutRef = useRef(null)

  const saveCurrentVariantNow = () => {
    // Ukládat pouze pro demo hlasy a když je selectedVoice skutečný hlas (ne 'demo1')
    if (!selectedVoice || selectedVoice === 'demo1') return
    if (voiceType !== 'demo') return
    if (isLoadingSettingsRef.current) return

    // Použít hodnoty z ref (vždy aktuální)
    // Uložíme všechny aktuální hodnoty - pokud uživatel něco změnil, uloží se to
    // Pokud uživatel nic nezměnil, uloží se defaultní hodnoty (což je v pořádku)
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

    // Získat slot-specifické defaultní hodnoty pro validaci (použijí se pouze jako fallback)
    const defaultSlot = getDefaultSlotSettings(activeVariant)
    const defaultTts = defaultSlot.ttsSettings
    const defaultQuality = defaultSlot.qualitySettings

    // Validace a načtení nastavení atomicky
    let loadedTts, loadedQuality

    // DŮLEŽITÉ: Pokud existuje uložené nastavení, použije se. Defaultní hodnoty se použijí pouze
    // pokud není uložené nastavení nebo pokud některá hodnota chybí/je neplatná.
    // Tím zajistíme, že uživatelské změny se nebudou přepisovat defaultními hodnotami.
    if (saved && saved.ttsSettings && saved.qualitySettings) {
      // Validace a načtení TTS nastavení s fallback na slot-specifické výchozí hodnoty
      loadedTts = {
        speed: typeof saved.ttsSettings.speed === 'number' && !isNaN(saved.ttsSettings.speed)
          ? saved.ttsSettings.speed
          : defaultTts.speed,
        temperature: typeof saved.ttsSettings.temperature === 'number' && !isNaN(saved.ttsSettings.temperature) && saved.ttsSettings.temperature > 0
          ? saved.ttsSettings.temperature
          : defaultTts.temperature,
        lengthPenalty: typeof saved.ttsSettings.lengthPenalty === 'number' && !isNaN(saved.ttsSettings.lengthPenalty)
          ? saved.ttsSettings.lengthPenalty
          : defaultTts.lengthPenalty,
        repetitionPenalty: typeof saved.ttsSettings.repetitionPenalty === 'number' && !isNaN(saved.ttsSettings.repetitionPenalty)
          ? saved.ttsSettings.repetitionPenalty
          : defaultTts.repetitionPenalty,
        topK: typeof saved.ttsSettings.topK === 'number' && !isNaN(saved.ttsSettings.topK)
          ? saved.ttsSettings.topK
          : defaultTts.topK,
        topP: typeof saved.ttsSettings.topP === 'number' && !isNaN(saved.ttsSettings.topP)
          ? saved.ttsSettings.topP
          : defaultTts.topP,
        seed: saved.ttsSettings.seed !== undefined && saved.ttsSettings.seed !== null
          ? (typeof saved.ttsSettings.seed === 'number' ? saved.ttsSettings.seed : null)
          : defaultTts.seed
      }

      // Validace a načtení quality nastavení s fallback na slot-specifické výchozí hodnoty
      loadedQuality = {
        qualityMode: saved.qualitySettings.qualityMode !== undefined
          ? saved.qualitySettings.qualityMode
          : defaultQuality.qualityMode,
        enhancementPreset: typeof saved.qualitySettings.enhancementPreset === 'string'
          ? saved.qualitySettings.enhancementPreset
          : defaultQuality.enhancementPreset,
        enableEnhancement: typeof saved.qualitySettings.enableEnhancement === 'boolean'
          ? saved.qualitySettings.enableEnhancement
          : defaultQuality.enableEnhancement,
        enableNormalization: typeof saved.qualitySettings.enableNormalization === 'boolean'
          ? saved.qualitySettings.enableNormalization
          : defaultQuality.enableNormalization,
        enableDenoiser: typeof saved.qualitySettings.enableDenoiser === 'boolean'
          ? saved.qualitySettings.enableDenoiser
          : defaultQuality.enableDenoiser,
        enableCompressor: typeof saved.qualitySettings.enableCompressor === 'boolean'
          ? saved.qualitySettings.enableCompressor
          : defaultQuality.enableCompressor,
        enableDeesser: typeof saved.qualitySettings.enableDeesser === 'boolean'
          ? saved.qualitySettings.enableDeesser
          : defaultQuality.enableDeesser,
        enableEq: typeof saved.qualitySettings.enableEq === 'boolean'
          ? saved.qualitySettings.enableEq
          : defaultQuality.enableEq,
        enableTrim: typeof saved.qualitySettings.enableTrim === 'boolean'
          ? saved.qualitySettings.enableTrim
          : defaultQuality.enableTrim,
        multiPass: typeof saved.qualitySettings.multiPass === 'boolean'
          ? saved.qualitySettings.multiPass
          : defaultQuality.multiPass,
        multiPassCount: typeof saved.qualitySettings.multiPassCount === 'number'
          ? saved.qualitySettings.multiPassCount
          : defaultQuality.multiPassCount,
        enableVad: typeof saved.qualitySettings.enableVad === 'boolean'
          ? saved.qualitySettings.enableVad
          : defaultQuality.enableVad,
        enableBatch: typeof saved.qualitySettings.enableBatch === 'boolean'
          ? saved.qualitySettings.enableBatch
          : defaultQuality.enableBatch,
        useHifigan: typeof saved.qualitySettings.useHifigan === 'boolean'
          ? saved.qualitySettings.useHifigan
          : defaultQuality.useHifigan,
        hifiganRefinementIntensity: typeof saved.qualitySettings.hifiganRefinementIntensity === 'number'
          ? saved.qualitySettings.hifiganRefinementIntensity
          : defaultQuality.hifiganRefinementIntensity,
        hifiganNormalizeOutput: typeof saved.qualitySettings.hifiganNormalizeOutput === 'boolean'
          ? saved.qualitySettings.hifiganNormalizeOutput
          : defaultQuality.hifiganNormalizeOutput,
        hifiganNormalizeGain: typeof saved.qualitySettings.hifiganNormalizeGain === 'number'
          ? saved.qualitySettings.hifiganNormalizeGain
          : defaultQuality.hifiganNormalizeGain,
        enableDialectConversion: typeof saved.qualitySettings.enableDialectConversion === 'boolean'
          ? saved.qualitySettings.enableDialectConversion
          : defaultQuality.enableDialectConversion,
        dialectCode: saved.qualitySettings.dialectCode !== undefined
          ? saved.qualitySettings.dialectCode
          : defaultQuality.dialectCode,
        dialectIntensity: typeof saved.qualitySettings.dialectIntensity === 'number'
          ? saved.qualitySettings.dialectIntensity
          : defaultQuality.dialectIntensity,
        whisperIntensity: typeof saved.qualitySettings.whisperIntensity === 'number'
          ? saved.qualitySettings.whisperIntensity
          : defaultQuality.whisperIntensity
      }
    } else {
      // Výchozí nastavení pro novou variantu - použij slot-specifické defaultní hodnoty
      const defaultSlot = getDefaultSlotSettings(activeVariant)
      loadedTts = { ...defaultSlot.ttsSettings }
      loadedQuality = { ...defaultSlot.qualitySettings }
    }

    // Aktualizuj state atomicky (všechno najednou)
    setTtsSettings(loadedTts)
    setQualitySettings(loadedQuality)

    // Aktualizuj také ref
    currentSettingsRef.current = {
      ttsSettings: { ...loadedTts },
      qualitySettings: { ...loadedQuality }
    }

    // DŮLEŽITÉ: Pokud není uložené nastavení, použijeme defaultní hodnoty,
    // ale NEULOŽÍME je automaticky. Uloží se pouze když uživatel něco změní.
    // Tím zajistíme, že uživatelské změny se nebudou přepisovat defaultními hodnotami.

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

    // Cleanup při unmount - uzavřít všechny progress SSE spojení
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

    // Pokud už probíhá generování, nové spuštění ignorovat
    if (loading) {
      return
    }

    setLoading(true)
    setError(null)
    setGeneratedAudio(null)
    setGeneratedVariants([])
    setTtsProgress(null)

    try {
      let voiceFile = null
      let demoVoice = null

      if (voiceType === 'upload' && uploadedVoice) {
        voiceFile = uploadedVoice
      } else if (voiceType === 'demo') {
        // Extrahuj pouze název souboru (ID) z selectedVoice, pokud obsahuje cestu
        let voiceId = selectedVoice
        if (voiceId && (voiceId.includes('/') || voiceId.includes('\\'))) {
          // Je to cesta - extrahuj pouze název souboru bez přípony
          const pathParts = voiceId.replace(/\\/g, '/').split('/')
          const filename = pathParts[pathParts.length - 1]
          voiceId = filename.replace(/\.wav$/i, '')
        }
        demoVoice = voiceId
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
        useHifigan: qualitySettings.useHifigan,
        // HiFi-GAN parametry
        hifiganRefinementIntensity: qualitySettings.hifiganRefinementIntensity,
        hifiganNormalizeOutput: qualitySettings.hifiganNormalizeOutput,
        hifiganNormalizeGain: qualitySettings.hifiganNormalizeGain,
        enableNormalization: qualitySettings.enableNormalization,
        enableDenoiser: qualitySettings.enableDenoiser,
        enableCompressor: qualitySettings.enableCompressor,
        enableDeesser: qualitySettings.enableDeesser,
        enableEq: qualitySettings.enableEq,
        enableTrim: qualitySettings.enableTrim,
        enableDialectConversion: qualitySettings.enableDialectConversion,
        dialectCode: qualitySettings.dialectCode,
        dialectIntensity: qualitySettings.dialectIntensity,
        // Whisper efekt parametry
        enableWhisper: qualitySettings.qualityMode === 'whisper' ? true : undefined,
        whisperIntensity: qualitySettings.qualityMode === 'whisper' && qualitySettings.whisperIntensity !== undefined
          ? qualitySettings.whisperIntensity
          : undefined
      }

      // Zrušit předchozí progress SSE spojení, pokud běží
      if (progressEventSourceRef.current) {
        progressEventSourceRef.current.close()
        progressEventSourceRef.current = null
      }
      // Zrušit fallback polling, pokud běží
      if (progressPollIntervalRef.current) {
        clearInterval(progressPollIntervalRef.current)
        progressPollIntervalRef.current = null
      }
      progressStoppedRef.current = false

      // Pro progress během běžícího requestu: vytvoř job_id na klientovi a použij SSE pro real-time updates
      const jobId =
        (typeof crypto !== 'undefined' && crypto.randomUUID && crypto.randomUUID()) ||
        `${Date.now()}-${Math.random().toString(16).slice(2)}`

      // aby UI hned ukázalo 0% (ne „nic") ještě před tím, než backend job zaregistruje
      setTtsProgress({ percent: 0, message: 'Odesílám požadavek…', eta_seconds: null })

      // Připojit se k SSE streamu pro real-time progress updates
      const eventSource = subscribeToTtsProgress(
        jobId,
        (progressData) => {
          if (progressStoppedRef.current) return
          setTtsProgress(progressData)

          // Pokud je progress dokončen nebo chybný, SSE se automaticky uzavře
          if (progressData.status === 'done' || progressData.status === 'error') {
            progressStoppedRef.current = true
            if (progressPollIntervalRef.current) {
              clearInterval(progressPollIntervalRef.current)
              progressPollIntervalRef.current = null
            }
          }
        },
        (error) => {
          console.error('SSE progress error:', error)
          // Při chybě SSE fallback na polling (průběžně, ne jen jednorázově)
          if (progressStoppedRef.current) return
          if (progressPollIntervalRef.current) return

          const poll = async () => {
            if (progressStoppedRef.current) return
            try {
              const p = await getTtsProgress(jobId)
              setTtsProgress(p)
              if (p?.status === 'done' || p?.status === 'error' || (typeof p?.percent === 'number' && p.percent >= 100)) {
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

      const result = await generateSpeech(text, voiceFile, demoVoice, ttsParams, jobId)

      // Zastavit SSE po dokončení generování (může být už uzavřeno automaticky)
      progressStoppedRef.current = true
      if (progressEventSourceRef.current) {
        progressEventSourceRef.current.close()
        progressEventSourceRef.current = null
      }
      if (progressPollIntervalRef.current) {
        clearInterval(progressPollIntervalRef.current)
        progressPollIntervalRef.current = null
      }

      // Finální kontrola progressu (pro jistotu)
      try {
        const p = await getTtsProgress(jobId)
        setTtsProgress(p)
      } catch (e) {
        // ignore
      }

      // Pokud je multi-pass, zobrazit varianty
      if (result.variants && result.variants.length > 0) {
        setGeneratedVariants(result.variants)
        // Nastavíme první jako výchozí, aby AudioPlayer (pokud by byl jen jeden) měl co přehrát
        setGeneratedAudio(result.variants[0].audio_url)
        console.log('Multi-pass: vygenerováno', result.variants.length, 'variant')
      } else {
        setGeneratedAudio(result.audio_url)
        setGeneratedVariants([])
      }

      // Automaticky uložit text do historie verzí po úspěšném generování
      saveTextVersion(text)
    } catch (err) {
      setError(err.message || 'Chyba při generování řeči')
      console.error('Generate error:', err)
      // Zastavit SSE při chybě
      progressStoppedRef.current = true
      if (progressEventSourceRef.current) {
        progressEventSourceRef.current.close()
        progressEventSourceRef.current = null
      }
      if (progressPollIntervalRef.current) {
        clearInterval(progressPollIntervalRef.current)
        progressPollIntervalRef.current = null
      }
    } finally {
      setLoading(false)
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
      <header className="app-header">
        <h1>🎤 XTTS-v2 Czech TTS Demo</h1>
        {modelStatus && (
          <div className="model-status">
            <span className={`status-indicator ${modelStatus.loaded ? 'loaded' : modelStatus.loading ? 'loading' : 'idle'}`}>
              {modelStatus.loaded
                ? '✓ Model načten'
                : modelStatus.loading
                  ? '⏳ Načítání modelu...'
                  : 'Připraven (On-Demand)'}
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
          <div className="main-header-row">
            {/* Záložky Generovat/Historie */}
            <Tabs activeTab={activeTab} onTabChange={setActiveTab} tabs={tabs} />

            {activeTab === 'generate' && (
              <button
                className={`btn-toggle-settings ${!showSettings ? 'collapsed' : ''}`}
                onClick={() => setShowSettings(!showSettings)}
                title={showSettings ? "Skrýt nastavení" : "Zobrazit nastavení"}
              >
                {showSettings ? '✕ Skrýt nastavení' : '⚙️ Nastavení'}
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
                  <button
                    className="btn-primary"
                    onClick={handleGenerate}
                    disabled={loading || !text.trim()}
                  >
                    {loading ? '⏳ Generuji...' : '🔊 Generovat řeč'}
                  </button>
                </div>

                {loading && <LoadingSpinner progress={ttsProgress} />}

                {error && (
                  <div className="error-message">
                    ⚠️ {error}
                  </div>
                )}

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

          {activeTab === 'bark' && (
            <Bark prompt={text} setPrompt={setText} />
          )}

          {activeTab === 'audioeditor' && (
            <AudioEditor />
          )}
        </div>
      </main>
    </div>
  )
}

export default App

