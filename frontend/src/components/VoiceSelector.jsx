import React, { useState } from 'react'
import AudioRecorder from './AudioRecorder'
import YouTubeImporter from './YouTubeImporter'
import './VoiceSelector.css'

function VoiceSelector({
  demoVoices,
  selectedVoice,
  voiceType,
  onVoiceSelect,
  onVoiceTypeChange,
  onVoiceUpload,
  onVoiceRecord,
  onYouTubeImport
}) {
  const [uploadedFileName, setUploadedFileName] = useState(null)

  const handleFileChange = (e) => {
    const file = e.target.files[0]
    if (file) {
      setUploadedFileName(file.name)
      onVoiceUpload(file)
    }
  }

  const handleRecordComplete = (result) => {
    onVoiceRecord(result)
    if (result && result.filename) {
      setUploadedFileName(`✓ Uloženo: ${result.filename}`)
    } else {
      setUploadedFileName('Nahráno z mikrofonu')
    }
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
            <div className="demo-voice-list">
              {demoVoices.map((voice) => (
                <label key={voice.id} className="demo-voice-item">
                  <input
                    type="radio"
                    name="demoVoice"
                    value={voice.id}
                    checked={selectedVoice === voice.id}
                    onChange={(e) => onVoiceSelect(e.target.value)}
                  />
                  <span>
                    {voice.name} ({voice.gender === 'male' ? 'Muž' : voice.gender === 'female' ? 'Žena' : 'Neznámé'})
                  </span>
                </label>
              ))}
            </div>
          ) : (
            <p className="no-demo-voices">
              Žádné demo hlasy nejsou k dispozici. Přidejte je do frontend/assets/demo-voices/
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
          {uploadedFileName && (
            <p className="upload-status">✓ {uploadedFileName}</p>
          )}
          <p className="upload-hint">
            Minimálně 6 sekund čistého audio (WAV, MP3)
          </p>
        </div>
      )}

      {voiceType === 'record' && (
        <div className="record-section">
          <AudioRecorder onRecordComplete={handleRecordComplete} />
          {uploadedFileName && (
            <p className="record-status">✓ {uploadedFileName}</p>
          )}
        </div>
      )}

      {voiceType === 'youtube' && (
        <div className="youtube-section">
          <YouTubeImporter
            onImportComplete={onYouTubeImport}
            onError={(err) => console.error('YouTube import error:', err)}
          />
        </div>
      )}
    </div>
  )
}

export default VoiceSelector

