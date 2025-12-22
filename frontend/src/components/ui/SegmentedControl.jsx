import React from 'react'
import './ui.css'

function SegmentedControl({ options, value, onChange, className = '' }) {
  return (
    <div className={`ui-segmented-control ${className}`}>
      {options.map((option) => {
        const optionValue = typeof option === 'string' ? option : option.value
        const optionLabel = typeof option === 'string' ? option : option.label
        const isSelected = value === optionValue

        return (
          <button
            key={optionValue}
            type="button"
            className={`ui-segmented-option ${isSelected ? 'selected' : ''}`}
            onClick={() => onChange(optionValue)}
          >
            {optionLabel}
          </button>
        )
      })}
    </div>
  )
}

export default SegmentedControl

