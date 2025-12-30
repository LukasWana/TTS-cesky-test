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

  const sanitizeText = (text) => {
    if (typeof text !== 'string') {
      return null
    }
    // Odstranit JSON fragmenty z textu
    let sanitized = text
      // Odstranit JSON fragmenty (např. ","timestamp":"...","id":...)
      .replace(/["\']?,\s*["\']?(?:timestamp|id|created_at|updated_at)["\']?\s*:\s*["\']?[^"\']*["\']?/g, '')
      // Odstranit JSON struktury (např. {...})
      // POZOR: Zachovat validní markery v hranatých závorkách
      .replace(/\{[^}]*\}/g, '')
      // Odstranit hranaté závorky, ale ZACHOVAT validní markery:
      // - [pause], [pause:200], [pause:200ms], [PAUSE] (case-insensitive)
      // - [intonation:fall]text[/intonation] a všechny varianty
      // - [lang:speaker]text[/lang] a [lang]text[/lang]
      // - [/intonation], [/lang] (uzavírací tagy)
      .replace(/\[(?!pause|PAUSE|intonation|\/intonation|lang|\/lang)[^\]]*\]/gi, '')
      // Odstranit zbytky JSON syntaxe (ale ne dvojtečky v markerech jako [pause:200])
      .replace(/["\']?\s*,\s*["\']?/g, ' ')
      // Normalizovat mezery
      .replace(/\s+/g, ' ')
      .trim()

    return sanitized.length > 0 ? sanitized : null
  }

  const loadTabVersions = (tabId) => {
    try {
      const key = `tts_text_versions_${tabId}`
      const stored = localStorage.getItem(key)
      if (stored) {
        // Zkontroluj, zda je to validní JSON (začíná [ nebo {)
        const trimmed = stored.trim()
        if (trimmed.startsWith('[') || trimmed.startsWith('{')) {
          const parsed = JSON.parse(stored)
          // Validace: zkontroluj, že je to pole a každá verze má správnou strukturu
          if (Array.isArray(parsed)) {
            // Filtruj a oprav poškozené verze
            const validVersions = parsed
              .filter(v => v && typeof v === 'object')
              .map(v => {
                // Zajisti, že text je string a ne JSON objekt
                if (v.text && typeof v.text === 'string') {
                  const sanitizedText = sanitizeText(v.text)
                  if (sanitizedText) {
                    return {
                      id: v.id || Date.now(),
                      text: sanitizedText,
                      timestamp: v.timestamp || new Date().toISOString()
                    }
                  }
                }
                // Pokud text není string nebo je poškozený, přeskočit
                return null
              })
              .filter(v => v !== null)

            // Pokud byly nějaké poškozené verze, ulož opravené
            if (validVersions.length !== parsed.length) {
              console.warn(`Opraveno ${parsed.length - validVersions.length} poškozených verzí v tabu ${tabId}`)
              saveTabVersions(tabId, validVersions)
            }

            return validVersions
          }
          // Pokud to není pole, vyčistit
          console.warn('Poškozená data v localStorage - není to pole, mazání:', key)
          localStorage.removeItem(key)
          return []
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

  // Auto-save aktuálního textu do tab-specific storage
  useEffect(() => {
    if (isLoadingTextRef.current) return
    if (!isInitializedRef.current) return
    saveTabText(activeTab, text)
  }, [text, activeTab])

  // Debounced auto-save verze textu do historie
  useEffect(() => {
    if (isLoadingTextRef.current) return
    if (!isInitializedRef.current) return
    if (!text || !text.trim()) return

    const timer = setTimeout(() => {
      saveTextVersion(text)
    }, 10000) // 10 sekund stability před uložením verze

    return () => clearTimeout(timer)
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
    if (!textToSave || !textToSave.trim()) {
      console.log('[saveTextVersion] Přeskočeno - prázdný text')
      return
    }

    // Sanitizace textu před uložením - odstranit JSON fragmenty
    const sanitizedText = sanitizeText(textToSave)
    if (!sanitizedText) {
      console.log('[saveTextVersion] Přeskočeno - text je prázdný po sanitizaci')
      return
    }

    // Normalizuj text pro porovnání (trim a případně další normalizace)
    const normalizedText = sanitizedText.trim()

    // Zkontroluj, zda už existuje verze se stejným textem
    const existingVersion = textVersions.find(
      version => version.text && version.text.trim() === normalizedText
    )

    // Pokud už existuje verze se stejným textem, neukládej novou
    if (existingVersion) {
      console.log('[saveTextVersion] Přeskočeno - verze se stejným textem již existuje:', normalizedText.substring(0, 50))
      return
    }

    const newVersion = {
      id: Date.now(),
      text: sanitizedText,
      timestamp: new Date().toISOString()
    }

    const updatedVersions = [newVersion, ...textVersions.slice(0, 19)]
    setTextVersions(updatedVersions)
    saveTabVersions(activeTab, updatedVersions)
    console.log('[saveTextVersion] Uložena nová verze:', normalizedText.substring(0, 50), 'pro tab:', activeTab)
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

