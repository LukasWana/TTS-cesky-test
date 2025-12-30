"""
Rychlý check, jestli je PyTorch v aktuálním prostředí CUDA-ready.
Exit codes:
  0 = OK (CUDA dostupná)
  1 = Není OK (torch chybí / CUDA není dostupná)
"""

import sys

try:
    import torch
except Exception:
    sys.exit(1)

if not torch.cuda.is_available():
    sys.exit(1)

# Volitelně: chceme CUDA build (např. 2.1.0+cu121). Pokud by někdy fungovalo i bez +cu, nevadí.
sys.exit(0)












