/**
 * Výchozí hodnoty a konstanty pro TTS nastavení
 */

// Výchozí hodnoty TTS parametrů (základní)
export const BASE_TTS_SETTINGS = {
  speed: 1.0,
  temperature: 0.7,
  lengthPenalty: 1.0,
  repetitionPenalty: 2.0,
  topK: 50,
  topP: 0.85,
  seed: null
}

export const BASE_QUALITY_SETTINGS = {
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
  whisperIntensity: 1.0,
  // Headroom
  targetHeadroomDb: -15.0
}

// Defaultní nastavení pro sloty P1-P5
export const DEFAULT_SLOT_SETTINGS = {
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
      whisperIntensity: 1.0,
      targetHeadroomDb: -15.0
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
      whisperIntensity: 1.0,
      targetHeadroomDb: -15.0
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
      whisperIntensity: 1.0,
      targetHeadroomDb: -15.0
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
      whisperIntensity: 1.0,
      targetHeadroomDb: -15.0
    }
  },
  variant5: { // P5 - Whisper
    ttsSettings: {
      speed: 0.85,
      temperature: 0.4,
      lengthPenalty: 1.15,
      repetitionPenalty: 2.3,
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
      enableDeesser: false,
      enableEq: true,
      enableTrim: true,
      enableDialectConversion: false,
      dialectCode: null,
      dialectIntensity: 1.0,
      whisperIntensity: 1.0,
      targetHeadroomDb: -15.0
    }
  }
}

/**
 * Získá výchozí nastavení pro daný slot
 * @param {string} variantId - ID varianty ('variant1' až 'variant5')
 * @returns {Object} Objekt s ttsSettings a qualitySettings
 */
export const getDefaultSlotSettings = (variantId) => {
  return DEFAULT_SLOT_SETTINGS[variantId] || {
    ttsSettings: { ...BASE_TTS_SETTINGS },
    qualitySettings: { ...BASE_QUALITY_SETTINGS }
  }
}

// Storage keys helpers
export const STORAGE_KEYS = {
  VARIANT_SETTINGS: (variantId) => `tts_variant_settings_${variantId}`,
  ACTIVE_VARIANT: 'tts_active_variant',
  TEXT_VERSIONS: (tab) => `tts_text_versions_${tab}`,
  REF_TEXT: (voiceType, voiceName) => `f5tts_ref_text_${voiceType}_${voiceName}`
}

