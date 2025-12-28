/**
 * Barevné palety pro kategorie audio vrstev
 * Každá kategorie má 4 odstíny pro lepší rozlišení vrstev
 */

// Barevné palety pro jednotlivé kategorie (4 odstíny každá)
const COLOR_PALETTES = {
  tts: [
    '#3b82f6', // Modrá - světlejší
    '#2563eb', // Modrá - střední
    '#1d4ed8', // Modrá - tmavší
    '#1e40af'  // Modrá - nejtmavší
  ],
  f5tts: [
    '#a855f7', // Fialová - světlejší
    '#9333ea', // Fialová - střední
    '#7e22ce', // Fialová - tmavší
    '#6b21a8'  // Fialová - nejtmavší
  ],
  music: [
    '#10b981', // Zelená - světlejší
    '#059669', // Zelená - střední
    '#047857', // Zelená - tmavší
    '#065f46'  // Zelená - nejtmavší
  ],
  bark: [
    '#f97316', // Oranžová - světlejší
    '#ea580c', // Oranžová - střední
    '#c2410c', // Oranžová - tmavší
    '#9a3412'  // Oranžová - nejtmavší
  ],
  file: [
    '#9ca3af', // Šedá - světlejší
    '#6b7280', // Šedá - střední
    '#4b5563', // Šedá - tmavší
    '#374151'  // Šedá - nejtmavší
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

