import React, { useEffect, useState } from 'react'
import { getBarkHistory, deleteBarkHistoryEntry, clearBarkHistory } from '../services/api'
import { deleteWaveformCache, clearWaveformCache } from '../utils/waveformCache'
import AudioPlayer from './AudioPlayer'
import { getCategoryColor } from '../utils/layerColors'
import './History.css'

// Použij 127.0.0.1 místo localhost kvůli IPv6 (::1) na Windows/Chrome
const API_BASE_URL = 'http://127.0.0.1:8000'

function BarkHistory({ onRestorePrompt }) {
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
      const data = await getBarkHistory(null, 0)
      // Přidat source pro Bark
      const entries = (data.history || []).map(entry => ({
        ...entry,
        source: 'bark'
      }))
      setHistory(entries)
      setStats(data.stats || null)
    } catch (err) {
      setError(err.message || 'Chyba při načítání historie Bark')
      console.error('Bark history load error:', err)
    } finally {
      setLoading(false)
    }
  }

  // Pomocná funkce pro převod hex barvy na RGB string
  const hexToRgb = (hex) => {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
    return result
      ? `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}`
      : '158, 158, 158' // výchozí šedá
  }

  const handleDelete = async (entryId, e) => {
    e.stopPropagation()
    if (!window.confirm('Opravdu chcete smazat tento záznam?')) {
      return
    }

    try {
      // Najít entry před smazáním pro vyčištění cache
      const entryToDelete = history.find(entry => entry.id === entryId)

      await deleteBarkHistoryEntry(entryId)

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
    if (!window.confirm('Opravdu chcete vymazat celou historii Bark? Tato akce je nevratná.')) {
      return
    }

    try {
      await clearBarkHistory()

      // Vyčistit celou waveform cache
      clearWaveformCache()

      setHistory([])
      setStats(null)
    } catch (err) {
      setError(err.message || 'Chyba při mazání historie Bark')
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
        <div className="history-loading">⏳ Načítání historie Bark...</div>
      </div>
    )
  }

  return (
    <div className="history-container">
      <div className="history-header">
        <h2>🔊 Historie FX & English</h2>
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
          <p className="history-empty-hint">Zde se zobrazí všechny vygenerované Bark audio soubory</p>
        </div>
      ) : (
        <div className="history-list">
          {history.map((entry) => {
            // Získat kategorii a barvu pro tento záznam
            const category = entry.source || 'bark'
            const categoryColor = getCategoryColor(category, 0)
            const rgb = hexToRgb(categoryColor)
            const isSelected = selectedEntry?.id === entry.id

            return (
            <div
              key={entry.id}
              className={`history-item ${isSelected ? 'selected' : ''}`}
              onClick={() => setSelectedEntry(isSelected ? null : entry)}
              style={{
                borderLeft: `3px solid ${categoryColor}`,
                borderColor: isSelected
                  ? `rgba(${rgb}, 0.4)`
                  : `rgba(${rgb}, 0.2)`,
                backgroundColor: isSelected
                  ? `rgba(${rgb}, 0.08)`
                  : `rgba(${rgb}, 0.03)`,
                boxShadow: isSelected
                  ? `0 10px 40px rgba(${rgb}, 0.15)`
                  : 'none'
              }}
              onMouseEnter={(e) => {
                if (!isSelected) {
                  e.currentTarget.style.borderColor = `rgba(${rgb}, 0.3)`
                  e.currentTarget.style.backgroundColor = `rgba(${rgb}, 0.05)`
                  e.currentTarget.style.boxShadow = `0 10px 30px rgba(${rgb}, 0.2)`
                }
              }}
              onMouseLeave={(e) => {
                if (!isSelected) {
                  e.currentTarget.style.borderColor = `rgba(${rgb}, 0.2)`
                  e.currentTarget.style.backgroundColor = `rgba(${rgb}, 0.03)`
                  e.currentTarget.style.boxShadow = 'none'
                }
              }}
            >
              <div className="history-item-header">
                <div className="history-item-info">
                  <span className="history-item-date">{formatDate(entry.created_at)}</span>
                  <span className="history-item-voice">Bark</span>
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

              {entry.bark_params && Object.keys(entry.bark_params).length > 0 && (
                <div className="history-item-params">
                  {entry.bark_params.model_size && (
                    <span className="param-badge">Model: {entry.bark_params.model_size}</span>
                  )}
                  {entry.bark_params.duration && (
                    <span className="param-badge">Dur: {entry.bark_params.duration}s</span>
                  )}
                  {entry.bark_params.temperature !== undefined && entry.bark_params.temperature !== null && (
                    <span className="param-badge">Temp: {Number(entry.bark_params.temperature).toFixed(2)}</span>
                  )}
                  {entry.bark_params.seed !== undefined && entry.bark_params.seed !== null && (
                    <span className="param-badge">Seed: {entry.bark_params.seed}</span>
                  )}
                </div>
              )}

              {selectedEntry?.id === entry.id && (
                <div className="history-item-details" onClick={(e) => e.stopPropagation()}>
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
            )
          })}
        </div>
      )}
    </div>
  )
}

export default BarkHistory

