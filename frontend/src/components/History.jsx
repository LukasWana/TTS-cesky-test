import React, { useState, useEffect } from 'react'
import { getHistory, deleteHistoryEntry, clearHistory } from '../services/api'
import AudioPlayer from './AudioPlayer'
import './History.css'

const API_BASE_URL = 'http://localhost:8000'

function History() {
  const [history, setHistory] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedEntry, setSelectedEntry] = useState(null)

  useEffect(() => {
    loadHistory()
  }, [])

  const loadHistory = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await getHistory(100, 0)
      setHistory(data.history || [])
      setStats(data.stats || null)
    } catch (err) {
      setError(err.message || 'Chyba při načítání historie')
      console.error('History load error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (entryId, e) => {
    e.stopPropagation()
    if (!window.confirm('Opravdu chcete smazat tento záznam?')) {
      return
    }

    try {
      await deleteHistoryEntry(entryId)
      setHistory(history.filter(entry => entry.id !== entryId))
    } catch (err) {
      setError(err.message || 'Chyba při mazání záznamu')
    }
  }

  const handleClearAll = async () => {
    if (!window.confirm('Opravdu chcete vymazat celou historii? Tato akce je nevratná.')) {
      return
    }

    try {
      await clearHistory()
      setHistory([])
      setStats(null)
    } catch (err) {
      setError(err.message || 'Chyba při mazání historie')
    }
  }

  const formatDate = (dateString) => {
    try {
      const date = new Date(dateString)
      return date.toLocaleString('cs-CZ', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch {
      return dateString
    }
  }

  const formatText = (text, maxLength = 100) => {
    if (text.length <= maxLength) return text
    return text.substring(0, maxLength) + '...'
  }

  const getVoiceTypeLabel = (type) => {
    const labels = {
      'demo': 'Demo hlas',
      'upload': 'Nahraný soubor',
      'record': 'Nahrávka z mikrofonu',
      'youtube': 'YouTube'
    }
    return labels[type] || type
  }

  if (loading) {
    return (
      <div className="history-container">
        <div className="history-loading">⏳ Načítání historie...</div>
      </div>
    )
  }

  return (
    <div className="history-container">
      <div className="history-header">
        <h2>📜 Historie generovaných audio</h2>
        {stats && (
          <div className="history-stats">
            <span>Celkem: <strong>{stats.total_entries}</strong></span>
          </div>
        )}
        {history.length > 0 && (
          <button className="btn-clear-all" onClick={handleClearAll}>
            🗑️ Vymazat vše
          </button>
        )}
      </div>

      {error && (
        <div className="history-error">
          ⚠️ {error}
        </div>
      )}

      {history.length === 0 ? (
        <div className="history-empty">
          <p>📭 Historie je prázdná</p>
          <p className="history-empty-hint">Zde se zobrazí všechny generované audio soubory</p>
        </div>
      ) : (
        <div className="history-list">
          {history.map((entry) => (
            <div
              key={entry.id}
              className={`history-item ${selectedEntry?.id === entry.id ? 'selected' : ''}`}
              onClick={() => setSelectedEntry(selectedEntry?.id === entry.id ? null : entry)}
            >
              <div className="history-item-header">
                <div className="history-item-info">
                  <span className="history-item-date">{formatDate(entry.created_at)}</span>
                  <span className="history-item-voice">
                    {getVoiceTypeLabel(entry.voice_type)}
                    {entry.voice_name && `: ${entry.voice_name}`}
                  </span>
                </div>
                <button
                  className="btn-delete-entry"
                  onClick={(e) => handleDelete(entry.id, e)}
                  title="Smazat záznam"
                >
                  🗑️
                </button>
              </div>

              <div className="history-item-text">
                "{formatText(entry.text)}"
              </div>

              {entry.tts_params && Object.keys(entry.tts_params).length > 0 && (
                <div className="history-item-params">
                  {entry.tts_params.speed && entry.tts_params.speed !== 1.0 && (
                    <span className="param-badge">Speed: {entry.tts_params.speed.toFixed(2)}</span>
                  )}
                  {entry.tts_params.temperature && entry.tts_params.temperature !== 0.7 && (
                    <span className="param-badge">Temp: {entry.tts_params.temperature.toFixed(2)}</span>
                  )}
                </div>
              )}

              {selectedEntry?.id === entry.id && (
                <div className="history-item-audio">
                  <AudioPlayer audioUrl={`${API_BASE_URL}${entry.audio_url}`} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default History

