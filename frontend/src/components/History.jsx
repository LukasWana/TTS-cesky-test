import React, { useState, useEffect } from 'react'
import { useSectionColor } from '../contexts/SectionColorContext'
import {
  getHistory, deleteHistoryEntry, clearHistory,
  getMusicHistory, deleteMusicHistoryEntry, clearMusicHistory,
  getBarkHistory, deleteBarkHistoryEntry, clearBarkHistory
} from '../services/api'
import { deleteWaveformCache, clearWaveformCache } from '../utils/waveformCache'
import AudioPlayer from './AudioPlayer'
import Icon from './ui/Icons'
import { getCategoryColor, getCategoryFromHistoryEntry } from '../utils/layerColors'
import './History.css'

// Použij 127.0.0.1 místo localhost kvůli IPv6 (::1) na Windows/Chrome
const API_BASE_URL = 'http://127.0.0.1:8000'

const HISTORY_TYPES = {
  tts: { label: 'mluvené slovo', icon: 'microphone' },
  music: { label: 'hudba', icon: 'music' },
  bark: { label: 'FX & English', icon: 'speaker' }
}

function History({ onRestoreText, onRestorePrompt, onSwitchTab }) {
  const { color, rgb } = useSectionColor()
  const style = {
    '--section-color': color,
    '--section-color-rgb': rgb
  }

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

      // Načíst všechny záznamy (limit = null)
      if (historyType === 'tts') {
        data = await getHistory(null, 0)
        // Přidat source pro rozlišení mezi tts a f5tts
        const entries = (data.history || []).map(entry => {
          const engine = entry.tts_params?.engine || ''
          const isSlovak = engine === 'f5-tts-slovak'
          return {
            ...entry,
            source: isSlovak ? 'f5tts' : 'tts'
          }
        })
        data = { ...data, history: entries }
      } else if (historyType === 'music') {
        data = await getMusicHistory(null, 0)
        // Přidat source pro hudbu
        const entries = (data.history || []).map(entry => ({
          ...entry,
          source: 'music'
        }))
        data = { ...data, history: entries }
      } else if (historyType === 'bark') {
        data = await getBarkHistory(null, 0)
        // Přidat source pro Bark
        const entries = (data.history || []).map(entry => ({
          ...entry,
          source: 'bark'
        }))
        data = { ...data, history: entries }
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
      // Najít entry před smazáním pro vyčištění cache
      const entryToDelete = history.find(entry => entry.id === entryId)

      if (historyType === 'tts') {
        await deleteHistoryEntry(entryId)
      } else if (historyType === 'music') {
        await deleteMusicHistoryEntry(entryId)
      } else if (historyType === 'bark') {
        await deleteBarkHistoryEntry(entryId)
      }

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

      // Vyčistit celou waveform cache (jednodušší než iterovat přes všechny položky)
      clearWaveformCache()

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

  // Pomocná funkce pro převod hex barvy na RGB string
  const hexToRgb = (hex) => {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
    return result
      ? `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}`
      : '158, 158, 158' // výchozí šedá
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
      <div className="history-container" style={style}>
        <div className="history-loading">⏳ Načítání historie...</div>
      </div>
    )
  }

  return (
    <div className="history-container" style={style}>
      <div className="history-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
          <h2>Historie</h2>
          <div className="history-filter-buttons">
            {Object.entries(HISTORY_TYPES).map(([key, { label, icon }]) => {
              // Mapování history type na kategorii
              const categoryMap = {
                'tts': 'tts',
                'music': 'music',
                'bark': 'bark'
              }
              const category = categoryMap[key] || 'file'
              const categoryColor = getCategoryColor(category, 0)
              const rgb = hexToRgb(categoryColor)
              const isActive = historyType === key

              return (
              <button
                key={key}
                className={`history-filter-btn ${isActive ? 'active' : ''}`}
                onClick={() => setHistoryType(key)}
                style={isActive ? {
                  background: `rgba(${rgb}, 0.2)`,
                  borderColor: `rgba(${rgb}, 0.4)`,
                  color: categoryColor
                } : {}}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.background = `rgba(${rgb}, 0.08)`
                    e.currentTarget.style.borderColor = `rgba(${rgb}, 0.2)`
                    e.currentTarget.style.color = categoryColor
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'
                    e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)'
                    e.currentTarget.style.color = 'rgba(255, 255, 255, 0.7)'
                  }
                }}
              >
                <Icon name={icon} size={16} style={{ display: 'inline-block', marginRight: '6px', verticalAlign: 'middle' }} />
                {label}
              </button>
              )
            })}
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
              <Icon name="trash" size={16} style={{ display: 'inline-block', marginRight: '6px', verticalAlign: 'middle' }} />
              Vymazat vše
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="history-error">
          <Icon name="warning" size={16} style={{ display: 'inline-block', marginRight: '6px', verticalAlign: 'middle' }} />
          {error}
        </div>
      )}

      {history.length === 0 ? (
        <div className="history-empty">
          <p><Icon name="inbox" size={16} style={{ display: 'inline-block', marginRight: '6px', verticalAlign: 'middle' }} /> Historie je prázdná</p>
          <p className="history-empty-hint">Zde se zobrazí všechny generované audio soubory</p>
        </div>
      ) : (
        <div className="history-list">
          {history.map((entry) => {
            // Získat kategorii a barvu pro tento záznam
            const category = getCategoryFromHistoryEntry(entry)
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
                  <Icon name="trash" size={16} />
                </button>
              </div>

              <div className="history-item-audio-preview">
                <AudioPlayer audioUrl={`${API_BASE_URL}${entry.audio_url}`} variant="compact" />
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
            )
          })}
        </div>
      )}
    </div>
  )
}

export default History

