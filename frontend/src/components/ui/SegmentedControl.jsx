import React from 'react'
import { useSectionColor } from '../../contexts/SectionColorContext'
import './ui.css'

function SegmentedControl({ options, value, onChange, className = '' }) {
  const { color, rgb } = useSectionColor()
  const style = {
    '--section-color': color,
    '--section-color-rgb': rgb
  }

  return (
    <div className={`ui-segmented-control ${className}`} style={style}>
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

