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
const speedInput = document.getElementById('speed');
const temperatureInput = document.getElementById('temperature');
const playlistContainer = document.getElementById('playlistContainer');
const playBtn = document.getElementById('playBtn');
const clearBtn = document.getElementById('clearPlaylist');
const statusDiv = document.getElementById('status');

function setStatus(msg, color = '#888') {
  if (statusDiv) {
    statusDiv.textContent = msg;
    statusDiv.style.color = color;
  }
}

function saveSettings() {
  const settings = {
    voice: voiceSelect.value,
    speed: speedInput.value,
    temperature: temperatureInput.value
  };
  chrome.storage.local.set(settings);
}

function loadSettings() {
  return chrome.storage.local.get(DEFAULT_SETTINGS).then(data => {
    if (voiceSelect) voiceSelect.value = data.voice || DEFAULT_SETTINGS.voice;
    if (speedInput) speedInput.value = data.speed || DEFAULT_SETTINGS.speed;
    if (temperatureInput) temperatureInput.value = data.temperature || DEFAULT_SETTINGS.temperature;
    // Don't save immediately, just load. Saving happens on change.
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

  // Add click handlers
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
      console.log('[Popup] Playlist updated:', { playlistLength: playlist.length, currentIndex, isPlaying });
      renderPlaylist();
      updatePlayButton();
    }
  } catch (err) {
    console.error('[Popup] Playlist update error:', err);
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
  chrome.runtime.sendMessage({ action: 'stop' });
}

function playAudioInPopup(url) {
  console.log('[Popup] Playing audio in popup:', url);

  if (!popupAudio) {
    popupAudio = document.getElementById('popupAudio');
  }

  if (currentBlobUrl && url !== currentBlobUrl) {
    console.log('[Popup] Revoking old blob URL:', currentBlobUrl);
    URL.revokeObjectURL(currentBlobUrl);
    currentBlobUrl = null;
  }

  popupAudio.oncanplay = function () {
    console.log('[Popup] Audio can play, starting playback');
    console.log('[Popup] Audio duration:', popupAudio.duration);
    console.log('[Popup] Audio readyState:', popupAudio.readyState);
    popupAudio.play().then(function () {
      console.log('[Popup] Audio started playing');
      isPlaying = true;
      updatePlayButton();
      setStatus('Přehrávám...', '#4caf50');
    }).catch(function (err) {
      console.error('[Popup] Audio play error:', err);
      console.error('[Popup] Play error details:', err.message);
      setStatus('Chyba přehrávání: ' + err.message, '#ff4444');
      isPlaying = false;
      updatePlayButton();
    });
  };

  popupAudio.onended = function () {
    console.log('[Popup] Audio ended');
    isPlaying = false;
    updatePlayButton();
    setStatus('Připraveno', '#888');
    if (currentBlobUrl) {
      console.log('[Popup] Revoking blob URL on ended:', currentBlobUrl);
      URL.revokeObjectURL(currentBlobUrl);
      currentBlobUrl = null;
    }
    chrome.runtime.sendMessage({ action: 'audio_played' });
  };

  popupAudio.onerror = function (e) {
    var errorCode = popupAudio.error ? popupAudio.error.code : 'N/A';
    var errorMsg = popupAudio.error ? popupAudio.error.message : 'Unknown';
    console.error('[Popup] Audio error code:', errorCode);
    console.error('[Popup] Audio error message:', errorMsg);
    console.error('[Popup] Audio src:', popupAudio.src);
    console.error('[Popup] Audio error event:', e);

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
    console.log('[Popup] Tracking blob URL:', currentBlobUrl);
  }
  popupAudio.src = url;
  console.log('[Popup] Setting audio src to:', url);
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

    // Use HTTP endpoint directly
    var response = await fetch('http://localhost:8000/api/voices/demo?lang=cs');
    if (!response.ok) throw new Error('Failed to fetch');

    var data = await response.json();

    if (data.voices && data.voices.length > 0) {
      voices = data.voices;
      if (voiceSelect) {
        voiceSelect.innerHTML = voices.map(function (v) {
          return '<option value="' + v.id + '">' + v.display_name + '</option>';
        }).join('');
      }

      loadSettings().then(function () {
        setStatus('Nalezeno ' + voices.length + ' hlasu', '#4caf50');
      });
    } else {
      if (voiceSelect) voiceSelect.innerHTML = '<option value="">Zadne hlasy</option>';
      setStatus('Zadne hlasy nenalezeny', '#ff9800');
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

// Listen for voices list
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('[Popup] Received message:', request.action);

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
    console.error('[Popup] Audio error received:', request.error);
    setStatus('Chyba přehrávání: ' + (request.error || 'Neznámá chyba'), '#ff4444');
    isPlaying = false;
    isStreaming = false;
    updatePlayButton();
    renderPlaylist();
  } else if (request.action === 'play_in_popup') {
    console.log('[Popup] Playing audio from background:', request.url);
    playAudioInPopup(request.url);
    sendResponse({ success: true });
  }

  return true;
});

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  console.log('[Popup] Initializing popup...');

  // Event listeners
  if (voiceSelect) {
    voiceSelect.onchange = () => {
      saveSettings();
    };
  }

  if (speedInput) speedInput.onchange = () => saveSettings();
  if (temperatureInput) temperatureInput.onchange = () => saveSettings();

  if (playBtn) {
    playBtn.onclick = () => {
      console.log('[Popup] Play button clicked, isPlaying:', isPlaying, 'isStreaming:', isStreaming, 'currentIndex:', currentIndex);
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

  // Check backend connection
  setTimeout(function () {
    fetch('http://localhost:8000/health', { method: 'GET' })
      .then(function (res) {
        if (res.ok) {
          console.log('[Popup] Backend is running');
        } else {
          console.log('[Popup] Backend returned:', res.status);
        }
      })
      .catch(function (err) {
        console.log('[Popup] Backend not reachable:', err.message);
      });
  }, 1000);
});