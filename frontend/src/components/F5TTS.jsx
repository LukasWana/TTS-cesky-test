import React, { useState, useRef, useEffect, useMemo } from 'react'
import { useSectionColor } from '../contexts/SectionColorContext'
import VoiceSelector from './VoiceSelector'
import TextInput from './TextInput'
import AudioPlayer from './AudioPlayer'
import LoadingSpinner from './LoadingSpinner'
import TTSSettings from './TTSSettings'
import Button from './ui/Button'
import Icon from './ui/Icons'
import { generateF5TTSSlovak, getDemoVoices, subscribeToTtsProgress, uploadVoice, recordVoice, downloadYouTubeVoice, transcribeReferenceAudio } from '../services/api'
import { getDefaultSlotSettings } from '../constants/ttsDefaults'
import PromptsHistory from './PromptsHistory'
import HelpSidebar from './HelpSidebar'
import { F5TTSHelpContent } from './HelpContent'
import './F5TTS.css'

// Klíče pro localStorage - varianty jsou vázané na konkrétní hlas (id)
// Pro F5TTS použijeme prefix f5tts_ místo xtts_
const getVariantStorageKey = (voiceId, variantId) => `f5tts_voice_${voiceId}_variant_${variantId}`

// Pomocné funkce pro localStorage
const saveVariantSettings = (voiceId, variantId, settings) => {
  try {
    localStorage.setItem(getVariantStorageKey(voiceId, variantId), JSON.stringify(settings))
  } catch (err) {
    if (err.name === 'QuotaExceededError' || err.code === 22) {
      console.warn('localStorage quota překročena v F5TTS, provádím automatické čištění...')
      // Zkusit vyčistit staré F5TTS variant settings
      try {
        const prefix = 'f5tts_voice_'
        const keys = []
        for (let i = 0; i < localStorage.length; i++) {
          const key = localStorage.key(i)
          if (key && key.startsWith(prefix)) {
            keys.push(key)
          }
        }
        // Odstranit nejstarší (ponechat jen posledních 50)
        if (keys.length > 50) {
          const toRemove = keys.length - 50
          for (let i = 0; i < toRemove; i++) {
            try {
              localStorage.removeItem(keys[i])
            } catch (e) {
              // Ignorovat
            }
          }
        }
        // Zkusit znovu
        localStorage.setItem(getVariantStorageKey(voiceId, variantId), JSON.stringify(settings))
        console.log('F5TTS nastavení úspěšně uloženo po automatickém čištění')
      } catch (cleanupErr) {
        console.error('Chyba při ukládání F5TTS nastavení i po čištění:', cleanupErr)
      }
    } else {
      console.error('Chyba při ukládání nastavení:', err)
    }
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

function F5TTS({ text: textProp, setText: setTextProp, versions, onSaveVersion, onDeleteVersion }) {
  const { color, rgb } = useSectionColor()
  const style = {
    '--section-color': color,
    '--section-color-rgb': rgb
  }

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
  // F5TTS je v tomto projektu fixně pro slovenštinu (nepřepíná se do češtiny).
  const language = 'sk'
  const [uploadedVoiceFileName, setUploadedVoiceFileName] = useState(null)
  const [voiceQuality, setVoiceQuality] = useState(null)
  const [refText, setRefText] = useState('')
  const [autoTranscribe, setAutoTranscribe] = useState(true)
  const [refTextLoading, setRefTextLoading] = useState(false)
  const [removeBackground, setRemoveBackground] = useState(false)
  const [helpOpen, setHelpOpen] = useState(false)

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

  // Nastavení pro aktuální variantu (vázané na vybraný hlas)
  // Použij slot-specifické defaultní hodnoty pro variant2 (P2) jako výchozí
  const defaultSlotForInit = getDefaultSlotSettings('variant2')
  const [ttsSettings, setTtsSettings] = useState(defaultSlotForInit.ttsSettings)
  const [qualitySettings, setQualitySettings] = useState(defaultSlotForInit.qualitySettings)

  const [activeVariant, setActiveVariant] = useState('variant2') // P2 - Přirozený jako default

  const progressEventSourceRef = useRef(null)
  // Ref pro sledování, zda se právě načítá nastavení (aby se neukládalo při načítání)
  const isLoadingSettingsRef = useRef(false)
  // Ref pro aktuální nastavení - vždy obsahuje nejnovější hodnoty
  const defaultSlotForRef = getDefaultSlotSettings('variant2')
  const currentSettingsRef = useRef({
    ttsSettings: defaultSlotForRef.ttsSettings,
    qualitySettings: defaultSlotForRef.qualitySettings
  })
  // Debounce timer pro ukládání
  const saveTimeoutRef = useRef(null)

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

  // Aktualizovat ref při každé změně nastavení
  useEffect(() => {
    currentSettingsRef.current = {
      ttsSettings: { ...ttsSettings },
      qualitySettings: { ...qualitySettings }
    }
  }, [ttsSettings, qualitySettings])

  const saveCurrentVariantNow = () => {
    // Ukládat pouze pro demo hlasy a když je selectedVoice skutečný hlas
    if (!selectedVoice) return
    if (voiceType !== 'demo' && voiceType !== 'record' && voiceType !== 'youtube') return
    if (isLoadingSettingsRef.current) return

    // Použít hodnoty z ref (vždy aktuální)
    const settings = {
      ttsSettings: { ...currentSettingsRef.current.ttsSettings },
      qualitySettings: { ...currentSettingsRef.current.qualitySettings }
    }

    try {
      // Pro demo hlasy použijeme selectedVoice jako ID
      const voiceId = typeof selectedVoice === 'string' ? selectedVoice : (selectedVoice?.id || selectedVoice?.name)
      if (voiceId) {
        saveVariantSettings(voiceId, activeVariant, settings)
        console.log('💾 Ukládám nastavení pro:', voiceId, activeVariant, settings) // Debug
      }
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

  // Copy/Paste settings functionality
  const handleCopySettings = () => {
    try {
      const settingsToCopy = {
        ttsSettings: { ...ttsSettings },
        qualitySettings: { ...qualitySettings },
        timestamp: Date.now(),
        sourceVariant: activeVariant
      }
      sessionStorage.setItem('tts_copied_settings_sk', JSON.stringify(settingsToCopy))
      console.log('📋 Nastavení zkopírována z varianty:', activeVariant, settingsToCopy)
    } catch (err) {
      console.error('Chyba při kopírování nastavení:', err)
    }
  }

  const handlePasteSettings = () => {
    try {
      const copiedData = sessionStorage.getItem('tts_copied_settings_sk')
      if (!copiedData) {
        console.warn('⚠️  Žádná zkopírovaná nastavení nenalezena')
        return false
      }

      const parsed = JSON.parse(copiedData)
      console.log('📥 Vkládám nastavení:', parsed.sourceVariant, '→', activeVariant)

      // Nastavit state - tímto se aktivuje useEffect pro uložení
      setTtsSettings({ ...parsed.ttsSettings })
      setQualitySettings({ ...parsed.qualitySettings })

      // Uložit do localStorage okamžitě pro aktuální variantu
      const voiceId = typeof selectedVoice === 'string' ? selectedVoice : (selectedVoice?.id || selectedVoice?.name)
      if (voiceId) {
        const settings = {
          ttsSettings: { ...parsed.ttsSettings },
          qualitySettings: { ...parsed.qualitySettings }
        }
        saveVariantSettings(voiceId, activeVariant, settings)
        console.log('✅ Vložená nastavení uložena do varianty:', activeVariant)
      }

      return true
    } catch (err) {
      console.error('❌ Chyba při vkládání nastavení:', err)
      return false
    }
  }

  // Uložení nastavení aktuální varianty do localStorage (vázané na hlas)
  // Ukládá se s debounce při změně nastavení, ale ne při načítání nebo změně varianty
  useEffect(() => {
    if (isLoadingSettingsRef.current) return
    if (!selectedVoice) return
    if (voiceType !== 'demo' && voiceType !== 'record' && voiceType !== 'youtube') return

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
  }, [ttsSettings, qualitySettings, selectedVoice, voiceType, activeVariant])

  // Načtení nastavení při změně varianty nebo hlasu
  useEffect(() => {
    // Načítat pouze pro demo hlasy a když je selectedVoice skutečný hlas
    if (!selectedVoice) return
    if (voiceType !== 'demo' && voiceType !== 'record' && voiceType !== 'youtube') return

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
    const voiceId = typeof selectedVoice === 'string' ? selectedVoice : (selectedVoice?.id || selectedVoice?.name)
    const saved = voiceId ? loadVariantSettings(voiceId, activeVariant) : null
    console.log('📖 Načítám nastavení pro:', voiceId, activeVariant, saved) // Debug

    // Získat slot-specifické defaultní hodnoty pro validaci (použijí se pouze jako fallback)
    const defaultSlot = getDefaultSlotSettings(activeVariant)
    const defaultTts = defaultSlot.ttsSettings
    const defaultQuality = defaultSlot.qualitySettings

    // Validace a načtení nastavení atomicky
    let loadedTts, loadedQuality

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
          : defaultTts.seed,
        nfeStep: typeof saved.ttsSettings.nfeStep === 'number' && !isNaN(saved.ttsSettings.nfeStep)
          ? saved.ttsSettings.nfeStep
          : defaultTts.nfeStep || 32,
        cfgStrength: typeof saved.ttsSettings.cfgStrength === 'number' && !isNaN(saved.ttsSettings.cfgStrength)
          ? saved.ttsSettings.cfgStrength
          : defaultTts.cfgStrength || 2.0,
        swaySamplingCoef: typeof saved.ttsSettings.swaySamplingCoef === 'number' && !isNaN(saved.ttsSettings.swaySamplingCoef)
          ? saved.ttsSettings.swaySamplingCoef
          : defaultTts.swaySamplingCoef || -1.0
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
        enableVad: typeof saved.qualitySettings.enableVad === 'boolean'
          ? saved.qualitySettings.enableVad
          : defaultQuality.enableVad,
        useHifigan: typeof saved.qualitySettings.useHifigan === 'boolean'
          ? saved.qualitySettings.useHifigan
          : defaultQuality.useHifigan,
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
          : defaultQuality.whisperIntensity,
        targetHeadroomDb: typeof saved.qualitySettings.targetHeadroomDb === 'number'
          ? saved.qualitySettings.targetHeadroomDb
          : (defaultQuality.targetHeadroomDb !== undefined ? defaultQuality.targetHeadroomDb : -15.0)
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

  const loadDemoVoices = async () => {
    try {
      const data = await getDemoVoices(language)
      const voices = data.voices || data || []
      setDemoVoices(voices)
    } catch (err) {
      console.error('Chyba při načítání demo hlasů:', err)
    }
  }

  const handleVoiceUpload = async (file, removeBg = false) => {
    setSelectedVoice(file)
    setVoiceType('upload')
    setUploadedVoiceFileName(file.name)
    setVoiceQuality(null) // Reset quality for new upload
    setRemoveBackground(removeBg) // Uložit hodnotu remove_background

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
            ; (async () => {
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
            ; (async () => {
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

    // Uložit verzi textu do historie
    if (onSaveVersion) {
      onSaveVersion(text)
    }

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

      // Sestavení parametrů pro F5-TTS - explicitně mapovat všechny parametry
      const ttsParams = {
        // TTS parametry
        speed: ttsSettings.speed,
        seed: ttsSettings.seed,
        nfeStep: ttsSettings.nfeStep,
        cfgStrength: ttsSettings.cfgStrength,
        swaySamplingCoef: ttsSettings.swaySamplingCoef,
        // Quality parametry
        qualityMode: qualitySettings.qualityMode,
        enhancementPreset: qualitySettings.enhancementPreset,
        enableEnhancement: qualitySettings.enableEnhancement,
        enableNormalization: qualitySettings.enableNormalization,
        enableDenoiser: qualitySettings.enableDenoiser,
        enableCompressor: qualitySettings.enableCompressor,
        enableDeesser: qualitySettings.enableDeesser,
        enableEq: qualitySettings.enableEq,
        enableTrim: qualitySettings.enableTrim,
        enableVad: qualitySettings.enableVad,
        useHifigan: qualitySettings.useHifigan,
        enableDialectConversion: qualitySettings.enableDialectConversion,
        dialectCode: qualitySettings.dialectCode,
        dialectIntensity: qualitySettings.dialectIntensity,
        whisperIntensity: qualitySettings.whisperIntensity,
        // Headroom
        targetHeadroomDb: qualitySettings.targetHeadroomDb !== undefined ? qualitySettings.targetHeadroomDb : -15.0,
        // Volitelný přepis referenčního audia (zlepšuje výslovnost/stabilitu, když sedí k referenci)
        refText: refText || null,
        // Separace hlasu od pozadí
        removeBackground: voiceType === 'upload' ? removeBackground : false
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


  return (
    <>
      <div className="generate-layout">
        <div className="generate-content">
          <div className="section-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <h2>F5-TTS (slovenské slovo)</h2>
              <button
                onClick={() => setHelpOpen(true)}
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
            <p className="section-hint">
              Pokročilý TTS engine s flow matching. V této aplikaci je nastavený pouze pro slovenštinu.
            </p>
          </div>

          <VoiceSelector
            selectedVoice={selectedVoice}
            onVoiceSelect={setSelectedVoice}
            demoVoices={demoVoices}
            voiceQuality={voiceQuality}
            language={language}
          />

          <TextInput
            value={text}
            onChange={setText}
            placeholder="Zadej text k syntéze..."
            maxLength={10000}
            versions={versions}
            onSaveVersion={() => onSaveVersion && onSaveVersion(text)}
            onDeleteVersion={onDeleteVersion}
          />

          <PromptsHistory
            modelType="f5tts-sk"
            onSelectPrompt={setText}
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

        <div className="settings-panel">
          <TTSSettings
            engine="f5"
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
              if (selectedVoice && (voiceType === 'demo' || voiceType === 'record' || voiceType === 'youtube')) {
                const voiceId = typeof selectedVoice === 'string' ? selectedVoice : (selectedVoice?.id || selectedVoice?.name)
                if (voiceId) {
                  const resetSettings = {
                    ttsSettings: { ...resetTts },
                    qualitySettings: { ...resetQuality }
                  }
                  saveVariantSettings(voiceId, activeVariant, resetSettings)
                }
              }
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

      <HelpSidebar
        isOpen={helpOpen}
        onClose={() => setHelpOpen(false)}
        title="Nápověda - F5-TTS (slovenské slovo)"
      >
        <F5TTSHelpContent />
      </HelpSidebar>
    </>
  )
}

export default F5TTS

