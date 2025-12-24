import React, { useEffect, useState } from 'react'
import { getSfxHistory, deleteSfxHistoryEntry, clearSfxHistory } from '../services/api'
import { deleteWaveformCache, clearWaveformCache } from '../utils/waveformCache'
import AudioPlayer from './AudioPlayer'
import './History.css'

// Použij 127.0.0.1 místo localhost kvůli IPv6 (::1) na Windows/Chrome
const API_BASE_URL = 'http://127.0.0.1:8000'

function SfxHistory({ onRestorePrompt }) {
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
      const data = await getSfxHistory(100, 0)
      setHistory(data.history || [])
      setStats(data.stats || null)
    } catch (err) {
      setError(err.message || 'Chyba při načítání SFX historie')
      console.error('SFX history load error:', err)
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
      // Najít entry před smazáním pro vyčištění cache
      const entryToDelete = history.find(entry => entry.id === entryId)

      await deleteSfxHistoryEntry(entryId)

      // Vyčistit cache pro smazané audio
      if (entryToDelete?.audio_url) {
        deleteWaveformCache(entryToDelete.audio_url)
      }

      setHistory(history.filter(entry => entry.id !== entryId))
    } catch (err) {
      setError(err.message || 'Chyba při mazání záznamu')
    }
  }

  const handleClearAll = async () => {
    if (!window.confirm('Opravdu chcete vymazat celou SFX historii? Tato akce je nevratná.')) {
      return
    }

    try {
      await clearSfxHistory()

      // Vyčistit celou waveform cache
      clearWaveformCache()

      setHistory([])
      setStats(null)
    } catch (err) {
      setError(err.message || 'Chyba při mazání SFX historie')
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

  const formatText = (text, maxLength = 120) => {
    if (!text) return ''
    if (text.length <= maxLength) return text
    return text.substring(0, maxLength) + '...'
  }

  if (loading) {
    return (
      <div className="history-container">
        <div className="history-loading">⏳ Načítání SFX historie...</div>
      </div>
    )
  }

  return (
    <div className="history-container">
      <div className="history-header">
        <h2>🔊 Historie SFX (AudioGen)</h2>
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
          <p className="history-empty-hint">Zde se zobrazí všechny vygenerované SFX efekty</p>
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
                  <span className="history-item-voice">SFX (AudioGen)</span>
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
                "{formatText(entry.prompt)}"
              </div>

              {entry.sfx_params && Object.keys(entry.sfx_params).length > 0 && (
                <div className="history-item-params">
                  {entry.sfx_params.model && (
                    <span className="param-badge">Model: {entry.sfx_params.model}</span>
                  )}
                  {entry.sfx_params.duration && (
                    <span className="param-badge">Dur: {entry.sfx_params.duration}s</span>
                  )}
                  {entry.sfx_params.temperature !== undefined && entry.sfx_params.temperature !== null && (
                    <span className="param-badge">Temp: {Number(entry.sfx_params.temperature).toFixed(2)}</span>
                  )}
                </div>
              )}

              {selectedEntry?.id === entry.id && (
                <div className="history-item-details">
                  <div className="history-item-audio">
                    <AudioPlayer audioUrl={`${API_BASE_URL}${entry.audio_url}`} />
                  </div>
                  <div className="history-item-actions">
                    <button
                      className="btn-restore-text"
                      onClick={() => onRestorePrompt && onRestorePrompt(entry.prompt)}
                    >
                      ✍️ Použít tento prompt
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default SfxHistory

