/**
 * Voice Assistant Reader v2 - Content Script
 * Simplified audio streaming with progress reporting
 */

var audio = null;
var isPlaying = false;
var isPaused = false;

function log(message) {
  console.log('[Voice Assistant v2] ' + message);
}

var audioCtx = null;
var nextStartTime = 0;
var isStreaming = false;
var pendingBuffers = [];

function initAudioContext() {
  if (!audioCtx) {
    var AudioContext = window.AudioContext || window.webkitAudioContext;
    audioCtx = new AudioContext();
    nextStartTime = 0;
  } else if (audioCtx.state === 'suspended') {
    audioCtx.resume();
  }
}

function playBufferedChunk(buffer, pauseAfterMs, chunkIndex, totalChunks) {
  var source = audioCtx.createBufferSource();
  source.buffer = buffer;
  source.connect(audioCtx.destination);

  var currentTime = audioCtx.currentTime;
  if (nextStartTime < currentTime) {
    nextStartTime = currentTime;
  }

  source.start(nextStartTime);

  var pauseSec = (pauseAfterMs || 0) / 1000.0;
  nextStartTime += buffer.duration + pauseSec;

  log('Playing chunk ' + (chunkIndex + 1) + '/' + (totalChunks || '?') + ' with pause ' + pauseAfterMs + 'ms');
}

function handleStreamChunk(base64Audio, chunkIndex, totalChunks, pauseAfterMs) {
  initAudioContext();
  isStreaming = true;
  isPlaying = true;
  
  log('Stream chunk ' + (chunkIndex + 1) + '/' + totalChunks + ' - pause: ' + (pauseAfterMs || 0) + 'ms');

  var binaryString = atob(base64Audio);
  var len = binaryString.length;
  var bytes = new Uint8Array(len);
  for (var i = 0; i < len; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }

  audioCtx.decodeAudioData(bytes.buffer, function(buffer) {
    playBufferedChunk(buffer, pauseAfterMs, chunkIndex, totalChunks);
  }, function(e) {
    log('Error decoding chunk ' + chunkIndex + ': ' + e.message);
  });
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

function handleMessage(request, sender, sendResponse) {
  log('Received message: ' + request.action);

  switch (request.action) {
    case 'play_audio':
      log('play_audio - URL: ' + (request.url ? request.url.substring(0, 50) + '...' : 'null'));
      stopStream();
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
      log('fetch_audio request: ' + request.url);
      fetchAudioAsBlob(request.url).then(function(blobUrl) {
        if (blobUrl) {
          sendResponse({ success: true, blobUrl: blobUrl });
        } else {
          sendResponse({ success: false, error: 'Failed to fetch audio' });
        }
      }).catch(function(err) {
        sendResponse({ success: false, error: err.message });
      });
      return true;
  }
  return true;
}

function playAudio(url, isLast) {
  log('Attempting to play: ' + (url ? url.substring(0, 50) + '...' : 'null'));

  if (!url) {
    log('Error: Empty URL');
    chrome.runtime.sendMessage({ action: 'audio_error', error: 'Empty URL - audio not available yet' });
    return;
  }

  if (url.indexOf('http://') !== 0 && url.indexOf('https://') !== 0 && url.indexOf('data:') !== 0) {
    log('Error: Invalid URL format');
    chrome.runtime.sendMessage({ action: 'audio_error', error: 'Invalid URL format' });
    return;
  }

  try {
    stopAudio();

    audio = new Audio();
    audio.src = url;
    audio.preload = 'auto';
    audio.crossOrigin = 'anonymous';

    log('Audio created with URL');

    audio.oncanplay = function() {
      log('Can play - starting playback');
      isPaused = false;
    };

    audio.onended = function() {
      log('Playback ended naturally');
      isPlaying = false;
      isPaused = false;
      chrome.runtime.sendMessage({ action: 'audio_played' });
    };

    audio.onerror = function(e) {
      var errorCode = 'N/A';
      var errorMsg = 'Unknown';
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
      log('ERROR - Code: ' + errorCode + ', Message: ' + errorMsg);
      isPlaying = false;
      isPaused = false;
      chrome.runtime.sendMessage({
        action: 'audio_error',
        error: 'Audio error (' + errorCode + '): ' + errorMsg
      });
    };

    audio.play().then(function() {
      log('Playback started successfully');
      isPlaying = true;
      isPaused = false;
    }).catch(function(err) {
      log('Play promise rejected: ' + err.message);
      isPlaying = false;
      chrome.runtime.sendMessage({ action: 'audio_error', error: 'Autoplay blocked: ' + err.message });
    });

  } catch (err) {
    log('Exception in playAudio: ' + err.message);
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
    audio.play().then(function() {
      isPlaying = true;
      isPaused = false;
      log('Resumed');
    }).catch(function(err) {
      log('Resume failed: ' + err.message);
    });
  }
}

function updateStatus(message) {
  if (message) log('Status update: ' + message);
}

async function fetchAudioAsBlob(url) {
  if (!url) {
    log('fetchAudioAsBlob: Empty URL');
    return null;
  }

  log('fetchAudioAsBlob fetching: ' + url.substring(0, 50));

  try {
    var response = await fetch(url);

    if (!response.ok) {
      log('fetchAudioAsBlob: HTTP ' + response.status);
      return null;
    }

    var blob = await response.blob();

    if (blob.size === 0) {
      log('fetchAudioAsBlob: Empty blob');
      return null;
    }

    var blobUrl = URL.createObjectURL(blob);
    log('fetchAudioAsBlob: Success, size: ' + blob.size);
    return blobUrl;

  } catch (e) {
    log('fetchAudioAsBlob error: ' + e.message);
    return null;
  }
}

chrome.runtime.onMessage.addListener(handleMessage);

log('Content script v2 loaded');
