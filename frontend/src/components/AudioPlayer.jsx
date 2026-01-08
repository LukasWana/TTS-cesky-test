import React, { useEffect, useRef, useState, useMemo } from 'react'
import WaveSurfer from 'wavesurfer.js'
import { getWaveformCache, setWaveformCache, deleteWaveformCache, isAudioNotFound, markAudioNotFound } from '../utils/waveformCache'
import './AudioPlayer.css'

function AudioPlayer({ audioUrl, variant = 'full' }) {
  const waveformRef = useRef(null)
  const wavesurfer = useRef(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [duration, setDuration] = useState(0)
  const [currentTime, setCurrentTime] = useState(0)
  const [hasError, setHasError] = useState(false)
  const retryRef = useRef(false)

  const fullUrl = audioUrl.startsWith('http')
    ? audioUrl
    : `http://127.0.0.1:8000${audioUrl}`

  // Načíst cached peaks bez setState (nechceme re-initovat WaveSurfer)
  const cached = useMemo(() => (audioUrl ? getWaveformCache(audioUrl) : null), [audioUrl])
  const cachedPeaks = cached?.peaks
  const cachedDuration = cached?.duration

  useEffect(() => {
    // Reset chyby při změně audioUrl
    setHasError(false)
    retryRef.current = false

    // Pokud víme, že soubor neexistuje, zobrazit chybu hned
    if (audioUrl && isAudioNotFound(audioUrl)) {
      setHasError(true)
      return
    }

    if (waveformRef.current) {
      wavesurfer.current = WaveSurfer.create({
        container: waveformRef.current,
        waveColor: 'rgba(255, 255, 255, 0.25)',
        progressColor: 'rgba(99, 102, 241, 0.6)',
        cursorColor: 'transparent',
        responsive: true,
        height: 40,
        normalize: true,
        interact: false,
        // WebAudio backend je robustnější pro dekódování různých formátů
        // MediaElement má problémy s některými WAV soubory (sample rate, atd.)
        backend: 'WebAudio',
        partialRender: true
      })

      // Použít cached peaks pro rychlé zobrazení waveformu
      // exportPeaks vrací Array<number[]> - každý prvek je array pro jeden kanál
      const hasValidCachedPeaks = Array.isArray(cachedPeaks) &&
        cachedPeaks.length > 0 &&
        Array.isArray(cachedPeaks[0]) &&
        cachedPeaks[0].length > 0 &&
        typeof cachedDuration === 'number' &&
        cachedDuration > 0

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
        const width = waveformRef.current?.clientWidth || 300
        // Plynulý waveform potřebuje víc bodů než sloupce.
        // Držíme to rozumně kvůli velikosti cache a výkonu.
        return Math.max(600, Math.min(2000, Math.floor(width * 4)))
      }

      const loadWithRetry = (url, peaks, duration) => {
        const p = peaks ? wavesurfer.current.load(url, peaks, duration) : wavesurfer.current.load(url)
        // Necháme veškerý error handling na 'error' eventu pro konzistenci
        return p.catch(() => { })
      }

      if (hasValidCachedPeaks) {
        const maxPeaks = getMaxPeaks()
        let peaksToUse = cachedPeaks[0].length > maxPeaks ? [downsample(cachedPeaks[0], maxPeaks)] : cachedPeaks
        loadWithRetry(fullUrl, peaksToUse, cachedDuration).catch(err => {
          // Ignorovat AbortError - je to normální při změně URL nebo unmountu komponenty
          if (err && (err.name === 'AbortError' || err.message?.includes('aborted'))) {
            return
          }
          console.error('Chyba při načítání audia (i bez peaks):', err)
          setHasError(true)
        })
      } else {
        wavesurfer.current.load(fullUrl).catch(err => {
          // Ignorovat AbortError - je to normální při změně URL nebo unmountu komponenty
          if (err && (err.name === 'AbortError' || err.message?.includes('aborted'))) {
            return
          }
          console.error('Chyba při načítání audia:', err)
          setHasError(true)
        })
      }

      wavesurfer.current.on('ready', () => {
        const dur = wavesurfer.current.getDuration()
        setDuration(dur)

        // Uložit peaks do cache pro budoucí použití
        try {
          if (audioUrl && !cachedPeaks) {
            // v7: exportPeaks vrací Array<number[]> (per channel)
            // maxLength odvodíme od šířky pro plynulejší průběh (a pořád rozumná velikost cache)
            const width = waveformRef.current?.clientWidth || 300
            const maxLength = Math.max(600, Math.min(2000, Math.floor(width * 4)))
            // precision zvýšena pro zachování plynulých hodnot (místo „zubatého“/kvantizovaného looku)
            const exported = wavesurfer.current.exportPeaks?.({ channels: 1, maxLength, precision: 6 })
            if (Array.isArray(exported) && exported.length > 0 && Array.isArray(exported[0]) && exported[0].length > 0 && typeof dur === 'number' && dur > 0) {
              setWaveformCache(audioUrl, {
                peaks: exported,
                duration: dur,
                timestamp: Date.now()
              })
            }
          }
        } catch (e) {
          console.warn('Chyba při ukládání peaks do cache:', e)
        }
      })

      // Error handling - pokud se načtení s cached peaks nepovede, zkusit bez peaks
      wavesurfer.current.on('error', (error) => {
        // Ignorovat AbortError - je to normální při změně URL nebo unmountu komponenty
        if (error && (error.name === 'AbortError' || error.message?.includes('aborted'))) {
          return
        }

        console.error('WaveSurfer error:', error)
        console.error('Error type:', error.constructor?.name || 'unknown')
        console.error('Audio URL:', fullUrl)

        // Zvlášť zpracovat MediaError (code 4 = Format error)
        if (error.code === 4 || error.message?.includes('Format error')) {
          console.error('MediaError: Format error - audio formát není podporován prohlížečem')
        }

        // Pokud už jsme v procesu retry nebo jsme ho dokončili, už nic neděláme
        if (retryRef.current) {
          setHasError(true)
          return
        }

        // Označíme, že jsme narazili na chybu a budeme zkoušet nápravu
        retryRef.current = true

        // Nejdřív ověřit, že soubor existuje a je dostupný
        fetch(fullUrl, { method: 'HEAD' })
          .then(res => {
            if (res.status === 404) {
              console.warn(`Audio 404 confirmed for ${audioUrl}`)
              deleteWaveformCache(audioUrl)
              markAudioNotFound(audioUrl)
              setHasError(true)
              return
            }

            // Soubor existuje, zkusíme reload bez peaks
            if (wavesurfer.current) {
              console.warn('Soubor existuje, zkouším reload bez peaks...')
              wavesurfer.current.load(fullUrl)
            }
          })
          .catch(err => {
            console.error('HEAD request failed:', err)
            setHasError(true)
          })
      })

      wavesurfer.current.on('audioprocess', () => {
        setCurrentTime(wavesurfer.current.getCurrentTime())
      })

      wavesurfer.current.on('play', () => setIsPlaying(true))
      wavesurfer.current.on('pause', () => setIsPlaying(false))
      wavesurfer.current.on('finish', () => setIsPlaying(false))

      return () => {
        if (wavesurfer.current) {
          try {
            // Zastavit přehrávání a uvolnit zdroje před destroy
            wavesurfer.current.pause()
            wavesurfer.current.unload()
          } catch (e) {
            // Ignorovat chyby při cleanup
          }
          try {
            wavesurfer.current.destroy()
          } catch (e) {
            // Ignorovat chyby při destroy
          }
          wavesurfer.current = null
        }
      }
    }
  }, [fullUrl, cachedPeaks, cachedDuration, audioUrl])

  const togglePlay = () => {
    if (wavesurfer.current) {
      wavesurfer.current.playPause()
    }
  }

  const handleDownload = () => {
    const link = document.createElement('a')
    link.href = fullUrl
    link.download = `tts-output-${Date.now()}.wav`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const formatTime = (time) => {
    const minutes = Math.floor(time / 60)
    const seconds = Math.floor(time % 60)
    return `${minutes}:${seconds.toString().padStart(2, '0')}`
  }

  return (
    <div className={`audio-player-section ${variant === 'compact' ? 'compact' : ''}`}>
      {variant !== 'compact' && (
        <div className="audio-player-header">
          <h2>Výstup</h2>
          <div className="audio-time">
            {formatTime(currentTime)} / {formatTime(duration)}
          </div>
        </div>
      )}

      <div className="audio-player-main">
        <button
          className={`play-button-large ${isPlaying ? 'playing' : ''}`}
          onClick={togglePlay}
          disabled={hasError}
        >
          {hasError ? '⚠️' : (isPlaying ? '⏸' : '▶')}
        </button>

        <div className="waveform-wrap">
          <div className="waveform-container" ref={waveformRef} style={{ display: hasError ? 'none' : 'block' }}></div>
          {variant === 'compact' && !hasError && typeof duration === 'number' && duration > 0 && (
            <div className="audio-duration-badge" title="Celkový čas souboru">
              {formatTime(duration)}
            </div>
          )}
          {hasError && <div className="waveform-error">Soubor nebyl nalezen</div>}
        </div>

        <button className="download-button-large" onClick={handleDownload} title="Stáhnout audio" disabled={hasError}>
          💾
        </button>
      </div>
    </div>
  )
}

export default AudioPlayer





