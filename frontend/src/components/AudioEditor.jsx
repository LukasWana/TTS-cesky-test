import React, { useState, useRef, useEffect, useCallback } from 'react'
import WaveSurfer from 'wavesurfer.js'
import './AudioEditor.css'
import { getHistory, getMusicHistory, getBarkHistory } from '../services/api'

const API_BASE_URL = 'http://localhost:8000'
const STORAGE_KEY = 'audio_editor_state'
const PROJECTS_STORAGE_KEY = 'audio_editor_projects'

// Komponenta pro waveform náhled v klipu
function LayerWaveform({
  layerId,
  audioUrl,
  blobUrl,
  audioBuffer,
  trimStart = 0,
  trimEnd = 0,
  duration = 0,
  loop = false,
  startTime = 0,
  loopAnchorTime = null,
  onReady
}) {
  const waveformContainerRef = useRef(null)
  const wavesurferRef = useRef(null)

  const renderWaveformDataUrl = useCallback((buffer, tStart, tEnd) => {
    try {
      if (!buffer) return null
      const width = 300
      const height = 40
      const canvas = document.createElement('canvas')
      canvas.width = width
      canvas.height = height
      const ctx = canvas.getContext('2d')
      if (!ctx) return null

      ctx.clearRect(0, 0, width, height)
      ctx.fillStyle = 'rgba(255, 255, 255, 0.08)'
      ctx.fillRect(0, 0, width, height)

      const sr = buffer.sampleRate
      const ch0 = buffer.getChannelData(0)
      const ch1 = buffer.numberOfChannels > 1 ? buffer.getChannelData(1) : null

      const s0 = Math.max(0, Math.min(ch0.length - 1, Math.floor(tStart * sr)))
      const s1 = Math.max(s0 + 1, Math.min(ch0.length, Math.floor(tEnd * sr)))
      const sliceLen = s1 - s0
      const step = Math.max(1, Math.floor(sliceLen / width))

      ctx.strokeStyle = 'rgba(255, 255, 255, 0.45)'
      ctx.lineWidth = 1
      const mid = height / 2

      for (let x = 0; x < width; x++) {
        const start = s0 + (x * step)
        const end = Math.min(s1, start + step)
        let min = 1
        let max = -1
        for (let i = start; i < end; i++) {
          const v = ch1 ? (ch0[i] + ch1[i]) / 2 : ch0[i]
          if (v < min) min = v
          if (v > max) max = v
        }
        const y1 = mid - (max * mid)
        const y2 = mid - (min * mid)
        ctx.beginPath()
        ctx.moveTo(x + 0.5, y1)
        ctx.lineTo(x + 0.5, y2)
        ctx.stroke()
      }

      return canvas.toDataURL('image/png')
    } catch (e) {
      console.error('Chyba při renderu waveform dataURL:', e)
      return null
    }
  }, [])

  // Pokud je loop aktivní, vykresli opakující se pattern (i když je klip stejně dlouhý jako cyklus)
  const shouldUseRepeatWaveform = loop && audioBuffer && (trimEnd - trimStart) > 0.05
  const repeatWaveformUrl = shouldUseRepeatWaveform ? renderWaveformDataUrl(audioBuffer, trimStart, trimEnd) : null

  // Debug: zkontrolovat, proč se repeat waveform nezobrazuje
  if (loop && !audioBuffer) {
    console.warn('LayerWaveform: loop je true, ale audioBuffer není předán', { layerId, loop, hasAudioBuffer: !!audioBuffer })
  }
  if (loop && audioBuffer && (trimEnd - trimStart) <= 0.05) {
    console.warn('LayerWaveform: loop je true, ale trimEnd - trimStart je příliš malé', {
      layerId,
      trimStart,
      trimEnd,
      diff: trimEnd - trimStart
    })
  }

  if (shouldUseRepeatWaveform && repeatWaveformUrl) {
    const cycle = Math.max(0.05, (trimEnd - trimStart))
    const tilePercent = Math.max(1, (cycle / Math.max(duration, 0.001)) * 100)
    // Fáze: kde v cyklu jsme na levém okraji klipu (t = startTime)
    const anchor = loopAnchorTime ?? startTime
    const phaseSeconds = ((startTime - anchor) % cycle + cycle) % cycle
    const phasePercentOfTile = (phaseSeconds / cycle) * 100

    return (
      <div
        className="layer-waveform layer-waveform-repeat"
        style={{
          backgroundImage: `url(${repeatWaveformUrl})`,
          backgroundRepeat: 'repeat-x',
          backgroundSize: `${tilePercent}% 100%`,
          backgroundPositionX: `${-phasePercentOfTile}%`,
          backgroundPositionY: '0'
        }}
      />
    )
  }

  useEffect(() => {
    if (!waveformContainerRef.current) return

    const url = audioUrl || blobUrl
    if (!url) return

    try {
      let fullUrl = url
      if (url && !url.startsWith('http') && !url.startsWith('blob:')) {
        fullUrl = `${API_BASE_URL}${url.startsWith('/') ? url : '/' + url}`
      }

      const wavesurfer = WaveSurfer.create({
        container: waveformContainerRef.current,
        waveColor: 'rgba(255, 255, 255, 0.25)',
        progressColor: 'rgba(99, 102, 241, 0.5)',
        cursorColor: 'transparent',
        barWidth: 1,
        barRadius: 0.5,
        responsive: true,
        height: 40,
        normalize: true,
        interact: false,
        backend: 'WebAudio'
      })

      wavesurferRef.current = wavesurfer

      wavesurfer.load(fullUrl)
      wavesurfer.on('ready', () => {
        if (onReady) onReady(wavesurfer)
      })

      return () => {
        if (wavesurferRef.current) {
          try {
            // Zastavit načítání, pokud probíhá
            if (wavesurferRef.current.isLoading && wavesurferRef.current.cancelLoad) {
              try {
                wavesurferRef.current.cancelLoad()
              } catch (e) {
                // Ignorovat chyby při cancelLoad
              }
            }
            // destroy() může vracet promise, takže ošetříme obě možnosti
            const destroyResult = wavesurferRef.current.destroy()
            if (destroyResult && typeof destroyResult.catch === 'function') {
              destroyResult.catch((e) => {
                // Ignorovat AbortError a NotAllowedError při cleanup
                if (e.name !== 'AbortError' && e.name !== 'NotAllowedError') {
                  console.error('Chyba při cleanup WaveSurfer (promise):', e)
                }
              })
            }
          } catch (e) {
            // Ignorovat chyby při cleanup (AbortError je OK)
            if (e.name !== 'AbortError' && e.name !== 'NotAllowedError') {
              console.error('Chyba při cleanup WaveSurfer (sync):', e)
            }
          }
          wavesurferRef.current = null
        }
      }
    } catch (err) {
      console.error('Chyba při vytváření waveform:', err)
    }
  }, [layerId, audioUrl, blobUrl])

  return <div ref={waveformContainerRef} className="layer-waveform" />
}

function AudioEditor() {
  const [layers, setLayers] = useState([])
  const [selectedLayerId, setSelectedLayerId] = useState(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [masterVolume, setMasterVolume] = useState(1.0)
  const [masterLevel, setMasterLevel] = useState({ left: 0, right: 0 })
  const [playbackPosition, setPlaybackPosition] = useState(0)
  const [maxDuration, setMaxDuration] = useState(0)
  const [draggingClip, setDraggingClip] = useState(null)
  const [resizingClip, setResizingClip] = useState(null)
  const [historyType, setHistoryType] = useState('all') // 'all' | 'tts' | 'music' | 'bark'
  const [history, setHistory] = useState([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [showHistory, setShowHistory] = useState(true)
  const [savedProjects, setSavedProjects] = useState([])
  const [showSaveDialog, setShowSaveDialog] = useState(false)
  const [projectName, setProjectName] = useState('')
  const [currentProjectId, setCurrentProjectId] = useState(null)

  const audioContextRef = useRef(null)
  const masterGainNodeRef = useRef(null)
  const analyserNodeRef = useRef(null)
  const sourceNodesRef = useRef({})
  const gainNodesRef = useRef({}) // Uložení gain nodes pro každou vrstvu
  const animationFrameRef = useRef(null)
  const playbackStartTimeRef = useRef(0)
  const pausedTimeRef = useRef(0)
  const timelineRef = useRef(null)
  const dragStartXRef = useRef(0)
  const dragStartTimeRef = useRef(0)
  const isLoadingStateRef = useRef(false)
  const saveTimeoutRef = useRef(null)
  const layerIdCounterRef = useRef(0) // Counter pro unikátní ID

  // Načtení seznamu projektů
  useEffect(() => {
    try {
      const saved = localStorage.getItem(PROJECTS_STORAGE_KEY)
      if (saved) {
        setSavedProjects(JSON.parse(saved))
      }
    } catch (err) {
      console.error('Chyba při načítání projektů:', err)
    }
  }, [])

  // Načtení stavu z localStorage
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved) {
        isLoadingStateRef.current = true
        const state = JSON.parse(saved)

        if (state.masterVolume !== undefined) {
          setMasterVolume(state.masterVolume)
        }
        if (state.currentTime !== undefined) {
          setCurrentTime(state.currentTime)
          setPlaybackPosition(state.currentTime / Math.max(state.maxDuration || 10, 1))
        }
        if (state.selectedLayerId !== undefined) {
          setSelectedLayerId(state.selectedLayerId)
        }
        if (state.showHistory !== undefined) {
          setShowHistory(state.showHistory)
        }
        if (state.historyType !== undefined) {
          setHistoryType(state.historyType)
        }

        // Načtení vrstev - pouze metadata, audio se načte znovu
        if (state.layers && Array.isArray(state.layers)) {
          // Načíst vrstvy postupně
          state.layers.forEach(async (layerData) => {
            try {
              if (layerData.audioUrl) {
                // Vrstva z historie
                const audioBuffer = await loadAudioFromUrl(layerData.audioUrl)
                const newLayer = {
                  id: layerData.id || `layer-${Date.now()}-${++layerIdCounterRef.current}-${Math.random().toString(36).substr(2, 9)}`,
                  name: layerData.name,
                  file: null,
                  audioBuffer: audioBuffer,
                  audioUrl: layerData.audioUrl,
                  startTime: layerData.startTime || 0,
                  duration: layerData.duration || audioBuffer.duration,
                  volume: layerData.volume || 1.0,
                  fadeIn: layerData.fadeIn || 0,
                  fadeOut: layerData.fadeOut || 0,
                  trimStart: layerData.trimStart || 0,
                  trimEnd: layerData.trimEnd || audioBuffer.duration,
                  loop: layerData.loop || false,
                  loopAnchorTime: (layerData.loopAnchorTime !== undefined && layerData.loopAnchorTime !== null)
                    ? layerData.loopAnchorTime
                    : (layerData.startTime || 0),
                  historyEntry: layerData.historyEntry
                }
                setLayers(prev => {
                  // Kontrola duplicitních ID - pokud existuje, vygenerovat nové unikátní ID
                  let finalId = newLayer.id
                  let attempts = 0
                  while (prev.some(l => l.id === finalId) && attempts < 10) {
                    finalId = `layer-${Date.now()}-${++layerIdCounterRef.current}-${Math.random().toString(36).substr(2, 9)}`
                    attempts++
                  }
                  newLayer.id = finalId
                  return [...prev, newLayer]
                })
              }
            } catch (err) {
              console.error('Chyba při načítání vrstvy:', err)
            }
          })
        }

        setTimeout(() => {
          isLoadingStateRef.current = false
        }, 100)
      }
    } catch (err) {
      console.error('Chyba při načítání stavu:', err)
      isLoadingStateRef.current = false
    }
  }, [])

  // Ukládání stavu do localStorage
  useEffect(() => {
    if (isLoadingStateRef.current) return

    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current)
    }

    saveTimeoutRef.current = setTimeout(() => {
      try {
        const stateToSave = {
          layers: layers.map(layer => ({
            id: layer.id,
            name: layer.name,
            audioUrl: layer.audioUrl,
            startTime: layer.startTime,
            duration: layer.duration,
            volume: layer.volume,
            fadeIn: layer.fadeIn,
            fadeOut: layer.fadeOut,
            trimStart: layer.trimStart,
            trimEnd: layer.trimEnd,
            loop: layer.loop || false,
            loopAnchorTime: (layer.loopAnchorTime !== undefined && layer.loopAnchorTime !== null)
              ? layer.loopAnchorTime
              : layer.startTime,
            historyEntry: layer.historyEntry
          })),
          masterVolume,
          currentTime,
          selectedLayerId,
          showHistory,
          historyType,
          maxDuration
        }
        localStorage.setItem(STORAGE_KEY, JSON.stringify(stateToSave))
      } catch (err) {
        console.error('Chyba při ukládání stavu:', err)
      }
    }, 500)

    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current)
      }
    }
  }, [layers, masterVolume, currentTime, selectedLayerId, showHistory, historyType, maxDuration])

  // Inicializace AudioContext - pouze jednou při mountu
  useEffect(() => {
    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext
      audioContextRef.current = new AudioContext()
      masterGainNodeRef.current = audioContextRef.current.createGain()
      analyserNodeRef.current = audioContextRef.current.createAnalyser()
      analyserNodeRef.current.fftSize = 256

      masterGainNodeRef.current.connect(analyserNodeRef.current)
      analyserNodeRef.current.connect(audioContextRef.current.destination)

      return () => {
        // Cleanup při unmount
        if (animationFrameRef.current) {
          cancelAnimationFrame(animationFrameRef.current)
        }
        // Zastavit všechny zdroje
        Object.values(sourceNodesRef.current).forEach(node => {
          try {
            node.stop()
          } catch (e) {}
        })
        sourceNodesRef.current = {}
        // Zavřít AudioContext
        if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
          audioContextRef.current.close().catch(err => {
            console.error('Chyba při zavírání AudioContext:', err)
          })
        }
      }
    } catch (err) {
      console.error('Chyba při inicializaci AudioContext:', err)
    }
  }, []) // Prázdné dependency - pouze jednou při mountu

  // Aktualizace master level meter - samostatný efekt řízený isPlaying
  useEffect(() => {
    if (!analyserNodeRef.current) return

    const updateLevels = () => {
      if (analyserNodeRef.current && isPlaying) {
        const dataArray = new Uint8Array(analyserNodeRef.current.frequencyBinCount)
        analyserNodeRef.current.getByteTimeDomainData(dataArray)

        let sum = 0
        for (let i = 0; i < dataArray.length; i++) {
          const normalized = (dataArray[i] - 128) / 128
          sum += normalized * normalized
        }
        const rms = Math.sqrt(sum / dataArray.length)
        const level = Math.min(rms * 2, 1.0)

        setMasterLevel({ left: level, right: level })
        animationFrameRef.current = requestAnimationFrame(updateLevels)
      } else {
        setMasterLevel({ left: 0, right: 0 })
        if (animationFrameRef.current) {
          cancelAnimationFrame(animationFrameRef.current)
          animationFrameRef.current = null
        }
      }
    }

    if (isPlaying) {
      updateLevels()
    } else {
      setMasterLevel({ left: 0, right: 0 })
    }

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
        animationFrameRef.current = null
      }
    }
  }, [isPlaying])

  // Aktualizace master gain
  useEffect(() => {
    if (masterGainNodeRef.current) {
      masterGainNodeRef.current.gain.value = masterVolume
    }
  }, [masterVolume])

  // Výpočet maximální délky
  useEffect(() => {
    const max = layers.reduce((max, layer) => {
      const endTime = layer.startTime + layer.duration
      return Math.max(max, endTime)
    }, 0)
    setMaxDuration(Math.max(max, 10)) // Minimálně 10 sekund
  }, [layers])

  // Aktualizace pozice přehrávání
  useEffect(() => {
    if (isPlaying) {
      const interval = setInterval(() => {
        const elapsed = (Date.now() - playbackStartTimeRef.current) / 1000 + pausedTimeRef.current
        setCurrentTime(Math.min(elapsed, maxDuration))
        setPlaybackPosition(Math.min(elapsed / maxDuration, 1))

        if (elapsed >= maxDuration) {
          handleStop()
        }
      }, 50)
      return () => clearInterval(interval)
    }
  }, [isPlaying, maxDuration])

  // Načtení historie
  useEffect(() => {
    if (showHistory) {
      loadHistory()
    }
  }, [historyType, showHistory])

  const loadHistory = async () => {
    try {
      setHistoryLoading(true)
      let allHistory = []

      if (historyType === 'all' || historyType === 'tts') {
        try {
          const ttsData = await getHistory(100, 0)
          const ttsEntries = (ttsData.history || []).map(entry => ({
            ...entry,
            source: 'tts',
            sourceLabel: '🎤 mluvené slovo'
          }))
          allHistory = [...allHistory, ...ttsEntries]
        } catch (err) {
          console.error('Chyba při načítání TTS historie:', err)
        }
      }

      if (historyType === 'all' || historyType === 'music') {
        try {
          const musicData = await getMusicHistory(100, 0)
          const musicEntries = (musicData.history || []).map(entry => ({
            ...entry,
            source: 'music',
            sourceLabel: '🎵 hudba'
          }))
          allHistory = [...allHistory, ...musicEntries]
        } catch (err) {
          console.error('Chyba při načítání MusicGen historie:', err)
        }
      }

      if (historyType === 'all' || historyType === 'bark') {
        try {
          const barkData = await getBarkHistory(100, 0)
          const barkEntries = (barkData.history || []).map(entry => ({
            ...entry,
            source: 'bark',
            sourceLabel: '🔊 FX & English'
          }))
          allHistory = [...allHistory, ...barkEntries]
        } catch (err) {
          console.error('Chyba při načítání Bark historie:', err)
        }
      }

      // Seřadit podle data (nejnovější první)
      allHistory.sort((a, b) => {
        const dateA = new Date(a.created_at || 0)
        const dateB = new Date(b.created_at || 0)
        return dateB - dateA
      })

      setHistory(allHistory)
    } catch (err) {
      console.error('Chyba při načítání historie:', err)
    } finally {
      setHistoryLoading(false)
    }
  }

  // Načtení audio souboru z URL
  const loadAudioFromUrl = async (audioUrl) => {
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
      if (!audioContextRef.current) {
        throw new Error('AudioContext není inicializován')
      }

      const audioBuffer = await audioContextRef.current.decodeAudioData(arrayBuffer)
      return audioBuffer
    } catch (err) {
      console.error('Chyba při načítání audio z URL:', err, audioUrl)
      throw err
    }
  }

  // Načtení audio souboru
  const loadAudioFile = async (file) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = async (e) => {
        try {
          const arrayBuffer = e.target.result
          const audioBuffer = await audioContextRef.current.decodeAudioData(arrayBuffer)
          resolve(audioBuffer)
        } catch (err) {
          reject(err)
        }
      }
      reader.onerror = reject
      reader.readAsArrayBuffer(file)
    })
  }

  // Vytvoření blob URL z AudioBuffer
  const createBlobUrl = async (audioBuffer) => {
    try {
      const wav = await audioBufferToWav(audioBuffer)
      const blob = new Blob([wav], { type: 'audio/wav' })
      return URL.createObjectURL(blob)
    } catch (err) {
      console.error('Chyba při vytváření blob URL:', err)
      return null
    }
  }

  // Pomocná funkce pro převod AudioBuffer na WAV
  const audioBufferToWav = async (buffer) => {
    const length = buffer.length
    const numberOfChannels = buffer.numberOfChannels
    const sampleRate = buffer.sampleRate
    const bytesPerSample = 2
    const blockAlign = numberOfChannels * bytesPerSample
    const byteRate = sampleRate * blockAlign
    const dataLength = length * blockAlign
    const buffer2 = new ArrayBuffer(44 + dataLength)
    const view = new DataView(buffer2)

    // WAV header
    const writeString = (offset, string) => {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i))
      }
    }

    writeString(0, 'RIFF')
    view.setUint32(4, 36 + dataLength, true)
    writeString(8, 'WAVE')
    writeString(12, 'fmt ')
    view.setUint32(16, 16, true)
    view.setUint16(20, 1, true)
    view.setUint16(22, numberOfChannels, true)
    view.setUint32(24, sampleRate, true)
    view.setUint32(28, byteRate, true)
    view.setUint16(32, blockAlign, true)
    view.setUint16(34, 16, true)
    writeString(36, 'data')
    view.setUint32(40, dataLength, true)

    // Audio data
    let offset = 44
    for (let i = 0; i < length; i++) {
      for (let channel = 0; channel < numberOfChannels; channel++) {
        const sample = Math.max(-1, Math.min(1, buffer.getChannelData(channel)[i]))
        view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true)
        offset += 2
      }
    }

    return buffer2
  }

  // Přidání nové vrstvy z historie
  const addLayerFromHistory = async (entry) => {
    try {
      const audioBuffer = await loadAudioFromUrl(entry.audio_url)
      const duration = audioBuffer.duration

      const name = entry.filename || entry.audio_url.split('/').pop() || 'Audio z historie'
      const sourceInfo = entry.sourceLabel || ''

      const newLayer = {
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
        loop: false, // Loopování zvuku
        loopAnchorTime: 0,
        historyEntry: entry
      }

      setLayers(prevLayers => [...prevLayers, newLayer])
      if (selectedLayerId === null) {
        setSelectedLayerId(newLayer.id)
      }
    } catch (err) {
      console.error('Chyba při načítání audio z historie:', err)
      alert('Chyba při načítání audio souboru z historie')
    }
  }

  // Přidání nové vrstvy
  const addLayer = async (file) => {
    try {
      const audioBuffer = await loadAudioFile(file)
      const duration = audioBuffer.duration

      // Vytvořit blob URL pro WaveSurfer
      const blobUrl = await createBlobUrl(audioBuffer)

      const newLayer = {
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
        loop: false, // Loopování zvuku
        loopAnchorTime: 0
      }

      setLayers(prevLayers => [...prevLayers, newLayer])
      if (selectedLayerId === null) {
        setSelectedLayerId(newLayer.id)
      }
    } catch (err) {
      console.error('Chyba při načítání audio:', err)
      alert('Chyba při načítání audio souboru')
    }
  }

  // Drag and drop
  const [isDragging, setIsDragging] = useState(false)

  const handleDragOver = (e) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = async (e) => {
    e.preventDefault()
    setIsDragging(false)

    const files = Array.from(e.dataTransfer.files).filter(file =>
      file.type.startsWith('audio/')
    )

    for (const file of files) {
      await addLayer(file)
    }
  }

  // File input
  const fileInputRef = useRef(null)
  const handleFileSelect = async (e) => {
    const files = Array.from(e.target.files).filter(file =>
      file.type.startsWith('audio/')
    )

    for (const file of files) {
      await addLayer(file)
    }

    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  // Aktualizace vrstvy
  const updateLayer = (layerId, updates) => {
    setLayers(prev =>
      prev.map(layer => {
        if (layer.id !== layerId) return layer

        const next = { ...layer, ...updates }

        // Když zapínáme loop a není anchor nebo je 0, ukotvit na aktuální startTime
        if (updates.loop === true) {
          // Pokud loopAnchorTime není nastavený nebo je 0 (což je default hodnota), nastavit na startTime
          if (layer.loopAnchorTime === undefined || layer.loopAnchorTime === null || layer.loopAnchorTime === 0) {
            next.loopAnchorTime = layer.startTime
          }
        }
        // Když vypínáme loop, můžeme nechat anchor (pro případné znovu zapnutí)

        return next
      })
    )
  }

  // Smazání vrstvy
  const deleteLayer = (layerId) => {
    setLayers(prevLayers => {
      const layer = prevLayers.find(l => l.id === layerId)
      if (!layer) return prevLayers

      // Zastavit přehrávání této vrstvy PRVNÍ
      if (sourceNodesRef.current[layerId]) {
        try {
          sourceNodesRef.current[layerId].stop()
        } catch (e) {}
        delete sourceNodesRef.current[layerId]
      }
      if (gainNodesRef.current[layerId]) {
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

      // Vrátit nový seznam bez smazané vrstvy
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
  }

  // Drag klipu na časové ose
  const handleClipMouseDown = (e, layerId, isLeftHandle = false, isRightHandle = false) => {
    e.stopPropagation()
    const layer = layers.find(l => l.id === layerId)
    if (!layer) return

    let isResizing = false
    let isDragging = false
    let isExtending = false // Prodlužování vrstvy z obou stran

    if (isLeftHandle || isRightHandle) {
      // Shift + handle = prodlužování, bez Shift = trim
      if (e.shiftKey) {
        isExtending = true
        setResizingClip({ layerId, isLeft: isLeftHandle, isRight: isRightHandle, extending: true })
      } else {
        isResizing = true
        setResizingClip({ layerId, isLeft: isLeftHandle, isRight: isRightHandle })
      }
    } else {
      isDragging = true
      setDraggingClip(layerId)
    }

    dragStartXRef.current = e.clientX
    dragStartTimeRef.current = layer.startTime
    const initialStartTime = layer.startTime
    const initialTrimStart = layer.trimStart
    const initialTrimEnd = layer.trimEnd
    const initialDuration = layer.duration
    const initialLoopAnchorTime = layer.loopAnchorTime ?? layer.startTime
    const trimmedDuration = initialTrimEnd - initialTrimStart

    const handleMouseMove = (e) => {
      if (!timelineRef.current) return

      const rect = timelineRef.current.getBoundingClientRect()
      const x = e.clientX - rect.left
      const percent = Math.max(0, Math.min(1, x / rect.width))
      const newTime = percent * maxDuration

      if (isDragging) {
        const newStartTime = Math.max(0, newTime)
        const delta = newStartTime - initialStartTime
        const updates = { startTime: newStartTime }
        if (layer.loop) {
          updates.loopAnchorTime = initialLoopAnchorTime + delta
        }
        updateLayer(layerId, updates)
      } else if (isExtending) {
        // Prodlužování vrstvy z obou stran (Shift + drag handle)
        if (isLeftHandle) {
          // Prodlužování zleva - posunout startTime doleva, duration se zvětší
          const timeDiff = newTime - initialStartTime
          const newStartTime = Math.max(0, initialStartTime + timeDiff)
          const newDuration = initialDuration - timeDiff
          updateLayer(layerId, {
            startTime: newStartTime,
            duration: Math.max(trimmedDuration, newDuration),
            // Anchor necháváme fixní => loop se "doplní" zleva (wrap)
            loopAnchorTime: initialLoopAnchorTime
          })
        } else if (isRightHandle) {
          // Prodlužování zprava - zvětšit duration
          const timeDiff = newTime - (initialStartTime + initialDuration)
          const newDuration = initialDuration + timeDiff
          updateLayer(layerId, {
            duration: Math.max(trimmedDuration, newDuration),
            loopAnchorTime: initialLoopAnchorTime
          })
        }
      } else if (isResizing) {
        // Trim (bez Shift)
        if (isLeftHandle) {
          const relativeTime = newTime - initialStartTime
          const newTrimStart = Math.max(0, Math.min(initialTrimEnd - 0.1, relativeTime))
          const trimDiff = initialTrimStart - newTrimStart
          const newStartTime = initialStartTime - trimDiff
          const newDuration = initialDuration + trimDiff
          updateLayer(layerId, {
            trimStart: newTrimStart,
            startTime: Math.max(0, newStartTime),
            duration: Math.max(0.1, newDuration)
          })
        } else if (isRightHandle) {
          const relativeTime = newTime - initialStartTime
          const newTrimEnd = Math.max(initialTrimStart + 0.1, Math.min(layer.audioBuffer.duration, relativeTime))
          const newDuration = newTrimEnd - initialTrimStart
          updateLayer(layerId, {
            trimEnd: newTrimEnd,
            duration: Math.max(0.1, newDuration)
          })
        }
      }
    }

    const handleMouseUp = () => {
      setDraggingClip(null)
      setResizingClip(null)
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }

  // Kliknutí na časovou osu pro přesun playheadu
  const handleTimelineClick = (e) => {
    if (!timelineRef.current) return
    const rect = timelineRef.current.getBoundingClientRect()
    const x = e.clientX - rect.left
    const percent = Math.max(0, Math.min(1, x / rect.width))
    const newTime = percent * maxDuration
    setCurrentTime(newTime)
    setPlaybackPosition(percent)
    pausedTimeRef.current = newTime
    if (isPlaying) {
      handleStop()
    }
  }

  // Playback
  const handlePlay = async () => {
    if (audioContextRef.current.state === 'suspended') {
      await audioContextRef.current.resume()
    }

    if (layers.length === 0) return

    // Zastavit všechny existující zdroje
    stopAllSources()

    const now = audioContextRef.current.currentTime
    const mod = (n, m) => ((n % m) + m) % m

    // Vytvořit nové zdroje pro každou vrstvu - všechny vrstvy, které se mají přehrávat
    layers.forEach(layer => {
      const layerStartTime = layer.startTime
      const layerEndTime = layerStartTime + layer.duration

      // Pokud je aktuální čas před začátkem vrstvy, naplánovat přehrávání s delay
      if (currentTime < layerStartTime) {
        const delay = layerStartTime - currentTime
        const trimStart = Math.max(0, Math.min(layer.trimStart, layer.audioBuffer.duration))
        const trimEnd = Math.max(trimStart + 0.1, Math.min(layer.trimEnd, layer.audioBuffer.duration))
        const trimmedDuration = trimEnd - trimStart

        // Přeskočit, pokud není co přehrávat
        if (trimmedDuration <= 0 || trimStart >= layer.audioBuffer.duration) {
          return
        }

        const playDuration = layer.duration
        const fadeInDuration = Math.min(layer.fadeIn, trimmedDuration)
        const fadeOutDuration = Math.min(layer.fadeOut, trimmedDuration)

        // Pokud je loop zapnutý, použít nativní loop na jednom zdroji
        if (layer.loop) {
          const source = audioContextRef.current.createBufferSource()
          const gainNode = audioContextRef.current.createGain()

          source.buffer = layer.audioBuffer
          source.loop = true
          source.loopStart = trimStart
          source.loopEnd = trimEnd

          source.connect(gainNode)
          gainNode.connect(masterGainNodeRef.current)

          const startAt = now + delay
          const durationToPlay = Math.max(0, playDuration)
          const cycle = Math.max(0.05, (trimEnd - trimStart))
          const anchor = (layer.loopAnchorTime !== undefined && layer.loopAnchorTime !== null)
            ? layer.loopAnchorTime
            : layer.startTime
          const offsetInCycle = mod(layerStartTime - anchor, cycle)
          const audioOffset = Math.max(trimStart, Math.min(trimStart + offsetInCycle, trimEnd))

          // Debug log pro loop playback
          console.log('Loop playback (future):', {
            layerId: layer.id,
            layerName: layer.name,
            loop: layer.loop,
            loopStart: trimStart,
            loopEnd: trimEnd,
            loopAnchorTime: layer.loopAnchorTime,
            anchor: anchor,
            layerStartTime: layerStartTime,
            cycle: cycle,
            offsetInCycle: offsetInCycle,
            audioOffset: audioOffset,
            durationToPlay: durationToPlay
          })

          // Gain + fade in/out
          gainNode.gain.setValueAtTime(0, startAt)
          if (fadeInDuration > 0) {
            gainNode.gain.linearRampToValueAtTime(layer.volume, startAt + Math.min(fadeInDuration, durationToPlay))
          } else {
            gainNode.gain.setValueAtTime(layer.volume, startAt)
          }
          if (fadeOutDuration > 0 && durationToPlay > fadeOutDuration) {
            const fadeOutStart = durationToPlay - fadeOutDuration
            gainNode.gain.setValueAtTime(layer.volume, startAt + fadeOutStart)
            gainNode.gain.linearRampToValueAtTime(0, startAt + durationToPlay)
          }

          try {
            if (durationToPlay > 0) {
              // Pro loop: start bez stop, stop se zavolá až když vrstva končí
              source.start(startAt, audioOffset)
              // Stop se zavolá až když vrstva končí (ne okamžitě)
              source.stop(startAt + durationToPlay)
              sourceNodesRef.current[layer.id] = source
              gainNodesRef.current[layer.id] = gainNode
            }
          } catch (err) {
            console.error('Chyba při startování loop audio zdroje:', err)
          }
        } else {
          // Bez loopu - normální přehrávání
          const source = audioContextRef.current.createBufferSource()
          const gainNode = audioContextRef.current.createGain()

          source.buffer = layer.audioBuffer
          source.connect(gainNode)
          gainNode.connect(masterGainNodeRef.current)

          // Nastavit hlasitost s fade in
          gainNode.gain.setValueAtTime(0, now + delay)
          if (fadeInDuration > 0) {
            gainNode.gain.linearRampToValueAtTime(layer.volume, now + delay + fadeInDuration)
          } else {
            gainNode.gain.setValueAtTime(layer.volume, now + delay)
          }

          // Nastavit fade out
          if (fadeOutDuration > 0 && trimmedDuration > fadeOutDuration) {
            const fadeOutStart = trimmedDuration - fadeOutDuration
            gainNode.gain.setValueAtTime(layer.volume, now + delay + fadeOutStart)
            gainNode.gain.linearRampToValueAtTime(0, now + delay + trimmedDuration)
          }

          try {
            source.start(now + delay, trimStart, trimmedDuration)
            sourceNodesRef.current[layer.id] = source
            gainNodesRef.current[layer.id] = gainNode
          } catch (err) {
            console.error('Chyba při startování audio zdroje:', err)
          }
        }
        return
      }

      // Pokud je aktuální čas po konci vrstvy, přeskočit
      if (currentTime >= layerEndTime) {
        return
      }

      // Vrstva se právě přehrává nebo už běží - přehrát od aktuální pozice
      const trimStart = Math.max(0, Math.min(layer.trimStart, layer.audioBuffer.duration))
      const trimEnd = Math.max(trimStart + 0.1, Math.min(layer.trimEnd, layer.audioBuffer.duration))
      const trimmedDuration = trimEnd - trimStart
      const layerTimeOffset = currentTime - layerStartTime
      const remainingLayerTime = layerEndTime - currentTime

      // Pokud je loop zapnutý, přehrát opakovaně
      if (layer.loop) {
        const source = audioContextRef.current.createBufferSource()
        const gainNode = audioContextRef.current.createGain()

        source.buffer = layer.audioBuffer
        source.loop = true
        source.loopStart = trimStart
        source.loopEnd = trimEnd

        source.connect(gainNode)
        gainNode.connect(masterGainNodeRef.current)

        // Když spouštíme uprostřed vrstvy, offset je posunutý v rámci cyklu podle anchoru
        const cycle = Math.max(0.05, trimmedDuration)
        const anchor = (layer.loopAnchorTime !== undefined && layer.loopAnchorTime !== null)
          ? layer.loopAnchorTime
          : layer.startTime
        const offsetInCycle = mod(currentTime - anchor, cycle)
        const audioOffset = Math.max(trimStart, Math.min(trimStart + offsetInCycle, trimEnd))
        const durationToPlay = Math.max(0, remainingLayerTime)

        // Debug log pro loop playback
        console.log('Loop playback (current):', {
          layerId: layer.id,
          layerName: layer.name,
          loop: layer.loop,
          loopStart: trimStart,
          loopEnd: trimEnd,
          loopAnchorTime: layer.loopAnchorTime,
          anchor: anchor,
          currentTime: currentTime,
          cycle: cycle,
          offsetInCycle: offsetInCycle,
          audioOffset: audioOffset,
          durationToPlay: durationToPlay
        })

        // Přeskočit, pokud není co přehrávat
        if (durationToPlay <= 0) return

        // Gain + fade in/out (globálně vůči vrstvě)
        const fadeInDuration = Math.min(layer.fadeIn, layer.duration)
        const fadeOutDuration = Math.min(layer.fadeOut, layer.duration)

        // Pokud už jsme ve fade-in, nastavíme počáteční hlasitost podle progressu
        const fadeInProgress = fadeInDuration > 0 ? Math.min(layerTimeOffset / fadeInDuration, 1) : 1
        gainNode.gain.setValueAtTime(layer.volume * fadeInProgress, now)
        if (fadeInDuration > 0 && layerTimeOffset < fadeInDuration) {
          gainNode.gain.linearRampToValueAtTime(layer.volume, now + (fadeInDuration - layerTimeOffset))
        }

        // Fade-out v čase konce vrstvy
        if (fadeOutDuration > 0 && durationToPlay > fadeOutDuration) {
          const fadeOutStart = durationToPlay - fadeOutDuration
          gainNode.gain.setValueAtTime(layer.volume, now + fadeOutStart)
          gainNode.gain.linearRampToValueAtTime(0, now + durationToPlay)
        }

        try {
          // Pro loop: start bez stop, stop se zavolá až když vrstva končí
          source.start(now, audioOffset)
          // Stop se zavolá až když vrstva končí (ne okamžitě)
          source.stop(now + durationToPlay)
          sourceNodesRef.current[layer.id] = source
          gainNodesRef.current[layer.id] = gainNode
        } catch (err) {
          console.error('Chyba při startování loop audio zdroje:', err)
        }
      } else {
        // Bez loopu - normální přehrávání
        const source = audioContextRef.current.createBufferSource()
        const gainNode = audioContextRef.current.createGain()

        source.buffer = layer.audioBuffer
        source.connect(gainNode)
        gainNode.connect(masterGainNodeRef.current)

        const audioOffset = Math.max(trimStart, Math.min(trimStart + layerTimeOffset, trimEnd))
        const remainingDuration = Math.max(0, Math.min(trimmedDuration - layerTimeOffset, remainingLayerTime))

        // Přeskočit, pokud není co přehrávat
        if (remainingDuration <= 0 || audioOffset >= trimEnd || audioOffset < trimStart) {
          return
        }

        // Aplikovat fade in/out s validací
        const fadeInDuration = Math.min(layer.fadeIn, trimmedDuration)
        const fadeOutDuration = Math.min(layer.fadeOut, trimmedDuration)

        // Nastavit hlasitost podle fade in progress
        const fadeInProgress = fadeInDuration > 0
          ? Math.min(layerTimeOffset / fadeInDuration, 1)
          : 1
        const initialVolume = layer.volume * fadeInProgress

        gainNode.gain.setValueAtTime(initialVolume, now)

        // Dokončit fade in, pokud ještě probíhá
        if (fadeInDuration > 0 && layerTimeOffset < fadeInDuration) {
          const fadeInRemaining = fadeInDuration - layerTimeOffset
          gainNode.gain.linearRampToValueAtTime(layer.volume, now + fadeInRemaining)
        }

        // Fade out
        if (fadeOutDuration > 0 && remainingDuration > fadeOutDuration) {
          const fadeOutStart = remainingDuration - fadeOutDuration
          gainNode.gain.setValueAtTime(layer.volume, now + fadeOutStart)
          gainNode.gain.linearRampToValueAtTime(0, now + remainingDuration)
        }

        try {
          source.start(now, audioOffset, remainingDuration)
          sourceNodesRef.current[layer.id] = source
          gainNodesRef.current[layer.id] = gainNode
        } catch (err) {
          console.error('Chyba při startování audio zdroje:', err)
        }
      }
    })

    playbackStartTimeRef.current = Date.now()
    pausedTimeRef.current = currentTime
    setIsPlaying(true)
  }

  // Jednotná funkce pro zastavení všech zdrojů
  const stopAllSources = () => {
    Object.values(sourceNodesRef.current).forEach(node => {
      try {
        node.stop()
      } catch (e) {}
    })
    sourceNodesRef.current = {}
    gainNodesRef.current = {}
  }

  const handleStop = () => {
    stopAllSources()
    setIsPlaying(false)
    setCurrentTime(0)
    setPlaybackPosition(0)
    pausedTimeRef.current = 0
  }

  const handlePause = () => {
    stopAllSources()
    pausedTimeRef.current = currentTime
    setIsPlaying(false)
  }

  const handleSeekToStart = () => {
    handleStop()
    setCurrentTime(0)
    setPlaybackPosition(0)
  }

  const handleSeekToEnd = () => {
    handleStop()
    setCurrentTime(maxDuration)
    setPlaybackPosition(1)
  }

  // Formátování času
  const formatTime = (time) => {
    const minutes = Math.floor(time / 60)
    const seconds = Math.floor(time % 60)
    return `${minutes}:${seconds.toString().padStart(2, '0')}`
  }

  // Nový projekt
  const handleNewProject = () => {
    setLayers(prevLayers => {
      if (prevLayers.length > 0 && !window.confirm('Opravdu chcete vytvořit nový projekt? Všechny vrstvy budou smazány.')) {
        return prevLayers
      }

      // Zastavit přehrávání
      stopAllSources()
      setIsPlaying(false)

      // Vymazat všechny vrstvy a cleanup blob URLs
      prevLayers.forEach(layer => {
        if (layer.blobUrl) {
          try {
            URL.revokeObjectURL(layer.blobUrl)
          } catch (e) {
            console.error('Chyba při revokování blob URL:', e)
          }
        }
        // Zastavit přehrávání každé vrstvy
        if (sourceNodesRef.current[layer.id]) {
          try {
            sourceNodesRef.current[layer.id].stop()
          } catch (e) {}
          delete sourceNodesRef.current[layer.id]
        }
        if (gainNodesRef.current[layer.id]) {
          delete gainNodesRef.current[layer.id]
        }
      })

      // Vyčistit všechny source nodes
      sourceNodesRef.current = {}
      gainNodesRef.current = {}

      // Reset stavů
      setSelectedLayerId(null)
      setCurrentTime(0)
      setPlaybackPosition(0)
      setCurrentProjectId(null)
      setProjectName('')

      return []
    })
  }

  // Uložit projekt
  const handleSaveProject = () => {
    if (layers.length === 0) {
      alert('Nelze uložit prázdný projekt')
      return
    }

    setShowSaveDialog(true)
  }

  // Potvrdit uložení projektu
  const confirmSaveProject = () => {
    const name = projectName.trim() || `Projekt ${new Date().toLocaleString('cs-CZ')}`

    const projectData = {
      id: currentProjectId || Date.now().toString(),
      name: name,
      createdAt: currentProjectId ? savedProjects.find(p => p.id === currentProjectId)?.createdAt : new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      layers: layers.map(layer => ({
        id: layer.id,
        name: layer.name,
        audioUrl: layer.audioUrl,
        startTime: layer.startTime,
        duration: layer.duration,
        volume: layer.volume,
        fadeIn: layer.fadeIn,
        fadeOut: layer.fadeOut,
        trimStart: layer.trimStart,
        trimEnd: layer.trimEnd,
        loop: layer.loop || false,
        loopAnchorTime: (layer.loopAnchorTime !== undefined && layer.loopAnchorTime !== null)
          ? layer.loopAnchorTime
          : layer.startTime,
        historyEntry: layer.historyEntry
      })),
      masterVolume,
      currentTime: 0, // Uložit na začátek
      selectedLayerId: null
    }

    try {
      let projects = [...savedProjects]
      if (currentProjectId) {
        // Aktualizovat existující projekt
        const index = projects.findIndex(p => p.id === currentProjectId)
        if (index !== -1) {
          projects[index] = projectData
        }
      } else {
        // Nový projekt
        projects.push(projectData)
      }

      localStorage.setItem(PROJECTS_STORAGE_KEY, JSON.stringify(projects))
      setSavedProjects(projects)
      setCurrentProjectId(projectData.id)
      setShowSaveDialog(false)
      setProjectName('')
      alert(`Projekt "${name}" byl uložen`)
    } catch (err) {
      console.error('Chyba při ukládání projektu:', err)
      alert('Chyba při ukládání projektu')
    }
  }

  // Načíst projekt
  const handleLoadProject = async (projectId) => {
    const project = savedProjects.find(p => p.id === projectId)
    if (!project) return

    if (layers.length > 0 && !window.confirm('Opravdu chcete načíst projekt? Aktuální vrstvy budou smazány.')) {
      return
    }

    // Zastavit přehrávání
    stopAllSources()
    setIsPlaying(false)

    // Vymazat všechny vrstvy
    layers.forEach(layer => {
      if (layer.blobUrl) {
        URL.revokeObjectURL(layer.blobUrl)
      }
    })

    setLayers([])
    setSelectedLayerId(null)
    setCurrentTime(0)
    setPlaybackPosition(0)
    setMasterVolume(project.masterVolume || 1.0)
    setCurrentProjectId(project.id)
    setProjectName(project.name)

    // Načíst vrstvy
    if (project.layers && Array.isArray(project.layers)) {
      for (const layerData of project.layers) {
        try {
          if (layerData.audioUrl) {
            const audioBuffer = await loadAudioFromUrl(layerData.audioUrl)
            const newLayer = {
              id: layerData.id || `layer-${Date.now()}-${++layerIdCounterRef.current}-${Math.random().toString(36).substr(2, 9)}`,
              name: layerData.name,
              file: null,
              audioBuffer: audioBuffer,
              audioUrl: layerData.audioUrl,
              startTime: layerData.startTime || 0,
              duration: layerData.duration || audioBuffer.duration,
              volume: layerData.volume || 1.0,
              fadeIn: layerData.fadeIn || 0,
              fadeOut: layerData.fadeOut || 0,
              trimStart: layerData.trimStart || 0,
              trimEnd: layerData.trimEnd || audioBuffer.duration,
              loop: layerData.loop || false,
              loopAnchorTime: layerData.loopAnchorTime ?? (layerData.startTime || 0),
              historyEntry: layerData.historyEntry
            }
            setLayers(prev => {
              // Kontrola duplicitních ID
              if (prev.some(l => l.id === newLayer.id)) {
                newLayer.id = `layer-${Date.now()}-${++layerIdCounterRef.current}-${Math.random().toString(36).substr(2, 9)}`
              }
              return [...prev, newLayer]
            })
          }
        } catch (err) {
          console.error('Chyba při načítání vrstvy z projektu:', err)
        }
      }
    }
  }

  // Smazat projekt
  const handleDeleteProject = (projectId, e) => {
    e.stopPropagation()
    const project = savedProjects.find(p => p.id === projectId)
    if (!project) return

    if (!window.confirm(`Opravdu chcete smazat projekt "${project.name}"?`)) {
      return
    }

    try {
      const projects = savedProjects.filter(p => p.id !== projectId)
      localStorage.setItem(PROJECTS_STORAGE_KEY, JSON.stringify(projects))
      setSavedProjects(projects)

      if (currentProjectId === projectId) {
        setCurrentProjectId(null)
        setProjectName('')
      }
    } catch (err) {
      console.error('Chyba při mazání projektu:', err)
      alert('Chyba při mazání projektu')
    }
  }

  const selectedLayer = layers.find(l => l.id === selectedLayerId)

  return (
    <div className="audio-editor">
      <div className="audio-editor-header">
        <div className="header-top">
          <div>
            <h2>🎚️ Audio Editor - Kompozice ve vrstvách</h2>
            <p className="audio-editor-hint">
              Přetáhněte audio soubory nebo klikněte pro výběr. Upravujte vrstvy, mixujte a exportujte výsledek.
            </p>
          </div>
          <div className="project-controls">
            <button
              className="btn-project btn-new"
              onClick={handleNewProject}
              title="Nový projekt"
            >
              📄 Nový projekt
            </button>
            <button
              className="btn-project btn-save"
              onClick={handleSaveProject}
              title="Uložit projekt"
            >
              💾 {currentProjectId ? 'Uložit změny' : 'Uložit projekt'}
            </button>
            <button
              className="btn-project btn-reset"
              onClick={() => {
                if (window.confirm('Opravdu chcete kompletně resetovat editor? Vymaže se vše včetně uložených projektů a localStorage.')) {
                  // Vymazat localStorage
                  localStorage.removeItem(STORAGE_KEY)
                  localStorage.removeItem(PROJECTS_STORAGE_KEY)
                  // Zastavit přehrávání
                  stopAllSources()
                  setIsPlaying(false)
                  // Vymazat všechny vrstvy
                  layers.forEach(layer => {
                    if (layer.blobUrl) {
                      URL.revokeObjectURL(layer.blobUrl)
                    }
                  })
                  // Reset všech stavů
                  setLayers([])
                  setSelectedLayerId(null)
                  setCurrentTime(0)
                  setPlaybackPosition(0)
                  setCurrentProjectId(null)
                  setProjectName('')
                  setSavedProjects([])
                  alert('Editor byl kompletně resetován. Stránka se obnoví.')
                  window.location.reload()
                }
              }}
              title="Kompletní reset editoru"
            >
              🔄 Reset všeho
            </button>
            {currentProjectId && (
              <span className="current-project-name">
                {projectName || 'Bez názvu'}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Save Dialog */}
      {showSaveDialog && (
        <div className="modal-overlay" onClick={() => setShowSaveDialog(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>{currentProjectId ? 'Uložit změny projektu' : 'Uložit nový projekt'}</h3>
            <div className="modal-form">
              <label>
                Název projektu:
                <input
                  type="text"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  placeholder="Zadejte název projektu"
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      confirmSaveProject()
                    } else if (e.key === 'Escape') {
                      setShowSaveDialog(false)
                    }
                  }}
                />
              </label>
              <div className="modal-buttons">
                <button className="btn-primary" onClick={confirmSaveProject}>
                  Uložit
                </button>
                <button className="btn-secondary" onClick={() => setShowSaveDialog(false)}>
                  Zrušit
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Saved Projects Panel */}
      {savedProjects.length > 0 && (
        <div className="projects-panel">
          <h3>📁 Uložené projekty</h3>
          <div className="projects-list">
            {savedProjects.map((project) => (
              <div
                key={project.id}
                className={`project-item ${currentProjectId === project.id ? 'active' : ''}`}
                onClick={() => handleLoadProject(project.id)}
              >
                <div className="project-item-header">
                  <span className="project-item-name">{project.name}</span>
                  <button
                    className="project-delete-btn"
                    onClick={(e) => handleDeleteProject(project.id, e)}
                    title="Smazat projekt"
                  >
                    ✕
                  </button>
                </div>
                <div className="project-item-meta">
                  <span>{project.layers?.length || 0} vrstev</span>
                  <span>
                    {new Date(project.updatedAt).toLocaleDateString('cs-CZ', {
                      day: '2-digit',
                      month: '2-digit',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Transport Controls */}
      <div className="transport-controls">
        <button
          className="transport-btn"
          onClick={handleSeekToStart}
          title="Na začátek"
        >
          ⏮
        </button>
        <button
          className={`transport-btn play-btn ${isPlaying ? 'playing' : ''}`}
          onClick={isPlaying ? handlePause : handlePlay}
          title={isPlaying ? 'Pauza' : 'Přehrát'}
        >
          {isPlaying ? '⏸' : '▶'}
        </button>
        <button
          className="transport-btn"
          onClick={handleStop}
          title="Stop"
        >
          ⏹
        </button>
        <button
          className="transport-btn"
          onClick={handleSeekToEnd}
          title="Na konec"
        >
          ⏭
        </button>
        <div className="time-display">
          {formatTime(currentTime)} / {formatTime(maxDuration)}
        </div>

        {/* Master Level Meter */}
        <div className="master-level-meter">
          <div className="meter-label">Master Level</div>
          <div className="meter-bars">
            <div className="meter-bar">
              <div
                className="meter-fill"
                style={{ height: `${masterLevel.left * 100}%` }}
              />
            </div>
            <div className="meter-bar">
              <div
                className="meter-fill"
                style={{ height: `${masterLevel.right * 100}%` }}
              />
            </div>
          </div>
        </div>

        {/* Master Volume Control */}
        <div className="master-volume-control">
          <label>Master Volume</label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={masterVolume}
            onChange={(e) => setMasterVolume(parseFloat(e.target.value))}
            className="volume-fader"
          />
          <span className="volume-value">{Math.round(masterVolume * 100)}%</span>
        </div>
      </div>

      {/* Timeline */}
      <div className="timeline-container" ref={timelineRef} onClick={handleTimelineClick}>
        <div className="timeline-header">
          <div className="timeline-ruler">
            {Array.from({ length: Math.ceil(maxDuration) + 1 }, (_, i) => (
              <div key={i} className="timeline-tick" style={{ left: `${(i / Math.max(maxDuration, 1)) * 100}%` }}>
                <span className="tick-label">{i}s</span>
              </div>
            ))}
          </div>
        </div>
        <div className="timeline-playhead" style={{ left: `${playbackPosition * 100}%` }} />
        <div className="layers-container" onClick={(e) => e.stopPropagation()}>
          {layers.map((layer, index) => (
            <div
              key={layer.id}
              className={`layer-track ${selectedLayerId === layer.id ? 'selected' : ''}`}
              onClick={() => setSelectedLayerId(layer.id)}
            >
              <div className="layer-label">
                {layer.name}
                {!layer.audioUrl && layer.blobUrl && (
                  <span className="layer-local-badge" title="Lokální soubor - nebude uložen v projektu">
                    📁
                  </span>
                )}
                <button
                  className="layer-delete-btn-inline"
                  onClick={(e) => {
                    e.stopPropagation()
                    if (window.confirm(`Opravdu chcete smazat vrstvu "${layer.name}"?`)) {
                      deleteLayer(layer.id)
                    }
                  }}
                  title="Smazat vrstvu"
                >
                  ✕
                </button>
              </div>
              <div className="layer-clip-container">
                <div
                  className={`layer-clip ${draggingClip === layer.id ? 'dragging' : ''}`}
                  style={{
                    left: `${(layer.startTime / Math.max(maxDuration, 1)) * 100}%`,
                    width: `${(layer.duration / Math.max(maxDuration, 1)) * 100}%`
                  }}
                  onMouseDown={(e) => handleClipMouseDown(e, layer.id)}
                >
                  <LayerWaveform
                    layerId={layer.id}
                    audioUrl={layer.audioUrl}
                    blobUrl={layer.blobUrl}
                    audioBuffer={layer.audioBuffer}
                    trimStart={layer.trimStart}
                    trimEnd={layer.trimEnd}
                    duration={layer.duration}
                    loop={layer.loop || false}
                    startTime={layer.startTime}
                    loopAnchorTime={layer.loopAnchorTime}
                    isVisible={true}
                    isSelected={selectedLayerId === layer.id}
                  />
                  <button
                    className="clip-delete-btn"
                    onClick={(e) => {
                      e.stopPropagation()
                      if (window.confirm(`Opravdu chcete smazat vrstvu "${layer.name}"?`)) {
                        deleteLayer(layer.id)
                      }
                    }}
                    title="Smazat vrstvu"
                  >
                    ✕
                  </button>
                  <div
                    className="clip-handle clip-handle-left"
                    onMouseDown={(e) => {
                      e.stopPropagation()
                      handleClipMouseDown(e, layer.id, true, false)
                    }}
                    title="Drag pro trim, Shift+Drag pro prodloužení zleva"
                  />
                  <div
                    className="clip-handle clip-handle-right"
                    onMouseDown={(e) => {
                      e.stopPropagation()
                      handleClipMouseDown(e, layer.id, false, true)
                    }}
                    title="Drag pro trim, Shift+Drag pro prodloužení zprava"
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* History Panel */}
      {showHistory && (
        <div className="history-panel">
          <div className="history-panel-header">
            <h3>📜 Historie všech modelů</h3>
            <div className="history-panel-controls">
              <select
                value={historyType}
                onChange={(e) => setHistoryType(e.target.value)}
                className="history-type-select"
              >
                <option value="all">Vše</option>
                <option value="tts">🎤 mluvené slovo</option>
                <option value="music">🎵 hudba</option>
                <option value="bark">🔊 FX & English</option>
              </select>
              <button
                className="btn-refresh-history"
                onClick={loadHistory}
                title="Obnovit historii"
              >
                🔄
              </button>
              <button
                className="btn-toggle-history"
                onClick={() => setShowHistory(false)}
                title="Skrýt historii"
              >
                ✕
              </button>
            </div>
          </div>
          {historyLoading ? (
            <div className="history-loading">⏳ Načítání historie...</div>
          ) : history.length === 0 ? (
            <div className="history-empty">Historie je prázdná</div>
          ) : (
            <div className="history-list-compact">
              {history.map((entry) => (
                <div
                  key={`${entry.source}-${entry.id}`}
                  className="history-item-compact"
                  onClick={() => addLayerFromHistory(entry)}
                >
                  <div className="history-item-compact-header">
                    <span className="history-item-source">{entry.sourceLabel}</span>
                    <span className="history-item-date">
                      {new Date(entry.created_at).toLocaleDateString('cs-CZ', {
                        day: '2-digit',
                        month: '2-digit',
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </span>
                  </div>
                  <div className="history-item-compact-text">
                    {entry.text ? (
                      <span title={entry.text}>
                        "{entry.text.length > 60 ? entry.text.substring(0, 60) + '...' : entry.text}"
                      </span>
                    ) : entry.prompt ? (
                      <span title={entry.prompt}>
                        {entry.prompt.length > 60 ? entry.prompt.substring(0, 60) + '...' : entry.prompt}
                      </span>
                    ) : (
                      <span style={{ fontStyle: 'italic', opacity: 0.6 }}>Bez popisu</span>
                    )}
                  </div>
                  <div className="history-item-compact-action">
                    ➕ Přidat do editoru
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {!showHistory && (
        <button
          className="btn-show-history"
          onClick={() => setShowHistory(true)}
        >
          📜 Zobrazit historii
        </button>
      )}

      {/* Drag and Drop Area */}
      <div
        className={`drop-zone ${isDragging ? 'dragging' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="audio/*"
          multiple
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />
        <div className="drop-zone-content">
          <div className="drop-zone-icon">📁</div>
          <div className="drop-zone-text">
            Přetáhněte audio soubory sem nebo klikněte pro výběr
          </div>
        </div>
      </div>

      {/* Layers List */}
      <div className="layers-panel">
        <h3>Vrstvy ({layers.length})</h3>
        <div className="layers-list">
          {layers.map((layer, index) => (
            <div
              key={layer.id}
              className={`layer-item ${selectedLayerId === layer.id ? 'selected' : ''}`}
              onClick={() => setSelectedLayerId(layer.id)}
            >
              <div className="layer-item-header">
                <span className="layer-item-name">
                  {layer.name}
                  {!layer.audioUrl && layer.blobUrl && (
                    <span className="layer-local-badge" title="Lokální soubor - nebude uložen v projektu">
                      📁
                    </span>
                  )}
                </span>
                <button
                  className="layer-delete-btn"
                  onClick={(e) => {
                    e.stopPropagation()
                    if (window.confirm(`Opravdu chcete smazat vrstvu "${layer.name}"?`)) {
                      deleteLayer(layer.id)
                    }
                  }}
                  title="Smazat vrstvu"
                >
                  ✕
                </button>
              </div>
              <div className="layer-item-controls">
                <div className="control-group">
                  <label>Hlasitost</label>
                  <input
                    type="range"
                    min="0"
                    max="2"
                    step="0.01"
                    value={layer.volume}
                    onChange={(e) => updateLayer(layer.id, { volume: parseFloat(e.target.value) })}
                  />
                  <span>{Math.round(layer.volume * 100)}%</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Layer Editor */}
      {selectedLayer && (
        <div className="layer-editor-panel">
          <div className="layer-editor-header">
            <h3>Editace vrstvy: {selectedLayer.name}</h3>
            <button
              className="btn-delete-layer"
              onClick={() => {
                if (window.confirm(`Opravdu chcete smazat vrstvu "${selectedLayer.name}"?`)) {
                  deleteLayer(selectedLayer.id)
                }
              }}
              title="Smazat vrstvu"
            >
              🗑️ Smazat vrstvu
            </button>
          </div>
          <div className="editor-controls">
            <div className="control-group">
              <label>Začátek (s)</label>
              <input
                type="number"
                min="0"
                step="0.1"
                value={selectedLayer.startTime.toFixed(1)}
                onChange={(e) => updateLayer(selectedLayer.id, { startTime: parseFloat(e.target.value) || 0 })}
              />
            </div>

            <div className="control-group">
              <label>Trim Start (s)</label>
              <input
                type="number"
                min="0"
                max={selectedLayer.audioBuffer.duration}
                step="0.1"
                value={selectedLayer.trimStart.toFixed(1)}
                onChange={(e) => {
                  const newTrimStart = Math.max(0, Math.min(parseFloat(e.target.value) || 0, selectedLayer.trimEnd - 0.1))
                  const newDuration = selectedLayer.trimEnd - newTrimStart
                  updateLayer(selectedLayer.id, {
                    trimStart: newTrimStart,
                    duration: newDuration
                  })
                }}
              />
            </div>

            <div className="control-group">
              <label>Trim End (s)</label>
              <input
                type="number"
                min={selectedLayer.trimStart + 0.1}
                max={selectedLayer.audioBuffer.duration}
                step="0.1"
                value={selectedLayer.trimEnd.toFixed(1)}
                onChange={(e) => {
                  const newTrimEnd = Math.max(selectedLayer.trimStart + 0.1, Math.min(parseFloat(e.target.value) || selectedLayer.audioBuffer.duration, selectedLayer.audioBuffer.duration))
                  const newDuration = newTrimEnd - selectedLayer.trimStart
                  updateLayer(selectedLayer.id, {
                    trimEnd: newTrimEnd,
                    duration: newDuration
                  })
                }}
              />
            </div>

            <div className="control-group">
              <label>Fade In (s)</label>
              <input
                type="number"
                min="0"
                max={selectedLayer.duration}
                step="0.1"
                value={selectedLayer.fadeIn.toFixed(1)}
                onChange={(e) => updateLayer(selectedLayer.id, { fadeIn: parseFloat(e.target.value) || 0 })}
              />
            </div>

            <div className="control-group">
              <label>Fade Out (s)</label>
              <input
                type="number"
                min="0"
                max={selectedLayer.duration}
                step="0.1"
                value={selectedLayer.fadeOut.toFixed(1)}
                onChange={(e) => updateLayer(selectedLayer.id, { fadeOut: parseFloat(e.target.value) || 0 })}
              />
            </div>

            <div className="control-group">
              <label>Hlasitost</label>
              <input
                type="range"
                min="0"
                max="2"
                step="0.01"
                value={selectedLayer.volume}
                onChange={(e) => updateLayer(selectedLayer.id, { volume: parseFloat(e.target.value) })}
              />
              <span>{Math.round(selectedLayer.volume * 100)}%</span>
            </div>

            <div className="control-group">
              <label>
                <input
                  type="checkbox"
                  checked={selectedLayer.loop || false}
                  onChange={(e) => updateLayer(selectedLayer.id, { loop: e.target.checked })}
                />
                🔁 Loopovat zvuk
              </label>
              <span className="control-hint">
                Zvuk se bude opakovat po celou délku vrstvy na timeline
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default AudioEditor

