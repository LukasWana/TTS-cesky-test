import React, { useState } from 'react'
import { downloadYouTubeVoice } from '../services/api'
import LoadingSpinner from './LoadingSpinner'
import './YouTubeImporter.css'

function YouTubeImporter({ onImportComplete, onError }) {
  const [url, setUrl] = useState('')
  const [startTime, setStartTime] = useState('')
  const [duration, setDuration] = useState('')
  const [filename, setFilename] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)

  const parseTimeToSeconds = (timeStr) => {
    if (!timeStr || timeStr.trim() === '') return null

    // Formát MM:SS nebo HH:MM:SS
    const parts = timeStr.split(':').map(p => parseInt(p.trim(), 10))

    if (parts.length === 1) {
      // Jen sekundy
      return parts[0]
    } else if (parts.length === 2) {
      // MM:SS
      return parts[0] * 60 + parts[1]
    } else if (parts.length === 3) {
      // HH:MM:SS
      return parts[0] * 3600 + parts[1] * 60 + parts[2]
    }

    return null
  }

  const formatSecondsToTime = (seconds) => {
    if (!seconds && seconds !== 0) return ''
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = Math.floor(seconds % 60)

    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`
  }

  const validateUrl = (urlStr) => {
    if (!urlStr || urlStr.trim() === '') {
      return 'URL je povinná'
    }

    // Podporuje více formátů YouTube URL
    const youtubePatterns = [
      /^(https?:\/\/)?(www\.)?(m\.)?youtube\.com\/watch\?v=[a-zA-Z0-9_-]{11}/,
      /^(https?:\/\/)?(www\.)?youtube\.com\/watch\?.*[&?]v=[a-zA-Z0-9_-]{11}/,
      /^(https?:\/\/)?youtu\.be\/[a-zA-Z0-9_-]{11}/,
      /^(https?:\/\/)?(www\.)?youtube\.com\/embed\/[a-zA-Z0-9_-]{11}/,
      /^(https?:\/\/)?(www\.)?youtube\.com\/v\/[a-zA-Z0-9_-]{11}/
    ]

    const isValid = youtubePatterns.some(pattern => pattern.test(urlStr))
    if (!isValid) {
      return 'Neplatná YouTube URL. Použijte formát: https://www.youtube.com/watch?v=VIDEO_ID'
    }

    return null
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    // Validace
    const urlError = validateUrl(url)
    if (urlError) {
      setError(urlError)
      return
    }

    // Parsování času
    const startSeconds = startTime ? parseTimeToSeconds(startTime) : null
    const durationSeconds = duration ? parseTimeToSeconds(duration) : null

    if (startSeconds !== null && startSeconds < 0) {
      setError('Začátek musí být >= 0')
      return
    }

    if (durationSeconds !== null) {
      if (durationSeconds < 6) {
        setError('Délka musí být minimálně 6 sekund')
        return
      }
      if (durationSeconds > 600) {
        setError('Délka nesmí přesáhnout 600 sekund (10 minut)')
        return
      }
    }

    setLoading(true)
    setError(null)
    setSuccess(null)

    try {
      const result = await downloadYouTubeVoice(
        url.trim(),
        startSeconds,
        durationSeconds,
        filename.trim() || null
      )

      setSuccess(`✓ Audio úspěšně staženo a uloženo jako: ${result.filename}`)

      // Callback pro rodičovskou komponentu
      if (onImportComplete) {
        onImportComplete(result)
      }

      // Reset formuláře
      setUrl('')
      setStartTime('')
      setDuration('')
      setFilename('')

    } catch (err) {
      const errorMessage = err.message || 'Chyba při stahování z YouTube'
      setError(errorMessage)
      if (onError) {
        onError(err)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="youtube-importer">
      <form onSubmit={handleSubmit} className="youtube-form">
        <div className="form-group">
          <label htmlFor="youtube-url">YouTube URL *</label>
          <input
            id="youtube-url"
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://www.youtube.com/watch?v=VIDEO_ID"
            disabled={loading}
            required
          />
          <small>Podporované formáty: youtube.com/watch?v=... nebo youtu.be/...</small>
        </div>

        <div className="time-inputs">
          <div className="form-group">
            <label htmlFor="start-time">Začátek (volitelné)</label>
            <input
              id="start-time"
              type="text"
              value={startTime}
              onChange={(e) => setStartTime(e.target.value)}
              placeholder="MM:SS nebo sekundy"
              disabled={loading}
            />
            <small>Např: 1:30 nebo 90 (sekundy)</small>
          </div>

          <div className="form-group">
            <label htmlFor="duration">Délka (volitelné)</label>
            <input
              id="duration"
              type="text"
              value={duration}
              onChange={(e) => setDuration(e.target.value)}
              placeholder="MM:SS nebo sekundy"
              disabled={loading}
            />
            <small>Min. 6s, max. 600s (10 min)</small>
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="filename">Název souboru (volitelné)</label>
          <input
            id="filename"
            type="text"
            value={filename}
            onChange={(e) => setFilename(e.target.value)}
            placeholder="např. male_cz"
            disabled={loading}
          />
          <small>Pokud není zadán, použije se automatický název</small>
        </div>

        {error && (
          <div className="error-message">
            ❌ {error}
          </div>
        )}

        {success && (
          <div className="success-message">
            {success}
          </div>
        )}

        <button
          type="submit"
          className="download-button"
          disabled={loading || !url.trim()}
        >
          {loading ? (
            <>
              <LoadingSpinner size="small" />
              <span>Stahování...</span>
            </>
          ) : (
            '📥 Stáhnout a uložit'
          )}
        </button>
      </form>
    </div>
  )
}

export default YouTubeImporter

