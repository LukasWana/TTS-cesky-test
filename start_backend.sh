#!/bin/bash

# Aktivace virtual environment
source venv/bin/activate

# Nastavení PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Výchozí headroom (pokud není nastaven zvenku)
: "${OUTPUT_HEADROOM_DB:=-9.0}"
export OUTPUT_HEADROOM_DB

# Spuštění backendu
cd backend
python main.py











