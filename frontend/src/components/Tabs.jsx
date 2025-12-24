import React from 'react'
import './Tabs.css'

function Tabs({ activeTab, onTabChange, tabs }) {
  return (
    <div className="tabs-container">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          className={`tab-button ${activeTab === tab.id ? 'active' : ''}`}
          onClick={() => onTabChange(tab.id)}
          title={tab.label}
        >
          {tab.icon && <span className="tab-icon" aria-hidden="true">{tab.icon}</span>}
          <span className="tab-label">{tab.label}</span>
        </button>
      ))}
    </div>
  )
}

export default Tabs














