import React, { useEffect, useState } from 'react'

/**
 * Debug komponenta pro sledování copy/paste nastavení
 */
export function SettingsDebugger() {
  const [sessionData, setSessionData] = useState(null)
  const [localStorageKeys, setLocalStorageKeys] = useState([])

  useEffect(() => {
    const interval = setInterval(() => {
      // Načíst sessionStorage data
      const copied = sessionStorage.getItem('tts_copied_settings')
      const copiedSk = sessionStorage.getItem('tts_copied_settings_sk')

      setSessionData({
        czech: copied ? JSON.parse(copied) : null,
        slovak: copiedSk ? JSON.parse(copiedSk) : null
      })

      // Najít všechny localStorage klíče s nastavením
      const keys = []
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i)
        if (key && key.includes('f5tts_voice')) {
          keys.push({
            key,
            data: JSON.parse(localStorage.getItem(key) || '{}')
          })
        }
      }
      setLocalStorageKeys(keys)
    }, 1000)

    return () => clearInterval(interval)
  }, [])

  return (
    <div style={{
      position: 'fixed',
      bottom: 10,
      right: 10,
      background: 'rgba(0,0,0,0.9)',
      color: '#fff',
      padding: '15px',
      borderRadius: '8px',
      fontSize: '11px',
      maxWidth: '400px',
      maxHeight: '300px',
      overflow: 'auto',
      zIndex: 99999,
      border: '1px solid rgba(255,255,255,0.2)'
    }}>
      <h3 style={{ margin: '0 0 10px 0', fontSize: '12px', color: '#4caf50' }}>
        🔍 Settings Debugger
      </h3>

      <div style={{ marginBottom: '10px' }}>
        <strong style={{ color: '#2196f3' }}>SessionStorage (schránka):</strong>
        {sessionData?.czech ? (
          <div style={{ marginLeft: '10px', fontSize: '10px' }}>
            <div>✅ Czech: {sessionData.czech.sourceVariant}</div>
            <div>Speed: {sessionData.czech.ttsSettings?.speed}</div>
          </div>
        ) : (
          <div style={{ marginLeft: '10px', color: '#999' }}>Prázdná</div>
        )}
      </div>

      <div>
        <strong style={{ color: '#ff9800' }}>LocalStorage ({localStorageKeys.length} klíčů):</strong>
        {localStorageKeys.slice(0, 3).map((item, i) => (
          <div key={i} style={{ marginLeft: '10px', fontSize: '10px', marginTop: '5px' }}>
            <div style={{ color: '#4caf50' }}>{item.key.split('_').pop()}</div>
            <div>Speed: {item.data.ttsSettings?.speed || 'N/A'}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
