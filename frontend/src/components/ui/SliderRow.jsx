import React from 'react'
import './ui.css'

function SliderRow({
  label,
  value,
  min,
  max,
  step,
  onChange,
  onReset,
  formatValue = (v) => v,
  showTicks = false,
  infoIcon = null,
  valueUnit = null,
  className = ''
}) {
  const percentage = ((value - min) / (max - min)) * 100

  return (
    <div className={`ui-slider-row ${className}`}>
      <div className="ui-slider-header">
        <label className="ui-slider-label">
          {label}
          {onReset && (
            <button
              className="ui-reset-icon-button"
              onClick={onReset}
              title="Resetovat na výchozí hodnotu"
            >
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
                <path d="M3 3v5h5" />
              </svg>
            </button>
          )}
          {infoIcon && <span className="ui-info-icon" title={infoIcon}>ⓘ</span>}
        </label>
        <div className="ui-slider-actions">
          <span className="ui-slider-value">
            <span className="ui-slider-value-number">{formatValue(value)}</span>
            {valueUnit && (
              <span className="ui-slider-value-unit">{valueUnit}</span>
            )}
          </span>
        </div>
      </div>
      <div className="ui-slider-container">
        <div
          className="ui-slider-track-fill"
          style={{ width: `${percentage}%` }}
        />
        {showTicks && (
          <div className="ui-slider-ticks">
            {Array.from({ length: 11 }).map((_, i) => (
              <div key={i} className="ui-slider-tick" />
            ))}
          </div>
        )}
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          className="ui-slider-input"
        />
      </div>
    </div>
  )
}

export default SliderRow

