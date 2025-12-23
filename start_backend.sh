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

# Výchozí headroom (pokud není nastaven zvenku)
: "${OUTPUT_HEADROOM_DB:=-9.0}"
export OUTPUT_HEADROOM_DB

# Spuštění backendu
cd backend
python main.py











