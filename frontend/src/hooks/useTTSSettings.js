import { useState, useEffect, useRef } from 'react'
import { getDefaultSlotSettings, STORAGE_KEYS } from '../constants/ttsDefaults'

/**
 * Hook pro správu TTS nastavení s localStorage persistence
 */
export const useTTSSettings = (selectedVoice, voiceType, activeVariant) => {
  const defaultSlot = getDefaultSlotSettings(activeVariant)
  const [ttsSettings, setTtsSettings] = useState(defaultSlot.ttsSettings)
  const [qualitySettings, setQualitySettings] = useState(defaultSlot.qualitySettings)

  const isLoadingSettingsRef = useRef(false)
  const currentSettingsRef = useRef({
    ttsSettings: defaultSlot.ttsSettings,
    qualitySettings: defaultSlot.qualitySettings
  })
  const saveTimeoutRef = useRef(null)

  // Aktualizovat ref při každé změně nastavení
  useEffect(() => {
    currentSettingsRef.current = {
      ttsSettings: { ...ttsSettings },
      qualitySettings: { ...qualitySettings }
    }
  }, [ttsSettings, qualitySettings])

  const loadVariantSettings = (voiceId, variantId) => {
    try {
      const key = STORAGE_KEYS.VARIANT_SETTINGS(`${voiceId}_${variantId}`)
      const stored = localStorage.getItem(key)
      if (stored) {
        return JSON.parse(stored)
      }
    } catch (err) {
      console.error('Chyba při načítání nastavení:', err)
    }
    return null
  }

  const saveVariantSettings = (voiceId, variantId, settings) => {
    try {
      const key = STORAGE_KEYS.VARIANT_SETTINGS(`${voiceId}_${variantId}`)
      localStorage.setItem(key, JSON.stringify(settings))
    } catch (err) {
      console.error('Chyba při ukládání nastavení:', err)
    }
  }

  const saveCurrentVariantNow = () => {
    if (!selectedVoice || selectedVoice === 'demo1') return
    if (voiceType !== 'demo') return
    if (isLoadingSettingsRef.current) return

    const settings = {
      ttsSettings: { ...currentSettingsRef.current.ttsSettings },
      qualitySettings: { ...currentSettingsRef.current.qualitySettings }
    }

    saveVariantSettings(selectedVoice, activeVariant, settings)
  }

  // Uložení nastavení s debounce
  useEffect(() => {
    if (isLoadingSettingsRef.current) return
    if (!selectedVoice || selectedVoice === 'demo1') return
    if (voiceType !== 'demo') return

    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current)
    }

    saveTimeoutRef.current = setTimeout(() => {
      saveCurrentVariantNow()
      saveTimeoutRef.current = null
    }, 300)

    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current)
        saveTimeoutRef.current = null
      }
    }
  }, [ttsSettings, qualitySettings, selectedVoice, voiceType, activeVariant])

  // Načtení nastavení při změně varianty nebo hlasu
  useEffect(() => {
    if (!selectedVoice || selectedVoice === 'demo1') return
    if (voiceType !== 'demo') return

    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current)
      saveTimeoutRef.current = null
    }

    isLoadingSettingsRef.current = true

    const saved = loadVariantSettings(selectedVoice, activeVariant)
    const defaultSlot = getDefaultSlotSettings(activeVariant)
    const defaultTts = defaultSlot.ttsSettings
    const defaultQuality = defaultSlot.qualitySettings

    let loadedTts, loadedQuality

    if (saved && saved.ttsSettings && saved.qualitySettings) {
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
        topK: typeof saved.ttsSettings.topK === 'number' && !isNaN(saved.ttsSettings.topK) && saved.ttsSettings.topK > 0
          ? saved.ttsSettings.topK
          : defaultTts.topK,
        topP: typeof saved.ttsSettings.topP === 'number' && !isNaN(saved.ttsSettings.topP) && saved.ttsSettings.topP > 0
          ? saved.ttsSettings.topP
          : defaultTts.topP,
        seed: saved.ttsSettings.seed !== undefined ? saved.ttsSettings.seed : defaultTts.seed
      }

      loadedQuality = {
        qualityMode: saved.qualitySettings.qualityMode !== undefined ? saved.qualitySettings.qualityMode : defaultQuality.qualityMode,
        enhancementPreset: saved.qualitySettings.enhancementPreset || defaultQuality.enhancementPreset,
        enableEnhancement: saved.qualitySettings.enableEnhancement !== undefined ? saved.qualitySettings.enableEnhancement : defaultQuality.enableEnhancement,
        multiPass: saved.qualitySettings.multiPass !== undefined ? saved.qualitySettings.multiPass : defaultQuality.multiPass,
        multiPassCount: typeof saved.qualitySettings.multiPassCount === 'number' && !isNaN(saved.qualitySettings.multiPassCount) && saved.qualitySettings.multiPassCount > 0
          ? saved.qualitySettings.multiPassCount
          : defaultQuality.multiPassCount,
        enableVad: saved.qualitySettings.enableVad !== undefined ? saved.qualitySettings.enableVad : defaultQuality.enableVad,
        enableBatch: saved.qualitySettings.enableBatch !== undefined ? saved.qualitySettings.enableBatch : defaultQuality.enableBatch,
        useHifigan: saved.qualitySettings.useHifigan !== undefined ? saved.qualitySettings.useHifigan : defaultQuality.useHifigan,
        hifiganRefinementIntensity: typeof saved.qualitySettings.hifiganRefinementIntensity === 'number' && !isNaN(saved.qualitySettings.hifiganRefinementIntensity)
          ? saved.qualitySettings.hifiganRefinementIntensity
          : defaultQuality.hifiganRefinementIntensity,
        hifiganNormalizeOutput: saved.qualitySettings.hifiganNormalizeOutput !== undefined ? saved.qualitySettings.hifiganNormalizeOutput : defaultQuality.hifiganNormalizeOutput,
        hifiganNormalizeGain: typeof saved.qualitySettings.hifiganNormalizeGain === 'number' && !isNaN(saved.qualitySettings.hifiganNormalizeGain)
          ? saved.qualitySettings.hifiganNormalizeGain
          : defaultQuality.hifiganNormalizeGain,
        enableNormalization: saved.qualitySettings.enableNormalization !== undefined ? saved.qualitySettings.enableNormalization : defaultQuality.enableNormalization,
        enableDenoiser: saved.qualitySettings.enableDenoiser !== undefined ? saved.qualitySettings.enableDenoiser : defaultQuality.enableDenoiser,
        enableCompressor: saved.qualitySettings.enableCompressor !== undefined ? saved.qualitySettings.enableCompressor : defaultQuality.enableCompressor,
        enableDeesser: saved.qualitySettings.enableDeesser !== undefined ? saved.qualitySettings.enableDeesser : defaultQuality.enableDeesser,
        enableEq: saved.qualitySettings.enableEq !== undefined ? saved.qualitySettings.enableEq : defaultQuality.enableEq,
        enableTrim: saved.qualitySettings.enableTrim !== undefined ? saved.qualitySettings.enableTrim : defaultQuality.enableTrim,
        enableDialectConversion: saved.qualitySettings.enableDialectConversion !== undefined ? saved.qualitySettings.enableDialectConversion : defaultQuality.enableDialectConversion,
        dialectCode: saved.qualitySettings.dialectCode !== undefined ? saved.qualitySettings.dialectCode : defaultQuality.dialectCode,
        dialectIntensity: typeof saved.qualitySettings.dialectIntensity === 'number' && !isNaN(saved.qualitySettings.dialectIntensity)
          ? saved.qualitySettings.dialectIntensity
          : defaultQuality.dialectIntensity,
        whisperIntensity: typeof saved.qualitySettings.whisperIntensity === 'number' && !isNaN(saved.qualitySettings.whisperIntensity)
          ? saved.qualitySettings.whisperIntensity
          : defaultQuality.whisperIntensity,
        targetHeadroomDb: typeof saved.qualitySettings.targetHeadroomDb === 'number' && !isNaN(saved.qualitySettings.targetHeadroomDb)
          ? saved.qualitySettings.targetHeadroomDb
          : defaultQuality.targetHeadroomDb
      }
    } else {
      loadedTts = { ...defaultTts }
      loadedQuality = { ...defaultQuality }
    }

    setTtsSettings(loadedTts)
    setQualitySettings(loadedQuality)

    isLoadingSettingsRef.current = false
  }, [selectedVoice, voiceType, activeVariant])

  return {
    ttsSettings,
    setTtsSettings,
    qualitySettings,
    setQualitySettings,
    saveCurrentVariantNow
  }
}

