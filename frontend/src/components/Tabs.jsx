import React from 'react'
import { getCategoryColor } from '../utils/layerColors'
import './Tabs.css'

function Tabs({ activeTab, onTabChange, tabs }) {
  // Mapování tab ID na kategorii pro barvy
  const getCategoryForTab = (tabId) => {
    const categoryMap = {
      'generate': 'tts',
      'f5tts': 'f5tts',
      'musicgen': 'music',
      'bark': 'bark',
      'audioeditor': 'file',
      'history': 'file',
      'voicepreparation': 'voicepreparation'
    }
    return categoryMap[tabId] || 'file'
  }

  // Pomocná funkce pro převod hex barvy na RGB string
  const hexToRgb = (hex) => {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
    return result
      ? `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}`
      : '158, 158, 158' // výchozí šedá
  }

  return (
    <div className="tabs-container">
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id
        const category = getCategoryForTab(tab.id)
        const categoryColor = getCategoryColor(category, 0)
        const rgb = hexToRgb(categoryColor)

        return (
        <button
          key={tab.id}
          className={`tab-button ${isActive ? 'active' : ''}`}
          onClick={() => onTabChange(tab.id)}
          title={tab.label}
          style={isActive ? {
            color: categoryColor,
            borderBottomColor: categoryColor,
            background: `rgba(${rgb}, 0.1)`
          } : {}}
        >
          {tab.icon && <span className="tab-icon" aria-hidden="true">{tab.icon}</span>}
          <span className="tab-label">{tab.label}</span>
          {isActive && (
            <span
              className="tab-button-indicator"
              style={{
                background: categoryColor
              }}
            />
          )}
        </button>
        )
      })}
    </div>
  )
}

export default Tabs














