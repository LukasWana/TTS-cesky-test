import React from 'react'
import './AudioPlayer.css'

function AudioPlayer({ audioUrl }) {
  const fullUrl = audioUrl.startsWith('http')
    ? audioUrl
    : `http://localhost:8000${audioUrl}`

  const handleDownload = () => {
    const link = document.createElement('a')
    link.href = fullUrl
    link.download = `tts-output-${Date.now()}.wav`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return (
    <div className="audio-player-section">
      <h2>Výstup</h2>
      <div className="audio-player-wrapper">
        <audio
          className="audio-player"
          controls
          src={fullUrl}
        >
          Váš prohlížeč nepodporuje přehrávání audio.
        </audio>
        <button
          className="download-button"
          onClick={handleDownload}
        >
          ⬇️ Stáhnout audio
        </button>
      </div>
    </div>
  )
}

export default AudioPlayer

