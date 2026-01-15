/**
 * Voice Assistant - Content Script
 * Simplified audio playback with error handling
 */

var audio = null;
var isPlaying = false;
var isPaused = false;

function log(message) {
  console.log('[Voice Assistant] ' + message);
}

// ================= STREAMING LOGIC =================

var audioCtx = null;
var nextStartTime = 0;
var isStreaming = false;
var streamPaused = false;
var streamPauseTime = 0; // Where we paused in context time
var streamOffsetComp = 0; // Compensation if we paused

function initAudioContext() {
  if (!audioCtx) {
    var AudioContext = window.AudioContext || window.webkitAudioContext;
    audioCtx = new AudioContext();
    nextStartTime = 0;
  } else if (audioCtx.state === 'suspended') {
    audioCtx.resume();
  }
}

function handleStreamChunk(base64Audio, chunkIndex, totalChunks, pauseAfterMs) {
  initAudioContext();
  isStreaming = true;
  isPlaying = true;

  // Base64 to ArrayBuffer
  var binaryString = atob(base64Audio);
  var len = binaryString.length;
  var bytes = new Uint8Array(len);
  for (var i = 0; i < len; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }

  // Decode and Schedule
  audioCtx.decodeAudioData(bytes.buffer, function (buffer) {
    playBufferedChunk(buffer, pauseAfterMs);
  }, function (e) {
    log('Error decoding chunk ' + chunkIndex + ': ' + e.message);
  });
}

function playBufferedChunk(buffer, pauseAfterMs) {
  var source = audioCtx.createBufferSource();
  source.buffer = buffer;
  source.connect(audioCtx.destination);

  // Schedule
  // Ensure we consistently schedule after the previous chunk
  // Use a small lookahead or audioCtx.currentTime if we fell behind
  var currentTime = audioCtx.currentTime;
  if (nextStartTime < currentTime) {
    nextStartTime = currentTime;
  }

  source.start(nextStartTime);

  // Update next start time: duration + pause
  var pauseSec = (pauseAfterMs || 0) / 1000.0;
  nextStartTime += buffer.duration + pauseSec;

  source.onended = function () {
    // If this was the last pending chunk (heuristic), we could mark done.
    // But better to wait for explicit 'stream_complete' or 'audio_played' from background logic.
    // However, source.onended fires when THIS chunk ends.
  };
}

function stopStream() {
  if (audioCtx) {
    try {
      audioCtx.close();
    } catch (e) { }
    audioCtx = null;
  }
  isStreaming = false;
  isPlaying = false;
  nextStartTime = 0;
  log('Stream stopped');
}
// ===================================================

function handleMessage(request, sender, sendResponse) {
  log('[Content] Received message:', request.action);

  switch (request.action) {
    case 'play_audio':
      log('[Content] play_audio - URL type:', typeof request.url);
      log('[Content] play_audio - URL starts with blob:', request.url ? request.url.startsWith('blob:') : 'null');
      log('[Content] play_audio - URL starts with http:', request.url ? request.url.startsWith('http') : 'null');
      log('[Content] play_audio - URL starts with /api:', request.url ? request.url.startsWith('/api') : 'null');
      stopStream(); // Ensure stream is stopped if upgrading to file playback
      playAudio(request.url, request.isLast);
      sendResponse({ success: true });
      break;

    case 'play_stream_chunk':
      handleStreamChunk(request.audio, request.chunkIndex, request.totalChunks, request.pause_after);
      sendResponse({ success: true });
      break;

    case 'stop':
      stopAudio();
      stopStream();
      sendResponse({ success: true });
      break;

    case 'pause':
      pauseAudio();
      if (audioCtx) audioCtx.suspend();
      sendResponse({ success: true });
      break;

    case 'resume':
      resumeAudio();
      if (audioCtx) audioCtx.resume();
      sendResponse({ success: true });
      break;

    case 'status':
      updateStatus(request.message);
      sendResponse({ success: true });
      break;

    case 'get_state':
      sendResponse({ isPlaying: isPlaying, isPaused: isPaused });
      break;

    case 'fetch_audio':
      log('[Content] fetch_audio request:', request.url);
      fetchAudioAsBlob(request.url).then(function (blobUrl) {
        if (blobUrl) {
          sendResponse({ success: true, blobUrl: blobUrl });
        } else {
          sendResponse({ success: false, error: 'Failed to fetch audio' });
        }
      }).catch(function (err) {
        sendResponse({ success: false, error: err.message });
      });
      return true;

  }
  return true;
}

function playAudio(url, isLast) {
  log('[playAudio] Attempting to play: ' + url);

  if (!url) {
    log('[playAudio] Error: Empty URL');
    chrome.runtime.sendMessage({ action: 'audio_error', error: 'Empty URL - audio not available yet' });
    return;
  }

  // Validate URL format
  // Validate URL format
  if (url.indexOf('http://') !== 0 && url.indexOf('https://') !== 0 && url.indexOf('data:') !== 0) {
    log('[playAudio] Error: Invalid URL format: ' + url.substring(0, 50) + '...');
    chrome.runtime.sendMessage({ action: 'audio_error', error: 'Invalid URL format: ' + url.substring(0, 20) });
    return;
  }

  try {
    stopAudio();

    audio = new Audio();
    audio.src = url;
    audio.preload = 'auto';
    audio.crossOrigin = 'anonymous';

    log('[playAudio] Audio created with URL: ' + url);

    audio.onloadstart = function () {
      log('[playAudio] Loading started...');
    };

    audio.oncanplay = function () {
      log('[playAudio] Can play - attempting to start playback');
      isPaused = false;
    };

    audio.onended = function () {
      log('[playAudio] Playback ended naturally');
      isPlaying = false;
      isPaused = false;
      chrome.runtime.sendMessage({ action: 'audio_played' });
    };

    audio.onerror = function (e) {
      var errorMsg = 'Unknown';
      var errorCode = 'N/A';
      if (audio.error) {
        errorCode = audio.error.code;
        switch (audio.error.code) {
          case 1: errorMsg = 'ABORTED'; break;
          case 2: errorMsg = 'NETWORK'; break;
          case 3: errorMsg = 'DECODE'; break;
          case 4: errorMsg = 'SRC_NOT_SUPPORTED'; break;
          default: errorMsg = audio.error.message || 'Unknown';
        }
      }
      log('[playAudio] ERROR - Code: ' + errorCode + ', Message: ' + errorMsg);
      log('[playAudio] Source URL: ' + url);
      log('[playAudio] Current state: isPlaying=' + isPlaying + ', isPaused=' + isPaused);
      isPlaying = false;
      isPaused = false;
      chrome.runtime.sendMessage({
        action: 'audio_error',
        error: 'Audio error (' + errorCode + '): ' + errorMsg
      });
    };

    audio.play().then(function () {
      log('[playAudio] Playback started successfully');
      isPlaying = true;
      isPaused = false;
    }).catch(function (err) {
      log('[playAudio] Play promise rejected: ' + err.message);
      log('[playAudio] This might be due to autoplay policy - try interacting with the page first');
      isPlaying = false;
      chrome.runtime.sendMessage({ action: 'audio_error', error: 'Autoplay blocked: ' + err.message });
    });

  } catch (err) {
    log('[playAudio] Exception in playAudio: ' + err.message);
    log('[playAudio] Stack: ' + err.stack);
    isPlaying = false;
    chrome.runtime.sendMessage({ action: 'audio_error', error: 'Exception: ' + err.message });
  }
}

function stopAudio() {
  if (audio) {
    audio.pause();
    audio.currentTime = 0;
    audio.src = '';
    audio = null;
  }
  isPlaying = false;
  isPaused = false;
  log('Stopped');
}

function pauseAudio() {
  if (audio && isPlaying) {
    audio.pause();
    isPaused = true;
    isPlaying = false;
    log('Paused');
  }
}

function resumeAudio() {
  if (audio && isPaused) {
    audio.play().then(function () {
      isPlaying = true;
      isPaused = false;
      log('Resumed');
    }).catch(function (err) {
      log('Resume failed: ' + err.message);
    });
  }
}

function updateStatus(message) {
  // UI update removed
  // Log status to console instead for debugging
  if (message) log('Status update: ' + message);
}

async function fetchAudioAsBlob(url) {
  if (!url) {
    log('[Content] fetchAudioAsBlob: Empty URL');
    return null;
  }

  log('[Content] fetchAudioAsBlob fetching:', url);

  try {
    var response = await fetch(url);

    if (!response.ok) {
      log('[Content] fetchAudioAsBlob: HTTP ' + response.status);
      return null;
    }

    var blob = await response.blob();

    if (blob.size === 0) {
      log('[Content] fetchAudioAsBlob: Empty blob');
      return null;
    }

    var blobUrl = URL.createObjectURL(blob);
    log('[Content] fetchAudioAsBlob: Success', blobUrl, 'size:', blob.size);
    return blobUrl;

  } catch (e) {
    log('[Content] fetchAudioAsBlob error:', e.message);
    return null;
  }
}

// Listen for messages
chrome.runtime.onMessage.addListener(handleMessage);

// Floating player removed as per user request.
// Use extension popup for controls.

log('Content script loaded');
