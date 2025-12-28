#!/bin/bash

# Aktivace virtual environment
source venv/bin/activate

# Nastavení PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Doinstaluj backend dependencies pokud chybí (hlavně MusicGen / transformers)
python -c "import transformers" >/dev/null 2>&1 || (
  echo "[INFO] transformers nejsou nainstalované – instaluji requirements.txt..."
  python -m pip install --upgrade pip
  pip install -r requirements.txt
)

# Kontrola Demucs (volitelné, ale doporučené pro separaci hlasu)
python -c "import demucs" >/dev/null 2>&1 || (
  echo "[INFO] Demucs není nainstalován – instaluji..."
  pip install "demucs>=4.0.0"
  if [ $? -ne 0 ]; then
    echo "WARNING: Instalace Demucs selhala. Separace hlasu od pozadí nebude dostupná."
    echo "Můžete nainstalovat později: pip install demucs"
  else
    echo "Demucs nainstalován úspěšně."
  fi
)

# Výchozí headroom (pokud není nastaven zvenku)
# POZOR: Musí odpovídat výchozí hodnotě v backend/config.py (-18.0 dB)!
# Změna této hodnoty může způsobit přebuzení audio!
: "${OUTPUT_HEADROOM_DB:=-18.0}"
export OUTPUT_HEADROOM_DB

# Spuštění backendu
cd backend
python main.py











