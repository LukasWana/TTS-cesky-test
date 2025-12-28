import { useState, useEffect, useRef } from 'react'
import { STORAGE_KEYS } from '../constants/ttsDefaults'

/**
 * Hook pro správu aktivní varianty s localStorage persistence
 */
export const useVariantManager = () => {
  const [activeVariant, setActiveVariant] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEYS.ACTIVE_VARIANT)
      return saved || 'variant1'
    } catch (err) {
      console.error('Chyba při načítání aktivní varianty:', err)
      return 'variant1'
    }
  })

  // Ref pro saveCurrentVariantNow callback - může být nastaven později
  const saveCurrentVariantNowRef = useRef(null)

  // Uložení aktivní varianty do localStorage
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEYS.ACTIVE_VARIANT, activeVariant)
    } catch (err) {
      console.error('Chyba při ukládání aktivní varianty:', err)
    }
  }, [activeVariant])

  const handleVariantChange = (nextVariant) => {
    if (nextVariant === activeVariant) return

    // Uložit aktuální stav před změnou varianty
    if (saveCurrentVariantNowRef.current) {
      saveCurrentVariantNowRef.current()
    }

    setActiveVariant(nextVariant)
  }

  // Funkce pro nastavení saveCurrentVariantNow callbacku
  const setSaveCurrentVariantNow = (callback) => {
    saveCurrentVariantNowRef.current = callback
  }

  return {
    activeVariant,
    setActiveVariant,
    handleVariantChange,
    setSaveCurrentVariantNow
  }
}

