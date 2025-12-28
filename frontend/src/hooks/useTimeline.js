import { useState, useRef, useMemo } from 'react'

/**
 * Hook pro správu časové osy v AudioEditoru
 */
export function useTimeline(layers, manualMaxDuration) {
  const [timelineZoom, setTimelineZoom] = useState(1) // 1..10
  const [timelineBaseWidthPx, setTimelineBaseWidthPx] = useState(0)
  const [timelineHover, setTimelineHover] = useState({ visible: false, percent: 0, time: 0 })
  const [draggingClip, setDraggingClip] = useState(null)
  const [resizingClip, setResizingClip] = useState(null)
  const [isEditingMaxDuration, setIsEditingMaxDuration] = useState(false)
  const [maxDurationInput, setMaxDurationInput] = useState('')

  const timelineRef = useRef(null) // scroll kontejner
  const timelineContentRef = useRef(null) // vnitřní obsah s měnitelnou šířkou
  const timelineRulerRef = useRef(null)
  const maxDurationInputRef = useRef(null)
  const dragStartXRef = useRef(0)
  const dragStartTimeRef = useRef(0)

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

  return {
    // State
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
    // Refs
    timelineRef,
    timelineContentRef,
    timelineRulerRef,
    maxDurationInputRef,
    dragStartXRef,
    dragStartTimeRef,
    // Computed
    computedMaxDuration,
    maxDuration,
    timelineContentWidthPx,
    timelineTicks,
    // Helpers
    getTimelinePercentFromClientX,
    formatTimeMMSS,
    clamp01
  }
}

