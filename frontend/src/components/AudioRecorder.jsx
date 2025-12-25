import React, { useState, useRef } from 'react'
import { recordVoice } from '../services/api'
import './AudioRecorder.css'

function AudioRecorder({ onRecordComplete, language = 'cs' }) {
  const [isRecording, setIsRecording] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)
  const [error, setError] = useState(null)
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])
  const timerRef = useRef(null)

  const startRecording = async () => {
    try {
      setError(null)
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })

      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      chunksRef.current = []

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data)
        }
      }

      mediaRecorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/wav' })

        // Zastavení streamu
        stream.getTracks().forEach(track => track.stop())

        // Odeslání na server
        try {
          await handleRecordComplete(blob)
        } catch (err) {
          setError('Chyba při ukládání nahrávky: ' + err.message)
        }
      }

      mediaRecorder.start()
      setIsRecording(true)
      setRecordingTime(0)

      // Timer pro zobrazení času
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1)
      }, 1000)

    } catch (err) {
      setError('Chyba při přístupu k mikrofonu: ' + err.message)
      console.error('Recording error:', err)
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }
    }
  }

  const handleRecordComplete = async (blob) => {
    try {
      // Konverze blob na base64
      const reader = new FileReader()
      reader.onloadend = async () => {
        try {
          const base64data = reader.result
          const result = await recordVoice(base64data, null, language)
          if (onRecordComplete) {
            onRecordComplete(result)  // Předat result místo blob
          }
        } catch (err) {
          throw new Error('Chyba při ukládání nahrávky: ' + err.message)
        }
      }
      reader.readAsDataURL(blob)
    } catch (err) {
      throw new Error('Chyba při zpracování nahrávky: ' + err.message)
    }
  }

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="audio-recorder">
      {!isRecording ? (
        <button
          className="record-button start"
          onClick={startRecording}
        >
          🎤 Začít nahrávat
        </button>
      ) : (
        <div className="recording-controls">
          <div className="recording-indicator">
            <span className="recording-dot"></span>
            Nahrávání: {formatTime(recordingTime)}
          </div>
          <button
            className="record-button stop"
            onClick={stopRecording}
          >
            ⏹ Zastavit
          </button>
        </div>
      )}

      {error && (
        <div className="recorder-error">
          ⚠️ {error}
        </div>
      )}

      <p className="recorder-hint">
        Minimálně 6 sekund čistého audio pro nejlepší výsledky
      </p>
    </div>
  )
}

export default AudioRecorder

