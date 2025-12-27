import React from 'react'
import Icon from './Icons'
import './ui.css'

function Section({ title, icon, children, onReset, isExpanded = true, onToggle, className = '' }) {
  return (
    <div className={`ui-section ${className}`}>
      {title && (
        <div className="ui-section-header" onClick={onToggle}>
          <div className="ui-section-title">
            {icon && (
              <span className="ui-section-icon">
                {typeof icon === 'string' ? (
                  <Icon name={icon} size={18} />
                ) : (
                  icon
                )}
              </span>
            )}
            <h4>{title}</h4>
          </div>
          <div className="ui-section-actions">
            {onReset && (
              <button
                className="ui-reset-button"
                onClick={(e) => {
                  e.stopPropagation()
                  onReset()
                }}
                title="Resetovat na výchozí hodnoty"
              >
                <Icon name="refresh" size={14} />
              </button>
            )}
            {onToggle && (
              <span className="ui-toggle-icon">
                <Icon name={isExpanded ? 'chevronDown' : 'chevronRight'} size={14} />
              </span>
            )}
          </div>
        </div>
      )}
      {isExpanded && children && (
        <div className="ui-section-content">
          {children}
        </div>
      )}
    </div>
  )
}

export default Section

