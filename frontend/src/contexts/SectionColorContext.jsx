import React, { createContext, useContext, useMemo } from 'react'
import { getCategoryColor } from '../utils/layerColors'

const SectionColorContext = createContext(null)

/**
 * Získá kategorii pro tab ID
 */
function getCategoryForTab(tabId) {
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

/**
 * Převod hex barvy na RGB string
 */
function hexToRgb(hex) {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
  return result
    ? `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}`
    : '158, 158, 158' // výchozí šedá
}

/**
 * Provider pro barvu sekce
 */
export function SectionColorProvider({ activeTab, children }) {
  const value = useMemo(() => {
    const category = getCategoryForTab(activeTab)
    const color = getCategoryColor(category, 0)
    const rgb = hexToRgb(color)

    return {
      color, // hlavní barva sekce (hex)
      rgb, // RGB string pro rgba
      category, // kategorie pro případné další použití
      getCategoryColor: (index = 0) => getCategoryColor(category, index),
      hexToRgb
    }
  }, [activeTab])

  return (
    <SectionColorContext.Provider value={value}>
      {children}
    </SectionColorContext.Provider>
  )
}

/**
 * Hook pro použití barvy sekce
 */
export function useSectionColor() {
  const context = useContext(SectionColorContext)
  if (!context) {
    // Fallback pro případy, kdy není Provider
    const defaultColor = '#6366f1'
    return {
      color: defaultColor,
      rgb: '99, 102, 241',
      category: 'file',
      getCategoryColor: () => defaultColor,
      hexToRgb
    }
  }
  return context
}








