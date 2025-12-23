import React, { useState, useEffect } from 'react'
import {
  getHistory, deleteHistoryEntry, clearHistory,
  getMusicHistory, deleteMusicHistoryEntry, clearMusicHistory,
  getBarkHistory, deleteBarkHistoryEntry, clearBarkHistory
} from '../services/api'
import AudioPlayer from './AudioPlayer'
import './History.css'

const API_BASE_URL = 'http://localhost:8000'

const HISTORY_TYPES = {
  tts: { label: 'mluvené slovo', icon: '🎤' },
  music: { label: 'hudba', icon: '🎵' },
  bark: { label: 'FX & English', icon: '🔊' }
}

function History({ onRestoreText, onRestorePrompt, onSwitchTab }) {
  const [historyType, setHistoryType] = useState('tts') // 'tts' | 'music' | 'bark'
  const [history, setHistory] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedEntry, setSelectedEntry] = useState(null)

  useEffect(() => {
    loadHistory()
  }, [historyType])

  const loadHistory = async () => {
    try {
      setLoading(true)
      setError(null)
      let data

      if (historyType === 'tts') {
        data = await getHistory(100, 0)
      } else if (historyType === 'music') {
        data = await getMusicHistory(100, 0)
      } else if (historyType === 'bark') {
        data = await getBarkHistory(100, 0)
      }

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
      if (historyType === 'tts') {
        await deleteHistoryEntry(entryId)
      } else if (historyType === 'music') {
        await deleteMusicHistoryEntry(entryId)
      } else if (historyType === 'bark') {
        await deleteBarkHistoryEntry(entryId)
      }
      setHistory(history.filter(entry => entry.id !== entryId))
    } catch (err) {
      setError(err.message || 'Chyba při mazání záznamu')
    }
  }

  const handleClearAll = async () => {
    const typeLabel = HISTORY_TYPES[historyType].label
    if (!window.confirm(`Opravdu chcete vymazat celou historii (${typeLabel})? Tato akce je nevratná.`)) {
      return
    }

    try {
      if (historyType === 'tts') {
        await clearHistory()
      } else if (historyType === 'music') {
        await clearMusicHistory()
      } else if (historyType === 'bark') {
        await clearBarkHistory()
      }
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
    if (!text) return ''
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

  const handleRestore = (entry) => {
    if (historyType === 'tts' && entry.text && onRestoreText) {
      onRestoreText(entry.text)
      if (onSwitchTab) onSwitchTab('generate')
    } else if (historyType === 'music' && entry.prompt && onRestorePrompt) {
      onRestorePrompt(entry.prompt)
      if (onSwitchTab) onSwitchTab('musicgen')
    } else if (historyType === 'bark' && entry.prompt && onRestorePrompt) {
      onRestorePrompt(entry.prompt)
      if (onSwitchTab) onSwitchTab('bark')
    }
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
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
          <h2>📜 Historie</h2>
          <div className="history-filter-buttons">
            {Object.entries(HISTORY_TYPES).map(([key, { label, icon }]) => (
              <button
                key={key}
                className={`history-filter-btn ${historyType === key ? 'active' : ''}`}
                onClick={() => setHistoryType(key)}
              >
                {icon} {label}
              </button>
            ))}
          </div>
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
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
                    {historyType === 'tts' && (
                      <>
                        {getVoiceTypeLabel(entry.voice_type)}
                        {entry.voice_name && `: ${entry.voice_name}`}
                      </>
                    )}
                    {historyType === 'music' && 'MusicGen'}
                    {historyType === 'bark' && 'Bark'}
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

              <div className="history-item-audio-preview">
                <AudioPlayer audioUrl={`${API_BASE_URL}${entry.audio_url}`} />
              </div>

              <div className="history-item-text">
                "{formatText(historyType === 'tts' ? entry.text : entry.prompt, 80)}"
              </div>

              {historyType === 'tts' && entry.tts_params && Object.keys(entry.tts_params).length > 0 && (
                <div className="history-item-params">
                  {entry.tts_params.speed && entry.tts_params.speed !== 1.0 && (
                    <span className="param-badge">Speed: {entry.tts_params.speed.toFixed(2)}</span>
                  )}
                  {entry.tts_params.temperature && entry.tts_params.temperature !== 0.7 && (
                    <span className="param-badge">Temp: {entry.tts_params.temperature.toFixed(2)}</span>
                  )}
                </div>
              )}

              {historyType === 'music' && entry.music_params && Object.keys(entry.music_params).length > 0 && (
                <div className="history-item-params">
                  {entry.music_params.model && (
                    <span className="param-badge">Model: {entry.music_params.model}</span>
                  )}
                  {entry.music_params.duration && (
                    <span className="param-badge">Dur: {entry.music_params.duration}s</span>
                  )}
                  {entry.music_params.temperature !== undefined && entry.music_params.temperature !== null && (
                    <span className="param-badge">Temp: {Number(entry.music_params.temperature).toFixed(2)}</span>
                  )}
                </div>
              )}

              {historyType === 'bark' && entry.bark_params && Object.keys(entry.bark_params).length > 0 && (
                <div className="history-item-params">
                  {entry.bark_params.seed !== undefined && entry.bark_params.seed !== null && (
                    <span className="param-badge">Seed: {entry.bark_params.seed}</span>
                  )}
                  {entry.bark_params.duration && (
                    <span className="param-badge">Dur: {entry.bark_params.duration}s</span>
                  )}
                  {entry.bark_params.temperature !== undefined && entry.bark_params.temperature !== null && (
                    <span className="param-badge">Temp: {Number(entry.bark_params.temperature).toFixed(2)}</span>
                  )}
                </div>
              )}

              {selectedEntry?.id === entry.id && (
                <div className="history-item-details" onClick={(e) => e.stopPropagation()}>
                  <div className="history-item-actions">
                    {historyType === 'music' && entry.music_params?.ambience_files?.length > 0 && (
                      <div className="result-hint" style={{ marginBottom: '10px' }}>
                        Mixované zvuky: {entry.music_params.ambience_files.join(', ')}
                      </div>
                    )}
                    <button
                      className="btn-restore-text"
                      onClick={() => handleRestore(entry)}
                    >
                      ✍️ {historyType === 'tts' ? 'Použít tento text' : 'Použít tento prompt'}
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

export default History

