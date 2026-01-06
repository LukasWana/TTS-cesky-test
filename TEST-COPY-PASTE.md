# 🔍 DIAGNOSTIKA COPY/PASTE NASTAVENÍ

## Kde se nastavení ukládají:

### 1. **SessionStorage** (dočasná schránka)
```javascript
Klíč: 'tts_copied_settings'  // Czech F5-TTS
Klíč: 'tts_copied_settings_sk'  // Slovak F5-TTS
```

**Co obsahuje:**
```json
{
  "ttsSettings": { speed, nfeStep, cfgStrength, ... },
  "qualitySettings": { enableEnhancement, ... },
  "timestamp": 1234567890,
  "sourceVariant": "variant2"
}
```

### 2. **LocalStorage** (trvalé uložení)
```javascript
Klíč: 'f5tts_cs_voice_{voiceId}_variant_{variantId}'
```

**Příklad:**
```
f5tts_cs_voice_demo_cs_1_variant_variant1
f5tts_cs_voice_demo_cs_1_variant_variant2
...
```

---

## Jak testovat v prohlížeči:

### 1. Otevřete DevTools (F12)
- Záložka: **Console**

### 2. Zkopírujte nastavení:
- Klikněte na tlačítko **"📋 Kopírovat"**
- V konzoli byste měli vidět:
  ```
  📋 Nastavení zkopírována z varianty: variant2 {...}
  ```

### 3. Zkontrolujte SessionStorage:
```javascript
// V konzoli napište:
sessionStorage.getItem('tts_copied_settings')
```
**Očekávaný výstup:** JSON string s nastavením

### 4. Vložte nastavení:
- Přepněte na jiný profil (např. P3)
- Klikněte na **"📥 Vložit"**
- V konzoli byste měli vidět:
  ```
  📥 Vkládám nastavení: variant2 → variant3
  ✅ Vložená nastavení uložena do varianty: variant3
  ```

### 5. Zkontrolujte LocalStorage:
```javascript
// V konzoli napište:
localStorage.getItem('f5tts_cs_voice_demo_cs_1_variant_variant3')
```

---

## Možné problémy:

### ❌ **Problém 1: Tlačítka nejsou viditelná**
**Řešení:** Zkontrolujte CSS, možná jsou překrytá

### ❌ **Problém 2: Funkce nejsou volány**
**Test:**
```javascript
// Otevřete konzoli a napište:
window.testCopy = () => {
  const data = {
    ttsSettings: { speed: 1.5, nfeStep: 48 },
    qualitySettings: { enableEnhancement: true }
  }
  sessionStorage.setItem('tts_copied_settings', JSON.stringify(data))
  console.log('✅ Test data uložena')
}

window.testPaste = () => {
  const data = sessionStorage.getItem('tts_copied_settings')
  console.log('📥 Načtená data:', JSON.parse(data))
}

// Pak zavolejte:
testCopy()
testPaste()
```

### ❌ **Problém 3: State se neaktualizuje**
- Po kliknutí na "Vložit" zkontrolujte, zda se slidery pohly
- Pokud ne, může být problém v React state aktualizaci

### ❌ **Problém 4: useEffect přepisuje změny**
- V kódu je useEffect s debounce (300ms)
- Možná přepisuje vložená nastavení

---

## Manuální test:

### Krok 1: Zkopírujte nastavení manuálně
```javascript
// V konzoli:
const settings = {
  ttsSettings: {
    speed: 1.8,
    nfeStep: 64,
    cfgStrength: 3.0,
    swaySamplingCoef: -1.0
  },
  qualitySettings: {
    enableEnhancement: true,
    enableDenoiser: true
  },
  timestamp: Date.now(),
  sourceVariant: 'variant1'
}
sessionStorage.setItem('tts_copied_settings', JSON.stringify(settings))
console.log('✅ Manuálně zkopírováno')
```

### Krok 2: Klikněte na "Vložit"
- Mělo by se aplikovat

### Krok 3: Pokud to nefunguje, zkuste přímo:
```javascript
// Simulace paste funkce:
const copiedData = sessionStorage.getItem('tts_copied_settings')
const parsed = JSON.parse(copiedData)
console.log('Data z schránky:', parsed)
```

---

## Kontrolní seznam:

- [ ] Tlačítka "Kopírovat" a "Vložit" jsou viditelná
- [ ] Kliknutí na "Kopírovat" zobrazí notifikaci "Nastavení zkopírováno"
- [ ] V konzoli se objeví log: `📋 Nastavení zkopírována...`
- [ ] SessionStorage obsahuje data (zkontrolovat v DevTools → Application → Session Storage)
- [ ] Kliknutí na "Vložit" zobrazí notifikaci "Nastavení vloženo"
- [ ] V konzoli se objeví log: `📥 Vkládám nastavení...`
- [ ] Slidery se přesunou na nové hodnoty
- [ ] LocalStorage se aktualizuje (zkontrolovat v DevTools → Application → Local Storage)

---

## Pokud nic z toho nefunguje:

**Možná chybí React import nebo build:**
1. Restartujte vývojový server (npm run dev)
2. Zkontrolujte, že frontend běží správně
3. Otevřete stránku v novém okně bez cache (Ctrl+Shift+R)
