import React, { useEffect, useRef, useState } from 'react'
import WaveSurfer from 'wavesurfer.js'
import './AudioPlayer.css'

function AudioPlayer({ audioUrl }) {
  const waveformRef = useRef(null)
  const wavesurfer = useRef(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [duration, setDuration] = useState(0)
  const [currentTime, setCurrentTime] = useState(0)

  const fullUrl = audioUrl.startsWith('http')
    ? audioUrl
    : `http://localhost:8000${audioUrl}`

  useEffect(() => {
    if (waveformRef.current) {
      wavesurfer.current = WaveSurfer.create({
        container: waveformRef.current,
        waveColor: '#6366f1',
        progressColor: '#a5b4fc',
        cursorColor: '#fff',
        barWidth: 2,
        barRadius: 3,
        responsive: true,
        height: 80,
        normalize: true,
        partialRender: true
      })

      wavesurfer.current.load(fullUrl)

      wavesurfer.current.on('ready', () => {
        setDuration(wavesurfer.current.getDuration())
      })

      wavesurfer.current.on('audioprocess', () => {
        setCurrentTime(wavesurfer.current.getCurrentTime())
      })

      wavesurfer.current.on('play', () => setIsPlaying(true))
      wavesurfer.current.on('pause', () => setIsPlaying(false))
      wavesurfer.current.on('finish', () => setIsPlaying(false))

      return () => {
        if (wavesurfer.current) {
          wavesurfer.current.destroy()
        }
      }
    }
  }, [fullUrl])

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
    <div className="audio-player-section">
      <div className="audio-player-header">
        <h2>Výstup</h2>
        <div className="audio-time">
          {formatTime(currentTime)} / {formatTime(duration)}
        </div>
      </div>

      <div className="audio-player-main">
        <button className="play-button-large" onClick={togglePlay}>
          {isPlaying ? '⏸' : '▶️'}
        </button>

        <div className="waveform-container" ref={waveformRef}></div>

        <button className="download-button-large" onClick={handleDownload}>
          💾
        </button>
      </div>
    </div>
  )
}

export default AudioPlayer





