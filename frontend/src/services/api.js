/**
 * API client pro komunikaci s backend
 */
const API_BASE_URL = 'http://localhost:8000'


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
 */
export async function generateSpeech(text, voiceFile = null, demoVoice = null, ttsParams = {}) {
  const formData = new FormData()
  formData.append('text', text)

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
 * Nahraje audio soubor pro voice cloning
 */
export async function uploadVoice(voiceFile) {
  const formData = new FormData()
  formData.append('voice_file', voiceFile)

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
export async function recordVoice(audioBlobBase64, filename = null) {
  const formData = new FormData()
  formData.append('audio_blob', audioBlobBase64)

  if (filename) {
    formData.append('filename', filename)
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
export async function getDemoVoices() {
  const response = await fetch(`${API_BASE_URL}/api/voices/demo`)

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
export async function downloadYouTubeVoice(url, startTime = null, duration = null, filename = null) {
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

  const response = await fetch(`${API_BASE_URL}/api/voice/youtube`, {
    method: 'POST',
    body: formData
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Chyba při stahování z YouTube')
  }

  return await response.json()
  return data
}

/**
 * Získá historii generovaných audio souborů
 */
export async function getHistory(limit = 50, offset = 0) {
  const response = await fetch(`${API_BASE_URL}/api/history?limit=${limit}&offset=${offset}`)

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


