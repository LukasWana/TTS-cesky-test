/**
 * API client pro komunikaci s backend
 */
// Použij 127.0.0.1 místo localhost kvůli IPv6 (::1) na Windows/Chrome, kde backend často neběží na IPv6
const API_BASE_URL = 'http://127.0.0.1:8000'


/**
 * Generuje řeč z textu
 * @param {string} text - Text k syntéze
 * @param {File|null} voiceFile - Nahraný audio soubor
 * @param {string|null} demoVoice - Název demo hlasu
 * @param {Object} ttsParams - Volitelné TTS parametry
 * @param {number} ttsParams.speed - Rychlost řeči (0.5-2.0)
 * @param {number} ttsParams.temperature - Teplota (0.0-1.0)
 * @param {number} ttsParams.lengthPenalty - Length penalty
 * @param {number} ttsParams.repetitionPenalty - Repetition penalty
 * @param {number} ttsParams.topK - Top-k sampling
 * @param {number} ttsParams.topP - Top-p sampling
 * @param {number|null} ttsParams.seed - Seed pro reprodukovatelnost (volitelné)
 * @param {string} ttsParams.qualityMode - Režim kvality (high_quality, natural, fast)
 * @param {string} ttsParams.enhancementPreset - Preset pro audio enhancement
 * @param {boolean} ttsParams.enableEnhancement - Zapnout/vypnout audio enhancement
 * @param {boolean} ttsParams.multiPass - Zapnout multi-pass generování
 * @param {number} ttsParams.multiPassCount - Počet variant při multi-pass
 * @param {boolean} ttsParams.enableVad - Zapnout Voice Activity Detection
 * @param {boolean} ttsParams.enableBatch - Zapnout batch processing
 * @param {boolean} ttsParams.useHifigan - Použít HiFi-GAN vocoder
 * @param {number} ttsParams.hifiganRefinementIntensity - Intenzita HiFi-GAN refinement (0.0-1.0)
 * @param {boolean} ttsParams.hifiganNormalizeOutput - Normalizovat výstup HiFi-GAN
 * @param {number} ttsParams.hifiganNormalizeGain - Normalizační gain (0.5-1.0)
 * @param {boolean} ttsParams.enableNormalization - Zapnout normalizaci
 * @param {boolean} ttsParams.enableDenoiser - Zapnout redukci šumu
 * @param {boolean} ttsParams.enableCompressor - Zapnout kompresi
 * @param {boolean} ttsParams.enableDeesser - Zapnout de-esser
 * @param {boolean} ttsParams.enableEq - Zapnout EQ
 * @param {boolean} ttsParams.enableTrim - Zapnout ořez ticha
 * @param {boolean} ttsParams.enableDialectConversion - Zapnout převod na nářečí
 * @param {string} ttsParams.dialectCode - Kód nářečí (moravske, hanacke, slezske, chodske, brnenske)
 * @param {number} ttsParams.dialectIntensity - Intenzita převodu (0.0-1.0)
 */
export async function generateSpeech(text, voiceFile = null, demoVoice = null, ttsParams = {}, jobId = null) {
  const formData = new FormData()
  formData.append('text', text)
  if (jobId) {
    formData.append('job_id', jobId)
  }

  if (voiceFile) {
    formData.append('voice_file', voiceFile)
  } else if (demoVoice) {
    formData.append('demo_voice', demoVoice)
  }

  // Přidání TTS parametrů pokud jsou zadány
  if (ttsParams.speed !== undefined && ttsParams.speed !== null) {
    formData.append('speed', ttsParams.speed.toString())
  }
  if (ttsParams.temperature !== undefined && ttsParams.temperature !== null) {
    formData.append('temperature', ttsParams.temperature.toString())
  }
  if (ttsParams.lengthPenalty !== undefined && ttsParams.lengthPenalty !== null) {
    formData.append('length_penalty', ttsParams.lengthPenalty.toString())
  }
  if (ttsParams.repetitionPenalty !== undefined && ttsParams.repetitionPenalty !== null) {
    formData.append('repetition_penalty', ttsParams.repetitionPenalty.toString())
  }
  if (ttsParams.topK !== undefined && ttsParams.topK !== null) {
    formData.append('top_k', ttsParams.topK.toString())
  }
  if (ttsParams.topP !== undefined && ttsParams.topP !== null) {
    formData.append('top_p', ttsParams.topP.toString())
  }
  if (ttsParams.seed !== undefined && ttsParams.seed !== null) {
    formData.append('seed', ttsParams.seed.toString())
  }
  if (ttsParams.qualityMode !== undefined && ttsParams.qualityMode !== null) {
    formData.append('quality_mode', ttsParams.qualityMode)
  }
  if (ttsParams.enhancementPreset !== undefined && ttsParams.enhancementPreset !== null) {
    formData.append('enhancement_preset', ttsParams.enhancementPreset)
  }
  if (ttsParams.enableEnhancement !== undefined && ttsParams.enableEnhancement !== null) {
    formData.append('enable_enhancement', ttsParams.enableEnhancement.toString())
  }
  if (ttsParams.multiPass !== undefined) {
    formData.append('multi_pass', ttsParams.multiPass.toString())
  }
  if (ttsParams.multiPassCount !== undefined) {
    formData.append('multi_pass_count', ttsParams.multiPassCount.toString())
  }
  if (ttsParams.enableVad !== undefined) {
    formData.append('enable_vad', ttsParams.enableVad.toString())
  }
  if (ttsParams.enableBatch !== undefined) {
    formData.append('enable_batch', ttsParams.enableBatch.toString())
  }
  if (ttsParams.useHifigan !== undefined) {
    formData.append('use_hifigan', ttsParams.useHifigan.toString())
  }
  if (ttsParams.hifiganRefinementIntensity !== undefined && ttsParams.useHifigan) {
    formData.append('hifigan_refinement_intensity', ttsParams.hifiganRefinementIntensity.toString())
  }
  if (ttsParams.hifiganNormalizeOutput !== undefined && ttsParams.useHifigan) {
    formData.append('hifigan_normalize_output', ttsParams.hifiganNormalizeOutput.toString())
  }
  if (ttsParams.hifiganNormalizeGain !== undefined && ttsParams.useHifigan) {
    formData.append('hifigan_normalize_gain', ttsParams.hifiganNormalizeGain.toString())
  }
  if (ttsParams.enableNormalization !== undefined) {
    formData.append('enable_normalization', ttsParams.enableNormalization.toString())
  }
  if (ttsParams.enableDenoiser !== undefined) {
    formData.append('enable_denoiser', ttsParams.enableDenoiser.toString())
  }
  if (ttsParams.enableCompressor !== undefined) {
    formData.append('enable_compressor', ttsParams.enableCompressor.toString())
  }
  if (ttsParams.enableDeesser !== undefined) {
    formData.append('enable_deesser', ttsParams.enableDeesser.toString())
  }
  if (ttsParams.enableEq !== undefined) {
    formData.append('enable_eq', ttsParams.enableEq.toString())
  }
  if (ttsParams.enableTrim !== undefined) {
    formData.append('enable_trim', ttsParams.enableTrim.toString())
  }
  if (ttsParams.enableWhisper !== undefined) {
    formData.append('enable_whisper', ttsParams.enableWhisper.toString())
  }
  if (ttsParams.whisperIntensity !== undefined && ttsParams.whisperIntensity !== null) {
    formData.append('whisper_intensity', ttsParams.whisperIntensity.toString())
  }
  if (ttsParams.enableDialectConversion !== undefined) {
    formData.append('enable_dialect_conversion', ttsParams.enableDialectConversion.toString())
  }
  if (ttsParams.dialectCode !== undefined && ttsParams.dialectCode !== null) {
    formData.append('dialect_code', ttsParams.dialectCode)
  }
  if (ttsParams.dialectIntensity !== undefined && ttsParams.dialectIntensity !== null) {
    formData.append('dialect_intensity', ttsParams.dialectIntensity.toString())
  }
  if (ttsParams.targetHeadroomDb !== undefined && ttsParams.targetHeadroomDb !== null) {
    formData.append('target_headroom_db', ttsParams.targetHeadroomDb.toString())
  }

  const response = await fetch(`${API_BASE_URL}/api/tts/generate`, {
    method: 'POST',
    body: formData
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Chyba při generování řeči')
  }

  return await response.json()
}

/**
 * Generuje řeč pomocí F5-TTS
 */
export async function generateF5TTS(text, voiceFile = null, demoVoice = null, ttsParams = {}, jobId = null) {
  const formData = new FormData()
  formData.append('text', text)
  if (jobId) {
    formData.append('job_id', jobId)
  }

  if (voiceFile) {
    formData.append('voice_file', voiceFile)
  } else if (demoVoice) {
    formData.append('demo_voice', demoVoice)
  }

  // Volitelný ref_text (přepis reference audio)
  if (ttsParams.refText !== undefined && ttsParams.refText !== null && ttsParams.refText.trim() !== '') {
    formData.append('ref_text', ttsParams.refText)
  }

  // TTS parametry (některé jsou ignorovány u F5, ale předáváme pro kompatibilitu)
  if (ttsParams.speed !== undefined && ttsParams.speed !== null) {
    formData.append('speed', ttsParams.speed.toString())
  }
  if (ttsParams.temperature !== undefined && ttsParams.temperature !== null) {
    formData.append('temperature', ttsParams.temperature.toString())
  }
  if (ttsParams.lengthPenalty !== undefined && ttsParams.lengthPenalty !== null) {
    formData.append('length_penalty', ttsParams.lengthPenalty.toString())
  }
  if (ttsParams.repetitionPenalty !== undefined && ttsParams.repetitionPenalty !== null) {
    formData.append('repetition_penalty', ttsParams.repetitionPenalty.toString())
  }
  if (ttsParams.topK !== undefined && ttsParams.topK !== null) {
    formData.append('top_k', ttsParams.topK.toString())
  }
  if (ttsParams.topP !== undefined && ttsParams.topP !== null) {
    formData.append('top_p', ttsParams.topP.toString())
  }
  if (ttsParams.seed !== undefined && ttsParams.seed !== null) {
    formData.append('seed', ttsParams.seed.toString())
  }
  if (ttsParams.qualityMode !== undefined && ttsParams.qualityMode !== null) {
    formData.append('quality_mode', ttsParams.qualityMode)
  }
  if (ttsParams.enhancementPreset !== undefined && ttsParams.enhancementPreset !== null) {
    formData.append('enhancement_preset', ttsParams.enhancementPreset)
  }
  if (ttsParams.enableEnhancement !== undefined && ttsParams.enableEnhancement !== null) {
    formData.append('enable_enhancement', ttsParams.enableEnhancement.toString())
  }
  if (ttsParams.enableVad !== undefined && ttsParams.enableVad !== null) {
    formData.append('enable_vad', ttsParams.enableVad.toString())
  }
  if (ttsParams.useHifigan !== undefined && ttsParams.useHifigan !== null) {
    formData.append('use_hifigan', ttsParams.useHifigan.toString())
  }
  if (ttsParams.enableNormalization !== undefined && ttsParams.enableNormalization !== null) {
    formData.append('enable_normalization', ttsParams.enableNormalization.toString())
  }
  if (ttsParams.enableDenoiser !== undefined && ttsParams.enableDenoiser !== null) {
    formData.append('enable_denoiser', ttsParams.enableDenoiser.toString())
  }
  if (ttsParams.enableCompressor !== undefined && ttsParams.enableCompressor !== null) {
    formData.append('enable_compressor', ttsParams.enableCompressor.toString())
  }
  if (ttsParams.enableDeesser !== undefined && ttsParams.enableDeesser !== null) {
    formData.append('enable_deesser', ttsParams.enableDeesser.toString())
  }
  if (ttsParams.enableEq !== undefined && ttsParams.enableEq !== null) {
    formData.append('enable_eq', ttsParams.enableEq.toString())
  }
  if (ttsParams.enableTrim !== undefined && ttsParams.enableTrim !== null) {
    formData.append('enable_trim', ttsParams.enableTrim.toString())
  }
  if (ttsParams.enableDialectConversion !== undefined && ttsParams.enableDialectConversion !== null) {
    formData.append('enable_dialect_conversion', ttsParams.enableDialectConversion.toString())
  }
  if (ttsParams.dialectCode !== undefined && ttsParams.dialectCode !== null) {
    formData.append('dialect_code', ttsParams.dialectCode)
  }
  if (ttsParams.dialectIntensity !== undefined && ttsParams.dialectIntensity !== null) {
    formData.append('dialect_intensity', ttsParams.dialectIntensity.toString())
  }
  if (ttsParams.hifiganRefinementIntensity !== undefined && ttsParams.hifiganRefinementIntensity !== null) {
    formData.append('hifigan_refinement_intensity', ttsParams.hifiganRefinementIntensity.toString())
  }
  if (ttsParams.hifiganNormalizeOutput !== undefined && ttsParams.hifiganNormalizeOutput !== null) {
    formData.append('hifigan_normalize_output', ttsParams.hifiganNormalizeOutput.toString())
  }
  if (ttsParams.hifiganNormalizeGain !== undefined && ttsParams.hifiganNormalizeGain !== null) {
    formData.append('hifigan_normalize_gain', ttsParams.hifiganNormalizeGain.toString())
  }
  if (ttsParams.enableWhisper !== undefined && ttsParams.enableWhisper !== null) {
    formData.append('enable_whisper', ttsParams.enableWhisper.toString())
  }
  if (ttsParams.whisperIntensity !== undefined && ttsParams.whisperIntensity !== null) {
    formData.append('whisper_intensity', ttsParams.whisperIntensity.toString())
  }
  if (ttsParams.targetHeadroomDb !== undefined && ttsParams.targetHeadroomDb !== null) {
    formData.append('target_headroom_db', ttsParams.targetHeadroomDb.toString())
  }

  const response = await fetch(`${API_BASE_URL}/api/tts/generate-f5`, {
    method: 'POST',
    body: formData
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Chyba při generování řeči (F5-TTS)')
  }

  return await response.json()
}

/**
 * Generuje řeč pomocí F5-TTS slovenského modelu
 */
export async function generateF5TTSSlovak(text, voiceFile = null, demoVoice = null, ttsParams = {}, jobId = null) {
  const formData = new FormData()
  formData.append('text', text)
  if (jobId) {
    formData.append('job_id', jobId)
  }

  if (voiceFile) {
    formData.append('voice_file', voiceFile)
  } else if (demoVoice) {
    formData.append('demo_voice', demoVoice)
  }

  // Volitelný ref_text (přepis reference audio)
  if (ttsParams.refText !== undefined && ttsParams.refText !== null && ttsParams.refText.trim() !== '') {
    formData.append('ref_text', ttsParams.refText)
  }

  // TTS parametry (stejné jako F5-TTS)
  if (ttsParams.speed !== undefined && ttsParams.speed !== null) {
    formData.append('speed', ttsParams.speed.toString())
  }
  if (ttsParams.temperature !== undefined && ttsParams.temperature !== null) {
    formData.append('temperature', ttsParams.temperature.toString())
  }
  if (ttsParams.lengthPenalty !== undefined && ttsParams.lengthPenalty !== null) {
    formData.append('length_penalty', ttsParams.lengthPenalty.toString())
  }
  if (ttsParams.repetitionPenalty !== undefined && ttsParams.repetitionPenalty !== null) {
    formData.append('repetition_penalty', ttsParams.repetitionPenalty.toString())
  }
  if (ttsParams.topK !== undefined && ttsParams.topK !== null) {
    formData.append('top_k', ttsParams.topK.toString())
  }
  if (ttsParams.topP !== undefined && ttsParams.topP !== null) {
    formData.append('top_p', ttsParams.topP.toString())
  }
  if (ttsParams.seed !== undefined && ttsParams.seed !== null) {
    formData.append('seed', ttsParams.seed.toString())
  }
  if (ttsParams.qualityMode !== undefined && ttsParams.qualityMode !== null) {
    formData.append('quality_mode', ttsParams.qualityMode)
  }
  if (ttsParams.enhancementPreset !== undefined && ttsParams.enhancementPreset !== null) {
    formData.append('enhancement_preset', ttsParams.enhancementPreset)
  }
  if (ttsParams.enableEnhancement !== undefined && ttsParams.enableEnhancement !== null) {
    formData.append('enable_enhancement', ttsParams.enableEnhancement.toString())
  }
  if (ttsParams.enableVad !== undefined && ttsParams.enableVad !== null) {
    formData.append('enable_vad', ttsParams.enableVad.toString())
  }
  if (ttsParams.useHifigan !== undefined && ttsParams.useHifigan !== null) {
    formData.append('use_hifigan', ttsParams.useHifigan.toString())
  }
  if (ttsParams.enableNormalization !== undefined && ttsParams.enableNormalization !== null) {
    formData.append('enable_normalization', ttsParams.enableNormalization.toString())
  }
  if (ttsParams.enableDenoiser !== undefined && ttsParams.enableDenoiser !== null) {
    formData.append('enable_denoiser', ttsParams.enableDenoiser.toString())
  }
  if (ttsParams.enableCompressor !== undefined && ttsParams.enableCompressor !== null) {
    formData.append('enable_compressor', ttsParams.enableCompressor.toString())
  }
  if (ttsParams.enableDeesser !== undefined && ttsParams.enableDeesser !== null) {
    formData.append('enable_deesser', ttsParams.enableDeesser.toString())
  }
  if (ttsParams.enableEq !== undefined && ttsParams.enableEq !== null) {
    formData.append('enable_eq', ttsParams.enableEq.toString())
  }
  if (ttsParams.enableTrim !== undefined && ttsParams.enableTrim !== null) {
    formData.append('enable_trim', ttsParams.enableTrim.toString())
  }
  if (ttsParams.hifiganRefinementIntensity !== undefined && ttsParams.hifiganRefinementIntensity !== null) {
    formData.append('hifigan_refinement_intensity', ttsParams.hifiganRefinementIntensity.toString())
  }
  if (ttsParams.hifiganNormalizeOutput !== undefined && ttsParams.hifiganNormalizeOutput !== null) {
    formData.append('hifigan_normalize_output', ttsParams.hifiganNormalizeOutput.toString())
  }
  if (ttsParams.hifiganNormalizeGain !== undefined && ttsParams.hifiganNormalizeGain !== null) {
    formData.append('hifigan_normalize_gain', ttsParams.hifiganNormalizeGain.toString())
  }
  if (ttsParams.enableWhisper !== undefined && ttsParams.enableWhisper !== null) {
    formData.append('enable_whisper', ttsParams.enableWhisper.toString())
  }
  if (ttsParams.whisperIntensity !== undefined && ttsParams.whisperIntensity !== null) {
    formData.append('whisper_intensity', ttsParams.whisperIntensity.toString())
  }
  if (ttsParams.targetHeadroomDb !== undefined && ttsParams.targetHeadroomDb !== null) {
    formData.append('target_headroom_db', ttsParams.targetHeadroomDb.toString())
  }
  if (ttsParams.removeBackground !== undefined && ttsParams.removeBackground !== null) {
    formData.append('remove_background', ttsParams.removeBackground.toString())
  }

  const response = await fetch(`${API_BASE_URL}/api/tts/generate-f5-sk`, {
    method: 'POST',
    body: formData
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Chyba při generování řeči (F5-TTS Slovak)')
  }

  return await response.json()
}

/**
 * Získá průběh generování TTS pro daný jobId (polling - pro zpětnou kompatibilitu)
 */
export async function getTtsProgress(jobId) {
  const response = await fetch(`${API_BASE_URL}/api/tts/progress/${jobId}`)
  if (!response.ok) {
    // Progress může dočasně vracet 404 (např. před startem) – caller si to ošetří
    const err = await response.json().catch(() => ({}))
    const e = new Error(err.detail || 'Progress není dostupný')
    e.status = response.status
    throw e
  }
  return await response.json()
}

/**
 * Vytvoří EventSource pro real-time progress updates pomocí Server-Sent Events (SSE)
 * @param {string} jobId - ID jobu pro sledování
 * @param {Function} onProgress - Callback funkce volaná při každé aktualizaci progressu
 * @param {Function} onError - Callback funkce volaná při chybě
 * @returns {EventSource} EventSource instance pro případné uzavření
 */
export function subscribeToTtsProgress(jobId, onProgress, onError) {
  const eventSource = new EventSource(`${API_BASE_URL}/api/tts/progress/${jobId}/stream`)

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      onProgress(data)

      // Pokud je job hotový nebo chybný, uzavřít spojení
      if (data.status === 'done' || data.status === 'error') {
        eventSource.close()
      }
    } catch (err) {
      console.error('Chyba při parsování SSE dat:', err)
      if (onError) {
        onError(err)
      }
    }
  }

  eventSource.onerror = (error) => {
    console.error('SSE chyba:', error)
    if (onError) {
      onError(error)
    }
    // EventSource automaticky zkusí znovu připojit, ale můžeme ho uzavřít při kritické chybě
    // eventSource.close()
  }

  return eventSource
}

/**
 * Nahraje audio soubor pro voice cloning
 */
export async function uploadVoice(voiceFile, removeBackground = false) {
  const formData = new FormData()
  formData.append('voice_file', voiceFile)
  formData.append('remove_background', removeBackground.toString())

  const response = await fetch(`${API_BASE_URL}/api/voice/upload`, {
    method: 'POST',
    body: formData
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Chyba při uploadu hlasu')
  }

  return await response.json()
}

/**
 * Uloží audio nahrané z mikrofonu jako demo hlas
 */
export async function recordVoice(audioBlobBase64, filename = null, lang = 'cs') {
  const formData = new FormData()
  formData.append('audio_blob', audioBlobBase64)

  if (filename) {
    formData.append('filename', filename)
  }
  if (lang) {
    formData.append('lang', lang)
  }

  const response = await fetch(`${API_BASE_URL}/api/voice/record`, {
    method: 'POST',
    body: formData
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Chyba při ukládání nahrávky')
  }

  return await response.json()
}

/**
 * Získá seznam demo hlasů
 */
export async function getDemoVoices(lang = 'cs') {
  const q = lang ? `?lang=${encodeURIComponent(lang)}` : ''
  const response = await fetch(`${API_BASE_URL}/api/voices/demo${q}`)

  if (!response.ok) {
    throw new Error('Chyba při načítání demo hlasů')
  }

  return await response.json()
}

/**
 * Získá status modelu
 */
export async function getModelStatus() {
  const response = await fetch(`${API_BASE_URL}/api/models/status`)

  if (!response.ok) {
    throw new Error('Chyba při kontrole statusu modelu')
  }

  return await response.json()
}

/**
 * Stáhne audio z YouTube a uloží jako demo hlas
 */
export async function downloadYouTubeVoice(url, startTime = null, duration = null, filename = null, lang = 'cs', removeBackground = false) {
  const formData = new FormData()
  formData.append('url', url)

  if (startTime !== null && startTime !== undefined) {
    formData.append('start_time', startTime.toString())
  }

  if (duration !== null && duration !== undefined) {
    formData.append('duration', duration.toString())
  }

  if (filename) {
    formData.append('filename', filename)
  }
  if (lang) {
    formData.append('lang', lang)
  }
  formData.append('remove_background', removeBackground.toString())

  const response = await fetch(`${API_BASE_URL}/api/voice/youtube`, {
    method: 'POST',
    body: formData
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Chyba při stahování z YouTube')
  }

  return await response.json()
}

/**
 * Přepíše referenční audio na text (ref_text) pomocí backend ASR (Whisper).
 * - buď pošle voice_file (upload)
 * - nebo demo_voice (id bez přípony)
 */
export async function transcribeReferenceAudio({ voiceFile = null, demoVoice = null, language = 'sk' } = {}) {
  const formData = new FormData()
  if (voiceFile) {
    formData.append('voice_file', voiceFile)
  }
  if (demoVoice) {
    formData.append('demo_voice', demoVoice)
  }
  if (language) {
    formData.append('language', language)
  }

  const response = await fetch(`${API_BASE_URL}/api/asr/transcribe`, {
    method: 'POST',
    body: formData
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || 'Chyba při přepisu audia')
  }

  return await response.json()
}

/**
 * Získá historii generovaných audio souborů
 */
export async function getHistory(limit = null, offset = 0) {
  const params = new URLSearchParams({ offset: String(offset) })
  if (limit !== null) {
    params.append('limit', String(limit))
  }
  const response = await fetch(`${API_BASE_URL}/api/history?${params.toString()}`)

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Chyba při načítání historie')
  }

  return await response.json()
}

/**
 * Získá konkrétní záznam z historie
 */
export async function getHistoryEntry(entryId) {
  const response = await fetch(`${API_BASE_URL}/api/history/${entryId}`)

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Chyba při načítání záznamu')
  }

  return await response.json()
}

/**
 * Smaže záznam z historie
 */
export async function deleteHistoryEntry(entryId) {
  const response = await fetch(`${API_BASE_URL}/api/history/${entryId}`, {
    method: 'DELETE'
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Chyba při mazání záznamu')
  }

  return await response.json()
}

/**
 * Vymaže celou historii
 */
export async function clearHistory() {
  const response = await fetch(`${API_BASE_URL}/api/history`, {
    method: 'DELETE'
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Chyba při mazání historie')
  }


  return await response.json()
}

/**
 * Generuje hudbu pomocí MusicGen
 * @param {string} prompt
 * @param {Object} params
 * @param {string|null} jobId
 */
export async function generateMusic(prompt, params = {}, jobId = null) {
  const formData = new FormData()
  formData.append('prompt', prompt)
  if (jobId) formData.append('job_id', jobId)

  if (params.model) formData.append('model', params.model) // small|medium|large
  if (params.precision !== undefined && params.precision !== null) formData.append('precision', String(params.precision)) // auto|fp32|fp16|bf16
  if (params.offload !== undefined && params.offload !== null) formData.append('offload', params.offload ? 'true' : 'false')
  if (params.maxVramGb !== undefined && params.maxVramGb !== null && params.maxVramGb !== '') formData.append('max_vram_gb', String(params.maxVramGb))
  if (params.duration !== undefined && params.duration !== null) formData.append('duration', String(params.duration))
  if (params.temperature !== undefined && params.temperature !== null) formData.append('temperature', String(params.temperature))
  if (params.topK !== undefined && params.topK !== null) formData.append('top_k', String(params.topK))
  if (params.topP !== undefined && params.topP !== null) formData.append('top_p', String(params.topP))
  if (params.seed !== undefined && params.seed !== null && params.seed !== '') formData.append('seed', String(params.seed))
  if (params.ambience !== undefined && params.ambience !== null) formData.append('ambience', String(params.ambience))
  if (params.ambienceGainDb !== undefined && params.ambienceGainDb !== null) formData.append('ambience_gain_db', String(params.ambienceGainDb))
  if (params.ambienceSeed !== undefined && params.ambienceSeed !== null && params.ambienceSeed !== '') formData.append('ambience_seed', String(params.ambienceSeed))
  if (params.ambienceFileStream) formData.append('ambience_file_stream', params.ambienceFileStream)
  if (params.ambienceFileBirds) formData.append('ambience_file_birds', params.ambienceFileBirds)

  const response = await fetch(`${API_BASE_URL}/api/musicgen/generate`, {
    method: 'POST',
    body: formData
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || 'Chyba při generování hudby')
  }

  return await response.json()
}

/**
 * Progress (polling) pro MusicGen
 */
export async function getMusicProgress(jobId) {
  const response = await fetch(`${API_BASE_URL}/api/music/progress/${jobId}`)
  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    const e = new Error(err.detail || 'Progress není dostupný')
    e.status = response.status
    throw e
  }
  return await response.json()
}

/**
 * Progress (SSE) pro MusicGen
 */
export function subscribeToMusicProgress(jobId, onProgress, onError) {
  const eventSource = new EventSource(`${API_BASE_URL}/api/music/progress/${jobId}/stream`)

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      onProgress(data)
      if (data.status === 'done' || data.status === 'error') {
        eventSource.close()
      }
    } catch (err) {
      console.error('Chyba při parsování SSE dat:', err)
      if (onError) onError(err)
    }
  }

  eventSource.onerror = (error) => {
    console.error('SSE chyba:', error)
    if (onError) onError(error)
  }

  return eventSource
}

/**
 * Samostatná historie MusicGen
 */
export async function getMusicHistory(limit = null, offset = 0) {
  const params = new URLSearchParams({ offset: String(offset) })
  if (limit !== null) {
    params.append('limit', String(limit))
  }
  const response = await fetch(`${API_BASE_URL}/api/music/history?${params.toString()}`)
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || 'Chyba při načítání hudební historie')
  }
  return await response.json()
}

export async function getMusicHistoryEntry(entryId) {
  const response = await fetch(`${API_BASE_URL}/api/music/history/${entryId}`)
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || 'Chyba při načítání záznamu')
  }
  return await response.json()
}

export async function deleteMusicHistoryEntry(entryId) {
  const response = await fetch(`${API_BASE_URL}/api/music/history/${entryId}`, { method: 'DELETE' })
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || 'Chyba při mazání záznamu')
  }
  return await response.json()
}

export async function clearMusicHistory() {
  const response = await fetch(`${API_BASE_URL}/api/music/history`, { method: 'DELETE' })
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || 'Chyba při mazání hudební historie')
  }
  return await response.json()
}

/**
 * Získá seznam dostupných ambience samplů
 */
export async function getAmbienceList() {
  const response = await fetch(`${API_BASE_URL}/api/music/ambience/list`)
  if (!response.ok) {
    throw new Error('Chyba při načítání seznamu ambience')
  }
  return await response.json()
}

/**
 * Generuje audio pomocí Bark modelu
 * @param {string} text - Textový prompt
 * @param {Object} params - Parametry generování
 * @param {string} params.modelSize - Velikost modelu ("small" nebo "large")
 * @param {number} params.temperature - Teplota (0.0-1.0)
 * @param {number|null} params.seed - Seed pro reprodukovatelnost
 * @param {number} params.duration - Délka v sekundách (1-120, None = výchozí ~14s)
 * @param {string|null} jobId - ID jobu pro progress tracking
 */
export async function generateBark(text, params = {}, jobId = null) {
  const formData = new FormData()
  formData.append('text', text)
  if (jobId) formData.append('job_id', jobId)

  if (params.modelSize) formData.append('model_size', params.modelSize)
  if (params.mode !== undefined && params.mode !== null) formData.append('mode', String(params.mode)) // auto|full|mixed|small
  if (params.offloadCpu !== undefined && params.offloadCpu !== null) formData.append('offload_cpu', params.offloadCpu ? 'true' : 'false')
  if (params.temperature !== undefined && params.temperature !== null) formData.append('temperature', String(params.temperature))
  if (params.seed !== undefined && params.seed !== null && params.seed !== '') formData.append('seed', String(params.seed))
  if (params.duration !== undefined && params.duration !== null) formData.append('duration', String(params.duration))

  const response = await fetch(`${API_BASE_URL}/api/bark/generate`, {
    method: 'POST',
    body: formData
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || 'Chyba při generování Bark audia')
  }

  return await response.json()
}

/**
 * Progress (polling) pro Bark
 */
export async function getBarkProgress(jobId) {
  const response = await fetch(`${API_BASE_URL}/api/bark/progress/${jobId}`)
  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    const e = new Error(err.detail || 'Progress není dostupný')
    e.status = response.status
    throw e
  }
  return await response.json()
}

/**
 * Progress (SSE) pro Bark
 */
export function subscribeToBarkProgress(jobId, onProgress, onError) {
  const eventSource = new EventSource(`${API_BASE_URL}/api/bark/progress/${jobId}/stream`)

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      onProgress(data)
      if (data.status === 'done' || data.status === 'error') {
        eventSource.close()
      }
    } catch (err) {
      console.error('Chyba při parsování SSE dat:', err)
      if (onError) onError(err)
    }
  }

  eventSource.onerror = (error) => {
    console.error('SSE chyba:', error)
    if (onError) onError(error)
  }

  return eventSource
}

/**
 * Samostatná historie Bark
 */
export async function getBarkHistory(limit = null, offset = 0) {
  const params = new URLSearchParams({ offset: String(offset) })
  if (limit !== null) {
    params.append('limit', String(limit))
  }
  const response = await fetch(`${API_BASE_URL}/api/bark/history?${params.toString()}`)
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || 'Chyba při načítání historie Bark')
  }
  return await response.json()
}

export async function getBarkHistoryEntry(entryId) {
  const response = await fetch(`${API_BASE_URL}/api/bark/history/${entryId}`)
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || 'Chyba při načítání záznamu')
  }
  return await response.json()
}

export async function deleteBarkHistoryEntry(entryId) {
  const response = await fetch(`${API_BASE_URL}/api/bark/history/${entryId}`, { method: 'DELETE' })
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || 'Chyba při mazání záznamu')
  }
  return await response.json()
}

export async function clearBarkHistory() {
  const response = await fetch(`${API_BASE_URL}/api/bark/history`, { method: 'DELETE' })
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || 'Chyba při mazání historie Bark')
  }
  return await response.json()
}

/**
 * Historie promptů - XTTS
 */
export async function getXTTSPromptsHistory(limit = null, offset = 0) {
  const params = new URLSearchParams({ offset: String(offset) })
  if (limit !== null) {
    params.append('limit', String(limit))
  }
  const response = await fetch(`${API_BASE_URL}/api/prompts/xtts/history?${params.toString()}`)
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || 'Chyba při načítání XTTS prompts historie')
  }
  return await response.json()
}

export async function deleteXTTSPromptEntry(entryId) {
  const response = await fetch(`${API_BASE_URL}/api/prompts/xtts/history/${entryId}`, { method: 'DELETE' })
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || 'Chyba při mazání záznamu')
  }
  return await response.json()
}

/**
 * Historie promptů - F5-TTS
 */
export async function getF5TTSPromptsHistory(limit = null, offset = 0) {
  const params = new URLSearchParams({ offset: String(offset) })
  if (limit !== null) {
    params.append('limit', String(limit))
  }
  const response = await fetch(`${API_BASE_URL}/api/prompts/f5tts/history?${params.toString()}`)
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || 'Chyba při načítání F5-TTS prompts historie')
  }
  return await response.json()
}

export async function deleteF5TTSPromptEntry(entryId) {
  const response = await fetch(`${API_BASE_URL}/api/prompts/f5tts/history/${entryId}`, { method: 'DELETE' })
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || 'Chyba při mazání záznamu')
  }
  return await response.json()
}

/**
 * Historie promptů - F5-TTS-SK
 */
export async function getF5TTSSKPromptsHistory(limit = null, offset = 0) {
  const params = new URLSearchParams({ offset: String(offset) })
  if (limit !== null) {
    params.append('limit', String(limit))
  }
  const response = await fetch(`${API_BASE_URL}/api/prompts/f5tts-sk/history?${params.toString()}`)
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || 'Chyba při načítání F5-TTS-SK prompts historie')
  }
  return await response.json()
}

export async function deleteF5TTSSKPromptEntry(entryId) {
  const response = await fetch(`${API_BASE_URL}/api/prompts/f5tts-sk/history/${entryId}`, { method: 'DELETE' })
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || 'Chyba při mazání záznamu')
  }
  return await response.json()
}


