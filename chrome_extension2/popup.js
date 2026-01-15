const DEFAULT_SETTINGS = {
  voice: "ai-speakato-Vlasta-female",
  speed: "1.0",
  temperature: "0.96"
};

let playlist = [];
let currentIndex = -1;
let isPlaying = false;
let isStreaming = false;
let voices = [];
let popupAudio = null;
let currentBlobUrl = null;

const voiceSelect = document.getElementById('voiceSelect');
const playBtn = document.getElementById('playBtn');
const clearBtn = document.getElementById('clearPlaylist');
const statusDiv = document.getElementById('status');
const progressSection = document.getElementById('progressSection');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const progressPercent = document.getElementById('progressPercent');
const playlistContainer = document.getElementById('playlistContainer');

function setStatus(msg, color = '#888') {
  if (statusDiv) {
    statusDiv.textContent = msg;
    statusDiv.style.color = color;
  }
}

function updateProgress(chunkIndex, totalChunks, message) {
  if (!progressSection || !progressFill || !progressText || !progressPercent) return;

  if (chunkIndex === -1 && totalChunks === -1) {
    progressSection.classList.add('hidden');
    return;
  }

  progressSection.classList.remove('hidden');

  if (totalChunks > 0 && chunkIndex >= 0) {
    const percent = Math.round(((chunkIndex + 1) / totalChunks) * 100);
    progressFill.style.width = percent + '%';
    progressText.textContent = message || 'Generuji část ' + (chunkIndex + 1) + '/' + totalChunks;
    progressPercent.textContent = percent + '%';
  } else if (message) {
    progressText.textContent = message;
    progressPercent.textContent = '';
  } else {
    progressText.textContent = 'Inicializace...';
    progressPercent.textContent = '';
  }
}

function saveSettings() {
  const settings = {
    voice: voiceSelect.value,
    speed: document.getElementById('speed')?.value || "1.0",
    temperature: document.getElementById('temperature')?.value || "0.96"
  };
  chrome.storage.local.set(settings);
}

function loadSettings() {
  return chrome.storage.local.get(DEFAULT_SETTINGS).then(data => {
    if (voiceSelect) voiceSelect.value = data.voice || DEFAULT_SETTINGS.voice;
    const speedInput = document.getElementById('speed');
    const temperatureInput = document.getElementById('temperature');
    if (speedInput) speedInput.value = data.speed || DEFAULT_SETTINGS.speed;
    if (temperatureInput) temperatureInput.value = data.temperature || DEFAULT_SETTINGS.temperature;
  });
}

function renderPlaylist() {
  if (!playlistContainer) return;

  if (playlist.length === 0) {
    playlistContainer.innerHTML = '<div class="playlist-empty">Vyberte text na stránce pro generování</div>';
    return;
  }

  playlistContainer.innerHTML = playlist.map((item, index) => `
    <div class="playlist-item ${index === currentIndex && isPlaying ? 'playing' : ''}" data-index="${index}">
      <div class="playlist-item-info">
        <div class="playlist-item-text">${item.text}</div>
        <div class="playlist-item-meta">${item.voice} • ${new Date(item.timestamp).toLocaleTimeString()}</div>
      </div>
      <button class="playlist-item-remove" data-id="${item.id}">&times;</button>
    </div>
  `).join('');

  playlistContainer.querySelectorAll('.playlist-item').forEach(el => {
    el.onclick = (e) => {
      if (!e.target.classList.contains('playlist-item-remove')) {
        const index = parseInt(el.dataset.index);
        playFromIndex(index);
      }
    };
  });

  playlistContainer.querySelectorAll('.playlist-item-remove').forEach(btn => {
    btn.onclick = (e) => {
      e.stopPropagation();
      const id = btn.dataset.id;
      chrome.runtime.sendMessage({ action: 'remove_item', id });
    };
  });
}

async function updatePlaylist() {
  try {
    const response = await chrome.runtime.sendMessage({ action: 'get_playlist' });
    if (response) {
      playlist = response.playlist || [];
      currentIndex = response.currentIndex || -1;
      isPlaying = response.isPlaying;
      console.log('[Popup v2] Playlist updated:', { playlistLength: playlist.length, currentIndex, isPlaying });
      renderPlaylist();
      updatePlayButton();
    }
  } catch (err) {
    console.error('[Popup v2] Playlist update error:', err);
    setStatus('Chyba při načítání playlistu', '#ff4444');
  }
}

function updatePlayButton() {
  if (!playBtn) return;
  if (isPlaying || isStreaming) {
    playBtn.innerHTML = '<span>⏹</span> Stop';
  } else {
    playBtn.innerHTML = '<span>▶</span> Přehrát';
  }
}

function playFromIndex(index) {
  chrome.runtime.sendMessage({ action: 'play_item', index });
}

function playAll() {
  chrome.runtime.sendMessage({ action: 'play_all' });
}

function stop() {
  if (popupAudio) {
    popupAudio.pause();
    popupAudio.currentTime = 0;
    popupAudio.src = '';
  }
  if (currentBlobUrl) {
    URL.revokeObjectURL(currentBlobUrl);
    currentBlobUrl = null;
  }
  isStreaming = false;
  updateProgress(-1, -1);
  chrome.runtime.sendMessage({ action: 'stop' });
}

function playAudioInPopup(url) {
  console.log('[Popup v2] Playing audio in popup:', url);

  if (!popupAudio) {
    popupAudio = document.getElementById('popupAudio');
  }

  if (currentBlobUrl && url !== currentBlobUrl) {
    console.log('[Popup v2] Revoking old blob URL:', currentBlobUrl);
    URL.revokeObjectURL(currentBlobUrl);
    currentBlobUrl = null;
  }

  popupAudio.oncanplay = function() {
    console.log('[Popup v2] Audio can play, starting playback');
    popupAudio.play().then(function() {
      console.log('[Popup v2] Audio started playing');
      isPlaying = true;
      updatePlayButton();
      setStatus('Přehrávám...', '#4caf50');
    }).catch(function(err) {
      console.error('[Popup v2] Audio play error:', err);
      setStatus('Chyba přehrávání: ' + err.message, '#ff4444');
      isPlaying = false;
      updatePlayButton();
    });
  };

  popupAudio.onended = function() {
    console.log('[Popup v2] Audio ended');
    isPlaying = false;
    updatePlayButton();
    setStatus('Připraveno', '#888');
    if (currentBlobUrl) {
      URL.revokeObjectURL(currentBlobUrl);
      currentBlobUrl = null;
    }
    chrome.runtime.sendMessage({ action: 'audio_played' });
  };

  popupAudio.onerror = function(e) {
    var errorCode = popupAudio.error ? popupAudio.error.code : 'N/A';
    var errorMsg = popupAudio.error ? popupAudio.error.message : 'Unknown';
    console.error('[Popup v2] Audio error code:', errorCode);
    console.error('[Popup v2] Audio error message:', errorMsg);

    if (errorCode === 4) {
      setStatus('Chyba: Nepodporovaný formát audia', '#ff4444');
    } else if (errorCode === 3) {
      setStatus('Chyba: Poškozený audio soubor', '#ff4444');
    } else {
      setStatus('Chyba audio (' + errorCode + '): ' + errorMsg, '#ff4444');
    }
    isPlaying = false;
    updatePlayButton();
    if (currentBlobUrl) {
      URL.revokeObjectURL(currentBlobUrl);
      currentBlobUrl = null;
    }
  };

  if (url.startsWith('blob:')) {
    currentBlobUrl = url;
  }
  popupAudio.src = url;
  popupAudio.load();
}

function clearPlaylist() {
  if (confirm('Vymazat celý playlist?')) {
    chrome.runtime.sendMessage({ action: 'clear_playlist' });
  }
}

async function fetchVoices() {
  try {
    if (voiceSelect) voiceSelect.innerHTML = '<option value="">Načítám...</option>';

    var response = await fetch('http://localhost:8000/api/voices/demo?lang=cs');
    if (!response.ok) throw new Error('Failed to fetch');

    var data = await response.json();

    if (data.voices && data.voices.length > 0) {
      voices = data.voices;
      if (voiceSelect) {
        voiceSelect.innerHTML = voices.map(function(v) {
          return '<option value="' + v.id + '">' + v.display_name + '</option>';
        }).join('');
      }

      loadSettings().then(function() {
        setStatus('Nalezeno ' + voices.length + ' hlasů', '#4caf50');
      });
    } else {
      if (voiceSelect) voiceSelect.innerHTML = '<option value="">Žádné hlasy</option>';
      setStatus('Žádné hlasy nenalezeny', '#ff9800');
    }

  } catch (err) {
    console.error('Fetch voices error:', err);
    if (voiceSelect) voiceSelect.innerHTML = '<option value="">Backend nedostupný</option>';

    if (err.message.includes('Failed to fetch')) {
      setStatus('Backend neběží (spusťte start_lite.bat)', '#ff4444');
    } else {
      setStatus('Chyba: ' + err.message, '#ff4444');
    }
  }
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('[Popup v2] Received message:', request.action);

  if (request.action === 'voices_list') {
    voices = request.voices || [];
    if (voiceSelect) {
      voiceSelect.innerHTML = voices.map(v =>
        `<option value="${v.id}">${v.display_name}</option>`
      ).join('');
    }

    loadSettings();
    setStatus(`Nalezeno ${voices.length} hlasů`, '#4caf50');
  } else if (request.action === 'playlist_changed') {
    playlist = request.playlist || [];
    currentIndex = request.currentIndex || -1;
    isPlaying = request.isPlaying;
    isStreaming = request.isStreaming || false;
    renderPlaylist();
    updatePlayButton();
    setStatus(isPlaying ? 'Přehrávám...' : (isStreaming ? 'Generuji...' : 'Připraveno'), isPlaying ? '#4caf50' : (isStreaming ? '#ff9800' : '#888'));
  } else if (request.action === 'state_change') {
    isPlaying = request.state === 'playing';
    updatePlayButton();
    renderPlaylist();
    setStatus(isPlaying ? 'Přehrávám...' : 'Pozastaveno', isPlaying ? '#4caf50' : '#ff9800');
  } else if (request.action === 'audio_error') {
    console.error('[Popup v2] Audio error received:', request.error);
    setStatus('Chyba přehrávání: ' + (request.error || 'Neznámá chyba'), '#ff4444');
    isPlaying = false;
    isStreaming = false;
    updatePlayButton();
    renderPlaylist();
    updateProgress(-1, -1);
  } else if (request.action === 'progress_update') {
    updateProgress(request.chunkIndex, request.totalChunks, request.message);
  } else if (request.action === 'play_in_popup') {
    console.log('[Popup v2] Playing audio from background:', request.url);
    playAudioInPopup(request.url);
    sendResponse({ success: true });
  }

  return true;
});

document.addEventListener('DOMContentLoaded', () => {
  console.log('[Popup v2] Initializing...');

  if (voiceSelect) {
    voiceSelect.onchange = () => {
      saveSettings();
    };
  }

  const speedInput = document.getElementById('speed');
  const temperatureInput = document.getElementById('temperature');
  if (speedInput) speedInput.onchange = () => saveSettings();
  if (temperatureInput) temperatureInput.onchange = () => saveSettings();

  if (playBtn) {
    playBtn.onclick = () => {
      console.log('[Popup v2] Play button clicked, isPlaying:', isPlaying, 'isStreaming:', isStreaming, 'currentIndex:', currentIndex);
      if (isPlaying || isStreaming) {
        stop();
      } else if (currentIndex >= 0) {
        playFromIndex(currentIndex);
      } else if (playlist.length > 0) {
        playAll();
      } else {
        setStatus('Playlist je prázdný', '#ff9800');
      }
    };
  }

  if (clearBtn) clearBtn.onclick = clearPlaylist;

  loadSettings();
  fetchVoices();
  updatePlaylist();

  setTimeout(function() {
    fetch('http://localhost:8000/health', { method: 'GET' })
      .then(function(res) {
        if (res.ok) {
          console.log('[Popup v2] Backend is running');
        } else {
          console.log('[Popup v2] Backend returned:', res.status);
        }
      })
      .catch(function(err) {
        console.log('[Popup v2] Backend not reachable:', err.message);
      });
  }, 1000);
});
