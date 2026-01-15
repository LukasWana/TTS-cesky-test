/**
 * Text Processing Module for Chrome Extension v2
 * Uses shared_text_splitter.js for consistent text processing
 */

function applyTTSFormatting(text) {
  return text.replace(/,/g, ' - ').replace(/\./g, ' ... ');
}

function processTextAdvanced(text) {
  var result = processText(text, {
    minSize: 150,
    maxSize: 300,
    enableWordWrap: true
  });
  
  console.log('[Background v2] Text processing result:', {
    originalLength: text.length,
    sentences: result.sentences,
    chunks: result.chunks.length,
    totalChunkLength: result.validation.totalLength,
    validation: result.validation
  });
  
  var formatted = result.chunks.map(function(chunk) {
    return applyTTSFormatting(chunk);
  });
  
  console.log('[Background v2] First chunk:', formatted[0] ? formatted[0].substring(0, 80) : 'none');
  console.log('[Background v2] Last chunk:', formatted[formatted.length - 1] ? formatted[formatted.length - 1].substring(0, 80) : 'none');
  
  return formatted;
}

function getProgress() {
  return chrome.storage.local.get('progress').then(function(data) {
    return data.progress || null;
  });
}

function setProgress(chunkIndex, totalChunks, message) {
  var progress = {
    chunkIndex: chunkIndex,
    totalChunks: totalChunks,
    message: message,
    timestamp: Date.now()
  };
  chrome.storage.local.set({ progress: progress });
  return progress;
}

function clearProgress() {
  chrome.storage.local.remove('progress');
}
