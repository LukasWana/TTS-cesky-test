/**
 * Voice Assistant Reader v2 - Background Script
 * Advanced text processing with improved sentence splitting and chunking
 * Consistent with backend/main_xtts_ws.py text processing
 */

const CONFIG = {
  wsUrl: 'ws://localhost:8000/ws/tts',
  restApiUrl: 'http://localhost:8000',
  chunkConfig: {
    minSize: 150,
    maxSize: 300,
    enableWordWrap: true
  },
  parallelWorkers: 2,
  maxPlaylistItems: 100
};

const CZ_ABBREVIATIONS = new Set([
  'např', 'tj', 'tzn', 'tzv', 'apod', 'č', 'resp', 'popř',
  'event', 'max', 'min', 'například', 'takzvaný', 'čís',
  'př', 'n', 'm', 'k', 's', 'v', 'z', 'u', 'o', 'i', 'a'
]);

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
  return text
    .replace(/—/g, '-').replace(/–/g, '-')
    .replace(/[""„""]/g, '"').replace(/[''‛'']/g, "'")
    .replace(/…/g, '...')
    .replace(/\s+/g, ' ')
    .trim();
}

function isAbbreviation(word) {
  var clean = word.toLowerCase().replace(/\.$/, '');
  return CZ_ABBREVIATIONS.has(clean);
}

function splitIntoSentences(text) {
  var sentences = [];
  var position = 0;
  var len = text.length;
  
  while (position < len) {
    var foundEnd = false;
    
    for (var i = position; i < len; i++) {
      var char = text[i];
      
      if (char === '.' || char === '!' || char === '?') {
        var isAbbrevWord = false;
        for (var j = i - 1; j >= position; j--) {
          if (text[j] === ' ') break;
          if (isAbbreviation(text.substring(j, i + 1))) {
            isAbbrevWord = true;
            break;
          }
        }
        if (isAbbrevWord) continue;
        
        var j = i + 1;
        while (j < len && (text[j] === ' ' || text[j] === '\n' || 
                           text[j] === '\r' || text[j] === '\t')) {
          j++;
        }
        
        if (j > i + 1 || i === len - 1) {
          var sentence = text.substring(position, j).trim();
          if (sentence.length > 0) {
            sentences.push(sentence);
          }
          position = j;
          foundEnd = true;
          break;
        }
      }
    }
    
    if (!foundEnd) {
      var remaining = text.substring(position).trim();
      if (remaining.length > 0) sentences.push(remaining);
      break;
    }
  }
  
  return sentences.filter(function(s) { return s.length > 0; });
}

function wrapSentence(sentence, maxSize) {
  if (sentence.length <= maxSize) return [sentence];
  
  var words = sentence.split(' ');
  var wrapped = [];
  var current = '';
  
  for (var i = 0; i < words.length; i++) {
    var word = words[i];
    var test = current ? current + ' ' + word : word;
    if (test.length > maxSize) {
      if (current) wrapped.push(current);
      current = word;
    } else {
      current = test;
    }
  }
  if (current) wrapped.push(current);
  return wrapped;
}

function splitIntoChunks(sentences, options) {
  var minSize = options.minSize || 150;
  var maxSize = options.maxSize || 300;
  var enableWordWrap = options.enableWordWrap !== false;
  
  if (sentences.length === 0) return [];
  
  var chunks = [];
  var currentChunk = '';
  
  for (var i = 0; i < sentences.length; i++) {
    var sentence = sentences[i];
    var wrappedParts = enableWordWrap ? wrapSentence(sentence, maxSize) : [sentence];
    
    for (var j = 0; j < wrappedParts.length; j++) {
      var part = wrappedParts[j];
      var testChunk = currentChunk ? currentChunk + ' ' + part : part;
      
      if (!currentChunk) {
        currentChunk = part;
      } else if (testChunk.length <= maxSize) {
        currentChunk = testChunk;
      } else {
        if (currentChunk) {
          chunks.push(currentChunk);
        }
        currentChunk = part;
      }
    }
  }
  
  if (currentChunk) chunks.push(currentChunk);
  return chunks;
}

function validateChunks(chunks, originalText) {
  var reconstructed = chunks.join(' ').replace(/\s+/g, ' ').trim();
  var original = originalText.replace(/\s+/g, ' ').trim();
  var similarity = reconstructed.length / Math.max(original.length, 1);
  
  return {
    isValid: similarity > 0.7,
    chunkCount: chunks.length,
    totalLength: chunks.reduce(function(sum, c) { return sum + c.length; }, 0),
    similarity: Math.round(similarity * 100) + '%'
  };
}

function applyTTSFormatting(text) {
  return text.replace(/,/g, ' - ').replace(/\./g, ' ... ');
}

function detectPause(text) {
  var trimmed = text.replace(/^["'"»«]+|["'"»«]+$/g, '').trim();
  var hasPause = /[.?!]["'»«]?\s*$/.test(trimmed);
  console.log('[Background v2] detectPause:', {
    text: text.substring(0, 60),
    trimmed: trimmed,
    hasPause: hasPause
  });
  return hasPause ? 250 : 0;
}

function processTextAdvanced(text) {
  var sanitized = sanitizeText(text);
  var sentences = splitIntoSentences(sanitized);
  var chunks = splitIntoChunks(sentences, CONFIG.chunkConfig);
  var validation = validateChunks(chunks, sanitized);
  
  console.log('[Background v2] Text processing:', {
    originalLength: text.length,
    sentences: sentences.length,
    chunks: chunks.length,
    validation: validation
  });
  
  if (sentences.length > 0) {
    console.log('[Background v2] Sample sentences:', sentences.slice(0, 3));
  }
  
  var result = chunks.map(function(chunk) {
    return {
      text: applyTTSFormatting(chunk),
      pauseAfter: detectPause(chunk)
    };
  });
  
  console.log('[Background v2] Processed chunks with pauses:', result.map(function(r) {
    return { text: r.text.substring(0, 40) + '...', pause: r.pauseAfter };
  }));
  
  return result;
}

function normalizeAudioUrl(url) {
  if (!url) return null;
  if (url.indexOf('http://') === 0 || url.indexOf('https://') === 0) return url;
  return CONFIG.restApiUrl + url;
}

async function fetchAudioAsDataUri(url) {
  if (!url) return null;
  console.log('[Background v2] Fetching audio as Data URI:', url);

  try {
    var response = await fetch(url, {
      method: 'GET',
      credentials: 'omit',
      mode: 'cors'
    });

    if (!response.ok) {
      console.error('[Background v2] Audio fetch failed:', response.status);
      return null;
    }

    var blob = await response.blob();
    if (blob.size === 0) {
      console.error('[Background v2] Audio blob is empty');
      return null;
    }

    return new Promise(function(resolve, reject) {
      var reader = new FileReader();
      reader.onloadend = function() {
        resolve(reader.result);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });

  } catch (e) {
    console.warn('[Background v2] Fetch for Data URI failed:', e.message);
    return null;
  }
}

function loadPlaylist() {
  return chrome.storage.local.get('playlist').then(function(data) {
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
  }).catch(function() { });
}

function notifyProgressUpdate(chunkIndex, totalChunks, message) {
  chrome.runtime.sendMessage({
    action: 'progress_update',
    chunkIndex: chunkIndex,
    totalChunks: totalChunks,
    message: message || 'Generuji...'
  }).catch(function() { });
}

function initWs() {
  return new Promise(function(resolve) {
    if (ws && ws.readyState === WebSocket.OPEN) { resolve(true); return; }
    ws = new WebSocket(CONFIG.wsUrl);
    ws.onopen = function() { console.log('[WS v2] Connected'); resolve(true); };
    ws.onmessage = function(event) {
      if (typeof event.data === 'string') {
        var data = JSON.parse(event.data);
        var type = data.type;
        var requestId = data.request_id;

        if (type === 'audio_chunk' && requestId && pendingRequests.has(requestId)) {
          var pending = pendingRequests.get(requestId);
          if (pending.tabId) {
            sendMessageToTab(pending.tabId, {
              action: 'play_stream_chunk',
              audio: data.audio,
              chunkIndex: data.chunk_index,
              totalChunks: data.total_chunks,
              pause_after: data.pause_after
            }).catch(function() { });
            
            notifyProgressUpdate(data.chunk_index, data.total_chunks,
              'Generuji část ' + (data.chunk_index + 1) + '/' + data.total_chunks);
          }
        }
        else if ((type === 'done' || type === 'stream_complete') && requestId && pendingRequests.has(requestId)) {
          var pending = pendingRequests.get(requestId);
          pending.resolve({ audioUrl: normalizeAudioUrl(data.audio_url), textPreview: data.text_preview || '' });
          pendingRequests.delete(requestId);
          notifyProgressUpdate(-1, -1, 'Hotovo');
        }
        else if (type === 'error' && requestId && pendingRequests.has(requestId)) {
          var pending = pendingRequests.get(requestId);
          pending.reject(new Error(data.message || 'Generation failed'));
          pendingRequests.delete(requestId);
          notifyProgressUpdate(-1, -1, 'Chyba: ' + (data.message || 'Neznámá chyba'));
        }
      }
    };
    ws.onclose = function() { console.log('[WS v2] Disconnected'); ws = null; setTimeout(function() { initWs(); }, 2000); };
    ws.onerror = function(error) { console.error('[WS v2] Error:', error); ws = null; resolve(false); };
    setTimeout(function() { if (!ws || ws.readyState !== WebSocket.OPEN) resolve(false); }, 5000);
  });
}

function generateAudio(text, voice, params, onStatus, tabId) {
  var requestId = getNextRequestId();
  var promise = new Promise(function(resolve, reject) {
    pendingRequests.set(requestId, { resolve: resolve, reject: reject, onStatus: onStatus, tabId: tabId });
  });
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    initWs().then(function(connected) {
      if (!connected) { pendingRequests.delete(requestId); reject(new Error('WebSocket not available')); }
    });
  }

  var payload = {
    type: 'generate',
    text: text,
    voice: voice,
    params: params,
    lang: 'cs',
    request_id: requestId,
    stream: params.stream !== false
  };

  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(payload));
  } else {
    setTimeout(function() {
      if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(payload));
    }, 500);
  }

  return promise;
}

function generateAudioWithPauses(chunksInfo, voice, params, tabId) {
  var requestId = getNextRequestId();
  var promise = new Promise(function(resolve, reject) {
    pendingRequests.set(requestId, { resolve: resolve, reject: reject, onStatus: null, tabId: tabId, chunksInfo: chunksInfo });
  });
  
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    initWs().then(function(connected) {
      if (!connected) { pendingRequests.delete(requestId); reject(new Error('WebSocket not available')); }
    });
  }

  var textToSend = chunksInfo.map(function(c) { return c.text; }).join(' ');
  
  var payload = {
    type: 'generate',
    text: textToSend,
    voice: voice,
    params: params,
    lang: 'cs',
    request_id: requestId,
    stream: true,
    chunks_with_pauses: chunksInfo
  };

  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(payload));
  } else {
    setTimeout(function() {
      if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(payload));
    }, 500);
  }

  return promise;
}

function sendMessageToTab(tabId, message) {
  return new Promise(function(resolve, reject) {
    chrome.tabs.sendMessage(tabId, message, function(response) {
      if (chrome.runtime.lastError) {
        chrome.scripting.executeScript({ target: { tabId: tabId }, files: ["content.js"] })
          .then(function() {
            setTimeout(function() {
              chrome.tabs.sendMessage(tabId, message, function(resp) {
                if (chrome.runtime.lastError) reject(new Error(chrome.runtime.lastError.message));
                else resolve(resp);
              });
            }, 100);
          }).catch(reject);
      } else resolve(response);
    });
  });
}

chrome.runtime.onInstalled.addListener(function() {
  chrome.contextMenus.create({ id: "read-selection", title: "Přečti nahlas (v2)", contexts: ["selection"] });
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
      setTimeout(function() { playNextInQueue(); }, 500);
      break;
    case 'audio_error':
      console.error('[Background v2] Audio error received:', request.error);
      isPlaying = false;
      notifyPlaylistChanged();
      break;
    case 'get_playlist':
      sendResponse({ playlist: playlist, currentIndex: currentPlayingIndex, isPlaying: isPlaying });
      return true;
    case 'play_item':
      if (request.index >= 0 && request.index < playlist.length) {
        currentPlayingIndex = request.index;
        audioQueue = playlist.slice(request.index);
        isPlaying = false;
        playNextInQueue();
      }
      break;
    case 'play_all':
      audioQueue = playlist.slice();
      currentPlayingIndex = 0;
      isPlaying = false;
      playNextInQueue();
      break;
    case 'stop':
      isPlaying = false;
      isStreaming = false;
      audioQueue = [];
      notifyProgressUpdate(-1, -1, '');
      var targetTabId = (currentPlayingIndex >= 0 && playlist[currentPlayingIndex]) ? playlist[currentPlayingIndex].tabId : null;
      if (targetTabId) sendMessageToTab(targetTabId, { action: 'stop' }).catch(function() { });
      else if (tabId) sendMessageToTab(tabId, { action: 'stop' }).catch(function() { });
      notifyPlaylistChanged();
      break;
    case 'pause':
      isPlaying = false;
      isStreaming = false;
      var targetTabId = (currentPlayingIndex >= 0 && playlist[currentPlayingIndex]) ? playlist[currentPlayingIndex].tabId : null;
      if (targetTabId) sendMessageToTab(targetTabId, { action: 'pause' }).catch(function() { });
      else if (tabId) sendMessageToTab(tabId, { action: 'pause' }).catch(function() { });
      notifyPlaylistChanged();
      break;
    case 'resume':
      var targetTabId = (currentPlayingIndex >= 0 && playlist[currentPlayingIndex]) ? playlist[currentPlayingIndex].tabId : null;
      if (targetTabId) {
        isPlaying = true;
        sendMessageToTab(targetTabId, { action: 'resume' }).catch(function() { });
      } else if (tabId && currentPlayingIndex >= 0) {
        isPlaying = true;
        sendMessageToTab(tabId, { action: 'resume' }).catch(function() { });
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
      chrome.storage.local.get(DEFAULT_SETTINGS).then(function(data) { sendResponse(data); });
      return true;
  }
  sendResponse({ success: true });
  return true;
}

chrome.runtime.onMessage.addListener(handleMessage);

chrome.contextMenus.onClicked.addListener(function(info, tab) {
  if (!info.selectionText) return;
  chrome.storage.local.get(DEFAULT_SETTINGS).then(function(settings) {
    if (info.menuItemId === "read-selection") {
      audioQueue = [];
      isStreaming = true;
      notifyPlaylistChanged();
      notifyProgressUpdate(0, 1, 'Zpracovávám text...');

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

      sendMessageToTab(tab.id, { action: 'status', message: 'Zpracovávám...' }).catch(function() { });

      console.log('[Background v2] Original text length:', info.selectionText.length);
      console.log('[Background v2] Original text preview:', info.selectionText.substring(0, 100));

      var processedChunks = processTextAdvanced(info.selectionText);
      
      // Rozdělit na text a pauzy - nahradit ... zpět na . pro TTS model
      var chunksInfo = processedChunks.map(function(item, index) {
        var cleanText = item.text.replace(/\.\.\./g, '.');  // Zpět na tečky
        return {
          index: index,
          text: cleanText,
          pauseAfter: item.pauseAfter
        };
      });
      
      console.log('[Background v2] Sending', chunksInfo.length, 'chunks to backend');
      console.log('[Background v2] Total text length:', chunksInfo.reduce(function(sum, c) { return sum + c.text.length; }, 0));
      console.log('[Background v2] Chunks with pauses:', chunksInfo.filter(function(c) { return c.pauseAfter > 0; }).length);

      initWs().then(function(connected) {
        if (!connected) {
          sendMessageToTab(tab.id, { action: 'error', message: 'Backend není připojen' }).catch(function() { });
          isStreaming = false;
          notifyPlaylistChanged();
          notifyProgressUpdate(-1, -1, 'Chyba: Backend nedostupný');
          return;
        }

        generateAudioWithPauses(chunksInfo, settings.voice, params, tab.id)
          .then(function(result) {
            console.log('[Background v2] Audio generated, audioUrl:', result.audioUrl);
            sendMessageToTab(tab.id, { action: 'status', message: 'Hotovo.' }).catch(function() { });
            
            // Přidat do playlistu i když není audioUrl (pro možnost retry)
            var audioUrl = result.audioUrl || null;
            addToPlaylist(info.selectionText, audioUrl, settings.voice, params, tab.id).then(function(item) {
              audioQueue = [item];
              for (var i = 0; i < playlist.length; i++) {
                if (playlist[i].id === item.id) {
                  currentPlayingIndex = i;
                  break;
                }
              }
              // Auto-play pokud máme audio URL
              if (audioUrl) {
                playNextInQueue();
              } else {
                console.log('[Background v2] No audio URL, item added to playlist for manual playback');
              }
            });
            isStreaming = false;
            notifyPlaylistChanged();
            notifyProgressUpdate(-1, -1, 'Hotovo');
          })
          .catch(function(err) {
            console.error('[Background v2] Stream error:', err);
            sendMessageToTab(tab.id, { action: 'error', message: err.message }).catch(function() { });
            
            // Přidat do playlistu i při chybě pro retry možnost
            addToPlaylist(info.selectionText, null, settings.voice, params, tab.id).then(function(item) {
              console.log('[Background v2] Error item added to playlist for retry');
            });
            
            isStreaming = false;
            notifyPlaylistChanged();
            notifyProgressUpdate(-1, -1, 'Chyba: ' + err.message);
          });
      });
      return;
    }
  });
});

loadPlaylist();

function playNextInQueue() {
  if (audioQueue.length === 0 || isPlaying) return;
  var next = audioQueue.shift();
  if (!next) return;
  console.log('[Background v2] Playing next item:', next);

  currentPlayingIndex = -1;
  for (var i = 0; i < playlist.length; i++) if (playlist[i].id === next.id) { currentPlayingIndex = i; break; }

  // Pokud audioUrl je null, pokusit se znovu vygenerovat
  if (!next.audioUrl && next.textFull) {
    console.log('[Background v2] No audioUrl, regenerating from textFull...');
    isPlaying = true;
    notifyPlaylistChanged();
    
    var params = next.params || { stream: true };
    
    initWs().then(function(connected) {
      if (!connected) {
        console.error('[Background v2] Backend not available for regeneration');
        isPlaying = false;
        notifyPlaylistChanged();
        return;
      }
      
      // Znovu zpracovat text
      var processedChunks = processTextAdvanced(next.textFull);
      var chunksInfo = processedChunks.map(function(item, index) {
        return { index: index, text: item.text, pauseAfter: item.pauseAfter };
      });
      
      generateAudioWithPauses(chunksInfo, next.voice, params, next.tabId)
        .then(function(result) {
          console.log('[Background v2] Regenerated audioUrl:', result.audioUrl);
          if (result.audioUrl) {
            // Aktualizovat položku v playlistu
            for (var j = 0; j < playlist.length; j++) {
              if (playlist[j].id === next.id) {
                playlist[j].audioUrl = result.audioUrl;
                break;
              }
            }
            savePlaylist();
            
            // Přehrát
            next.audioUrl = result.audioUrl;
            playAudioFromUrl(next);
          } else {
            isPlaying = false;
            notifyPlaylistChanged();
          }
        })
        .catch(function(err) {
          console.error('[Background v2] Regeneration failed:', err);
          isPlaying = false;
          notifyPlaylistChanged();
        });
    });
    return;
  }

  if (!next.audioUrl) {
    console.error('[Background v2] No audioUrl and no textFull:', next);
    isPlaying = false;
    notifyPlaylistChanged();
    return;
  }

  playAudioFromUrl(next);
}

function playAudioFromUrl(next) {
  var normalizedUrl = next.audioUrl;
  if (normalizedUrl.indexOf('http://') !== 0 && normalizedUrl.indexOf('https://') !== 0) {
    normalizedUrl = CONFIG.restApiUrl + normalizedUrl;
  }
  normalizedUrl = normalizedUrl.replace('0.0.0.0', 'localhost');
  console.log('[Background v2] Normalized URL:', normalizedUrl);

  isPlaying = true;
  notifyPlaylistChanged();

  var targetTabId = next.tabId;
  if (!targetTabId && currentPlayingIndex >= 0 && playlist[currentPlayingIndex]) {
    targetTabId = playlist[currentPlayingIndex].tabId;
  }

  if (!targetTabId) {
    console.error('[Background v2] No target Tab ID for playback');
    isPlaying = false;
    notifyPlaylistChanged();
    return;
  }

  fetchAudioAsDataUri(normalizedUrl).then(function(dataUri) {
    if (dataUri) {
      sendMessageToTab(targetTabId, {
        action: 'play_audio',
        url: dataUri
      }).catch(function(err) {
        console.error('[Background v2] Failed to send audio to content script:', err);
        isPlaying = false;
        notifyPlaylistChanged();
      });
    } else {
      sendMessageToTab(targetTabId, {
        action: 'play_audio',
        url: normalizedUrl
      }).catch(function(err) {
        console.error('[Background v2] Failed to send fallback URL:', err);
        isPlaying = false;
        notifyPlaylistChanged();
      });
    }
  }).catch(function(err) {
    console.error('[Background v2] Playback critical error:', err);
    isPlaying = false;
    notifyPlaylistChanged();
  });
}
