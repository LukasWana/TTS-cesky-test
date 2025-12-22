import React from 'react'
import './ui.css'

function Chips({ items, onRemove, className = '' }) {
  if (!items || items.length === 0) return null

  return (
    <div className={`ui-chips ${className}`}>
      {items.map((item, index) => {
        const label = typeof item === 'string' ? item : item.label
        const icon = typeof item === 'object' && item.icon ? item.icon : null

        return (
          <div key={index} className="ui-chip">
            {icon && <span className="ui-chip-icon">{icon}</span>}
            <span className="ui-chip-label">{label}</span>
            {onRemove && (
              <button
                className="ui-chip-remove"
                onClick={() => onRemove(index)}
                title="Odstranit"
              >
                ×
              </button>
            )}
          </div>
        )
      })}
    </div>
  )
}

export default Chips

