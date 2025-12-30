import { useState, useEffect, useRef } from 'react'
import { STORAGE_KEYS } from '../constants/ttsDefaults'

/**
 * Hook pro správu textu a verzí podle záložek
 */
export const useTextVersions = (activeTab) => {
  const [textsByTab, setTextsByTab] = useState({
    generate: '',
    f5tts: '',
    musicgen: '',
    bark: '',
    audioeditor: ''
  })
  const [textVersions, setTextVersions] = useState([])

  const isLoadingTextRef = useRef(false)
  const isInitializedRef = useRef(false)
  const previousTabRef = useRef(activeTab)

  const loadTabText = (tabId) => {
    try {
      const key = STORAGE_KEYS.TEXT_VERSIONS(tabId)
      return localStorage.getItem(key) || ''
    } catch (err) {
      console.error('Chyba při načítání textu:', err)
      return ''
    }
  }

  const saveTabText = (tabId, text) => {
    try {
      const key = STORAGE_KEYS.TEXT_VERSIONS(tabId)
      localStorage.setItem(key, text)
    } catch (err) {
      console.error('Chyba při ukládání textu:', err)
    }
  }

  const loadTabVersions = (tabId) => {
    try {
      const key = `tts_text_versions_${tabId}`
      const stored = localStorage.getItem(key)
      if (stored) {
        // Zkontroluj, zda je to validní JSON (začíná [ nebo {)
        const trimmed = stored.trim()
        if (trimmed.startsWith('[') || trimmed.startsWith('{')) {
          return JSON.parse(stored)
        } else {
          // Poškozená data - není to JSON, vyčistit
          console.warn('Poškozená data v localStorage, mazání:', key)
          localStorage.removeItem(key)
          return []
        }
      }
    } catch (err) {
      console.error('Chyba při načítání historie verzí:', err)
      // Pokud selže parsování, vyčistit poškozená data
      try {
        const key = `tts_text_versions_${tabId}`
        localStorage.removeItem(key)
      } catch (cleanupErr) {
        console.error('Chyba při čištění poškozených dat:', cleanupErr)
      }
    }
    return []
  }

  const saveTabVersions = (tabId, versions) => {
    try {
      const key = `tts_text_versions_${tabId}`
      localStorage.setItem(key, JSON.stringify(versions))
    } catch (err) {
      console.error('Chyba při ukládání historie verzí:', err)
    }
  }

  // Načtení textu při startu
  useEffect(() => {
    if (isInitializedRef.current) return

    isLoadingTextRef.current = true

    const loadedTexts = {
      generate: loadTabText('generate'),
      f5tts: loadTabText('f5tts'),
      musicgen: loadTabText('musicgen'),
      bark: loadTabText('bark'),
      audioeditor: loadTabText('audioeditor')
    }
    setTextsByTab(loadedTexts)

    const savedVersions = loadTabVersions(activeTab)
    if (savedVersions && savedVersions.length > 0) {
      setTextVersions(savedVersions)
    }

    isLoadingTextRef.current = false
    isInitializedRef.current = true
    previousTabRef.current = activeTab
  }, [])

  // Aktuální text pro zobrazení
  const text = textsByTab[activeTab] || ''
  const setText = (newText) => {
    setTextsByTab(prev => ({
      ...prev,
      [activeTab]: newText
    }))
  }

  // Auto-save aktuálního textu
  useEffect(() => {
    if (isLoadingTextRef.current) return
    if (!isInitializedRef.current) return
    saveTabText(activeTab, text)
  }, [text, activeTab])

  // Ukládání a načítání při změně záložky
  useEffect(() => {
    if (!isInitializedRef.current) return

    if (previousTabRef.current !== activeTab) {
      const previousText = textsByTab[previousTabRef.current] || ''
      saveTabText(previousTabRef.current, previousText)
      saveTabVersions(previousTabRef.current, textVersions)
    }

    isLoadingTextRef.current = true

    const savedVersions = loadTabVersions(activeTab)
    setTextVersions(savedVersions || [])

    isLoadingTextRef.current = false
    previousTabRef.current = activeTab
  }, [activeTab])

  const saveTextVersion = (textToSave) => {
    if (!textToSave || !textToSave.trim()) return

    // Normalizuj text pro porovnání (trim a případně další normalizace)
    const normalizedText = textToSave.trim()

    // Zkontroluj, zda už existuje verze se stejným textem
    const existingVersion = textVersions.find(
      version => version.text && version.text.trim() === normalizedText
    )

    // Pokud už existuje verze se stejným textem, neukládej novou
    if (existingVersion) {
      return
    }

    const newVersion = {
      id: Date.now(),
      text: textToSave,
      timestamp: new Date().toISOString()
    }

    const updatedVersions = [newVersion, ...textVersions.slice(0, 19)]
    setTextVersions(updatedVersions)
    saveTabVersions(activeTab, updatedVersions)
  }

  const deleteTextVersion = (versionId) => {
    const updatedVersions = textVersions.filter(v => v.id !== versionId)
    setTextVersions(updatedVersions)
    saveTabVersions(activeTab, updatedVersions)
  }

  return {
    text,
    setText,
    textsByTab,
    setTextsByTab,
    textVersions,
    setTextVersions,
    saveTextVersion,
    deleteTextVersion
  }
}

