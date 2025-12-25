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
  fadeIn = 0,
  fadeOut = 0,
  isSelected = false,
  onFadeInChange = null,
  onFadeOutChange = null,
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

  // Vypočítat fade procenta pro vizualizaci
  const trimmedDuration = Math.max(0.01, trimEnd - trimStart)
  const fadeInPercent = trimmedDuration > 0 ? Math.min(100, (fadeIn / trimmedDuration) * 100) : 0
  const fadeOutPercent = trimmedDuration > 0 ? Math.min(100, (fadeOut / trimmedDuration) * 100) : 0


  // Render fade overlay
  const renderFadeOverlay = () => {
    if (fadeIn <= 0 && fadeOut <= 0) return null
    return (
      <div
        className="fade-overlay"
        style={{
          background: `linear-gradient(
            to right,
            rgba(0, 0, 0, 0.4) 0%,
            rgba(0, 0, 0, 0.4) ${fadeInPercent}%,
            transparent ${fadeInPercent}%,
            transparent ${100 - fadeOutPercent}%,
            rgba(0, 0, 0, 0.4) ${100 - fadeOutPercent}%,
            rgba(0, 0, 0, 0.4) 100%
          )`,
          pointerEvents: 'none'
        }}
      />
    )
  }

  // Render fade handles
  const renderFadeHandles = () => {
    if (!isSelected || (!onFadeInChange && !onFadeOutChange)) return null
    return (
      <>
        {fadeIn > 0 && onFadeInChange && (
          <div
            className="fade-handle fade-handle-in"
            style={{ left: `${fadeInPercent}%` }}
            onMouseDown={(e) => {
              e.stopPropagation()
              const startX = e.clientX
              const startFadeIn = fadeIn
              const rect = e.currentTarget.closest('.layer-clip')?.getBoundingClientRect()
              if (!rect) return

              const handleMouseMove = (moveE) => {
                const deltaX = moveE.clientX - startX
                const deltaPercent = (deltaX / rect.width) * 100
                const deltaTime = (deltaPercent / 100) * trimmedDuration
                const newFadeIn = Math.max(0, Math.min(trimmedDuration - fadeOut, startFadeIn + deltaTime))
                onFadeInChange(newFadeIn)
              }

              const handleMouseUp = () => {
                document.removeEventListener('mousemove', handleMouseMove)
                document.removeEventListener('mouseup', handleMouseUp)
              }

              document.addEventListener('mousemove', handleMouseMove)
              document.addEventListener('mouseup', handleMouseUp)
            }}
            title={`Fade In: ${fadeIn.toFixed(2)}s`}
          />
        )}
        {fadeOut > 0 && onFadeOutChange && (
          <div
            className="fade-handle fade-handle-out"
            style={{ right: `${fadeOutPercent}%` }}
            onMouseDown={(e) => {
              e.stopPropagation()
              const startX = e.clientX
              const startFadeOut = fadeOut
              const rect = e.currentTarget.closest('.layer-clip')?.getBoundingClientRect()
              if (!rect) return

              const handleMouseMove = (moveE) => {
                const deltaX = moveE.clientX - startX
                const deltaPercent = (deltaX / rect.width) * 100
                const deltaTime = (deltaPercent / 100) * trimmedDuration
                const newFadeOut = Math.max(0, Math.min(trimmedDuration - fadeIn, startFadeOut - deltaTime))
                onFadeOutChange(newFadeOut)
              }

              const handleMouseUp = () => {
                document.removeEventListener('mousemove', handleMouseMove)
                document.removeEventListener('mouseup', handleMouseUp)
              }

              document.addEventListener('mousemove', handleMouseMove)
              document.addEventListener('mouseup', handleMouseUp)
            }}
            title={`Fade Out: ${fadeOut.toFixed(2)}s`}
          />
        )}
      </>
    )
  }

  if (shouldUseRepeatWaveform && repeatWaveformUrl) {
    const cycle = Math.max(0.05, (trimEnd - trimStart))
    const tilePercent = Math.max(1, (cycle / Math.max(duration, 0.001)) * 100)
    // Fáze: kde v cyklu jsme na levém okraji klipu (t = startTime)
    const anchor = loopAnchorTime ?? startTime
    const phaseSeconds = ((startTime - anchor) % cycle + cycle) % cycle
    const phasePercentOfTile = (phaseSeconds / cycle) * 100

    return (
      <div className="layer-waveform-wrapper">
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
        {renderFadeOverlay()}
        {renderFadeHandles()}
      </div>
    )
  }

  if (staticWaveformUrl) {
    return (
      <div className="layer-waveform-wrapper">
        <div
          className="layer-waveform"
          style={{
            backgroundImage: `url(${staticWaveformUrl})`,
            backgroundRepeat: 'no-repeat',
            backgroundSize: '100% 100%',
            backgroundPosition: '0 0'
          }}
        />
        {renderFadeOverlay()}
        {renderFadeHandles()}
      </div>
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
    prev.loopAnchorTime === next.loopAnchorTime &&
    prev.fadeIn === next.fadeIn &&
    prev.fadeOut === next.fadeOut &&
    prev.isSelected === next.isSelected
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
  // Optimalizace: re-render pouze pokud se změnilo entry.id nebo entry.audio_url
  return prevProps.entry?.id === nextProps.entry?.id &&
         prevProps.entry?.audio_url === nextProps.entry?.audio_url &&
         (prevProps.entry?.text || prevProps.entry?.prompt) === (nextProps.entry?.text || nextProps.entry?.prompt)
})

function AudioEditor() {
  const [layers, setLayers] = useState([])
  const [selectedLayerId, setSelectedLayerId] = useState(null)
  const [expandedLayerId, setExpandedLayerId] = useState(null) // ID vrstvy s otevřeným panelem nastavení
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [masterVolume, setMasterVolume] = useState(1.0)
  const [masterLevel, setMasterLevel] = useState({ left: 0, right: 0 })
  const [playbackPosition, setPlaybackPosition] = useState(0)
  const [manualMaxDuration, setManualMaxDuration] = useState(null) // null = auto (dle vrstev)
  const [isEditingMaxDuration, setIsEditingMaxDuration] = useState(false)
  const [maxDurationInput, setMaxDurationInput] = useState('')
  const [timelineZoom, setTimelineZoom] = useState(1) // 1..10
  const [timelineBaseWidthPx, setTimelineBaseWidthPx] = useState(0)
  const [timelineHover, setTimelineHover] = useState({ visible: false, percent: 0, time: 0 })
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
  const timelineRef = useRef(null) // scroll kontejner
  const timelineContentRef = useRef(null) // vnitřní obsah s měnitelnou šířkou
  const timelineRulerRef = useRef(null)
  const maxDurationInputRef = useRef(null)
  const dragStartXRef = useRef(0)
  const dragStartTimeRef = useRef(0)
  const isLoadingStateRef = useRef(false)
  const saveTimeoutRef = useRef(null)
  const layerIdCounterRef = useRef(0) // Counter pro unikátní ID
  const didHydrateFromStorageRef = useRef(false) // ochrana proti dvojitému běhu useEffect v React.StrictMode (DEV)

  const computedMaxDuration = useMemo(() => {
    const max = layers.reduce((acc, layer) => {
      const endTime = (layer?.startTime || 0) + (layer?.duration || 0)
      return Math.max(acc, endTime)
    }, 0)
    return Math.max(max, 10) // Minimálně 10 sekund
  }, [layers])

  const maxDuration = useMemo(() => {
    if (typeof manualMaxDuration === 'number' && Number.isFinite(manualMaxDuration) && manualMaxDuration > 0) {
      return Math.max(computedMaxDuration, manualMaxDuration)
    }
    return computedMaxDuration
  }, [computedMaxDuration, manualMaxDuration])

  const timelineContentWidthPx = useMemo(() => {
    const base = Math.max(300, timelineBaseWidthPx || 0)
    const z = Math.max(1, Math.min(10, Number(timelineZoom) || 1))
    return Math.max(base, Math.floor(base * z))
  }, [timelineBaseWidthPx, timelineZoom])

  const clamp01 = (v) => Math.max(0, Math.min(1, v))

  const getTimelinePercentFromClientX = (clientX) => {
    const scrollEl = timelineRef.current
    const contentEl = timelineContentRef.current
    const contentWidth = contentEl?.clientWidth || timelineContentWidthPx || 1
    if (!scrollEl || !Number.isFinite(contentWidth) || contentWidth <= 0) return 0
    const rect = scrollEl.getBoundingClientRect()
    const x = (clientX - rect.left) + (scrollEl.scrollLeft || 0)
    return clamp01(x / contentWidth)
  }

  const formatTimeMMSS = (time) => {
    const total = Math.max(0, Math.floor(time || 0))
    const minutes = Math.floor(total / 60)
    const seconds = total % 60
    return `${minutes}:${seconds.toString().padStart(2, '0')}`
  }

  const getNiceStep = (minStepSec) => {
    const candidates = [1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600]
    for (const c of candidates) {
      if (c >= minStepSec) return c
    }
    return candidates[candidates.length - 1]
  }

  const timelineTicks = useMemo(() => {
    const durationSec = Math.max(1, Math.ceil(maxDuration))
    const widthPx = Math.max(1, timelineContentWidthPx)
    const pxPerSecond = widthPx / durationSec

    const minLabelPx = 90 // cíleně větší, aby se popisky nikdy neslévaly
    const majorStepSec = getNiceStep(minLabelPx / Math.max(pxPerSecond, 0.0001))
    const minorStepSec = majorStepSec >= 10 ? Math.max(1, Math.floor(majorStepSec / 5)) : majorStepSec

    const ticks = []
    for (let s = 0; s <= durationSec; s += minorStepSec) {
      const isMajor = (s % majorStepSec) === 0
      ticks.push({
        sec: s,
        percent: (s / durationSec) * 100,
        isMajor
      })
    }
    // vždy přidat poslední tick na konci (pro přesný konec i když minorStep nesedí)
    if (ticks.length === 0 || ticks[ticks.length - 1].sec !== durationSec) {
      ticks.push({ sec: durationSec, percent: 100, isMajor: true })
    }
    return { ticks, majorStepSec, minorStepSec }
  }, [maxDuration, timelineContentWidthPx])

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
  }, [layers, masterVolume, currentTime, selectedLayerId, showHistory, historyType, maxDuration, manualMaxDuration])

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

        // Validace fade in/out hodnot
        if (updates.fadeIn !== undefined || updates.fadeOut !== undefined) {
          const trimmedDuration = Math.max(0.01, (next.trimEnd || 0) - (next.trimStart || 0))
          const fadeIn = next.fadeIn || 0
          const fadeOut = next.fadeOut || 0

          // Zajistit, aby fade in + fade out nepřesáhly trimmedDuration
          if (fadeIn + fadeOut > trimmedDuration) {
            if (updates.fadeIn !== undefined) {
              // Pokud se mění fadeIn, upravit fadeOut
              next.fadeIn = Math.max(0, Math.min(trimmedDuration, fadeIn))
              next.fadeOut = Math.max(0, Math.min(trimmedDuration - next.fadeIn, fadeOut))
            } else if (updates.fadeOut !== undefined) {
              // Pokud se mění fadeOut, upravit fadeIn
              next.fadeOut = Math.max(0, Math.min(trimmedDuration, fadeOut))
              next.fadeIn = Math.max(0, Math.min(trimmedDuration - next.fadeOut, fadeIn))
            }
          } else {
            // Omezit jednotlivé hodnoty na trimmedDuration
            next.fadeIn = Math.max(0, Math.min(trimmedDuration, fadeIn))
            next.fadeOut = Math.max(0, Math.min(trimmedDuration, fadeOut))
          }
        }

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
        const fadeInDuration = Math.min(layer.fadeIn || 0, trimmedDuration)
        const fadeOutDuration = Math.min(layer.fadeOut || 0, trimmedDuration)

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
              {layers.map((layer, index) => (
                <React.Fragment key={layer.id}>
                  <div
                    className={`layer-track ${selectedLayerId === layer.id ? 'selected' : ''}`}
                    onClick={() => setSelectedLayerId(layer.id)}
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
                        fadeIn={layer.fadeIn || 0}
                        fadeOut={layer.fadeOut || 0}
                        isSelected={selectedLayerId === layer.id}
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
              ))}
            </div>
          </div>
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

      {/* Layers List - přesunuto do timeline */}
      {/* Layer Editor - přesunuto do timeline */}
    </div>
  )
}

export default AudioEditor

