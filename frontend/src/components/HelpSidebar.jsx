import React, { useEffect } from 'react'
import Icon from './ui/Icons'
import './HelpSidebar.css'

function HelpSidebar({ isOpen, onClose, title, children }) {
  // Zavření pomocí ESC klávesy
  useEffect(() => {
    if (!isOpen) return

    const handleEscape = (e) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }

    document.addEventListener('keydown', handleEscape)
    // Zamezení scrollování body když je sidebar otevřený
    document.body.style.overflow = 'hidden'

    return () => {
      document.removeEventListener('keydown', handleEscape)
      document.body.style.overflow = ''
    }
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <>
      <div className="help-sidebar-overlay" onClick={onClose} />
      <div className="help-sidebar">
        <div className="help-sidebar-header">
          <h2>{title}</h2>
          <button
            className="help-sidebar-close"
            onClick={onClose}
            title="Zavřít (ESC)"
            aria-label="Zavřít nápovědu"
          >
            <Icon name="x" size={20} />
          </button>
        </div>
        <div className="help-sidebar-content">
          {children}
        </div>
      </div>
    </>
  )
}

export default HelpSidebar

