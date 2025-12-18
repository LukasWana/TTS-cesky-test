import React, { useState } from 'react'
import './VariantSelector.css'

function VariantSelector({ variants, onSelect, onClose }) {
  const [selectedIndex, setSelectedIndex] = useState(null)
  const [playingIndex, setPlayingIndex] = useState(null)
  const [audioRefs, setAudioRefs] = useState({})

  const handlePlay = (index, audioUrl) => {
    // Zastav všechny ostatní přehrávače
    Object.values(audioRefs).forEach(ref => {
      if (ref && !ref.paused) {
        ref.pause()
        ref.currentTime = 0
      }
    })

    // Pokud už hraje stejný, zastav ho
    if (playingIndex === index) {
      setPlayingIndex(null)
      return
    }

    // Spusť nový
    setPlayingIndex(index)
    const audio = new Audio(audioUrl)
    audioRefs[index] = audio
    setAudioRefs({ ...audioRefs })

    audio.onended = () => {
      setPlayingIndex(null)
    }

    audio.play().catch(err => {
      console.error('Error playing audio:', err)
      setPlayingIndex(null)
    })
  }

  const handleSelect = (index) => {
    setSelectedIndex(index)
    if (onSelect) {
      onSelect(variants[index])
    }
  }

  if (!variants || variants.length === 0) {
    return null
  }

  return (
    <div className="variant-selector-overlay" onClick={onClose}>
      <div className="variant-selector" onClick={(e) => e.stopPropagation()}>
        <div className="variant-selector-header">
          <h3>Vyberte nejlepší variantu</h3>
          <button className="close-button" onClick={onClose}>×</button>
        </div>
        <div className="variants-list">
          {variants.map((variant, index) => (
            <div
              key={index}
              className={`variant-item ${selectedIndex === index ? 'selected' : ''}`}
            >
              <div className="variant-info">
                <div className="variant-number">Variant {variant.index || index + 1}</div>
                <div className="variant-metadata">
                  <span>Seed: {variant.seed}</span>
                  <span>Temperature: {variant.temperature?.toFixed(2)}</span>
                </div>
              </div>
              <div className="variant-controls">
                <button
                  className={`play-button ${playingIndex === index ? 'playing' : ''}`}
                  onClick={() => handlePlay(index, variant.audio_url)}
                >
                  {playingIndex === index ? '⏸️' : '▶️'}
                </button>
                <button
                  className="select-button"
                  onClick={() => handleSelect(index)}
                >
                  {selectedIndex === index ? '✓ Vybráno' : 'Vybrat'}
                </button>
              </div>
            </div>
          ))}
        </div>
        {selectedIndex !== null && (
          <div className="variant-selector-footer">
            <button className="confirm-button" onClick={onClose}>
              Potvrdit výběr
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default VariantSelector





