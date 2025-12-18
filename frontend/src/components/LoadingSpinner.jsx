import React from 'react'
import './LoadingSpinner.css'

function LoadingSpinner() {
  return (
    <div className="loading-spinner-container">
      <div className="loading-spinner"></div>
      <p className="loading-text">Generuji audio...</p>
    </div>
  )
}

export default LoadingSpinner




