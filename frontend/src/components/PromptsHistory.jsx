import React, { useState, useEffect } from 'react'
import {
  getXTTSPromptsHistory,
  getF5TTSPromptsHistory,
  getF5TTSSKPromptsHistory,
  deleteXTTSPromptEntry,
  deleteF5TTSPromptEntry,
  deleteF5TTSSKPromptEntry
} from '../services/api'
import Icon from './ui/Icons'
import './PromptsHistory.css'

function PromptsHistory({ modelType, onSelectPrompt }) {
  // modelType: 'xtts' | 'f5tts' | 'f5tts-sk'
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    if (expanded) {
      loadHistory()
    }
  }, [expanded, modelType])

  const loadHistory = async () => {
    try {
      setLoading(true)
      setError(null)
      let data

      if (modelType === 'xtts') {
        data = await getXTTSPromptsHistory(null, 0)
      } else if (modelType === 'f5tts') {
        data = await getF5TTSPromptsHistory(null, 0)
      } else if (modelType === 'f5tts-sk') {
        data = await getF5TTSSKPromptsHistory(null, 0)
      } else {
        return
      }

      setHistory(data.history || [])
    } catch (err) {
      setError(err.message || 'Chyba při načítání historie promptů')
      console.error('PromptsHistory load error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (entryId, e) => {
    e.stopPropagation()
    if (!window.confirm('Opravdu chcete smazat tento prompt z historie?')) {
      return
    }

    try {
      if (modelType === 'xtts') {
        await deleteXTTSPromptEntry(entryId)
      } else if (modelType === 'f5tts') {
        await deleteF5TTSPromptEntry(entryId)
      } else if (modelType === 'f5tts-sk') {
        await deleteF5TTSSKPromptEntry(entryId)
      }

      // Obnovit historii
      await loadHistory()
    } catch (err) {
      alert('Chyba při mazání: ' + (err.message || 'Neznámá chyba'))
    }
  }

  const handleSelect = (prompt) => {
    if (onSelectPrompt) {
      onSelectPrompt(prompt)
    }
    setExpanded(false)
  }

  const formatDate = (dateString) => {
    if (!dateString) return ''
    try {
      const date = new Date(dateString)
      return date.toLocaleString('cs-CZ', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch {
      return dateString
    }
  }

  const formatText = (text, maxLength = 80) => {
    if (!text) return ''
    if (text.length <= maxLength) return text
    return text.substring(0, maxLength) + '...'
  }

  const getModelLabel = () => {
    switch (modelType) {
      case 'xtts': return 'XTTS'
      case 'f5tts': return 'F5-TTS'
      case 'f5tts-sk': return 'F5-TTS-SK'
      default: return 'TTS'
    }
  }

  if (!expanded) {
    return (
      <div className="prompts-history-collapsed">
        <button
          className="btn-prompts-history-toggle"
          onClick={() => setExpanded(true)}
          title={`Zobrazit historii promptů (${getModelLabel()})`}
        >
          <Icon name="scroll" size={16} />
          <span>Historie promptů</span>
        </button>
      </div>
    )
  }

  return (
    <div className="prompts-history-expanded">
      <div className="prompts-history-header">
        <h4>Historie promptů ({getModelLabel()})</h4>
        <button
          className="btn-close-prompts-history"
          onClick={() => setExpanded(false)}
          title="Zavřít"
        >
          <Icon name="x" size={16} />
        </button>
      </div>

      {loading && (
        <div className="prompts-history-loading">
          ⏳ Načítání historie...
        </div>
      )}

      {error && (
        <div className="prompts-history-error">
          ⚠️ {error}
        </div>
      )}

      {!loading && !error && (
        <div className="prompts-history-list">
          {history.length === 0 ? (
            <div className="prompts-history-empty">
              Žádné uložené prompty
            </div>
          ) : (
            history.map((entry) => (
              <div
                key={entry.id}
                className="prompts-history-item"
                onClick={() => handleSelect(entry.prompt)}
              >
                <div className="prompts-history-item-header">
                  <span className="prompts-history-date">
                    {formatDate(entry.created_at)}
                  </span>
                  <button
                    className="btn-delete-prompt"
                    onClick={(e) => handleDelete(entry.id, e)}
                    title="Smazat prompt"
                  >
                    <Icon name="trash" size={14} />
                  </button>
                </div>
                <div className="prompts-history-preview">
                  "{formatText(entry.prompt, 100)}"
                </div>
                {entry.tts_params && Object.keys(entry.tts_params).length > 0 && (
                  <div className="prompts-history-params">
                    {entry.tts_params.speed && entry.tts_params.speed !== 1.0 && (
                      <span className="param-badge">Speed: {entry.tts_params.speed.toFixed(2)}</span>
                    )}
                    {entry.tts_params.temperature && entry.tts_params.temperature !== 0.7 && (
                      <span className="param-badge">Temp: {entry.tts_params.temperature.toFixed(2)}</span>
                    )}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}

export default PromptsHistory

