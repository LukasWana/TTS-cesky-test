import React, { useState } from 'react'
import AudioRecorder from './AudioRecorder'
import YouTubeImporter from './YouTubeImporter'
import Chips from './ui/Chips'
import './VoiceSelector.css'

function VoiceSelector({
  demoVoices,
  selectedVoice,
  voiceType,
  uploadedVoiceFileName,
  onVoiceSelect,
  onVoiceTypeChange,
  onVoiceUpload,
  onVoiceRecord,
  onYouTubeImport,
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
    <div className="voice-selector">
      <h2>Výběr hlasu</h2>

      <div className="voice-options">
        <label className="voice-option">
          <input
            type="radio"
            name="voiceType"
            value="demo"
            checked={voiceType === 'demo'}
            onChange={(e) => onVoiceTypeChange(e.target.value)}
          />
          <span>Demo hlas</span>
        </label>

        <label className="voice-option">
          <input
            type="radio"
            name="voiceType"
            value="upload"
            checked={voiceType === 'upload'}
            onChange={(e) => onVoiceTypeChange(e.target.value)}
          />
          <span>Nahrát soubor</span>
        </label>

        <label className="voice-option">
          <input
            type="radio"
            name="voiceType"
            value="record"
            checked={voiceType === 'record'}
            onChange={(e) => onVoiceTypeChange(e.target.value)}
          />
          <span>Nahrát z mikrofonu</span>
        </label>

        <label className="voice-option">
          <input
            type="radio"
            name="voiceType"
            value="youtube"
            checked={voiceType === 'youtube'}
            onChange={(e) => onVoiceTypeChange(e.target.value)}
          />
          <span>YouTube URL</span>
        </label>
      </div>

      {voiceType === 'demo' && (
        <div className="demo-voices">
          {demoVoices.length > 0 ? (
            <div className="demo-voice-select-wrapper">
              <select
                className="demo-voice-select"
                value={selectedVoice}
                onChange={(e) => onVoiceSelect(e.target.value)}
              >
                {demoVoices.map((voice) => (
                  <option key={voice.id} value={voice.id}>
                    {voice.display_name || voice.name}
                  </option>
                ))}
              </select>
            </div>
          ) : (
            <p className="no-demo-voices">
              Žádné demo hlasy nejsou k dispozici. Přidejte je do assets/{language === 'sk' ? 'slovak voices' : 'czech voices'}/
            </p>
          )}
        </div>
      )}

      {voiceType === 'upload' && (
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
      )}

      {voiceType === 'record' && (
        <div className="record-section">
          <AudioRecorder onRecordComplete={handleRecordComplete} language={language} />
          {uploadedVoiceFileName && (
            <p className="record-status">✓ {uploadedVoiceFileName}</p>
          )}
        </div>
      )}

      {voiceType === 'youtube' && (
        <div className="youtube-section">
          <YouTubeImporter
            onImportComplete={onYouTubeImport}
            onError={(err) => console.error('YouTube import error:', err)}
            language={language}
          />
        </div>
      )}

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

export default VoiceSelector

