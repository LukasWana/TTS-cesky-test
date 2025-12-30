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
      // Použít jiný klíč pro plain text (ne verze)
      const key = `tts_text_content_${tabId}`
      return localStorage.getItem(key) || ''
    } catch (err) {
      console.error('Chyba při načítání textu:', err)
      return ''
    }
  }

  const saveTabText = (tabId, text) => {
    try {
      // Použít jiný klíč pro plain text (ne verze)
      const key = `tts_text_content_${tabId}`
      localStorage.setItem(key, text)
    } catch (err) {
      console.error('Chyba při ukládání textu:', err)
    }
  }

  const loadTabVersions = (tabId) => {
    try {
      const key = `tts_text_versions_${tabId}`
      const stored = localStorage.getItem(key)
      if (!stored) {
        return []
      }

      // Prázdný string není validní JSON
      const trimmed = stored.trim()
      if (trimmed === '') {
        console.warn('Prázdná data v localStorage, mazání:', key)
        localStorage.removeItem(key)
        return []
      }

      // Zkontroluj, zda je to validní JSON (začíná [ nebo {)
      if (!trimmed.startsWith('[') && !trimmed.startsWith('{')) {
        // Možná je to plain text místo JSON - zkusit to zachránit
        console.warn('Neočekávaný formát dat v localStorage, pokus o opravu:', key)
        try {
          // Zkusit parsovat jako JSON string
          const parsed = JSON.parse(stored)
          if (Array.isArray(parsed)) {
            return parsed
          }
        } catch (e) {
          // Pokud to není validní JSON, smazat
          console.warn('Poškozená data v localStorage, mazání:', key)
          localStorage.removeItem(key)
          return []
        }
        // Pokud to není pole, smazat
        console.warn('Data nejsou pole, mazání:', key)
        localStorage.removeItem(key)
        return []
      }

      // Pokusit se parsovat JSON
      const parsed = JSON.parse(stored)

      // Validovat, že je to pole
      if (!Array.isArray(parsed)) {
        console.warn('Data nejsou pole, mazání:', key)
        localStorage.removeItem(key)
        return []
      }

      // Validovat strukturu pole - každý prvek by měl mít text a id
      const validVersions = parsed.filter(v => {
        if (typeof v !== 'object' || v === null) return false
        if (typeof v.text !== 'string') return false
        return true
      })

      // Pokud se počet liší, opravit data
      if (validVersions.length !== parsed.length) {
        console.warn('Některé verze byly nevalidní, opravuji:', key)
        try {
          localStorage.setItem(key, JSON.stringify(validVersions))
        } catch (saveErr) {
          console.error('Chyba při opravě dat:', saveErr)
        }
      }

      return validVersions
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
      // Validovat, že versions je pole
      if (!Array.isArray(versions)) {
        console.warn('Pokus o uložení nevalidních verzí (není pole), ignoruji')
        return
      }

      const key = `tts_text_versions_${tabId}`

      // Omezit počet verzí na 20 (aby se neplnil localStorage)
      const versionsToSave = versions.slice(0, 20)

      localStorage.setItem(key, JSON.stringify(versionsToSave))
    } catch (err) {
      if (err.name === 'QuotaExceededError' || err.code === 22) {
        // Pokud je localStorage plný, zkusit uložit jen posledních 5 verzí
        try {
          const key = `tts_text_versions_${tabId}`
          const limitedVersions = versions.slice(0, 5)
          localStorage.setItem(key, JSON.stringify(limitedVersions))
          console.warn('Uloženo jen posledních 5 verzí kvůli QuotaExceededError')
        } catch (retryErr) {
          console.error('Chyba při ukládání historie verzí i po omezení:', retryErr)
        }
      } else {
        console.error('Chyba při ukládání historie verzí:', err)
      }
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

  // Automatické ukládání verzí při změně textVersions
  useEffect(() => {
    if (!isInitializedRef.current) return
    if (isLoadingTextRef.current) return

    saveTabVersions(activeTab, textVersions)
  }, [textVersions, activeTab])

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

