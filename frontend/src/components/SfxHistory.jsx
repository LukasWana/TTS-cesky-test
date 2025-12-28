import React, { useEffect, useState } from 'react'
import { getSfxHistory, deleteSfxHistoryEntry, clearSfxHistory } from '../services/api'
import { deleteWaveformCache, clearWaveformCache } from '../utils/waveformCache'
import AudioPlayer from './AudioPlayer'
import { getCategoryColor } from '../utils/layerColors'
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
      // Přidat source pro SFX (použijeme 'file' jako kategorii)
      const entries = (data.history || []).map(entry => ({
        ...entry,
        source: 'file'
      }))
      setHistory(entries)
      setStats(data.stats || null)
    } catch (err) {
      setError(err.message || 'Chyba při načítání SFX historie')
      console.error('SFX history load error:', err)
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
          {history.map((entry) => {
            // Získat kategorii a barvu pro tento záznam
            const category = entry.source || 'file'
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
            )
          })}
        </div>
      )}
    </div>
  )
}

export default SfxHistory

