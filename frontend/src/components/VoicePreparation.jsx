import React, { useState } from 'react'
import AudioRecorder from './AudioRecorder'
import YouTubeImporter from './YouTubeImporter'
import Chips from './ui/Chips'
import './VoicePreparation.css'

function VoicePreparation({
  onVoiceUpload,
  onVoiceRecord,
  onYouTubeImport,
  uploadedVoiceFileName,
  voiceQuality,
  language = 'cs'
}) {
  const [removeBackground, setRemoveBackground] = useState(false)

  const handleFileChange = (e) => {
    const file = e.target.files[0]
    if (file) {
      // Předat soubor i hodnotu remove_background
      onVoiceUpload(file, removeBackground)
    }
  }

  const handleRecordComplete = (result) => {
    onVoiceRecord(result)
  }

  return (
    <div className="voice-preparation">
      <h2>Příprava hlasů</h2>
      <p className="preparation-description">
        Nahrajte nový hlas pro použití v generování řeči. Můžete nahrát soubor, nahrát z mikrofonu nebo stáhnout z YouTube.
      </p>

      <div className="preparation-sections">
        {/* Sekce: Nahrát soubor */}
        <div className="preparation-section">
          <h3>📁 Nahrát soubor</h3>
          <div className="upload-section">
            <label className="upload-button">
              <input
                type="file"
                accept="audio/*"
                onChange={handleFileChange}
                style={{ display: 'none' }}
              />
              📁 Vybrat audio soubor
            </label>
            {uploadedVoiceFileName && (
              <p className="upload-status">✓ {uploadedVoiceFileName}</p>
            )}
            <div className="form-group" style={{ marginTop: '10px' }}>
              <label>
                <input
                  type="checkbox"
                  checked={removeBackground}
                  onChange={(e) => setRemoveBackground(e.target.checked)}
                />
                Odstranit zvuky a hudbu v pozadí (ponechat jen hlas)
              </label>
              <small style={{ display: 'block', marginTop: '5px', color: '#666' }}>
                Použije AI pro separaci hlasu od pozadí. Může trvat déle.
              </small>
            </div>
            <p className="upload-hint">
              Minimálně 6 sekund čistého audio (WAV, MP3)
            </p>
          </div>
        </div>

        {/* Sekce: Nahrát z mikrofonu */}
        <div className="preparation-section">
          <h3>🎤 Nahrát z mikrofonu</h3>
          <div className="record-section">
            <AudioRecorder onRecordComplete={handleRecordComplete} language={language} />
            {uploadedVoiceFileName && (
              <p className="record-status">✓ {uploadedVoiceFileName}</p>
            )}
          </div>
        </div>

        {/* Sekce: YouTube URL */}
        <div className="preparation-section">
          <h3>📺 YouTube URL</h3>
          <div className="youtube-section">
            <YouTubeImporter
              onImportComplete={onYouTubeImport}
              onError={(err) => console.error('YouTube import error:', err)}
              language={language}
            />
          </div>
        </div>
      </div>

      {voiceQuality && (
        <div className={`quality-feedback ${voiceQuality.score}`}>
          <div className="quality-header">
            <span className="quality-icon">
              {voiceQuality.score === 'good' ? '✅' : voiceQuality.score === 'fair' ? '⚠️' : '❌'}
            </span>
            <span className="quality-label">
              Kvalita vzorku: <strong>{
                voiceQuality.score === 'good' ? 'Dobrá' :
                  voiceQuality.score === 'fair' ? 'Průměrná' :
                    voiceQuality.score === 'poor' ? 'Špatná' : 'Neznámá'
              }</strong>
            </span>
            <span className="quality-snr">SNR: {voiceQuality.snr.toFixed(1)} dB</span>
          </div>
          {voiceQuality.warnings && voiceQuality.warnings.length > 0 && (
            <div className="quality-warnings-chips">
              <Chips items={voiceQuality.warnings.map(w => ({ label: w, icon: '⚠️' }))} />
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default VoicePreparation







