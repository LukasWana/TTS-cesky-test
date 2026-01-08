import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import { useSectionColor } from '../contexts/SectionColorContext'
import WaveSurfer from 'wavesurfer.js'
import './AudioEditor.css'
import { getHistory, getMusicHistory, getBarkHistory, getApplioFiles } from '../services/api'
import { getWaveformCache, setWaveformCache } from '../utils/waveformCache'
import LayerWaveform from './audioEditor/LayerWaveform'
import HistoryItemPreview from './audioEditor/HistoryItemPreview'
import { useLayers } from '../hooks/useLayers'
import { useTimeline } from '../hooks/useTimeline'
import { getCategoryColor } from '../utils/layerColors'
import Icon from './ui/Icons'

// Použij 127.0.0.1 místo localhost kvůli IPv6 (::1) na Windows/Chrome
const API_BASE_URL = 'http://127.0.0.1:8000'
const STORAGE_KEY = 'audio_editor_state'
const PROJECTS_STORAGE_KEY = 'audio_editor_projects'

const HISTORY_TYPES = {
  all: { label: 'Vše', icon: 'grid' },
  tts: { label: 'české slovo', icon: 'microphone' },
  f5tts: { label: 'slovenské slovo', icon: 'microphone' },
  music: { label: 'hudba', icon: 'music' },
  bark: { label: 'FX & English', icon: 'speaker' },
  applio: { label: 'Applio', icon: 'microphone' }
}

// LayerWaveform and HistoryItemPreview are now imported from separate files

// Pomocná funkce pro převod hex barvy na RGB hodnoty
function hexToRgb(hex) {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
  return result
    ? `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}`
    : '158, 158, 158' // výchozí šedá
}

function AudioEditor() {
  const { color, rgb } = useSectionColor()
  const style = {
    '--section-color': color,
    '--section-color-rgb': rgb
  }

  // Audio context a playback refs
  const audioContextRef = useRef(null)
  const masterGainNodeRef = useRef(null)
  const analyserNodeRef = useRef(null)
  const sourceNodesRef = useRef({})
  const gainNodesRef = useRef({})
  const animationFrameRef = useRef(null)
  const playbackStartTimeRef = useRef(0)
  const pausedTimeRef = useRef(0)
  const isLoadingStateRef = useRef(false)
  const saveTimeoutRef = useRef(null)
  const didHydrateFromStorageRef = useRef(false)
  const fileInputRef = useRef(null)

  // Playback state
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [masterVolume, setMasterVolume] = useState(1.0)
  const [masterLevel, setMasterLevel] = useState({ left: 0, right: 0 })
  const [playbackPosition, setPlaybackPosition] = useState(0)
  const [manualMaxDuration, setManualMaxDuration] = useState(null)

  // History state
  const [historyType, setHistoryType] = useState('all')
  const [history, setHistory] = useState([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [showHistory, setShowHistory] = useState(true)

  // Projects state
  const [savedProjects, setSavedProjects] = useState([])
  const [showSaveDialog, setShowSaveDialog] = useState(false)
  const [projectName, setProjectName] = useState('')
  const [currentProjectId, setCurrentProjectId] = useState(null)
  const [isExporting, setIsExporting] = useState(false)

  // Drag and drop state
  const [isDragging, setIsDragging] = useState(false)

  // Použít hooks pro layers a timeline
  const layersHook = useLayers()
  const {
    layers,
    setLayers,
    selectedLayerId,
    setSelectedLayerId,
    expandedLayerId,
    setExpandedLayerId,
    addLayer: addLayerFromHook,
    addLayerFromHistory: addLayerFromHistoryHook,
    updateLayer,
    deleteLayer: deleteLayerFromHook
  } = layersHook

  const timelineHook = useTimeline(layers, manualMaxDuration)
  const {
    timelineZoom,
    setTimelineZoom,
    timelineBaseWidthPx,
    setTimelineBaseWidthPx,
    timelineHover,
    setTimelineHover,
    draggingClip,
    setDraggingClip,
    resizingClip,
    setResizingClip,
    isEditingMaxDuration,
    setIsEditingMaxDuration,
    maxDurationInput,
    setMaxDurationInput,
    timelineRef,
    timelineContentRef,
    timelineRulerRef,
    maxDurationInputRef,
    dragStartXRef,
    dragStartTimeRef,
    computedMaxDuration,
    maxDuration,
    timelineContentWidthPx,
    timelineTicks,
    getTimelinePercentFromClientX,
    formatTimeMMSS,
    clamp01
  } = timelineHook

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
    // React 18 StrictMode (DEV) spustí effect 2× (setup/cleanup/setup). Tento guard zabrání duplicitnímu přidání vrstev.
    if (didHydrateFromStorageRef.current) return
    didHydrateFromStorageRef.current = true

    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved) {
        isLoadingStateRef.current = true
        const state = JSON.parse(saved)

        if (state.masterVolume !== undefined) {
          setMasterVolume(state.masterVolume)
        }
        if (state.manualMaxDuration !== undefined) {
          const v = state.manualMaxDuration
          setManualMaxDuration((typeof v === 'number' && Number.isFinite(v) && v > 0) ? v : null)
        }
        if (state.currentTime !== undefined) {
          setCurrentTime(state.currentTime)
          const denom = Math.max((state.manualMaxDuration ?? state.maxDuration ?? 10), 1)
          setPlaybackPosition(state.currentTime / denom)
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
          const makeNewLayerId = () =>
            `layer-${Date.now()}-${++layerIdCounterRef.current}-${Math.random().toString(36).substr(2, 9)}`

          const hydrate = async () => {
            try {
              // Vždy hydratovat jako "replace", ne append (eliminuje duplikace a race conditions).
              const usedIds = new Set()
              const layerDatas = state.layers.filter(ld => ld && ld.audioUrl)

              const loadedLayers = []
              for (const layerData of layerDatas) {
                const audioBuffer = await loadAudioFromUrl(layerData.audioUrl)

                let id = layerData.id || makeNewLayerId()
                let attempts = 0
                while (usedIds.has(id) && attempts < 10) {
                  id = makeNewLayerId()
                  attempts++
                }
                usedIds.add(id)

                loadedLayers.push({
                  id,
                  name: layerData.name,
                  file: null,
                  audioBuffer,
                  audioUrl: layerData.audioUrl,
                  startTime: layerData.startTime || 0,
                  duration: layerData.duration || audioBuffer.duration,
                  // Pozor: volume může být 0 (mute) => nesmí spadnout na 1.0
                  volume: layerData.volume ?? 1.0,
                  fadeIn: layerData.fadeIn || 0,
                  fadeOut: layerData.fadeOut || 0,
                  trimStart: layerData.trimStart || 0,
                  trimEnd: layerData.trimEnd || audioBuffer.duration,
                  loop: layerData.loop || false,
                  loopAnchorTime: (layerData.loopAnchorTime !== undefined && layerData.loopAnchorTime !== null)
                    ? layerData.loopAnchorTime
                    : (layerData.startTime || 0),
                  historyEntry: layerData.historyEntry,
                  category: layerData.category || 'file',
                  color: layerData.color || getCategoryColor(layerData.category || 'file', 0)
                })
              }

              setLayers(loadedLayers)

              // Pokud uložený selectedLayerId neexistuje, vyber první vrstvu.
              if (state.selectedLayerId !== undefined) {
                const exists = loadedLayers.some(l => l.id === state.selectedLayerId)
                if (!exists) {
                  setSelectedLayerId(loadedLayers[0]?.id ?? null)
                }
              }
            } catch (err) {
              console.error('Chyba při načítání vrstev:', err)
            }
          }

          hydrate()
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

  // Pomocná funkce pro serializaci historyEntry (odstraní neserializovatelné hodnoty)
  const sanitizeHistoryEntry = useCallback((entry) => {
    if (!entry) return null

    try {
      // Vytvořit kopii pouze s serializovatelnými hodnotami
      const sanitized = {}
      const allowedKeys = ['id', 'audio_url', 'filename', 'text', 'prompt', 'voice_type', 'voice_name',
                          'tts_params', 'music_params', 'bark_params', 'created_at', 'source', 'sourceLabel']

      for (const key of allowedKeys) {
        if (entry.hasOwnProperty(key)) {
          const value = entry[key]
          // Zkontrolovat, zda je hodnota serializovatelná
          if (value !== undefined && value !== null) {
            if (typeof value === 'object' && !Array.isArray(value)) {
              // Pro objekty zkusit serializaci
              try {
                JSON.stringify(value)
                sanitized[key] = value
              } catch (e) {
                // Pokud objekt není serializovatelný, přeskočit
                console.warn(`Neserializovatelná hodnota v historyEntry.${key}:`, e)
              }
            } else {
              sanitized[key] = value
            }
          }
        }
      }

      return Object.keys(sanitized).length > 0 ? sanitized : null
    } catch (err) {
      console.warn('Chyba při sanitizaci historyEntry:', err)
      return null
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
            historyEntry: sanitizeHistoryEntry(layer.historyEntry),
            category: layer.category || 'file',
            color: layer.color || getCategoryColor(layer.category || 'file', 0)
          })),
          masterVolume,
          currentTime,
          selectedLayerId,
          showHistory,
          historyType,
          maxDuration,
          manualMaxDuration
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
  }, [layers, masterVolume, currentTime, selectedLayerId, showHistory, historyType, maxDuration, manualMaxDuration, sanitizeHistoryEntry])

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

  // Realtime aktualizace hlasitosti vrstev během přehrávání.
  // Používáme separátní volume gain node (bez automatizace), aby změna slideru fungovala i "za běhu"
  // a zároveň nenarušila fade-in/fade-out automatizaci na envelope gain node.
  useEffect(() => {
    if (!isPlaying) return
    const ctx = audioContextRef.current
    if (!ctx) return
    const now = ctx.currentTime

    for (const layer of layers) {
      const nodes = gainNodesRef.current?.[layer.id]
      const volumeGain = nodes?.volumeGain
      if (!volumeGain) continue
      const v = Number(layer.volume)
      const safeV = Number.isFinite(v) ? Math.max(0, Math.min(1, v)) : 1.0
      try {
        // jemný smoothing, aby to neklikalo
        volumeGain.gain.setTargetAtTime(safeV, now, 0.01)
      } catch (e) {
        try {
          volumeGain.gain.setValueAtTime(safeV, now)
        } catch (e2) {}
      }
    }
  }, [layers, isPlaying])

  // Pokud se změní délka projektu, ohlídat currentTime + playhead
  useEffect(() => {
    if (!Number.isFinite(maxDuration) || maxDuration <= 0) return
    if (currentTime > maxDuration) {
      setCurrentTime(maxDuration)
      setPlaybackPosition(1)
      pausedTimeRef.current = maxDuration
    }
  }, [maxDuration, currentTime])

  // Fokus inputu při editaci délky
  useEffect(() => {
    if (!isEditingMaxDuration) return
    const t = setTimeout(() => {
      maxDurationInputRef.current?.focus?.()
      maxDurationInputRef.current?.select?.()
    }, 0)
    return () => clearTimeout(t)
  }, [isEditingMaxDuration])

  // Měření šířky timeline (pro adaptivní ticky + zoom)
  useEffect(() => {
    const el = timelineRef.current
    if (!el) return

    const update = () => {
      setTimelineBaseWidthPx(el.clientWidth || 0)
    }
    update()

    const ro = new ResizeObserver(() => update())
    ro.observe(el)

    return () => {
      ro.disconnect()
    }
  }, [])

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

      // Načíst data z API (rychle, bez waveformů) - všechny záznamy
      if (historyType === 'all' || historyType === 'tts' || historyType === 'f5tts') {
        try {
          const ttsData = await getHistory(null, 0)
          const ttsEntries = (ttsData.history || []).map(entry => {
            // Rozlišení mezi českým a slovenským slovem podle engine v tts_params
            const engine = entry.tts_params?.engine || ''
            const isSlovak = engine === 'f5-tts-slovak'

            // Filtrování podle typu
            if (historyType === 'tts' && isSlovak) {
              return null // České slovo - přeskočit slovenské
            }
            if (historyType === 'f5tts' && !isSlovak) {
              return null // Slovenské slovo - přeskočit ostatní
            }

            return {
              ...entry,
              source: isSlovak ? 'f5tts' : 'tts',
              sourceLabel: isSlovak ? '🇸🇰 slovenské slovo' : '🎤 české slovo'
            }
          }).filter(entry => entry !== null) // Odstranit null hodnoty

          allHistory = [...allHistory, ...ttsEntries]
        } catch (err) {
          console.error('Chyba při načítání TTS historie:', err)
        }
      }

      if (historyType === 'all' || historyType === 'music') {
        try {
          const musicData = await getMusicHistory(null, 0)
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
          const barkData = await getBarkHistory(null, 0)
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

      if (historyType === 'all' || historyType === 'applio') {
        try {
          const applioData = await getApplioFiles()
          const applioEntries = (applioData.history || []).map(entry => ({
            ...entry,
            source: 'applio',
            sourceLabel: '🎤 Applio'
          }))
          allHistory = [...allHistory, ...applioEntries]
        } catch (err) {
          console.error('Chyba při načítání Applio historie:', err)
        }
      }

      // Seřadit podle data (nejnovější první)
      allHistory.sort((a, b) => {
        const dateA = new Date(a.created_at || 0)
        const dateB = new Date(b.created_at || 0)
        return dateB - dateA
      })

      // Nastavit historii - waveformy se načtou lazy loadingem přes Intersection Observer
      setHistory(allHistory)
    } catch (err) {
      console.error('Chyba při načítání historie:', err)
    } finally {
      setHistoryLoading(false)
    }
  }

  // loadAudioFromUrl, loadAudioFile a createBlobUrl jsou nyní v useLayers hooku
  // Používáme je přes wrapper funkce

  // Export projektu jako WAV soubor
  const exportProjectAsWav = async () => {
    if (layers.length === 0) {
      alert('Nelze exportovat prázdný projekt')
      return
    }

    try {
      setIsExporting(true)

      if (!audioContextRef.current) {
        throw new Error('AudioContext není inicializován')
      }

      const sampleRate = audioContextRef.current.sampleRate
      const totalLength = Math.ceil(maxDuration * sampleRate)

      // Vytvořit finální buffer (stereo)
      const numberOfChannels = 2
      const outputBuffer = audioContextRef.current.createBuffer(numberOfChannels, totalLength, sampleRate)
      const leftChannel = outputBuffer.getChannelData(0)
      const rightChannel = outputBuffer.getChannelData(1)

      // Mixovat všechny vrstvy
      for (const layer of layers) {
        if (!layer.audioBuffer) continue

        // Oříznutí podle trim
        const trimStart = Math.max(0, Math.min(layer.trimStart, layer.audioBuffer.duration))
        const trimEnd = Math.max(trimStart + 0.1, Math.min(layer.trimEnd, layer.audioBuffer.duration))
        const trimmedDuration = trimEnd - trimStart

        // Vypočítat, kolikrát se má loop opakovat
        const cycleDuration = trimmedDuration
        const layerDuration = layer.duration
        const numCycles = layer.loop ? Math.ceil(layerDuration / cycleDuration) : 1

        // Získat audio data z původního bufferu
        const sourceChannels = layer.audioBuffer.numberOfChannels
        const sourceLeft = layer.audioBuffer.getChannelData(0)
        const sourceRight = sourceChannels > 1 ? layer.audioBuffer.getChannelData(1) : sourceLeft

        // Vypočítat offset v původním bufferu
        const sourceStartSample = Math.floor(trimStart * layer.audioBuffer.sampleRate)
        const sourceEndSample = Math.floor(trimEnd * layer.audioBuffer.sampleRate)
        const sourceLength = sourceEndSample - sourceStartSample

        // Resample ratio
        const resampleRatio = layer.audioBuffer.sampleRate / sampleRate

        // Pro každý cyklus
        for (let cycle = 0; cycle < numCycles; cycle++) {
          const cycleStartTime = layer.startTime + (cycle * cycleDuration)
          const cycleStartSample = Math.floor(cycleStartTime * sampleRate)
          const cycleEndSample = Math.min(
            Math.floor((cycleStartTime + cycleDuration) * sampleRate),
            totalLength
          )

          // Vypočítat délku tohoto cyklu
          const cycleLength = cycleEndSample - cycleStartSample
          if (cycleLength <= 0) continue

          // Mixovat do výstupního bufferu
          for (let i = 0; i < cycleLength; i++) {
            const outputIndex = cycleStartSample + i
            if (outputIndex >= totalLength) break

            // Vypočítat pozici v původním bufferu (s resamplingem)
            const sourceIndex = sourceStartSample + (i * resampleRatio)
            const sourceIndexFloor = Math.floor(sourceIndex)
            const sourceIndexCeil = Math.min(sourceIndexFloor + 1, sourceEndSample - 1)
            const fraction = sourceIndex - sourceIndexFloor

            // Lineární interpolace
            let leftSample = 0
            let rightSample = 0

            if (sourceIndexFloor < sourceEndSample && sourceIndexFloor >= sourceStartSample) {
              const left1 = sourceLeft[sourceIndexFloor]
              const right1 = sourceRight[sourceIndexFloor]
              const left2 = sourceIndexCeil < sourceEndSample ? sourceLeft[sourceIndexCeil] : left1
              const right2 = sourceIndexCeil < sourceEndSample ? sourceRight[sourceIndexCeil] : right1

              leftSample = left1 + (left2 - left1) * fraction
              rightSample = right1 + (right2 - right1) * fraction
            }

            // Vypočítat čas v rámci vrstvy pro fade in/out
            const timeInLayer = (outputIndex / sampleRate) - layer.startTime
            const timeInCycle = timeInLayer % cycleDuration
            const fadeInDuration = Math.min(layer.fadeIn, cycleDuration)
            const fadeOutDuration = Math.min(layer.fadeOut, cycleDuration)

            // Aplikovat fade in
            let fadeMultiplier = 1.0
            if (fadeInDuration > 0 && timeInCycle < fadeInDuration) {
              fadeMultiplier = timeInCycle / fadeInDuration
            }

            // Aplikovat fade out
            if (fadeOutDuration > 0 && timeInCycle > (cycleDuration - fadeOutDuration)) {
              const fadeOutProgress = (cycleDuration - timeInCycle) / fadeOutDuration
              fadeMultiplier = Math.min(fadeMultiplier, fadeOutProgress)
            }

            // Aplikovat volume a master volume
            const finalVolume = layer.volume * masterVolume * fadeMultiplier
            leftSample *= finalVolume
            rightSample *= finalVolume

            // Mixovat do výstupního bufferu (s ochranou proti clippingu)
            leftChannel[outputIndex] = Math.max(-1, Math.min(1, leftChannel[outputIndex] + leftSample))
            rightChannel[outputIndex] = Math.max(-1, Math.min(1, rightChannel[outputIndex] + rightSample))
          }
        }
      }

      // Vytvořit WAV a stáhnout
      const wav = await audioBufferToWav(outputBuffer)
      const blob = new Blob([wav], { type: 'audio/wav' })
      const url = URL.createObjectURL(blob)

      const link = document.createElement('a')
      const filename = projectName
        ? `${projectName.replace(/[^a-z0-9]/gi, '_')}.wav`
        : `audio-project-${new Date().toISOString().replace(/[:.]/g, '-')}.wav`
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)

      // Vyčistit URL
      setTimeout(() => URL.revokeObjectURL(url), 100)

      alert(`Projekt byl úspěšně exportován jako ${filename}`)
    } catch (err) {
      console.error('Chyba při exportu projektu:', err)
      alert('Chyba při exportu projektu: ' + err.message)
    } finally {
      setIsExporting(false)
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

  // Wrapper funkce pro addLayer a addLayerFromHistory, které používají hooks
  const addLayer = useCallback(async (file) => {
    try {
      await addLayerFromHook(file, audioContextRef, audioBufferToWav, sourceNodesRef, gainNodesRef)
    } catch (err) {
      console.error('Chyba při načítání audio:', err)
      alert('Chyba při načítání audio souboru')
    }
  }, [addLayerFromHook])

  const addLayerFromHistory = useCallback(async (entry) => {
    try {
      await addLayerFromHistoryHook(entry, audioContextRef, sourceNodesRef, gainNodesRef)
    } catch (err) {
      console.error('Chyba při načítání audio z historie:', err)
      alert('Chyba při načítání audio souboru z historie')
    }
  }, [addLayerFromHistoryHook])

  const deleteLayer = useCallback((layerId) => {
    deleteLayerFromHook(layerId, sourceNodesRef, gainNodesRef)
  }, [deleteLayerFromHook])

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

  // fileInputRef je už definován výše
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

  // updateLayer a deleteLayer jsou nyní v useLayers hooku
  // Používáme je přímo z hooku

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
      const percent = getTimelinePercentFromClientX(e.clientX)
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
    const percent = getTimelinePercentFromClientX(e.clientX)
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
          const envelopeGain = audioContextRef.current.createGain()
          const volumeGain = audioContextRef.current.createGain()

          source.buffer = layer.audioBuffer
          source.loop = true
          source.loopStart = trimStart
          source.loopEnd = trimEnd

          source.connect(envelopeGain)
          envelopeGain.connect(volumeGain)
          volumeGain.connect(masterGainNodeRef.current)

          // Realtime volume (bez automatizace)
          volumeGain.gain.setValueAtTime(Number.isFinite(Number(layer.volume)) ? layer.volume : 1.0, now)

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

          // Envelope gain (0..1) + fade in/out
          envelopeGain.gain.setValueAtTime(0, startAt)
          if (fadeInDuration > 0) {
            envelopeGain.gain.linearRampToValueAtTime(1, startAt + Math.min(fadeInDuration, durationToPlay))
          } else {
            envelopeGain.gain.setValueAtTime(1, startAt)
          }
          if (fadeOutDuration > 0 && durationToPlay > fadeOutDuration) {
            const fadeOutStart = durationToPlay - fadeOutDuration
            envelopeGain.gain.setValueAtTime(1, startAt + fadeOutStart)
            envelopeGain.gain.linearRampToValueAtTime(0, startAt + durationToPlay)
          }

          try {
            if (durationToPlay > 0) {
              // Pro loop: start bez stop, stop se zavolá až když vrstva končí
              source.start(startAt, audioOffset)
              // Stop se zavolá až když vrstva končí (ne okamžitě)
              source.stop(startAt + durationToPlay)
              sourceNodesRef.current[layer.id] = source
              gainNodesRef.current[layer.id] = { envelopeGain, volumeGain }
            }
          } catch (err) {
            console.error('Chyba při startování loop audio zdroje:', err)
          }
        } else {
          // Bez loopu - normální přehrávání
          const source = audioContextRef.current.createBufferSource()
          const envelopeGain = audioContextRef.current.createGain()
          const volumeGain = audioContextRef.current.createGain()

          source.buffer = layer.audioBuffer
          source.connect(envelopeGain)
          envelopeGain.connect(volumeGain)
          volumeGain.connect(masterGainNodeRef.current)

          // Realtime volume (bez automatizace)
          volumeGain.gain.setValueAtTime(Number.isFinite(Number(layer.volume)) ? layer.volume : 1.0, now)

          // Nastavit hlasitost s fade in
          envelopeGain.gain.setValueAtTime(0, now + delay)
          if (fadeInDuration > 0) {
            envelopeGain.gain.linearRampToValueAtTime(1, now + delay + fadeInDuration)
          } else {
            envelopeGain.gain.setValueAtTime(1, now + delay)
          }

          // Nastavit fade out
          if (fadeOutDuration > 0 && trimmedDuration > fadeOutDuration) {
            const fadeOutStart = trimmedDuration - fadeOutDuration
            envelopeGain.gain.setValueAtTime(1, now + delay + fadeOutStart)
            envelopeGain.gain.linearRampToValueAtTime(0, now + delay + trimmedDuration)
          }

          try {
            source.start(now + delay, trimStart, trimmedDuration)
            sourceNodesRef.current[layer.id] = source
            gainNodesRef.current[layer.id] = { envelopeGain, volumeGain }
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
        const envelopeGain = audioContextRef.current.createGain()
        const volumeGain = audioContextRef.current.createGain()

        source.buffer = layer.audioBuffer
        source.loop = true
        source.loopStart = trimStart
        source.loopEnd = trimEnd

        source.connect(envelopeGain)
        envelopeGain.connect(volumeGain)
        volumeGain.connect(masterGainNodeRef.current)

        // Realtime volume (bez automatizace)
        volumeGain.gain.setValueAtTime(Number.isFinite(Number(layer.volume)) ? layer.volume : 1.0, now)

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
        const fadeInDuration = Math.min(layer.fadeIn || 0, trimmedDuration)
        const fadeOutDuration = Math.min(layer.fadeOut || 0, trimmedDuration)

        // Pokud už jsme ve fade-in, nastavíme počáteční hlasitost podle progressu
        const fadeInProgress = fadeInDuration > 0 ? Math.min(layerTimeOffset / fadeInDuration, 1) : 1
        envelopeGain.gain.setValueAtTime(1 * fadeInProgress, now)
        if (fadeInDuration > 0 && layerTimeOffset < fadeInDuration) {
          envelopeGain.gain.linearRampToValueAtTime(1, now + (fadeInDuration - layerTimeOffset))
        }

        // Fade-out v čase konce vrstvy
        if (fadeOutDuration > 0 && durationToPlay > fadeOutDuration) {
          const fadeOutStart = durationToPlay - fadeOutDuration
          envelopeGain.gain.setValueAtTime(1, now + fadeOutStart)
          envelopeGain.gain.linearRampToValueAtTime(0, now + durationToPlay)
        }

        try {
          // Pro loop: start bez stop, stop se zavolá až když vrstva končí
          source.start(now, audioOffset)
          // Stop se zavolá až když vrstva končí (ne okamžitě)
          source.stop(now + durationToPlay)
          sourceNodesRef.current[layer.id] = source
          gainNodesRef.current[layer.id] = { envelopeGain, volumeGain }
        } catch (err) {
          console.error('Chyba při startování loop audio zdroje:', err)
        }
      } else {
        // Bez loopu - normální přehrávání
        const source = audioContextRef.current.createBufferSource()
        const envelopeGain = audioContextRef.current.createGain()
        const volumeGain = audioContextRef.current.createGain()

        source.buffer = layer.audioBuffer
        source.connect(envelopeGain)
        envelopeGain.connect(volumeGain)
        volumeGain.connect(masterGainNodeRef.current)

        // Realtime volume (bez automatizace)
        volumeGain.gain.setValueAtTime(Number.isFinite(Number(layer.volume)) ? layer.volume : 1.0, now)

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
        const initialEnvelope = 1 * fadeInProgress

        envelopeGain.gain.setValueAtTime(initialEnvelope, now)

        // Dokončit fade in, pokud ještě probíhá
        if (fadeInDuration > 0 && layerTimeOffset < fadeInDuration) {
          const fadeInRemaining = fadeInDuration - layerTimeOffset
          envelopeGain.gain.linearRampToValueAtTime(1, now + fadeInRemaining)
        }

        // Fade out
        if (fadeOutDuration > 0 && remainingDuration > fadeOutDuration) {
          const fadeOutStart = remainingDuration - fadeOutDuration
          envelopeGain.gain.setValueAtTime(1, now + fadeOutStart)
          envelopeGain.gain.linearRampToValueAtTime(0, now + remainingDuration)
        }

        try {
          source.start(now, audioOffset, remainingDuration)
          sourceNodesRef.current[layer.id] = source
          gainNodesRef.current[layer.id] = { envelopeGain, volumeGain }
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
    const total = Math.max(0, Math.floor(time || 0))
    const hours = Math.floor(total / 3600)
    const minutes = Math.floor((total % 3600) / 60)
    const seconds = total % 60
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
    }
    return `${minutes}:${seconds.toString().padStart(2, '0')}`
  }

  const parseTimeToSeconds = (raw) => {
    const s = String(raw ?? '').trim()
    if (!s) return null // prázdné = auto

    // Povolit i čisté sekundy (např. "90")
    if (/^\d+(\.\d+)?$/.test(s)) {
      const n = Number(s)
      return Number.isFinite(n) ? n : NaN
    }

    const parts = s.split(':').map(p => p.trim())
    if (parts.length !== 2 && parts.length !== 3) return NaN
    if (parts.some(p => p === '' || !/^\d+$/.test(p))) return NaN

    const nums = parts.map(p => Number(p))
    if (parts.length === 2) {
      const [m, sec] = nums
      if (sec >= 60) return NaN
      return (m * 60) + sec
    }
    const [h, m, sec] = nums
    if (m >= 60 || sec >= 60) return NaN
    return (h * 3600) + (m * 60) + sec
  }

  const startEditMaxDuration = () => {
    setIsEditingMaxDuration(true)
    setMaxDurationInput(formatTime(maxDuration))
  }

  const cancelEditMaxDuration = () => {
    setIsEditingMaxDuration(false)
    setMaxDurationInput('')
  }

  const commitEditMaxDuration = () => {
    const parsed = parseTimeToSeconds(maxDurationInput)
    if (parsed === null) {
      setManualMaxDuration(null)
      setIsEditingMaxDuration(false)
      return
    }
    if (!Number.isFinite(parsed) || parsed <= 0) {
      // Nezapisovat nesmysly; necháme uživatele opravit
      return
    }
    const clamped = Math.max(10, computedMaxDuration, parsed)
    setManualMaxDuration(clamped)
    if (currentTime > clamped) {
      setCurrentTime(clamped)
      setPlaybackPosition(1)
      pausedTimeRef.current = clamped
    }
    setIsEditingMaxDuration(false)
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
      setManualMaxDuration(null)

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

    try {
      const projectData = {
        id: currentProjectId || Date.now().toString(),
        name: name,
        createdAt: currentProjectId ? savedProjects.find(p => p.id === currentProjectId)?.createdAt : new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        manualMaxDuration,
        maxDuration,
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
          historyEntry: sanitizeHistoryEntry(layer.historyEntry),
          category: layer.category || 'file',
          color: layer.color || getCategoryColor(layer.category || 'file', 0)
        })),
        masterVolume,
        currentTime: 0, // Uložit na začátek
        selectedLayerId: null
      }

      // Zkusit serializaci před uložením, abychom zachytili chyby
      const serialized = JSON.stringify(projectData)

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
      const errorMessage = err.message || 'Neznámá chyba'
      alert(`Chyba při ukládání projektu: ${errorMessage}\n\nZkuste zkontrolovat konzoli pro více informací.`)
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
    // masterVolume může být 0 => nesmí se přepsat na 1.0
    setMasterVolume(project.masterVolume ?? 1.0)
    setCurrentProjectId(project.id)
    setProjectName(project.name)
    setManualMaxDuration((typeof project.manualMaxDuration === 'number' && Number.isFinite(project.manualMaxDuration) && project.manualMaxDuration > 0)
      ? project.manualMaxDuration
      : null)

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
              // Pozor: volume může být 0 (mute) => nesmí spadnout na 1.0
              volume: layerData.volume ?? 1.0,
              fadeIn: layerData.fadeIn || 0,
              fadeOut: layerData.fadeOut || 0,
              trimStart: layerData.trimStart || 0,
              trimEnd: layerData.trimEnd || audioBuffer.duration,
              loop: layerData.loop || false,
              loopAnchorTime: layerData.loopAnchorTime ?? (layerData.startTime || 0),
              historyEntry: layerData.historyEntry,
              category: layerData.category || 'file',
              color: layerData.color || getCategoryColor(layerData.category || 'file', 0)
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
    <div
      className="audio-editor"
      style={style}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className="audio-editor-header">
        <div className="header-top">
          <div>
            <h2>🎚️ Audio Editor - Kompozice ve vrstvách</h2>
            <p className="audio-editor-hint">
              Přetáhněte audio soubory do editoru. Upravujte vrstvy, mixujte a exportujte výsledek.
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
              className="btn-project btn-export-wav"
              onClick={exportProjectAsWav}
              title="Exportovat projekt jako WAV soubor"
              disabled={layers.length === 0 || isExporting}
            >
              {isExporting ? '⏳ Exportuji...' : '💾 Exportovat jako WAV'}
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
          <span className="time-display-current">{formatTime(currentTime)}</span>
          <span className="time-display-sep">/</span>
          {isEditingMaxDuration ? (
            <input
              ref={maxDurationInputRef}
              className="time-display-duration-input"
              value={maxDurationInput}
              onChange={(e) => setMaxDurationInput(e.target.value)}
              onBlur={commitEditMaxDuration}
              onKeyDown={(e) => {
                if (e.key === 'Enter') commitEditMaxDuration()
                if (e.key === 'Escape') cancelEditMaxDuration()
              }}
              inputMode="numeric"
              placeholder="mm:ss nebo hh:mm:ss"
              title="Zadej délku projektu (mm:ss nebo hh:mm:ss). Prázdné = auto."
            />
          ) : (
            <button
              type="button"
              className={`time-display-duration-btn ${manualMaxDuration ? 'manual' : 'auto'}`}
              onClick={startEditMaxDuration}
              title="Klikni pro úpravu délky projektu (mm:ss / hh:mm:ss)."
            >
              {formatTime(maxDuration)}
            </button>
          )}
          {manualMaxDuration ? (
            <button
              type="button"
              className="time-display-auto-btn"
              onClick={() => setManualMaxDuration(null)}
              title="Přepnout délku zpět na automatiku (dle vrstev)"
            >
              AUTO
            </button>
          ) : null}
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
      <div className="timeline-container">
        <div className="timeline-scroll" ref={timelineRef} onClick={handleTimelineClick}>
          <div className="timeline-content" ref={timelineContentRef} style={{ width: `${timelineContentWidthPx}px` }}>
            <div className="timeline-header">
              <div className="timeline-zoom-controls" onClick={(e) => e.stopPropagation()}>
                <span className="timeline-zoom-label">Zoom</span>
                <input
                  className="timeline-zoom-slider"
                  type="range"
                  min="1"
                  max="10"
                  step="0.25"
                  value={timelineZoom}
                  onChange={(e) => setTimelineZoom(parseFloat(e.target.value))}
                  title="Zoom timeline"
                />
                <span className="timeline-zoom-value">{Math.round(timelineZoom * 100)}%</span>
              </div>

              <div
                className="timeline-ruler"
                ref={timelineRulerRef}
                onMouseMove={(e) => {
                  const percent = getTimelinePercentFromClientX(e.clientX)
                  const t = percent * maxDuration
                  setTimelineHover({ visible: true, percent, time: t })
                }}
                onMouseLeave={() => setTimelineHover((p) => ({ ...p, visible: false }))}
              >
                {timelineTicks.ticks.map((t) => (
                  <div
                    key={t.sec}
                    className={`timeline-tick ${t.isMajor ? 'major' : 'minor'}`}
                    style={{ left: `${t.percent}%` }}
                  >
                    {t.isMajor ? <span className="tick-label">{formatTimeMMSS(t.sec)}</span> : null}
                  </div>
                ))}
                {timelineHover.visible ? (
                  <div className="timeline-hover-tooltip" style={{ left: `${timelineHover.percent * 100}%` }}>
                    {formatTimeMMSS(timelineHover.time)}
                  </div>
                ) : null}
              </div>
            </div>

            <div className="timeline-playhead" style={{ left: `${playbackPosition * 100}%` }} />
            <div className="layers-container" onClick={(e) => e.stopPropagation()}>
              {layers.map((layer, index) => {
                // Získat barvu vrstvy, nebo použít výchozí
                const layerColor = layer.color || getCategoryColor(layer.category || 'file', 0)
                const isSelected = selectedLayerId === layer.id
                const rgb = hexToRgb(layerColor)

                return (
                <React.Fragment key={layer.id}>
                  <div
                    className={`layer-track ${isSelected ? 'selected' : ''}`}
                    onClick={() => setSelectedLayerId(layer.id)}
                    style={{
                      borderColor: isSelected ? layerColor : `rgba(${rgb}, 0.3)`,
                      backgroundColor: isSelected ? `rgba(${rgb}, 0.15)` : `rgba(${rgb}, 0.05)`,
                      boxShadow: isSelected ? `0 0 15px rgba(${rgb}, 0.3)` : 'none'
                    }}
                    onMouseEnter={(e) => {
                      if (!isSelected) {
                        e.currentTarget.style.borderColor = `rgba(${rgb}, 0.5)`
                        e.currentTarget.style.backgroundColor = `rgba(${rgb}, 0.1)`
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isSelected) {
                        e.currentTarget.style.borderColor = `rgba(${rgb}, 0.3)`
                        e.currentTarget.style.backgroundColor = `rgba(${rgb}, 0.05)`
                      }
                    }}
                  >
                    <div className="layer-label" style={{ userSelect: 'none' }}>
                      <button
                        className="layer-settings-btn"
                        onClick={(e) => {
                          e.stopPropagation()
                          setExpandedLayerId(expandedLayerId === layer.id ? null : layer.id)
                        }}
                        title={expandedLayerId === layer.id ? 'Zavřít nastavení' : 'Otevřít nastavení'}
                      >
                        {expandedLayerId === layer.id ? '▼' : '▶'}
                      </button>
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
                            setExpandedLayerId(null)
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
                        width: `${(layer.duration / Math.max(maxDuration, 1)) * 100}%`,
                        borderColor: isSelected ? layerColor : `rgba(${rgb}, 0.4)`,
                        backgroundColor: `rgba(${rgb}, 0.1)`
                      }}
                      onMouseDown={(e) => handleClipMouseDown(e, layer.id)}
                      onMouseEnter={(e) => {
                        if (!isSelected) {
                          e.currentTarget.style.borderColor = `rgba(${rgb}, 0.6)`
                          e.currentTarget.style.backgroundColor = `rgba(${rgb}, 0.15)`
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (!isSelected) {
                          e.currentTarget.style.borderColor = `rgba(${rgb}, 0.4)`
                          e.currentTarget.style.backgroundColor = `rgba(${rgb}, 0.1)`
                        }
                      }}
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
                        fadeIn={layer.fadeIn || 0}
                        fadeOut={layer.fadeOut || 0}
                        isSelected={selectedLayerId === layer.id}
                        color={layerColor}
                        onFadeInChange={(newFadeIn) => {
                          const trimmedDuration = Math.max(0.01, layer.trimEnd - layer.trimStart)
                          const validFadeIn = Math.max(0, Math.min(trimmedDuration - (layer.fadeOut || 0), newFadeIn))
                          updateLayer(layer.id, { fadeIn: validFadeIn })
                        }}
                        onFadeOutChange={(newFadeOut) => {
                          const trimmedDuration = Math.max(0.01, layer.trimEnd - layer.trimStart)
                          const validFadeOut = Math.max(0, Math.min(trimmedDuration - (layer.fadeIn || 0), newFadeOut))
                          updateLayer(layer.id, { fadeOut: validFadeOut })
                        }}
                        isVisible={true}
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
                  {expandedLayerId === layer.id && (
                    <div className="layer-settings-panel" onClick={(e) => e.stopPropagation()} style={{ userSelect: 'none' }}>
                      <div className="layer-settings-header">
                        <h4>Nastavení: {layer.name}</h4>
                        <button
                          className="layer-settings-close-btn"
                          onClick={(e) => {
                            e.stopPropagation()
                            setExpandedLayerId(null)
                          }}
                          title="Zavřít nastavení"
                        >
                          ✕
                        </button>
                      </div>
                      <div className="layer-settings-content">
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
                        <div className="control-group">
                          <label>Začátek (s)</label>
                          <input
                            type="number"
                            min="0"
                            step="0.1"
                            value={layer.startTime.toFixed(1)}
                            onChange={(e) => updateLayer(layer.id, { startTime: parseFloat(e.target.value) || 0 })}
                          />
                        </div>
                        <div className="control-group">
                          <label>Trim Start (s)</label>
                          <input
                            type="number"
                            min="0"
                            max={layer.audioBuffer?.duration || 0}
                            step="0.1"
                            value={layer.trimStart.toFixed(1)}
                            onChange={(e) => {
                              const newTrimStart = Math.max(0, Math.min(parseFloat(e.target.value) || 0, layer.trimEnd - 0.1))
                              const newDuration = layer.trimEnd - newTrimStart
                              updateLayer(layer.id, {
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
                            min={(layer.trimStart || 0) + 0.1}
                            max={layer.audioBuffer?.duration || 0}
                            step="0.1"
                            value={layer.trimEnd.toFixed(1)}
                            onChange={(e) => {
                              const newTrimEnd = Math.max((layer.trimStart || 0) + 0.1, Math.min(parseFloat(e.target.value) || layer.audioBuffer?.duration || 0, layer.audioBuffer?.duration || 0))
                              const newDuration = newTrimEnd - (layer.trimStart || 0)
                              updateLayer(layer.id, {
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
                            max={Math.max(0.01, (layer.trimEnd || 0) - (layer.trimStart || 0))}
                            step="0.1"
                            value={layer.fadeIn.toFixed(1)}
                            onChange={(e) => {
                              const trimmedDuration = Math.max(0.01, (layer.trimEnd || 0) - (layer.trimStart || 0))
                              const newFadeIn = Math.max(0, Math.min(trimmedDuration - (layer.fadeOut || 0), parseFloat(e.target.value) || 0))
                              updateLayer(layer.id, { fadeIn: newFadeIn })
                            }}
                          />
                        </div>
                        <div className="control-group">
                          <label>Fade Out (s)</label>
                          <input
                            type="number"
                            min="0"
                            max={Math.max(0.01, (layer.trimEnd || 0) - (layer.trimStart || 0))}
                            step="0.1"
                            value={layer.fadeOut.toFixed(1)}
                            onChange={(e) => {
                              const trimmedDuration = Math.max(0.01, (layer.trimEnd || 0) - (layer.trimStart || 0))
                              const newFadeOut = Math.max(0, Math.min(trimmedDuration - (layer.fadeIn || 0), parseFloat(e.target.value) || 0))
                              updateLayer(layer.id, { fadeOut: newFadeOut })
                            }}
                          />
                        </div>
                        <div className="control-group">
                          <label>
                            <input
                              type="checkbox"
                              checked={layer.loop || false}
                              onChange={(e) => updateLayer(layer.id, { loop: e.target.checked })}
                            />
                            🔁 Loopovat zvuk
                          </label>
                        </div>
                        <button
                          className="btn-delete-layer"
                          onClick={() => {
                            if (window.confirm(`Opravdu chcete smazat vrstvu "${layer.name}"?`)) {
                              deleteLayer(layer.id)
                              setExpandedLayerId(null)
                            }
                          }}
                          title="Smazat vrstvu"
                        >
                          🗑️ Smazat vrstvu
                        </button>
                      </div>
                    </div>
                  )}
                </React.Fragment>
                )
              })}
            </div>
          </div>
        </div>
      </div>

      {/* History Panel */}
      {showHistory && (
        <div className="history-panel">
          <div className="history-panel-header">
            <h3>📜 Historie všech modelů</h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap', justifyContent: 'center', width: '100%' }}>
              <div className="history-filter-buttons">
                {Object.entries(HISTORY_TYPES).map(([key, { label, icon }]) => {
                  // Mapování history type na kategorii
                  const categoryMap = {
                    'all': 'file',
                    'tts': 'tts',
                    'f5tts': 'f5tts',
                    'music': 'music',
                    'bark': 'bark',
                    'applio': 'applio'
                  }
                  const category = categoryMap[key] || 'file'
                  const categoryColor = getCategoryColor(category, 0)
                  const rgb = hexToRgb(categoryColor)
                  const isActive = historyType === key

                  return (
                  <button
                    key={key}
                    className={`history-filter-btn ${isActive ? 'active' : ''}`}
                    onClick={() => setHistoryType(key)}
                    style={isActive ? {
                      background: `rgba(${rgb}, 0.2)`,
                      borderColor: `rgba(${rgb}, 0.4)`,
                      color: categoryColor
                    } : {}}
                    onMouseEnter={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.background = `rgba(${rgb}, 0.08)`
                        e.currentTarget.style.borderColor = `rgba(${rgb}, 0.2)`
                        e.currentTarget.style.color = categoryColor
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'
                        e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)'
                        e.currentTarget.style.color = 'rgba(255, 255, 255, 0.7)'
                      }
                    }}
                  >
                    <Icon name={icon} size={16} style={{ display: 'inline-block', marginRight: '6px', verticalAlign: 'middle' }} />
                    {label}
                  </button>
                  )
                })}
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
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
          </div>
          {historyLoading ? (
            <div className="history-loading">⏳ Načítání historie...</div>
          ) : history.length === 0 ? (
            <div className="history-empty">Historie je prázdná</div>
          ) : (
            <div className="history-list-compact">
              {history.map((entry) => (
                <HistoryItemPreview
                  key={`${entry.source}-${entry.id}`}
                  entry={entry}
                  onAddToEditor={addLayerFromHistory}
                />
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

      {/* Hidden file input for programmatic file selection */}
      <input
        ref={fileInputRef}
        type="file"
        accept="audio/*"
        multiple
        onChange={handleFileSelect}
        style={{ display: 'none' }}
      />

      {/* Layers List - přesunuto do timeline */}
      {/* Layer Editor - přesunuto do timeline */}
    </div>
  )
}

export default AudioEditor

