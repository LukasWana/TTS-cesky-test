import React, { useState } from 'react'
import './TTSSettings.css'

function TTSSettings({ settings, onChange, onReset }) {
  const [isExpanded, setIsExpanded] = useState(false)

  const handleChange = (key, value) => {
    const numValue = parseFloat(value)
    if (!isNaN(numValue)) {
      onChange({ ...settings, [key]: numValue })
    }
  }

  return (
    <div className="tts-settings">
      <div className="tts-settings-header" onClick={() => setIsExpanded(!isExpanded)}>
        <h3>⚙️ Nastavení hlasu</h3>
        <span className="toggle-icon">{isExpanded ? '▼' : '▶'}</span>
      </div>

      {isExpanded && (
        <div className="tts-settings-content">
          <div className="settings-grid">
            {/* Rychlost řeči */}
            <div className="setting-item">
              <label htmlFor="speed">
                Rychlost řeči (Speed)
                <span className="setting-value">{settings.speed.toFixed(2)}</span>
              </label>
              <input
                type="range"
                id="speed"
                min="0.5"
                max="2.0"
                step="0.1"
                value={settings.speed}
                onChange={(e) => handleChange('speed', e.target.value)}
              />
              <div className="setting-range">
                <span>0.5x</span>
                <span>1.0x</span>
                <span>2.0x</span>
              </div>
            </div>

            {/* Teplota */}
            <div className="setting-item">
              <label htmlFor="temperature">
                Teplota (Temperature)
                <span className="setting-value">{settings.temperature.toFixed(2)}</span>
              </label>
              <input
                type="range"
                id="temperature"
                min="0.0"
                max="1.0"
                step="0.05"
                value={settings.temperature}
                onChange={(e) => handleChange('temperature', e.target.value)}
              />
              <div className="setting-range">
                <span>Konzistentní (0.0)</span>
                <span>Variabilní (1.0)</span>
              </div>
            </div>

            {/* Length Penalty */}
            <div className="setting-item">
              <label htmlFor="lengthPenalty">
                Length Penalty
                <span className="setting-value">{settings.lengthPenalty.toFixed(2)}</span>
              </label>
              <input
                type="range"
                id="lengthPenalty"
                min="0.5"
                max="2.0"
                step="0.1"
                value={settings.lengthPenalty}
                onChange={(e) => handleChange('lengthPenalty', e.target.value)}
              />
              <div className="setting-range">
                <span>Krátké (0.5)</span>
                <span>Dlouhé (2.0)</span>
              </div>
            </div>

            {/* Repetition Penalty */}
            <div className="setting-item">
              <label htmlFor="repetitionPenalty">
                Repetition Penalty
                <span className="setting-value">{settings.repetitionPenalty.toFixed(2)}</span>
              </label>
              <input
                type="range"
                id="repetitionPenalty"
                min="1.0"
                max="5.0"
                step="0.1"
                value={settings.repetitionPenalty}
                onChange={(e) => handleChange('repetitionPenalty', e.target.value)}
              />
              <div className="setting-range">
                <span>Méně opakování (1.0)</span>
                <span>Více opakování (5.0)</span>
              </div>
            </div>

            {/* Top-K */}
            <div className="setting-item">
              <label htmlFor="topK">
                Top-K Sampling
                <span className="setting-value">{settings.topK}</span>
              </label>
              <input
                type="range"
                id="topK"
                min="1"
                max="100"
                step="1"
                value={settings.topK}
                onChange={(e) => handleChange('topK', parseInt(e.target.value))}
              />
              <div className="setting-range">
                <span>1</span>
                <span>50</span>
                <span>100</span>
              </div>
            </div>

            {/* Top-P */}
            <div className="setting-item">
              <label htmlFor="topP">
                Top-P Sampling
                <span className="setting-value">{settings.topP.toFixed(2)}</span>
              </label>
              <input
                type="range"
                id="topP"
                min="0.0"
                max="1.0"
                step="0.05"
                value={settings.topP}
                onChange={(e) => handleChange('topP', e.target.value)}
              />
              <div className="setting-range">
                <span>0.0</span>
                <span>0.85</span>
                <span>1.0</span>
              </div>
            </div>
          </div>

          <div className="settings-actions">
            <button className="btn-reset" onClick={onReset}>
              🔄 Obnovit výchozí hodnoty
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default TTSSettings

