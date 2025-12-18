import React, { useState, useRef, useEffect } from 'react'
import './TextInput.css'

function TextInput({ value, onChange, maxLength = 5000, versions = [], onSaveVersion, onDeleteVersion }) {
  const [showHistory, setShowHistory] = useState(false)
  const dropdownRef = useRef(null)
  const remaining = maxLength - value.length

  // Zavřít dropdown při kliknutí mimo
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowHistory(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const formatDate = (isoString) => {
    const date = new Date(isoString)
    return date.toLocaleString('cs-CZ', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const truncateText = (text, len = 60) => {
    if (text.length <= len) return text
    return text.substring(0, len) + '...'
  }

  return (
    <div className="text-input-section">
      <div className="text-input-header">
        <h2>Text k syntéze</h2>
        <div className="text-actions">
          <button
            className="btn-text-action"
            onClick={onSaveVersion}
            title="Uložit aktuální verzi"
            disabled={!value.trim()}
          >
            💾 Uložit verzi
          </button>
          <div className="history-dropdown-container" ref={dropdownRef}>
            <button
              className={`btn-text-action ${showHistory ? 'active' : ''}`}
              onClick={() => setShowHistory(!showHistory)}
              title="Historie verzí textu"
            >
              📜 Historie {versions.length > 0 && <span className="version-count">{versions.length}</span>}
            </button>

            {showHistory && (
              <div className="history-dropdown">
                <div className="history-dropdown-header">
                  <span>Předchozí verze</span>
                  <button className="btn-close-dropdown" onClick={() => setShowHistory(false)}>✕</button>
                </div>
                <div className="history-dropdown-list">
                  {versions.length === 0 ? (
                    <div className="history-dropdown-empty">Žádné uložené verze</div>
                  ) : (
                    versions.map((v) => (
                      <div key={v.id} className="history-dropdown-item" onClick={() => {
                        onChange(v.text)
                        setShowHistory(false)
                      }}>
                        <div className="version-info">
                          <span className="version-date">{formatDate(v.timestamp)}</span>
                          <button
                            className="btn-delete-version"
                            onClick={(e) => {
                              e.stopPropagation()
                              onDeleteVersion(v.id)
                            }}
                            title="Smazat verzi"
                          >
                            🗑️
                          </button>
                        </div>
                        <div className="version-preview">{truncateText(v.text)}</div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
      <div className="text-input-wrapper">
        <textarea
          className="text-input"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Zadejte český text k syntéze řeči..."
          maxLength={maxLength}
          rows={6}
        />
        <div className="char-counter">
          <span className={remaining < 50 ? 'warning' : ''}>
            {value.length}/{maxLength}
          </span>
        </div>
      </div>
    </div>
  )
}

export default TextInput




