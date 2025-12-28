import { useState, useRef, useCallback } from 'react'
import { getCategoryFromHistoryEntry, getColorForNewLayer } from '../utils/layerColors'

const API_BASE_URL = 'http://127.0.0.1:8000'

/**
 * Hook pro správu vrstev v AudioEditoru
 */
export function useLayers() {
  const [layers, setLayers] = useState([])
  const [selectedLayerId, setSelectedLayerId] = useState(null)
  const [expandedLayerId, setExpandedLayerId] = useState(null)
  const layerIdCounterRef = useRef(0)

  // Načtení audio z URL (vyžaduje audioContextRef)
  const loadAudioFromUrl = useCallback(async (audioUrl, audioContextRef) => {
    try {
      let fullUrl = audioUrl
      if (!audioUrl.startsWith('http')) {
        fullUrl = `${API_BASE_URL}${audioUrl.startsWith('/') ? audioUrl : '/' + audioUrl}`
      }

      const response = await fetch(fullUrl)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const arrayBuffer = await response.arrayBuffer()
      if (!audioContextRef?.current) {
        throw new Error('AudioContext není inicializován')
      }

      const audioBuffer = await audioContextRef.current.decodeAudioData(arrayBuffer)
      return audioBuffer
    } catch (error) {
      console.error('Chyba při načítání audio z URL:', error)
      throw error
    }
  }, [])

  // Načtení audio ze souboru (vyžaduje audioContextRef)
  const loadAudioFile = useCallback(async (file, audioContextRef) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = async (e) => {
        try {
          const arrayBuffer = e.target.result
          if (!audioContextRef?.current) {
            throw new Error('AudioContext není inicializován')
          }
          const audioBuffer = await audioContextRef.current.decodeAudioData(arrayBuffer)
          resolve(audioBuffer)
        } catch (err) {
          reject(err)
        }
      }
      reader.onerror = reject
      reader.readAsArrayBuffer(file)
    })
  }, [])

  // Vytvoření blob URL z AudioBuffer (vyžaduje audioBufferToWav funkci)
  const createBlobUrl = useCallback(async (audioBuffer, audioBufferToWav) => {
    try {
      const wav = await audioBufferToWav(audioBuffer)
      const blob = new Blob([wav], { type: 'audio/wav' })
      return URL.createObjectURL(blob)
    } catch (err) {
      console.error('Chyba při vytváření blob URL:', err)
      throw err
    }
  }, [])

  // Přidání vrstvy ze souboru
  const addLayer = useCallback(async (file, audioContextRef, audioBufferToWav, sourceNodesRef, gainNodesRef) => {
    try {
      const audioBuffer = await loadAudioFile(file, audioContextRef)
      const duration = audioBuffer.duration
      const blobUrl = await createBlobUrl(audioBuffer, audioBufferToWav)

      // Určit kategorii a barvu pro nahraný soubor
      const category = 'file'
      let newLayer = null

      setLayers(prevLayers => {
        const newLayerColor = getColorForNewLayer(prevLayers, category)

        newLayer = {
          id: `layer-${Date.now()}-${++layerIdCounterRef.current}-${Math.random().toString(36).substr(2, 9)}`,
          name: file.name,
          file: file,
          audioBuffer: audioBuffer,
          blobUrl: blobUrl,
          startTime: 0,
          duration: duration,
          volume: 1.0,
          fadeIn: 0,
          fadeOut: 0,
          trimStart: 0,
          trimEnd: duration,
          loop: false,
          loopAnchorTime: 0,
          category: category,
          color: newLayerColor
        }

        if (selectedLayerId === null) {
          setSelectedLayerId(newLayer.id)
        }
        return [...prevLayers, newLayer]
      })

      return newLayer
    } catch (err) {
      console.error('Chyba při načítání audio:', err)
      throw err
    }
  }, [loadAudioFile, createBlobUrl, selectedLayerId])

  // Přidání vrstvy z historie
  const addLayerFromHistory = useCallback(async (entry, audioContextRef, sourceNodesRef, gainNodesRef) => {
    try {
      const audioBuffer = await loadAudioFromUrl(entry.audio_url, audioContextRef)
      const duration = audioBuffer.duration

      const name = entry.filename || entry.audio_url.split('/').pop() || 'Audio z historie'
      const sourceInfo = entry.sourceLabel || ''

      // Určit kategorii z history entry
      const category = getCategoryFromHistoryEntry(entry)
      let newLayer = null

      setLayers(prevLayers => {
        const newLayerColor = getColorForNewLayer(prevLayers, category)

        newLayer = {
          id: `layer-${Date.now()}-${++layerIdCounterRef.current}-${Math.random().toString(36).substr(2, 9)}`,
          name: `${sourceInfo} - ${name}`,
          file: null,
          audioBuffer: audioBuffer,
          audioUrl: entry.audio_url,
          startTime: 0,
          duration: duration,
          volume: 1.0,
          fadeIn: 0,
          fadeOut: 0,
          trimStart: 0,
          trimEnd: duration,
          loop: false,
          loopAnchorTime: 0,
          historyEntry: entry,
          category: category,
          color: newLayerColor
        }

        setSelectedLayerId(prev => (prev === null ? newLayer.id : prev))
        return [...prevLayers, newLayer]
      })

      return newLayer
    } catch (err) {
      console.error('Chyba při načítání audio z historie:', err)
      throw err
    }
  }, [loadAudioFromUrl])

  // Aktualizace vrstvy
  const updateLayer = useCallback((layerId, updates) => {
    setLayers(prev =>
      prev.map(layer => {
        if (layer.id !== layerId) return layer

        const next = { ...layer, ...updates }

        // Validace fade in/out hodnot
        if (updates.fadeIn !== undefined || updates.fadeOut !== undefined) {
          const trimmedDuration = Math.max(0.01, (next.trimEnd || 0) - (next.trimStart || 0))
          const fadeIn = next.fadeIn || 0
          const fadeOut = next.fadeOut || 0

          if (fadeIn + fadeOut > trimmedDuration) {
            if (updates.fadeIn !== undefined) {
              next.fadeIn = Math.max(0, Math.min(trimmedDuration, fadeIn))
              next.fadeOut = Math.max(0, Math.min(trimmedDuration - next.fadeIn, fadeOut))
            } else if (updates.fadeOut !== undefined) {
              next.fadeOut = Math.max(0, Math.min(trimmedDuration, fadeOut))
              next.fadeIn = Math.max(0, Math.min(trimmedDuration - next.fadeOut, fadeIn))
            }
          } else {
            next.fadeIn = Math.max(0, Math.min(trimmedDuration, fadeIn))
            next.fadeOut = Math.max(0, Math.min(trimmedDuration, fadeOut))
          }
        }

        // Když zapínáme loop a není anchor nebo je 0, ukotvit na aktuální startTime
        if (updates.loop === true) {
          if (layer.loopAnchorTime === undefined || layer.loopAnchorTime === null || layer.loopAnchorTime === 0) {
            next.loopAnchorTime = layer.startTime
          }
        }

        return next
      })
    )
  }, [])

  // Smazání vrstvy
  const deleteLayer = useCallback((layerId, sourceNodesRef, gainNodesRef) => {
    setLayers(prevLayers => {
      const layer = prevLayers.find(l => l.id === layerId)
      if (!layer) return prevLayers

      // Zastavit přehrávání této vrstvy
      if (sourceNodesRef?.current?.[layerId]) {
        try {
          sourceNodesRef.current[layerId].stop()
        } catch (e) {}
        delete sourceNodesRef.current[layerId]
      }
      if (gainNodesRef?.current?.[layerId]) {
        delete gainNodesRef.current[layerId]
      }

      // Cleanup blob URL
      if (layer.blobUrl) {
        try {
          URL.revokeObjectURL(layer.blobUrl)
        } catch (e) {
          console.error('Chyba při revokování blob URL:', e)
        }
      }

      const newLayers = prevLayers.filter(l => l.id !== layerId)

      // Aktualizovat vybranou vrstvu
      if (selectedLayerId === layerId) {
        if (newLayers.length > 0) {
          setSelectedLayerId(newLayers[0].id)
        } else {
          setSelectedLayerId(null)
        }
      }

      return newLayers
    })
  }, [selectedLayerId])

  return {
    layers,
    setLayers,
    selectedLayerId,
    setSelectedLayerId,
    expandedLayerId,
    setExpandedLayerId,
    addLayer,
    addLayerFromHistory,
    updateLayer,
    deleteLayer,
    loadAudioFromUrl,
    loadAudioFile
  }
}

