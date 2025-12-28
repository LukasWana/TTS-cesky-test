import React from 'react'
import Chips from './ui/Chips'
import './VoiceSelector.css'

function VoiceSelector({
  demoVoices,
  selectedVoice,
  onVoiceSelect,
  voiceQuality,
  language = 'cs'
}) {
  return (
    <div className="voice-selector">
      <h2>Výběr hlasu</h2>

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

