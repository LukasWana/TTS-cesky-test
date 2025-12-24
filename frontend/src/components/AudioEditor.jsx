import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import WaveSurfer from 'wavesurfer.js'
import './AudioEditor.css'
import { getHistory, getMusicHistory, getBarkHistory } from '../services/api'
import { getWaveformCache, setWaveformCache } from '../utils/waveformCache'

// Použij 127.0.0.1 místo localhost kvůli IPv6 (::1) na Windows/Chrome
const API_BASE_URL = 'http://127.0.0.1:8000'
const STORAGE_KEY = 'audio_editor_state'
const PROJECTS_STORAGE_KEY = 'audio_editor_projects'

// Komponenta pro waveform náhled v klipu
const LayerWaveform = React.memo(function LayerWaveform({
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
      const padding = 2 // Padding aby waveform nešel až na okraj

      // Nejprve najít max absolutní amplitudu v celém segmentu pro grafickou normalizaci
      let globalMaxAmplitude = 0
      for (let i = s0; i < s1; i++) {
        const raw = ch1 ? (ch0[i] + ch1[i]) / 2 : ch0[i]
        const abs = Math.abs(raw)
        if (abs > globalMaxAmplitude) globalMaxAmplitude = abs
      }

      // Vypočítat normalizační faktor: škálovat tak, aby vyplnil výšku (s paddingem)
      const availableHeight = (height / 2) - padding
      const scale = globalMaxAmplitude > 0 ? availableHeight / globalMaxAmplitude : 1

      // Renderovat waveform s grafickou normalizací na výšku
      for (let x = 0; x < width; x++) {
        const start = s0 + (x * step)
        const end = Math.min(s1, start + step)
        let min = 1
        let max = -1
        for (let i = start; i < end; i++) {
          const raw = ch1 ? (ch0[i] + ch1[i]) / 2 : ch0[i]
          const v = Math.max(-1, Math.min(1, raw))
          if (v < min) min = v
          if (v > max) max = v
        }
        // Aplikovat škálování pro vyplnění výšky canvasu
        const y1 = mid - (max * scale)
        const y2 = mid - (min * scale)
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
  const repeatWaveformUrl = useMemo(() => {
    if (!shouldUseRepeatWaveform) return null
    return renderWaveformDataUrl(audioBuffer, trimStart, trimEnd)
  }, [shouldUseRepeatWaveform, audioBuffer, trimStart, trimEnd, renderWaveformDataUrl])

  // Statický waveform pro non-loop (výrazně levnější než WaveSurfer, a hlavně nemizí při re-renderech)
  const staticWaveformUrl = useMemo(() => {
    if (!audioBuffer) return null
    const len = trimEnd - trimStart
    if (!(len > 0.01)) return null
    // Pro loop používáme repeatWaveformUrl výše
    if (shouldUseRepeatWaveform) return null
    return renderWaveformDataUrl(audioBuffer, trimStart, trimEnd)
  }, [audioBuffer, trimStart, trimEnd, shouldUseRepeatWaveform, renderWaveformDataUrl])

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

  if (staticWaveformUrl) {
    return (
      <div
        className="layer-waveform"
        style={{
          backgroundImage: `url(${staticWaveformUrl})`,
          backgroundRepeat: 'no-repeat',
          backgroundSize: '100% 100%',
          backgroundPosition: '0 0'
        }}
      />
    )
  }

  // Fallback: pokud nemáme buffer, zobraz placeholder (lepší než spouštět WaveSurfer na každém re-renderu editoru)
  return <div className="layer-waveform layer-waveform-placeholder" />
}, (prev, next) => {
  return (
    prev.audioBuffer === next.audioBuffer &&
    prev.trimStart === next.trimStart &&
    prev.trimEnd === next.trimEnd &&
    prev.duration === next.duration &&
    prev.loop === next.loop &&
    prev.startTime === next.startTime &&
    prev.loopAnchorTime === next.loopAnchorTime
  )
})

// Komponenta pro náhled položky v historii
const HistoryItemPreview = React.memo(function HistoryItemPreview({ entry, onAddToEditor }) {
  const waveformRef = useRef(null)
  const wavesurferRef = useRef(null)
  const containerRef = useRef(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [hasError, setHasError] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [shouldLoad, setShouldLoad] = useState(false)
  const errorTimeoutRef = useRef(null)
  const observerRef = useRef(null)

  const audioUrl = entry?.audio_url
  const prompt = entry?.text || entry?.prompt || 'Bez popisu'

  // Validace a vytvoření full URL
  const fullUrl = React.useMemo(() => {
    if (!audioUrl) {
      return null
    }
    if (audioUrl.startsWith('http://') || audioUrl.startsWith('https://')) {
      return audioUrl
    }
    // Zajistit, že URL začíná lomítkem
    const normalizedUrl = audioUrl.startsWith('/') ? audioUrl : `/${audioUrl}`
    return `${API_BASE_URL}${normalizedUrl}`
  }, [audioUrl])

  // Načíst cached peaks bez setState (nechceme re-initovat WaveSurfer)
  const cached = useMemo(() => (audioUrl ? getWaveformCache(audioUrl) : null), [audioUrl])
  const cachedPeaks = cached?.peaks
  const cachedDuration = cached?.duration

  // Canvas overlay odstraněn - WaveSurfer už renderuje waveform sám

  // Intersection Observer pro lazy loading - načítat pouze viditelné položky
  useEffect(() => {
    if (!containerRef.current || !fullUrl) {
      setIsLoading(false)
      return
    }

    // Vytvořit observer pro detekci, kdy je prvek viditelný
    observerRef.current = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            // Prvek je viditelný - začít načítat waveform
            setShouldLoad(true)
            // Odpojit observer, už není potřeba
            if (observerRef.current && containerRef.current) {
              observerRef.current.unobserve(containerRef.current)
            }
          }
        })
      },
      {
        rootMargin: '100px', // Začít načítat 100px před tím, než je prvek viditelný
        threshold: 0.01
      }
    )

    observerRef.current.observe(containerRef.current)

    return () => {
      if (observerRef.current && containerRef.current) {
        observerRef.current.unobserve(containerRef.current)
      }
    }
  }, [fullUrl])

  // Načíst waveform pouze když je prvek viditelný (shouldLoad = true)
  useEffect(() => {
    if (!waveformRef.current || !fullUrl || !shouldLoad) {
      return
    }

    // Reset states při novém načítání
    setHasError(false)
    setIsLoading(true)

    // Vyčistit předchozí timeout
    if (errorTimeoutRef.current) {
      clearTimeout(errorTimeoutRef.current)
      errorTimeoutRef.current = null
    }

    let wavesurfer = null

    try {
      wavesurfer = WaveSurfer.create({
        container: waveformRef.current,
        waveColor: 'rgba(255, 255, 255, 0.25)',
        progressColor: 'rgba(99, 102, 241, 0.6)',
        cursorColor: 'transparent',
        // Pozn.: barWidth/barGap/barRadius přepínají renderer do „sloupců“ (barcode look).
        // Pro náhledy chceme plynulý průběh jako v editoru -> necháme default waveform renderer.
        responsive: true,
        height: 40,
        normalize: true,
        interact: false,
        // Preview: MediaElement backend je výrazně lehčí než WebAudio decode pro waveform list
        backend: 'MediaElement',
        partialRender: true
      })

      wavesurferRef.current = wavesurfer

      // Handler pro úspěšné načtení - uložit peaks do cache
      wavesurfer.on('ready', () => {
        setHasError(false)
        setIsLoading(false)

        // Uložit peaks do cache pro budoucí použití
        try {
          if (audioUrl) {
            // v7: exportPeaks vrací Array<number[]> (per channel)
            // maxLength odvodíme od šířky pro lepší kvalitu cache a detailnější zobrazení
            // precision zvýšena na 6 pro zachování plynulých hodnot (místo binary 0/1)
            const width = waveformRef.current?.clientWidth || 260
            const maxLength = Math.max(600, Math.min(2000, Math.floor(width * 4)))
            const exported = wavesurfer.exportPeaks?.({
              channels: 1,
              maxLength,
              precision: 6
            })
            const duration = wavesurfer.getDuration?.()
            if (Array.isArray(exported) && exported.length > 0 && Array.isArray(exported[0]) && exported[0].length > 0 && typeof duration === 'number' && duration > 0) {
              setWaveformCache(audioUrl, {
                peaks: exported,
                duration,
                timestamp: Date.now()
              })
            }
          }
        } catch (e) {
          console.warn('Chyba při ukládání peaks do cache:', e)
        }

        // Zrušit timeout pro chybu, pokud existuje
        if (errorTimeoutRef.current) {
          clearTimeout(errorTimeoutRef.current)
          errorTimeoutRef.current = null
        }
      })

      // Error handling - pouze skutečné chyby
      wavesurfer.on('error', (error) => {
        // Ignorovat některé běžné chyby, které se mohou objevit při cleanup
        if (error && typeof error === 'object') {
          const errorMessage = error.message || error.toString()
          // Ignorovat chyby související s cleanup nebo abort
          if (errorMessage.includes('AbortError') ||
              errorMessage.includes('NotAllowedError') ||
              errorMessage.includes('cancelLoad')) {
            return
          }
        }
        console.error('WaveSurfer error při načítání audio:', error, fullUrl)
        setIsLoading(false)
        setHasError(true)
      })

      wavesurfer.on('play', () => setIsPlaying(true))
      wavesurfer.on('pause', () => setIsPlaying(false))
      wavesurfer.on('finish', () => setIsPlaying(false))

      // Timeout pro detekci pomalého načítání (10 sekund)
      errorTimeoutRef.current = setTimeout(() => {
        if (isLoading) {
          console.warn('Audio se načítá příliš dlouho:', fullUrl)
          // Nezobrazit chybu, jen logovat - možná se ještě načte
        }
      }, 10000)

      // Načíst audio
      try {
        // Největší win: pokud máme cached peaks + duration, WaveSurfer vykreslí waveform okamžitě
        const hasCached = Array.isArray(cachedPeaks) && cachedPeaks.length > 0 && Array.isArray(cachedPeaks[0]) && typeof cachedDuration === 'number'

        // Downsample peaks stabilně: pro každý bucket vezmi vzorek s největší |amplitudou|
        // a zachovej znaménko. Abs-only dělá waveform „potichu" a vizuálně divný.
        const downsample = (arr, targetLen) => {
          if (!Array.isArray(arr) || targetLen <= 0) return arr
          if (arr.length <= targetLen) return arr
          const out = new Array(targetLen)
          const step = arr.length / targetLen
          for (let i = 0; i < targetLen; i++) {
            const start = Math.floor(i * step)
            const end = Math.min(arr.length, Math.floor((i + 1) * step))
            let best = 0
            for (let j = start; j < end; j++) {
              const v = arr[j] || 0
              if (Math.abs(v) > Math.abs(best)) best = v
            }
            out[i] = best
          }
          return out
        }

        // Normalizace peaks na výšku: najít globální max a škálovat všechny hodnoty
        // Stejná logika jako v editoru - waveform vyplní celou výšku
        const normalizePeaksToHeight = (peaks) => {
          if (!Array.isArray(peaks) || peaks.length === 0) return peaks
          if (!Array.isArray(peaks[0])) return peaks

          // Najít max absolutní hodnotu v celém peaks array
          let maxAbs = 0
          for (let ch = 0; ch < peaks.length; ch++) {
            const channel = peaks[ch]
            if (Array.isArray(channel)) {
              for (let i = 0; i < channel.length; i++) {
                const abs = Math.abs(channel[i] || 0)
                if (abs > maxAbs) maxAbs = abs
              }
            }
          }

          // Pokud není co normalizovat, vrátit původní peaks
          if (maxAbs <= 0) return peaks

          // Stejná logika jako v LayerWaveform: vyplnit výšku s paddingem 2px
          // DŮLEŽITÉ: WaveSurfer očekává peaks v rozsahu -1 až 1, takže musíme škálovat
          // v rámci tohoto rozsahu, ne na pixely
          const height = 40
          const padding = 2
          const maxHeight = height / 2 // = 20px (maximální výška na jednu stranu)
          const availableHeight = maxHeight - padding // = 18px (dostupná výška s paddingem)
          const heightRatio = availableHeight / maxHeight // = 0.9 (90% výšky)
          const scale = maxAbs > 0 ? heightRatio / maxAbs : 1

          // Aplikovat škálování na všechny hodnoty (výsledek bude v rozsahu -0.9 až 0.9)
          const normalized = peaks.map(channel => {
            if (!Array.isArray(channel)) return channel
            return channel.map(v => (v || 0) * scale)
          })

          return normalized
        }
        const getMaxPeaks = () => {
          const width = waveformRef.current?.clientWidth || 260
          // Plynulý waveform potřebuje víc bodů než sloupce.
          // Držíme to rozumně kvůli velikosti cache a výkonu.
          return Math.max(600, Math.min(2000, Math.floor(width * 4)))
        }

        let peaksToUse = cachedPeaks
        if (hasCached) {
          const maxPeaks = getMaxPeaks()
          const ch0 = cachedPeaks[0]
          if (Array.isArray(ch0) && ch0.length > maxPeaks) {
            // Downsampling pro optimalizaci
            peaksToUse = [downsample(ch0, maxPeaks)]
          } else if (Array.isArray(ch0)) {
            // Použít cached peaks přímo
            peaksToUse = cachedPeaks
          }
        }

        const loadPromise = hasCached
          ? wavesurfer.load(fullUrl, peaksToUse, cachedDuration)
          : wavesurfer.load(fullUrl)
        if (loadPromise && typeof loadPromise.catch === 'function') {
          loadPromise.catch((error) => {
            // Ignorovat abort chyby
            if (error && error.name &&
                (error.name === 'AbortError' || error.name === 'NotAllowedError')) {
              return
            }
            console.error('Chyba při načítání audio URL:', error, fullUrl)
            setIsLoading(false)
            setHasError(true)
          })
        }
      } catch (loadError) {
        // Ignorovat abort chyby
        if (loadError && loadError.name &&
            (loadError.name === 'AbortError' || loadError.name === 'NotAllowedError')) {
          return
        }
        console.error('Chyba při volání load():', loadError, fullUrl)
        setIsLoading(false)
        setHasError(true)
      }

      return () => {
        // Vyčistit timeout
        if (errorTimeoutRef.current) {
          clearTimeout(errorTimeoutRef.current)
          errorTimeoutRef.current = null
        }

        if (wavesurferRef.current) {
          try {
            // Zastavit přehrávání
            if (wavesurferRef.current.isPlaying && wavesurferRef.current.isPlaying()) {
              wavesurferRef.current.pause()
            }
            // Zastavit načítání, pokud probíhá
            if (wavesurferRef.current.isLoading && wavesurferRef.current.cancelLoad) {
              try {
                wavesurferRef.current.cancelLoad()
              } catch (e) {
                // Ignorovat chyby při cancelLoad
              }
            }
            // Zničit instanci
            const destroyResult = wavesurferRef.current.destroy()
            if (destroyResult && typeof destroyResult.catch === 'function') {
              destroyResult.catch((e) => {
                // Ignorovat všechny cleanup chyby
                if (e.name !== 'AbortError' && e.name !== 'NotAllowedError') {
                  console.debug('Cleanup warning:', e)
                }
              })
            }
          } catch (e) {
            // Ignorovat všechny cleanup chyby
            if (e.name !== 'AbortError' && e.name !== 'NotAllowedError') {
              console.debug('Cleanup warning:', e)
            }
          }
          wavesurferRef.current = null
        }
      }
    } catch (err) {
      console.error('Chyba při vytváření WaveSurfer instance:', err)
      setIsLoading(false)
      setHasError(true)
    }
  }, [fullUrl, shouldLoad, audioUrl, cachedPeaks, cachedDuration])

  const togglePlay = (e) => {
    e.stopPropagation()
    if (wavesurferRef.current && !hasError) {
      try {
        wavesurferRef.current.playPause()
      } catch (error) {
        console.error('Chyba při přehrávání:', error)
        setHasError(true)
      }
    }
  }

  const handleClick = (e) => {
    // Pokud klikneme na play button, nechceme přidat do editoru
    if (e.target.closest('.history-item-play-btn')) {
      return
    }
    if (onAddToEditor) onAddToEditor(entry)
  }

  // Pokud není audio URL, nezobrazovat waveform
  if (!audioUrl || !fullUrl) {
    return (
      <div className="history-item-compact" onClick={handleClick}>
        <div className="history-item-compact-text">
          {prompt}
        </div>
        <div className="history-item-error" style={{ fontSize: '0.75rem', color: 'rgba(255, 255, 255, 0.5)', marginTop: '8px' }}>
          Audio není k dispozici
        </div>
      </div>
    )
  }

  return (
    <div
      ref={containerRef}
      className="history-item-compact"
      onClick={handleClick}
    >
      <div className="history-item-waveform-container">
        <button
          className="history-item-play-btn"
          onClick={togglePlay}
          title={isPlaying ? 'Pauza' : 'Přehrát'}
          disabled={hasError || isLoading || !shouldLoad}
        >
          {hasError ? '⚠️' : (isLoading && !shouldLoad ? '⏳' : (isPlaying ? '⏸' : '▶'))}
        </button>
        {!shouldLoad ? (
          <div className="history-item-waveform-placeholder" style={{
            flex: 1,
            minHeight: '40px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'rgba(255, 255, 255, 0.3)',
            fontSize: '0.7rem'
          }}>
            Načítání...
          </div>
        ) : hasError ? (
          <div className="history-item-waveform-error" style={{
            flex: 1,
            minHeight: '40px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'rgba(255, 255, 255, 0.4)',
            fontSize: '0.75rem'
          }}>
            Chyba při načítání
          </div>
        ) : (
          <div className="history-item-waveform" ref={waveformRef}></div>
        )}
      </div>
      <div className="history-item-compact-text">
        {prompt}
      </div>
    </div>
  )
}, (prevProps, nextProps) => {
  // Optimalizace: re-render pouze pokud se změnilo entry.id nebo entry.audio_url
  return prevProps.entry?.id === nextProps.entry?.id &&
         prevProps.entry?.audio_url === nextProps.entry?.audio_url &&
         (prevProps.entry?.text || prevProps.entry?.prompt) === (nextProps.entry?.text || nextProps.entry?.prompt)
})

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
  const [isExporting, setIsExporting] = useState(false)

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

      // Načíst data z API (rychle, bez waveformů)
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

      // Nastavit historii - waveformy se načtou lazy loadingem přes Intersection Observer
      setHistory(allHistory)
    } catch (err) {
      console.error('Chyba při načítání historie:', err)
    } finally {
      setHistoryLoading(false)
    }
  }

  // Načtení audio souboru z URL
  const loadAudioFromUrl = useCallback(async (audioUrl) => {
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
  }, [])

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

  // Přidání nové vrstvy z historie
  const addLayerFromHistory = useCallback(async (entry) => {
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
      setSelectedLayerId(prev => (prev === null ? newLayer.id : prev))
    } catch (err) {
      console.error('Chyba při načítání audio z historie:', err)
      alert('Chyba při načítání audio souboru z historie')
    }
  }, [loadAudioFromUrl])

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
    <div
      className="audio-editor"
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

