import { useState, useEffect, useRef } from 'react'
import { getDefaultSlotSettings, STORAGE_KEYS } from '../constants/ttsDefaults'

// Maximální počet uložených variant settings (LRU cache)
const MAX_VARIANT_SETTINGS = 50

/**
 * Získá všechny klíče variant settings z localStorage (XTTS i F5TTS)
 */
const getAllVariantSettingsKeys = () => {
  const keys = []
  const prefixes = ['tts_variant_settings_', 'f5tts_voice_']
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i)
      if (key) {
        for (const prefix of prefixes) {
          if (key.startsWith(prefix)) {
            keys.push(key)
            break
          }
        }
      }
    }
  } catch (err) {
    console.error('Chyba při procházení localStorage:', err)
  }
  return keys
}

/**
 * Vyčistí staré variant settings, pokud překročíme limit
 * Používá LRU strategii - odstraní nejstarší záznamy
 */
const cleanupOldVariantSettings = () => {
  try {
    const keys = getAllVariantSettingsKeys()

    if (keys.length <= MAX_VARIANT_SETTINGS) {
      return // Není potřeba čistit
    }

    // Seřadit podle času posledního přístupu (pokud máme timestamp)
    // Pokud ne, odstranit nejstarší (první v seznamu)
    const toRemove = keys.length - MAX_VARIANT_SETTINGS

    // Odstranit nejstarší záznamy
    for (let i = 0; i < toRemove; i++) {
      try {
        localStorage.removeItem(keys[i])
      } catch (err) {
        console.warn('Chyba při mazání starého nastavení:', keys[i], err)
      }
    }

    console.log(`Vyčištěno ${toRemove} starých variant settings z localStorage`)
  } catch (err) {
    console.error('Chyba při čištění starých variant settings:', err)
  }
}

/**
 * Pokusí se vyčistit localStorage při QuotaExceededError
 */
const handleQuotaExceeded = () => {
  try {
    // 1. Vyčistit staré variant settings
    cleanupOldVariantSettings()

    // 2. Zkusit vyčistit waveform cache (může být velký)
    try {
      const waveformKeys = ['waveform_peaks_cache_v3', 'audio_not_found_cache']
      waveformKeys.forEach(key => {
        try {
          localStorage.removeItem(key)
        } catch (e) {
          // Ignorovat
        }
      })
    } catch (e) {
      // Ignorovat
    }

    // 3. Zkusit vyčistit staré text versions (ponechat jen aktuální)
    try {
      // Ponechat jen posledních 5 verzí pro každou záložku
      const tabs = ['generate', 'f5tts', 'musicgen', 'bark', 'audioeditor']
      tabs.forEach(tab => {
        const tabKey = `tts_text_versions_${tab}`
        try {
          const stored = localStorage.getItem(tabKey)
          if (stored) {
            const trimmed = stored.trim()
            // Validovat, že je to validní JSON
            if (trimmed && (trimmed.startsWith('[') || trimmed.startsWith('{'))) {
              try {
                const versions = JSON.parse(stored)
                if (Array.isArray(versions) && versions.length > 5) {
                  const limitedVersions = versions.slice(-5)
                  localStorage.setItem(tabKey, JSON.stringify(limitedVersions))
                }
              } catch (parseErr) {
                // Pokud selže parsování, data jsou poškozená - smazat
                console.warn('Poškozená text versions data při čištění, mazání:', tabKey)
                localStorage.removeItem(tabKey)
              }
            } else {
              // Nevalidní formát - smazat
              console.warn('Nevalidní formát text versions při čištění, mazání:', tabKey)
              localStorage.removeItem(tabKey)
            }
          }
        } catch (e) {
          // Ignorovat chyby při čištění jednotlivých záložek
          console.warn('Chyba při čištění text versions pro:', tab, e)
        }
      })
    } catch (e) {
      // Ignorovat
      console.warn('Chyba při čištění text versions:', e)
    }

    console.log('Provedeno automatické čištění localStorage kvůli QuotaExceededError')
  } catch (err) {
    console.error('Chyba při automatickém čištění localStorage:', err)
  }
}

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

      // Pravidelně kontrolovat a čistit stará nastavení
      if (Math.random() < 0.1) { // 10% šance na kontrolu (aby nebylo příliš často)
        cleanupOldVariantSettings()
      }
    } catch (err) {
      if (err.name === 'QuotaExceededError' || err.code === 22) {
        console.warn('localStorage quota překročena, provádím automatické čištění...')
        handleQuotaExceeded()

        // Zkusit znovu po vyčištění
        try {
          localStorage.setItem(key, JSON.stringify(settings))
          console.log('Nastavení úspěšně uloženo po automatickém čištění')
        } catch (retryErr) {
          console.error('Chyba při ukládání nastavení i po čištění:', retryErr)
          // Pokud stále selže, zkusit uložit bez některých nepodstatných hodnot
          try {
            const minimalSettings = {
              ttsSettings: {
                speed: settings.ttsSettings.speed,
                temperature: settings.ttsSettings.temperature,
                lengthPenalty: settings.ttsSettings.lengthPenalty,
                repetitionPenalty: settings.ttsSettings.repetitionPenalty,
                topK: settings.ttsSettings.topK,
                topP: settings.ttsSettings.topP,
                seed: settings.ttsSettings.seed
              },
              qualitySettings: {
                qualityMode: settings.qualitySettings.qualityMode,
                enhancementPreset: settings.qualitySettings.enhancementPreset,
                enableEnhancement: settings.qualitySettings.enableEnhancement,
                useHifigan: settings.qualitySettings.useHifigan,
                enableNormalization: settings.qualitySettings.enableNormalization,
                enableDenoiser: settings.qualitySettings.enableDenoiser,
                enableCompressor: settings.qualitySettings.enableCompressor,
                enableDeesser: settings.qualitySettings.enableDeesser,
                enableEq: settings.qualitySettings.enableEq,
                enableTrim: settings.qualitySettings.enableTrim
              }
            }
            localStorage.setItem(key, JSON.stringify(minimalSettings))
            console.log('Nastavení uloženo v minimalizované podobě')
          } catch (minimalErr) {
            console.error('Nepodařilo se uložit ani minimalizované nastavení:', minimalErr)
          }
        }
      } else {
        console.error('Chyba při ukládání nastavení:', err)
      }
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

