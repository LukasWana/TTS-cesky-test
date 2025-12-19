#!/bin/bash

# Aktivace virtual environment
source venv/bin/activate

# Nastavení PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Spuštění backendu
cd backend
python main.py







