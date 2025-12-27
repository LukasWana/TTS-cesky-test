import React from 'react'
import Icon from './Icons'
import './ui.css'

function SelectRow({
  label,
  value,
  options,
  onChange,
  icon = null,
  infoIcon = null,
  className = ''
}) {
  return (
    <div className={`ui-select-row ${className}`}>
      <label className="ui-select-label">
        {icon && (
          <span className="ui-select-icon">
            {typeof icon === 'string' ? <Icon name={icon} size={14} /> : icon}
          </span>
        )}
        {label}
        {infoIcon && <span className="ui-info-icon" title={infoIcon}>ⓘ</span>}
      </label>
      <div className="ui-select-wrapper">
        <select
          className="ui-select-input"
          value={value || ''}
          onChange={(e) => onChange(e.target.value)}
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <span className="ui-select-chevron">▼</span>
      </div>
    </div>
  )
}

export default SelectRow

