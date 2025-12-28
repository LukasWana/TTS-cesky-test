import React, { useState, useRef, useEffect, useMemo } from 'react'
import WaveSurfer from 'wavesurfer.js'
import { getWaveformCache, setWaveformCache } from '../../utils/waveformCache'

// Použij 127.0.0.1 místo localhost kvůli IPv6 (::1) na Windows/Chrome
const API_BASE_URL = 'http://127.0.0.1:8000'

/**
 * Komponenta pro náhled položky v historii
 */
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

  const [durationSec, setDurationSec] = useState(
    typeof cachedDuration === 'number' && cachedDuration > 0 ? cachedDuration : 0
  )

  useEffect(() => {
    setDurationSec(typeof cachedDuration === 'number' && cachedDuration > 0 ? cachedDuration : 0)
  }, [cachedDuration, audioUrl])

  const formatDurationMMSS = (time) => {
    const t = Math.max(0, Math.floor(Number(time) || 0))
    const minutes = Math.floor(t / 60)
    const seconds = Math.floor(t % 60)
    return `${minutes}:${seconds.toString().padStart(2, '0')}`
  }

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
        responsive: true,
        height: 40,
        normalize: true,
        interact: false,
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
              setDurationSec(duration)
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

      // Error handling
      wavesurfer.on('error', (error) => {
        if (error && typeof error === 'object') {
          const errorMessage = error.message || error.toString()
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

      // Timeout pro detekci pomalého načítání
      errorTimeoutRef.current = setTimeout(() => {
        if (isLoading) {
          console.warn('Audio se načítá příliš dlouho:', fullUrl)
        }
      }, 10000)

      // Načíst audio
      try {
        const hasCached = Array.isArray(cachedPeaks) && cachedPeaks.length > 0 && Array.isArray(cachedPeaks[0]) && typeof cachedDuration === 'number'

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

        const normalizePeaksToHeight = (peaks) => {
          if (!Array.isArray(peaks) || peaks.length === 0) return peaks
          if (!Array.isArray(peaks[0])) return peaks

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

          if (maxAbs <= 0) return peaks

          const height = 40
          const padding = 2
          const maxHeight = height / 2
          const availableHeight = maxHeight - padding
          const heightRatio = availableHeight / maxHeight
          const scale = maxAbs > 0 ? heightRatio / maxAbs : 1

          const normalized = peaks.map(channel => {
            if (!Array.isArray(channel)) return channel
            return channel.map(v => (v || 0) * scale)
          })

          return normalized
        }

        const getMaxPeaks = () => {
          const width = waveformRef.current?.clientWidth || 260
          return Math.max(600, Math.min(2000, Math.floor(width * 4)))
        }

        let peaksToUse = cachedPeaks
        if (hasCached) {
          const maxPeaks = getMaxPeaks()
          const ch0 = cachedPeaks[0]
          if (Array.isArray(ch0) && ch0.length > maxPeaks) {
            peaksToUse = [downsample(ch0, maxPeaks)]
          } else if (Array.isArray(ch0)) {
            peaksToUse = cachedPeaks
          }
        }

        const loadPromise = hasCached
          ? wavesurfer.load(fullUrl, peaksToUse, cachedDuration)
          : wavesurfer.load(fullUrl)
        if (loadPromise && typeof loadPromise.catch === 'function') {
          loadPromise.catch((error) => {
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
        if (loadError && loadError.name &&
            (loadError.name === 'AbortError' || loadError.name === 'NotAllowedError')) {
          return
        }
        console.error('Chyba při volání load():', loadError, fullUrl)
        setIsLoading(false)
        setHasError(true)
      }

      return () => {
        if (errorTimeoutRef.current) {
          clearTimeout(errorTimeoutRef.current)
          errorTimeoutRef.current = null
        }

        if (wavesurferRef.current) {
          try {
            if (wavesurferRef.current.isPlaying && wavesurferRef.current.isPlaying()) {
              wavesurferRef.current.pause()
            }
            if (wavesurferRef.current.isLoading && wavesurferRef.current.cancelLoad) {
              try {
                wavesurferRef.current.cancelLoad()
              } catch (e) {
                // Ignorovat chyby při cancelLoad
              }
            }
            const destroyResult = wavesurferRef.current.destroy()
            if (destroyResult && typeof destroyResult.catch === 'function') {
              destroyResult.catch((e) => {
                if (e.name !== 'AbortError' && e.name !== 'NotAllowedError') {
                  console.debug('Cleanup warning:', e)
                }
              })
            }
          } catch (e) {
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
  }, [fullUrl, shouldLoad, audioUrl, cachedPeaks, cachedDuration, isLoading])

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
    if (e.target.closest('.history-item-play-btn')) {
      return
    }
    if (onAddToEditor) onAddToEditor(entry)
  }

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
        {!hasError && typeof durationSec === 'number' && durationSec > 0 && (
          <div className="history-item-duration-badge" title="Celkový čas souboru">
            {formatDurationMMSS(durationSec)}
          </div>
        )}
      </div>
      <div className="history-item-compact-text">
        {prompt}
      </div>
    </div>
  )
}, (prevProps, nextProps) => {
  return prevProps.entry?.id === nextProps.entry?.id &&
         prevProps.entry?.audio_url === nextProps.entry?.audio_url &&
         (prevProps.entry?.text || prevProps.entry?.prompt) === (nextProps.entry?.text || nextProps.entry?.prompt)
})

export default HistoryItemPreview

