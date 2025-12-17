/**
 * API client pro komunikaci s backend
 */
const API_BASE_URL = 'http://localhost:8000'

/**
 * Generuje řeč z textu
 */
export async function generateSpeech(text, voiceFile = null, demoVoice = null) {
  const formData = new FormData()
  formData.append('text', text)

  if (voiceFile) {
    formData.append('voice_file', voiceFile)
  } else if (demoVoice) {
    formData.append('demo_voice', demoVoice)
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
}

