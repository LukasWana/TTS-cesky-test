import React from 'react'
import { useSectionColor } from '../../contexts/SectionColorContext'
import './ui.css'

function Input({
  type = 'text',
  placeholder,
  value,
  onChange,
  onFocus,
  onBlur,
  disabled = false,
  error = false,
  label,
  helperText,
  icon,
  iconPosition = 'left',
  className = '',
  fullWidth = true,
  ...props
}) {
  const { color, rgb } = useSectionColor()
  const baseClass = 'ui-input-wrapper'
  const errorClass = error ? 'ui-input-error' : ''
  const fullWidthClass = fullWidth ? 'ui-input-full-width' : ''
  const combinedClass = `${baseClass} ${errorClass} ${fullWidthClass} ${className}`.trim()

  const style = {
    '--section-color': color,
    '--section-color-rgb': rgb
  }

  return (
    <div className={combinedClass} style={style}>
      {label && <label className="ui-input-label">{label}</label>}
      <div className="ui-input-container">
        {icon && iconPosition === 'left' && (
          <span className="ui-input-icon ui-input-icon-left">{icon}</span>
        )}
        <input
          type={type}
          className="ui-input"
          placeholder={placeholder}
          value={value}
          onChange={onChange}
          onFocus={onFocus}
          onBlur={onBlur}
          disabled={disabled}
          {...props}
        />
        {icon && iconPosition === 'right' && (
          <span className="ui-input-icon ui-input-icon-right">{icon}</span>
        )}
      </div>
      {helperText && (
        <span className={`ui-input-helper ${error ? 'ui-input-helper-error' : ''}`}>
          {helperText}
        </span>
      )}
    </div>
  )
}

export default Input

