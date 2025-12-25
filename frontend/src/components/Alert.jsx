import React from 'react'
import Icon from './ui/Icons'
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
    success: 'check',
    error: 'close',
    warning: 'warning',
    info: 'info'
  }

  const displayIconName = icon || defaultIcons[type]

  return (
    <div className={combinedClass} {...props}>
      <div className="alert-content">
        {displayIconName && (
          <span className="alert-icon">
            {typeof displayIconName === 'string' ? <Icon name={displayIconName} size={18} /> : displayIconName}
          </span>
        )}
        <div className="alert-text">
          {title && <div className="alert-title">{title}</div>}
          {message && <div className="alert-message">{message}</div>}
        </div>
      </div>
      {onClose && (
        <button className="alert-close" onClick={onClose} aria-label="Zavřít">
          <Icon name="close" size={18} />
        </button>
      )}
    </div>
  )
}

export default Alert

