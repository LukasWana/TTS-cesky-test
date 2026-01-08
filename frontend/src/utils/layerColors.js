/**
 * Barevné palety pro kategorie audio vrstev
 * Každá kategorie má 4 odstíny pro lepší rozlišení vrstev
 */

// Barevné palety pro jednotlivé kategorie (4 odstíny každá)
const COLOR_PALETTES = {
  tts: [
    '#3b82f6',
    '#2563eb',
    '#1d4ed8',
    '#1e40af'
  ],
  f5tts: [
    '#a855f7',
    '#9333ea',
    '#7e22ce',
    '#6b21a8'
  ],
  music: [
    '#10b981',
    '#059669',
    '#047857',
    '#065f46'
  ],
  bark: [
    '#f97316',
    '#ea580c',
    '#c2410c',
    '#9a3412'
  ],
  applio: [
    '#06b6d4',
    '#0891b2',
    '#0e7490',
    '#155e75'
  ],
  file: [
    '#9ca3af',
    '#6b7280',
    '#4b5563',
    '#374151'
  ],
  voicepreparation: [
    '#8b0000',
    '#991b1b',
    '#b91c1c',
    '#dc2626'
  ]
}

/**
 * Získá barvu pro kategorii a index vrstvy
 * @param {string} category - Kategorie vrstvy (tts, f5tts, music, bark, file)
 * @param {number} index - Index vrstvy v kategorii (0-based)
 * @returns {string} Hex barva
 */
export function getCategoryColor(category, index = 0) {
  const palette = COLOR_PALETTES[category] || COLOR_PALETTES.file
  const shadeIndex = index % palette.length
  return palette[shadeIndex]
}

/**
 * Určí kategorii z history entry
 * @param {Object} entry - History entry objekt
 * @returns {string} Kategorie (tts, f5tts, music, bark, file)
 */
export function getCategoryFromHistoryEntry(entry) {
  if (!entry) return 'file'

  // Pokud má entry source, použij ho
  if (entry.source) {
    return entry.source
  }

  // Fallback na file
  return 'file'
}

/**
 * Získá počet vrstev v dané kategorii
 * @param {Array} layers - Pole všech vrstev
 * @param {string} category - Kategorie
 * @returns {number} Počet vrstev v kategorii
 */
export function getLayerCountInCategory(layers, category) {
  return layers.filter(layer => layer.category === category).length
}

/**
 * Získá barvu pro novou vrstvu na základě kategorie a existujících vrstev
 * @param {Array} layers - Pole všech existujících vrstev
 * @param {string} category - Kategorie nové vrstvy
 * @returns {string} Hex barva
 */
export function getColorForNewLayer(layers, category) {
  const countInCategory = getLayerCountInCategory(layers, category)
  return getCategoryColor(category, countInCategory)
}

