import React from 'react'
import './LoadingSpinner.css'

function formatEta(seconds) {
  if (seconds === null || seconds === undefined) return null
  const s = Math.max(0, Number(seconds) || 0)
  if (s < 60) return `${Math.round(s)}s`
  const m = Math.floor(s / 60)
  const r = Math.round(s % 60)
  return `${m}m ${r}s`
}

function LoadingSpinner({ progress }) {
  const percent = progress?.percent
  const eta = formatEta(progress?.eta_seconds)
  const message = progress?.message || 'Generuji audio...'
  return (
    <div className="loading-spinner-container">
      <div className="loading-spinner"></div>
      <p className="loading-text">
        {message}
        {typeof percent === 'number' ? ` (${Math.round(percent)}%)` : ''}
        {eta ? ` · ETA ${eta}` : ''}
      </p>
      {typeof percent === 'number' && (
        <div className="loading-progress">
          <div className="loading-progress-bar" style={{ width: `${Math.min(100, Math.max(0, percent))}%` }} />
        </div>
      )}
    </div>
  )
}

export default LoadingSpinner





