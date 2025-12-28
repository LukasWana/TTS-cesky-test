import React, { useState } from 'react'
import Icon from './ui/Icons'
import { getCategoryColor } from '../utils/layerColors'
import './Sidebar.css'

function Sidebar({ activeTab, onTabChange, tabs, isOpen, onClose, modelStatus }) {
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
    <>
      {/* Mobile overlay */}
      {isOpen && <div className="sidebar-overlay" onClick={onClose} />}

      {/* Sidebar */}
      <aside className={`sidebar ${isOpen ? 'sidebar-open' : ''}`}>
        <div className="sidebar-header">
          <div className="sidebar-logo">
            <svg width="32" height="32" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect width="100" height="100" rx="20" fill="url(#grad1)"/>
              <defs>
                <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" style={{stopColor: '#6366f1', stopOpacity: 1}} />
                  <stop offset="100%" style={{stopColor: '#8b5cf6', stopOpacity: 1}} />
                </linearGradient>
              </defs>
              <rect x="40" y="30" width="20" height="35" rx="10" fill="#ffffff" opacity="0.95"/>
              <rect x="47" y="65" width="6" height="8" fill="#ffffff" opacity="0.95"/>
              <path d="M 25 50 Q 30 45, 35 50 T 40 50" stroke="#ffffff" strokeWidth="2" fill="none" opacity="0.8"/>
              <path d="M 60 50 Q 65 45, 70 50 T 75 50" stroke="#ffffff" strokeWidth="2" fill="none" opacity="0.8"/>
            </svg>
            <span className="sidebar-logo-text">Voice Studio</span>
          </div>
          <button className="sidebar-close" onClick={onClose} aria-label="Zavřít menu">
            <Icon name="close" size={20} />
          </button>
        </div>

        {modelStatus && (
          <div className="sidebar-model-status">
            <div className={`sidebar-status-indicator ${modelStatus.loaded ? 'loaded' : modelStatus.loading ? 'loading' : 'idle'}`}>
              {modelStatus.loaded
                ? <><Icon name="check" size={14} style={{ display: 'inline-block', marginRight: '4px', verticalAlign: 'middle' }} /> Model načten</>
                : modelStatus.loading
                  ? <><Icon name="clock" size={14} style={{ display: 'inline-block', marginRight: '4px', verticalAlign: 'middle' }} /> Načítání modelu...</>
                  : 'Připraven (On-Demand)'}
            </div>
            <div className="sidebar-device-info">
              Device: <strong>{modelStatus.device.toUpperCase()}</strong>
              {modelStatus.gpu_name && ` (${modelStatus.gpu_name})`}
              {modelStatus.device_forced && (
                <span className="sidebar-device-forced"> [vynuceno: {modelStatus.force_device}]</span>
              )}
            </div>
          </div>
        )}

        <nav className="sidebar-nav">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id
            const category = getCategoryForTab(tab.id)
            const categoryColor = getCategoryColor(category, 0)
            const rgb = hexToRgb(categoryColor)

            return (
            <button
              key={tab.id}
              className={`sidebar-nav-item ${isActive ? 'active' : ''}`}
              onClick={() => {
                onTabChange(tab.id)
              }}
              style={isActive ? {
                background: `rgba(${rgb}, 0.1)`,
                color: categoryColor,
                borderLeftColor: categoryColor
              } : {}}
            >
              {tab.icon && (
                <span className="sidebar-nav-icon">
                  <Icon name={tab.icon} size={20} />
                </span>
              )}
              <span className="sidebar-nav-label">{tab.label}</span>
            </button>
            )
          })}
        </nav>
      </aside>
    </>
  )
}

export default Sidebar

