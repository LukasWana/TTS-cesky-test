/**
 * Voice Assistant - Background Script
 * WebSocket for TTS, HTTP for voices
 */

const CONFIG = {
  wsUrl: 'ws://localhost:8000/ws/tts',
  restApiUrl: 'http://localhost:8000',
  chunkConfig: { minSize: 200, maxSize: 500, targetSize: 400 },
  parallelWorkers: 2,
  maxPlaylistItems: 100
};

const DEFAULT_SETTINGS = {
  voice: "ai-speakato-Vlasta-female",
  speed: "1.0",
  temperature: "0.96",
  length_penalty: "0.50",
  repetition_penalty: "2.5",
  top_k: "1",
  top_p: "1.00",
  seed: "8"
};

var ws = null;
var requestIdCounter = 0;
var pendingRequests = new Map();
var playlist = [];
var currentPlayingIndex = -1;
var isPlaying = false;
var isStreaming = false;
var audioQueue = [];

function getNextRequestId() { return ++requestIdCounter; }
function getTimestamp() { return Date.now(); }
function generateId() {
  if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
    var array = new Uint32Array(1);
    crypto.getRandomValues(array);
    return Date.now().toString(36) + array[0].toString(36);
  }
  return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

function sanitizeText(text) {
  var cleanText = text.replace(/—/g, "-").replace(/–/g, "-")
    .replace(/[\u201C\u201D\u201E\u201F"„"]/g, "").replace(/[\u2018\u2019']/g, "")
    .replace(/…/g, "...").replace(/\s+/g, " ");
  return cleanText.replace(/[^a-zA-Z0-9áčďéěíňóřšťúůýžÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ \.,\-\?!]/g, "").trim();
}

function splitIntoSentences(text) {
  var sentenceEndings = /[.!?]+[\s\r\n]+/;
  var sentences = [];
  var position = 0;
  while (position < text.length) {
    var match = text.substring(position).match(sentenceEndings);
    if (match) {
      var sentence = text.substring(position, position + match.index + match[0].length).trim();
      if (sentence.length > 0) sentences.push(sentence);
      position += match.index + match[0].length;
    } else {
      var remaining = text.substring(position).trim();
      if (remaining.length > 0) sentences.push(remaining);
      break;
    }
  }
  return sentences.filter(function (s) { return s.length > 0; });
}

function groupSentencesIntoChunks(sentences) {
  if (sentences.length === 0) return [];
  var chunks = [];
  var currentChunk = "";
  var currentLength = 0;
  for (var i = 0; i < sentences.length; i++) {
    var sentence = sentences[i];
    var sentenceLength = sentence.length + 1;
    if (currentLength === 0) {
      currentChunk = sentence;
      currentLength = sentenceLength;
    } else if (currentLength + sentenceLength <= CONFIG.chunkConfig.maxSize) {
      currentChunk += " " + sentence;
      currentLength += sentenceLength;
    } else {
      if (currentLength >= CONFIG.chunkConfig.minSize) {
        chunks.push(currentChunk);
      } else {
        var lastSpaceIndex = currentChunk.lastIndexOf(" ");
        if (lastSpaceIndex > CONFIG.chunkConfig.minSize) {
          chunks.push(currentChunk.substring(0, lastSpaceIndex));
          currentChunk = currentChunk.substring(lastSpaceIndex + 1) + " " + sentence;
          currentLength = currentChunk.length + 1;
          continue;
        } else {
          chunks.push(currentChunk);
          currentChunk = sentence;
          currentLength = sentenceLength;
          continue;
        }
      }
      currentChunk = sentence;
      currentLength = sentenceLength;
    }
  }
  if (currentChunk.length > 0) chunks.push(currentChunk);
  return chunks;
}

function applyTTSFormatting(text) { return text.replace(/,/g, " - ").replace(/\./g, " ... "); }

function processText(text) {
  var sanitized = sanitizeText(text);
  var sentences = splitIntoSentences(sanitized);
  var rawChunks = groupSentencesIntoChunks(sentences);
  return rawChunks.map(applyTTSFormatting);
}

function normalizeAudioUrl(url) {
  if (!url) return null;
  if (url.indexOf('http://') === 0 || url.indexOf('https://') === 0) return url;
  return CONFIG.restApiUrl + url;
}

async function fetchAudioAsDataUri(url) {
  if (!url) return null;
  console.log('[Background] Fetching audio as Data URI:', url);

  try {
    var response = await fetch(url, {
      method: 'GET',
      credentials: 'omit',
      mode: 'cors'
    });

    if (!response.ok) {
      console.error('[Background] Audio fetch failed:', response.status, response.statusText);
      return null;
    }

    var blob = await response.blob();
    if (blob.size === 0) {
      console.error('[Background] Audio blob is empty');
      return null;
    }

    return new Promise(function (resolve, reject) {
      var reader = new FileReader();
      reader.onloadend = function () {
        resolve(reader.result); // This is the Data URI
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });

  } catch (e) {
    console.warn('[Background] Fetch for Data URI failed:', e.message);
    return null;
  }
}
// Removed fetchAudioViaContentScript as it is no longer used

function loadPlaylist() {
  return chrome.storage.local.get('playlist').then(function (data) {
    playlist = data.playlist || [];
    return playlist;
  });
}

function savePlaylist() {
  var itemsToSave = playlist.slice();
  if (itemsToSave.length > CONFIG.maxPlaylistItems) itemsToSave = itemsToSave.slice(-CONFIG.maxPlaylistItems);
  return chrome.storage.local.set({ playlist: itemsToSave });
}

function addToPlaylist(text, audioUrl, voice, params, tabId) {
  var item = {
    id: generateId(),
    text: text.substring(0, 200),
    textFull: text,
    audioUrl: audioUrl,
    voice: voice,
    params: params,
    tabId: tabId,
    timestamp: getTimestamp(),
    duration: null
  };
  playlist.push(item);
  savePlaylist();
  notifyPlaylistChanged();
  return Promise.resolve(item);
}

function removeFromPlaylist(id) {
  var index = -1;
  for (var i = 0; i < playlist.length; i++) if (playlist[i].id === id) { index = i; break; }
  if (index !== -1) {
    playlist.splice(index, 1);
    if (currentPlayingIndex >= index) currentPlayingIndex = Math.max(0, currentPlayingIndex - 1);
    savePlaylist();
    notifyPlaylistChanged();
  }
}

function clearPlaylist() {
  playlist = [];
  currentPlayingIndex = -1;
  isPlaying = false;
  isStreaming = false;
  chrome.storage.local.set({ playlist: [] });
  notifyPlaylistChanged();
}

function notifyPlaylistChanged() {
  chrome.runtime.sendMessage({
    action: 'playlist_changed',
    playlist: playlist,
    currentIndex: currentPlayingIndex,
    isPlaying: isPlaying,
    isStreaming: isStreaming
  }).catch(function () { });
}

function initWs() {
  return new Promise(function (resolve) {
    if (ws && ws.readyState === WebSocket.OPEN) { resolve(true); return; }
    ws = new WebSocket(CONFIG.wsUrl);
    ws.onopen = function () { console.log('[WS] Connected'); resolve(true); };
    ws.onmessage = function (event) {
      if (typeof event.data === 'string') {
        var data = JSON.parse(event.data);
        var type = data.type;
        var requestId = data.request_id;

        // STREAMING: Forward chunks directly to tab
        if (type === 'audio_chunk' && requestId && pendingRequests.has(requestId)) {
          var pending = pendingRequests.get(requestId);
          if (pending.tabId) {
            sendMessageToTab(pending.tabId, {
              action: 'play_stream_chunk',
              audio: data.audio,
              chunkIndex: data.chunk_index,
              totalChunks: data.total_chunks,
              pause_after: data.pause_after
            }).catch(function () { });
          }
        }
        // DONE
        else if ((type === 'done' || type === 'stream_complete') && requestId && pendingRequests.has(requestId)) {
          var pending = pendingRequests.get(requestId);
          pending.resolve({ audioUrl: normalizeAudioUrl(data.audio_url), textPreview: data.text_preview || '' });
          pendingRequests.delete(requestId);
        }
        // ERROR
        else if (type === 'error' && requestId && pendingRequests.has(requestId)) {
          var pending = pendingRequests.get(requestId);
          pending.reject(new Error(data.message || 'Generation failed'));
          pendingRequests.delete(requestId);
        }
      }
    };
    ws.onclose = function () { console.log('[WS] Disconnected'); ws = null; setTimeout(function () { initWs(); }, 2000); };
    ws.onerror = function (error) { console.error('[WS] Error:', error); ws = null; resolve(false); };
    setTimeout(function () { if (!ws || ws.readyState !== WebSocket.OPEN) resolve(false); }, 5000);
  });
}

function generateAudio(text, voice, params, onStatus, tabId) {
  var requestId = getNextRequestId();
  var promise = new Promise(function (resolve, reject) {
    pendingRequests.set(requestId, { resolve: resolve, reject: reject, onStatus: onStatus, tabId: tabId });
  });
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    initWs().then(function (connected) {
      if (!connected) { pendingRequests.delete(requestId); reject(new Error('WebSocket not available')); }
    });
  }

  // Always force cs lang for now as per previous logic
  var payload = {
    type: 'generate',
    text: text,
    voice: voice,
    params: params,
    lang: 'cs',
    request_id: requestId,
    stream: params.stream || false
  };

  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(payload));
  } else {
    // Retry once if just connected
    setTimeout(function () {
      if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(payload));
    }, 500);
  }

  return promise;
}

function playNextInQueue_OLD() {
  if (audioQueue.length === 0 || isPlaying) return;
  var next = audioQueue.shift();
  if (!next) return;
  console.log('[Background] Playing next item:', next);
  currentPlayingIndex = -1;
  for (var i = 0; i < playlist.length; i++) if (playlist[i].id === next.id) { currentPlayingIndex = i; break; }

  if (!next.audioUrl) {
    console.error('[Background] No audioUrl for item:', next);
    isPlaying = false;
    notifyPlaylistChanged();
    return;
  }

  console.log('[Background] Audio URL:', next.audioUrl);

  var normalizedUrl = next.audioUrl;
  if (normalizedUrl.indexOf('http://') !== 0 && normalizedUrl.indexOf('https://') !== 0) {
    normalizedUrl = CONFIG.restApiUrl + normalizedUrl;
  }

  // Fix: Browsers usually cannot fetch from 0.0.0.0, replace with localhost
  normalizedUrl = normalizedUrl.replace('0.0.0.0', 'localhost');

  console.log('[Background] Normalized URL:', normalizedUrl);

  isPlaying = true;
  notifyPlaylistChanged();

  fetchAudioAsBlob(normalizedUrl).then(function (blobUrl) {
    if (blobUrl) {
      console.log('[Background] Using blob URL for playback');
      chrome.runtime.sendMessage({
        action: 'play_in_popup',
        url: blobUrl,
        originalUrl: normalizedUrl
      }).catch(function (err) {
        console.error('[Background] Failed to send play_in_popup message:', err);
        isPlaying = false;
        notifyPlaylistChanged();
      });
    } else {
      throw new Error("Direct blob fetch returned null");
    }
  }).catch(function (err) {
    console.log('[Background] Direct fetch failed, trying via content script...');
    var targetTabId = (currentPlayingIndex >= 0 && playlist[currentPlayingIndex])
      ? playlist[currentPlayingIndex].tabId : null;

    if (targetTabId) {
      fetchAudioViaContentScript(normalizedUrl, targetTabId).then(function (blobUrl) {
        if (blobUrl) {
          chrome.runtime.sendMessage({ action: 'play_in_popup', url: blobUrl });
        } else {
          console.warn('[Background] Content script fetch failed, falling back to direct URL');
          chrome.runtime.sendMessage({
            action: 'play_in_popup',
            url: normalizedUrl
          }).catch(function (err) {
            console.error('[Background] Failed to send direct URL:', err);
            isPlaying = false;
            notifyPlaylistChanged();
          });
        }
      });
    } else {
      console.error('[Background] No tab ID available');
      isPlaying = false;
      notifyPlaylistChanged();
    }
  });
}

function sendMessageToTab(tabId, message) {
  return new Promise(function (resolve, reject) {
    chrome.tabs.sendMessage(tabId, message, function (response) {
      if (chrome.runtime.lastError) {
        chrome.scripting.executeScript({ target: { tabId: tabId }, files: ["content.js"] })
          .then(function () {
            setTimeout(function () {
              chrome.tabs.sendMessage(tabId, message, function (resp) {
                if (chrome.runtime.lastError) reject(new Error(chrome.runtime.lastError.message));
                else resolve(resp);
              });
            }, 100);
          }).catch(reject);
      } else resolve(response);
    });
  });
}

chrome.runtime.onInstalled.addListener(function () {
  chrome.contextMenus.create({ id: "read-selection", title: "Precti nahlas", contexts: ["selection"] });
});

function handleMessage(request, sender, sendResponse) {
  var tabId = sender.tab ? sender.tab.id : null;
  var action = request.action;
  switch (action) {
    case 'play_next':
      audioQueue = request.queue || [];
      currentPlayingIndex = request.currentIndex || 0;
      isPlaying = false;
      playNextInQueue();
      break;
    case 'audio_played':
      isPlaying = false;
      notifyPlaylistChanged();
      setTimeout(function () { playNextInQueue(); }, 500);
      break;
    case 'audio_error':
      console.error('[Background] Audio error received:', request.error);
      console.error('[Background] Current index:', currentPlayingIndex, 'Playlist length:', playlist.length);
      isPlaying = false;
      notifyPlaylistChanged();
      // Don't auto-continue on error to prevent error loops
      // setTimeout(function () { playNextInQueue(); }, 500);
      break;
    case 'get_playlist':
      sendResponse({ playlist: playlist, currentIndex: currentPlayingIndex, isPlaying: isPlaying });
      return true;
    case 'play_item':
      if (request.index >= 0 && request.index < playlist.length) {
        console.log('[Background] Playing item at index:', request.index);
        currentPlayingIndex = request.index;
        audioQueue = playlist.slice(request.index);
        isPlaying = false;
        playNextInQueue();
      } else {
        console.error('[Background] Invalid play_item index:', request.index);
      }
      break;
    case 'play_all':
      console.log('[Background] Playing all, playlist length:', playlist.length);
      audioQueue = playlist.slice();
      currentPlayingIndex = 0;
      isPlaying = false;
      playNextInQueue();
      break;
    case 'stop':
      isPlaying = false;
      isStreaming = false;
      audioQueue = [];
      var targetTabId = (currentPlayingIndex >= 0 && playlist[currentPlayingIndex]) ? playlist[currentPlayingIndex].tabId : null;
      if (targetTabId) sendMessageToTab(targetTabId, { action: 'stop' }).catch(function () { });
      else if (tabId) sendMessageToTab(tabId, { action: 'stop' }).catch(function () { });
      notifyPlaylistChanged();
      break;
    case 'pause':
      isPlaying = false;
      isStreaming = false;
      var targetTabId = (currentPlayingIndex >= 0 && playlist[currentPlayingIndex]) ? playlist[currentPlayingIndex].tabId : null;
      if (targetTabId) sendMessageToTab(targetTabId, { action: 'pause' }).catch(function () { });
      else if (tabId) sendMessageToTab(tabId, { action: 'pause' }).catch(function () { });
      notifyPlaylistChanged();
      break;
    case 'resume':
      var targetTabId = (currentPlayingIndex >= 0 && playlist[currentPlayingIndex]) ? playlist[currentPlayingIndex].tabId : null;
      if (targetTabId) {
        isPlaying = true;
        sendMessageToTab(targetTabId, { action: 'resume' }).catch(function () { });
      } else if (tabId && currentPlayingIndex >= 0) {
        isPlaying = true;
        sendMessageToTab(tabId, { action: 'resume' }).catch(function () { });
      }
      notifyPlaylistChanged();
      break;
    case 'remove_item':
      removeFromPlaylist(request.id);
      break;
    case 'clear_playlist':
      clearPlaylist();
      break;
    case 'get_settings':
      chrome.storage.local.get(DEFAULT_SETTINGS).then(function (data) { sendResponse(data); });
      return true;
  }
  sendResponse({ success: true });
  return true;
}

chrome.runtime.onMessage.addListener(handleMessage);

chrome.contextMenus.onClicked.addListener(function (info, tab) {
  if (!info.selectionText) return;
  chrome.storage.local.get(DEFAULT_SETTINGS).then(function (settings) {

    // STREAMING MODE: Send whole text
    if (info.menuItemId === "read-selection") {
      audioQueue = [];
      isStreaming = true; // Mark as streaming so Stop button works
      notifyPlaylistChanged();

      var params = {
        speed: settings.speed,
        temperature: settings.temperature,
        length_penalty: settings.length_penalty,
        repetition_penalty: settings.repetition_penalty,
        top_k: settings.top_k,
        top_p: settings.top_p,
        seed: settings.seed,
        enable_enhancement: "False",
        stream: true
      };

      sendMessageToTab(tab.id, { action: 'status', message: 'Streamuji...' }).catch(function () { });

      // Format text according to user request: blocks of 8-10 words enclosed in quotes
      function formatTextForModel(text) {
        var cleanText = sanitizeText(text);
        var words = cleanText.split(/\s+/);
        var chunks = [];
        var currentChunk = [];

        for (var i = 0; i < words.length; i++) {
          currentChunk.push(words[i]);

          var size = currentChunk.length;
          var w = words[i];
          // Simple heuristic: break at 10 words, or between 8-10 if punctuation found
          var endsWithPunct = /[.,?!:;]$/.test(w);

          if (size >= 10 || (size >= 8 && endsWithPunct) || i === words.length - 1) {
            chunks.push('"' + currentChunk.join(' ') + '"');
            currentChunk = [];
          }
        }
        return chunks.join(' ');
      }

      var formattedText = formatTextForModel(info.selectionText);
      console.log('[Background] Original text:', info.selectionText);
      console.log('[Background] Formatted text:', formattedText);

      initWs().then(function (connected) {
        if (!connected) {
          sendMessageToTab(tab.id, { action: 'error', message: 'Backend není připojen' }).catch(function () { });
          isStreaming = false;
          notifyPlaylistChanged();
          return;
        }

        generateAudio(formattedText, settings.voice, params, null, tab.id)
          .then(function (result) {
            console.log('[Background] Audio generated, audioUrl:', result.audioUrl);
            sendMessageToTab(tab.id, { action: 'status', message: 'Hotovo.' }).catch(function () { });
            // Add to playlist only if we have a valid audio URL
            if (result.audioUrl) {
              addToPlaylist(info.selectionText, result.audioUrl, settings.voice, params, tab.id).then(function (item) {
                // Auto-play the new item
                audioQueue = [item];
                // Find the index of the new item
                for (var i = 0; i < playlist.length; i++) {
                  if (playlist[i].id === item.id) {
                    currentPlayingIndex = i;
                    break;
                  }
                }
                playNextInQueue();
              });
            } else {
              console.warn('[Background] No audio URL returned, not adding to playlist');
            }
            // Reset isStreaming since streaming is done
            isStreaming = false;
            notifyPlaylistChanged();
          })
          .catch(function (err) {
            console.error("Stream error:", err);
            sendMessageToTab(tab.id, { action: 'error', message: err.message }).catch(function () { });
            isStreaming = false;
            notifyPlaylistChanged();
          });
      });
      return;
    }

    // Legacy / Non-stream mode (if needed, or just remove)
    // For now, "read-selection" handles it all vertically.
  });
});

loadPlaylist();

function playNextInQueue() {
  if (audioQueue.length === 0 || isPlaying) return;
  var next = audioQueue.shift();
  if (!next) return;
  console.log('[Background] Playing next item:', next);

  // Find index
  currentPlayingIndex = -1;
  for (var i = 0; i < playlist.length; i++) if (playlist[i].id === next.id) { currentPlayingIndex = i; break; }

  if (!next.audioUrl) {
    console.error('[Background] No audioUrl for item:', next);
    isPlaying = false;
    notifyPlaylistChanged();
    return;
  }

  var normalizedUrl = next.audioUrl;
  if (normalizedUrl.indexOf('http://') !== 0 && normalizedUrl.indexOf('https://') !== 0) {
    normalizedUrl = CONFIG.restApiUrl + normalizedUrl;
  }

  // Fix: Browsers usually cannot fetch from 0.0.0.0, replace with localhost
  normalizedUrl = normalizedUrl.replace('0.0.0.0', 'localhost');
  console.log('[Background] Normalized URL:', normalizedUrl);

  isPlaying = true;
  notifyPlaylistChanged();

  // Use text item's tabId if available, otherwise current playlist item's tabId
  var targetTabId = next.tabId;
  if (!targetTabId && currentPlayingIndex >= 0 && playlist[currentPlayingIndex]) {
    targetTabId = playlist[currentPlayingIndex].tabId;
  }

  if (!targetTabId) {
    console.error('[Background] No target Tab ID for playback');
    isPlaying = false;
    notifyPlaylistChanged();
    return;
  }

  console.log('[Background] Fetching via Data URI strategy for tab:', targetTabId);

  // Strategy: Fetch in background into Data URI, send to Content Script
  fetchAudioAsDataUri(normalizedUrl).then(function (dataUri) {
    if (dataUri) {
      console.log('[Background] Audio fetched as Data URI, sending to content script');
      sendMessageToTab(targetTabId, {
        action: 'play_audio',
        url: dataUri
      }).catch(function (err) {
        console.error('[Background] Failed to send audio to content script:', err);
        isPlaying = false;
        notifyPlaylistChanged();
      });
    } else {
      console.warn('[Background] Data URI fetch failed, trying direct URL fallback to content script');
      // Fallback: Just send the URL and hope Content Script can handle it
      sendMessageToTab(targetTabId, {
        action: 'play_audio',
        url: normalizedUrl
      }).catch(function (err) {
        console.error('[Background] Failed to send direct fallback URL:', err);
        isPlaying = false;
        notifyPlaylistChanged();
      });
    }
  }).catch(function (err) {
    console.error('[Background] Playback critical error:', err);
    isPlaying = false;
    notifyPlaylistChanged();
  });
}
