import React from 'react'
import './TextInput.css'

function TextInput({ value, onChange, maxLength = 500 }) {
  const remaining = maxLength - value.length

  return (
    <div className="text-input-section">
      <h2>Text k syntéze</h2>
      <div className="text-input-wrapper">
        <textarea
          className="text-input"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Zadejte český text k syntéze řeči..."
          maxLength={maxLength}
          rows={6}
        />
        <div className="char-counter">
          <span className={remaining < 50 ? 'warning' : ''}>
            {value.length}/{maxLength}
          </span>
        </div>
      </div>
    </div>
  )
}

export default TextInput

