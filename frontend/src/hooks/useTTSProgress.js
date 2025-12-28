import { useState, useEffect, useRef } from 'react'
import { subscribeToTtsProgress, getTtsProgress } from '../services/api'

/**
 * Hook pro správu TTS progress tracking (SSE + fallback polling)
 */
export const useTTSProgress = () => {
  const [ttsProgress, setTtsProgress] = useState(null)
  const progressEventSourceRef = useRef(null)
  const progressPollIntervalRef = useRef(null)
  const progressStoppedRef = useRef(false)

  const startProgressTracking = (jobId) => {
    // Zrušit předchozí progress tracking
    if (progressEventSourceRef.current) {
      progressEventSourceRef.current.close()
      progressEventSourceRef.current = null
    }
    if (progressPollIntervalRef.current) {
      clearInterval(progressPollIntervalRef.current)
      progressPollIntervalRef.current = null
    }
    progressStoppedRef.current = false

    // Nastavit počáteční progress
    setTtsProgress({ percent: 0, message: 'Odesílám požadavek…', eta_seconds: null })

    // Připojit se k SSE streamu
    const eventSource = subscribeToTtsProgress(
      jobId,
      (progressData) => {
        if (progressStoppedRef.current) return
        setTtsProgress(progressData)

        if (progressData.status === 'done' || progressData.status === 'error') {
          progressStoppedRef.current = true
          if (progressPollIntervalRef.current) {
            clearInterval(progressPollIntervalRef.current)
            progressPollIntervalRef.current = null
          }
        }
      },
      (error) => {
        console.error('SSE progress error:', error)
        // Fallback na polling
        if (progressStoppedRef.current) return
        if (progressPollIntervalRef.current) return

        const poll = async () => {
          if (progressStoppedRef.current) return
          try {
            const p = await getTtsProgress(jobId)
            setTtsProgress(p)
            if (p?.status === 'done' || p?.status === 'error' || (typeof p?.percent === 'number' && p.percent >= 100)) {
              progressStoppedRef.current = true
              if (progressPollIntervalRef.current) {
                clearInterval(progressPollIntervalRef.current)
                progressPollIntervalRef.current = null
              }
            }
          } catch (_e) {
            // ignore
          }
        }

        poll()
        progressPollIntervalRef.current = setInterval(poll, 500)
      }
    )

    progressEventSourceRef.current = eventSource
  }

  const stopProgressTracking = () => {
    progressStoppedRef.current = true
    if (progressEventSourceRef.current) {
      progressEventSourceRef.current.close()
      progressEventSourceRef.current = null
    }
    if (progressPollIntervalRef.current) {
      clearInterval(progressPollIntervalRef.current)
      progressPollIntervalRef.current = null
    }
    setTtsProgress(null)
  }

  // Cleanup při unmount
  useEffect(() => {
    return () => {
      stopProgressTracking()
    }
  }, [])

  return {
    ttsProgress,
    setTtsProgress,
    startProgressTracking,
    stopProgressTracking
  }
}

