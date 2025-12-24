import React from 'react'
import './Alert.css'

function Alert({
  type = 'info',
  title,
  message,
  onClose,
  className = '',
  icon,
  ...props
}) {
  const baseClass = 'alert'
  const typeClass = `alert-${type}`
  const combinedClass = `${baseClass} ${typeClass} ${className}`.trim()

  const defaultIcons = {
    success: '✓',
    error: '✕',
    warning: '⚠',
    info: 'ℹ'
  }

  const displayIcon = icon || defaultIcons[type]

  return (
    <div className={combinedClass} {...props}>
      <div className="alert-content">
        {displayIcon && <span className="alert-icon">{displayIcon}</span>}
        <div className="alert-text">
          {title && <div className="alert-title">{title}</div>}
          {message && <div className="alert-message">{message}</div>}
        </div>
      </div>
      {onClose && (
        <button className="alert-close" onClick={onClose} aria-label="Zavřít">
          ×
        </button>
      )}
    </div>
  )
}

export default Alert

