import React, { useState, useRef, useEffect } from 'react'
import './TextInput.css'

function TextInput({
  value = '',
  onChange,
  maxLength,
  versions = [],
  onSaveVersion,
  onDeleteVersion,
  placeholder = 'Zadej text...'
}) {
  const [showHistory, setShowHistory] = useState(false)
  const historyRef = useRef(null)
  const dropdownRef = useRef(null)

  // Zavřít dropdown při kliknutí mimo
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target) &&
        historyRef.current &&
        !historyRef.current.contains(event.target)
      ) {
        setShowHistory(false)
      }
    }

    if (showHistory) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showHistory])

  const handleChange = (e) => {
    const newValue = e.target.value
    if (!maxLength || newValue.length <= maxLength) {
      onChange(newValue)
    }
  }

  const handleVersionClick = (versionText) => {
    onChange(versionText)
    setShowHistory(false)
  }

  const handleDeleteVersion = (e, index) => {
    e.stopPropagation()
    if (onDeleteVersion) {
      onDeleteVersion(index)
    }
  }

  const currentLength = value ? value.length : 0
  const isNearLimit = maxLength && currentLength > maxLength * 0.9

  return (
    <div className="text-input-section">
      {(versions && versions.length > 0) || onSaveVersion ? (
        <div className="text-input-header">
          <div className="text-actions">
            {onSaveVersion && (
              <button
                className="btn-text-action"
                onClick={onSaveVersion}
                disabled={!value || !value.trim()}
              >
                💾 Uložit verzi
              </button>
            )}
            {versions && versions.length > 0 && (
              <div className="history-dropdown-container" ref={historyRef}>
                <button
                  className={`btn-text-action ${showHistory ? 'active' : ''}`}
                  onClick={() => setShowHistory(!showHistory)}
                >
                  📜 Historie
                  {versions.length > 0 && (
                    <span className="version-count">{versions.length}</span>
                  )}
                </button>
                {showHistory && (
                  <div className="history-dropdown" ref={dropdownRef}>
                    <div className="history-dropdown-header">
                      <span>Uložené verze ({versions.length})</span>
                      <button
                        className="btn-close-dropdown"
                        onClick={() => setShowHistory(false)}
                      >
                        ✕
                      </button>
                    </div>
                    <div className="history-dropdown-list">
                      {versions.length === 0 ? (
                        <div className="history-dropdown-empty">
                          Žádné uložené verze
                        </div>
                      ) : (
                        versions.map((version, index) => (
                          <div
                            key={index}
                            className="history-dropdown-item"
                            onClick={() => handleVersionClick(version.text || version)}
                          >
                            <div className="version-info">
                              <span className="version-date">
                                {version.date
                                  ? new Date(version.date).toLocaleString('cs-CZ', {
                                      day: '2-digit',
                                      month: '2-digit',
                                      year: 'numeric',
                                      hour: '2-digit',
                                      minute: '2-digit'
                                    })
                                  : `Verze ${index + 1}`
                                }
                              </span>
                              {onDeleteVersion && (
                                <button
                                  className="btn-delete-version"
                                  onClick={(e) => handleDeleteVersion(e, index)}
                                  title="Smazat verzi"
                                >
                                  🗑️
                                </button>
                              )}
                            </div>
                            <div className="version-preview">
                              {typeof version === 'string' ? version : (version.text || '')}
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      ) : null}

      <div className="text-input-wrapper">
        <textarea
          className="text-input"
          value={value}
          onChange={handleChange}
          placeholder={placeholder}
          rows={6}
        />
        {maxLength && (
          <div className={`char-counter ${isNearLimit ? 'warning' : ''}`}>
            {currentLength} / {maxLength}
          </div>
        )}
      </div>
    </div>
  )
}

export default TextInput
