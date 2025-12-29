import { useState } from 'react'
import { generateSpeech } from '../services/api'

/**
 * Hook pro TTS generování
 */
export const useTTSGeneration = (
  text,
  selectedVoice,
  voiceType,
  uploadedVoice,
  ttsSettings,
  qualitySettings,
  startProgressTracking
) => {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [generatedAudio, setGeneratedAudio] = useState(null)
  const [generatedVariants, setGeneratedVariants] = useState([])

  const handleGenerate = async (saveTextVersion) => {
    if (!text.trim()) {
      setError('Zadejte text k syntéze')
      return
    }

    if (loading) {
      return
    }

    setLoading(true)
    setError(null)
    setGeneratedAudio(null)
    setGeneratedVariants([])

    try {
      let voiceFile = null
      let demoVoice = null

      if (voiceType === 'upload' && uploadedVoice) {
        voiceFile = uploadedVoice
      } else if (voiceType === 'demo') {
        let voiceId = selectedVoice
        if (voiceId && (voiceId.includes('/') || voiceId.includes('\\'))) {
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
        multiPass: qualitySettings.multiPass,
        multiPassCount: qualitySettings.multiPassCount,
        enableVad: qualitySettings.enableVad,
        enableBatch: qualitySettings.enableBatch,
        useHifigan: qualitySettings.useHifigan,
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
        enableWhisper: qualitySettings.qualityMode === 'whisper' ? true : undefined,
        whisperIntensity: qualitySettings.qualityMode === 'whisper' && qualitySettings.whisperIntensity !== undefined
          ? qualitySettings.whisperIntensity
          : undefined,
        targetHeadroomDb: qualitySettings.targetHeadroomDb !== undefined ? qualitySettings.targetHeadroomDb : -15.0
      }

      // Vytvoř job_id pro progress tracking
      const jobId =
        (typeof crypto !== 'undefined' && crypto.randomUUID && crypto.randomUUID()) ||
        `${Date.now()}-${Math.random().toString(16).slice(2)}`

      // Spustit progress tracking
      if (startProgressTracking) {
        startProgressTracking(jobId)
      }

      const result = await generateSpeech(text, voiceFile, demoVoice, ttsParams, jobId)

      // Pokud je multi-pass, zobrazit varianty
      if (result.variants && result.variants.length > 0) {
        setGeneratedVariants(result.variants)
        setGeneratedAudio(result.variants[0].audio_url)
        console.log('Multi-pass: vygenerováno', result.variants.length, 'variant')
      } else {
        setGeneratedAudio(result.audio_url)
        setGeneratedVariants([])
      }

      // Automaticky uložit text do historie verzí po úspěšném generování
      if (saveTextVersion) {
        console.log('[useTTSGeneration] Volám saveTextVersion s textem:', text.substring(0, 50))
        saveTextVersion(text)
      } else {
        console.warn('[useTTSGeneration] saveTextVersion není definován!')
      }
    } catch (err) {
      setError(err.message || 'Chyba při generování řeči')
      console.error('Generate error:', err)
    } finally {
      setLoading(false)
    }
  }

  return {
    loading,
    error,
    setError,
    generatedAudio,
    setGeneratedAudio,
    generatedVariants,
    setGeneratedVariants,
    handleGenerate
  }
}

