/**
 * Shared Text Splitting Utility
 * Používá Chrome extension i backend (přes PyExecJS nebo import)
 */

const CZ_ABBREVIATIONS = new Set([
  'např', 'tj', 'tzn', 'tzv', 'apod', 'č', 'resp', 'popř',
  'event', 'max', 'min', 'například', 'takzvaný', 'čís',
  'př', 'n', 'm', 'k', 's', 'v', 'z', 'u', 'o', 'i', 'a'
]);

function isAbbreviation(word) {
  const clean = word.toLowerCase().replace(/\.$/, '');
  return CZ_ABBREVIATIONS.has(clean);
}

function splitIntoSentences(text) {
  const sentences = [];
  let position = 0;
  const len = text.length;
  
  while (position < len) {
    let foundEnd = false;
    
    for (let i = position; i < len; i++) {
      const char = text[i];
      
      if (char === '.' || char === '!' || char === '?') {
        let isAbbrevWord = false;
        for (let j = i - 1; j >= position; j--) {
          if (text[j] === ' ') break;
          if (isAbbreviation(text.substring(j, i + 1))) {
            isAbbrevWord = true;
            break;
          }
        }
        if (isAbbrevWord) continue;
        
        let j = i + 1;
        while (j < len && (text[j] === ' ' || text[j] === '\n' || 
                           text[j] === '\r' || text[j] === '\t')) {
          j++;
        }
        
        if (j > i + 1 || i === len - 1) {
          const sentence = text.substring(position, j).trim();
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
      const remaining = text.substring(position).trim();
      if (remaining.length > 0) sentences.push(remaining);
      break;
    }
  }
  
  return sentences.filter(s => s.length > 0);
}

function splitIntoChunks(sentences, options = {}) {
  const {
    minSize = 150,
    maxSize = 300,
    enableWordWrap = true
  } = options;
  
  if (sentences.length === 0) return [];
  
  const chunks = [];
  
  function wrapSentence(sentence, max) {
    if (sentence.length <= max) return [sentence];
    
    const words = sentence.split(' ');
    const wrapped = [];
    let current = '';
    
    for (const word of words) {
      const test = current ? `${current} ${word}` : word;
      if (test.length > max) {
        if (current) wrapped.push(current);
        current = word;
      } else {
        current = test;
      }
    }
    if (current) wrapped.push(current);
    return wrapped;
  }
  
  let currentChunk = '';
  
  for (const sentence of sentences) {
    const wrappedParts = enableWordWrap 
      ? wrapSentence(sentence, maxSize) 
      : [sentence];
    
    for (const part of wrappedParts) {
      const testChunk = currentChunk ? `${currentChunk} ${part}` : part;
      
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
  const reconstructed = chunks.join(' ').replace(/\s+/g, ' ').trim();
  const original = originalText.replace(/\s+/g, ' ').trim();
  const similarity = reconstructed.length / Math.max(original.length, 1);
  
  return {
    isValid: similarity > 0.7,
    chunkCount: chunks.length,
    totalLength: chunks.reduce((sum, c) => sum + c.length, 0),
    similarity: Math.round(similarity * 100) + '%'
  };
}

function processText(text, options = {}) {
  const sanitized = sanitizeText(text);
  const sentences = splitIntoSentences(sanitized);
  const chunks = splitIntoChunks(sentences, options);
  const validation = validateChunks(chunks, sanitized);
  
  return {
    chunks,
    sentences: sentences.length,
    validation
  };
}

function sanitizeText(text) {
  return text
    .replace(/—/g, '-').replace(/–/g, '-')
    .replace(/[""„""]/g, '"').replace(/[''‛'']/g, "'")
    .replace(/…/g, '...')
    .replace(/\s+/g, ' ')
    .trim();
}

function applyTTSFormatting(text) {
  return text.replace(/,/g, ' - ').replace(/\./g, ' ... ');
}

function formatTextForStreaming(chunks) {
  return chunks.map(chunk => applyTTSFormatting(chunk)).join(' ');
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { 
    splitIntoSentences, 
    splitIntoChunks, 
    processText,
    validateChunks,
    sanitizeText,
    applyTTSFormatting,
    formatTextForStreaming,
    CZ_ABBREVIATIONS
  };
}
