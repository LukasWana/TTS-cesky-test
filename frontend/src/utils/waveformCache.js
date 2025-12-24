// bump verze kvůli špatně uloženým peaks z předchozího nastavení (barcode look)
const WAVEFORM_CACHE_KEY = 'waveform_peaks_cache_v2'

// In-memory cache to avoid JSON.parse/stringify per item render
let _mem = null
let _flushTimer = null
let _dirty = false

function _loadMem() {
  if (_mem) return _mem
  try {
    _mem = JSON.parse(localStorage.getItem(WAVEFORM_CACHE_KEY) || '{}')
  } catch (e) {
    _mem = {}
  }
  return _mem
}

function _scheduleFlush() {
  if (_flushTimer) return
  _flushTimer = setTimeout(() => {
    _flushTimer = null
    if (!_dirty) return
    _dirty = false
    try {
      localStorage.setItem(WAVEFORM_CACHE_KEY, JSON.stringify(_mem || {}))
    } catch (e) {
      // quota / serialization issues - ignore
    }
  }, 500)
}

function _enforceCap(cache, maxEntries) {
  const entries = Object.entries(cache)
  if (entries.length <= maxEntries) return cache
  entries.sort((a, b) => (b[1]?.timestamp || 0) - (a[1]?.timestamp || 0))
  return Object.fromEntries(entries.slice(0, maxEntries))
}

/**
 * Vytvoří kanonický klíč pro cache z audio URL.
 * Normalizuje různé formáty URL na stejný klíč:
 * - "http://localhost:8000/api/audio/x.wav" -> "/api/audio/x.wav"
 * - "/api/audio/x.wav" -> "/api/audio/x.wav"
 * - "api/audio/x.wav" -> "/api/audio/x.wav"
 */
export function canonicalAudioCacheKey(audioUrl) {
  if (!audioUrl) return null
  try {
    // Pokud je to full URL, extrahovat path
    if (audioUrl.startsWith('http://') || audioUrl.startsWith('https://')) {
      const url = new URL(audioUrl)
      return url.pathname
    }
    // Pokud už je relativní, normalizovat (zajistit začátek s /)
    return audioUrl.startsWith('/') ? audioUrl : `/${audioUrl}`
  } catch (e) {
    // Fallback: použít URL jak je, pokud není validní
    return audioUrl.startsWith('/') ? audioUrl : `/${audioUrl}`
  }
}

export function getWaveformCache(audioUrl) {
  if (!audioUrl) return null
  const key = canonicalAudioCacheKey(audioUrl)
  if (!key) return null
  const mem = _loadMem()
  return mem[key] || null
}

export function setWaveformCache(audioUrl, value) {
  if (!audioUrl) return
  const key = canonicalAudioCacheKey(audioUrl)
  if (!key) return
  const mem = _loadMem()
  mem[key] = value
  _mem = _enforceCap(mem, 500)
  _dirty = true
  _scheduleFlush()
}

export function deleteWaveformCache(audioUrl) {
  if (!audioUrl) return
  const key = canonicalAudioCacheKey(audioUrl)
  if (!key) return
  const mem = _loadMem()
  if (key in mem) {
    delete mem[key]
    _mem = mem
    _dirty = true
    _scheduleFlush()
  }
}

export function clearWaveformCache() {
  _mem = {}
  _dirty = false
  if (_flushTimer) {
    clearTimeout(_flushTimer)
    _flushTimer = null
  }
  try {
    localStorage.removeItem(WAVEFORM_CACHE_KEY)
  } catch (e) {
    // ignore
  }
}


