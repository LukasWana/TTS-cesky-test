import React, { useCallback, useMemo } from 'react'

/**
 * Komponenta pro waveform náhled v klipu
 */
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

export default LayerWaveform

