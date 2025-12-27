"""
Middleware setup pro FastAPI aplikaci
"""
import sys
import os
import warnings
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI

# Potlačení deprecation warnings
warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated.*", category=UserWarning)
warnings.filterwarnings("ignore", message=".*resume_download.*", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*weight_norm is deprecated.*", category=UserWarning)

# Windows + librosa/numba: na některých sestavách padá numba ufunc při pitch shifting
if os.name == "nt":
    os.environ.setdefault("NUMBA_DISABLE_JIT", "1")

# Windows: zajisti UTF-8 pro výpisy
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def setup_cors(app: FastAPI):
    """Nastaví CORS middleware"""
    app.add_middleware(
        CORSMiddleware,
        # Pro dev režim povolíme CORS široce, aby šly načítat WAVy přes WaveSurfer z FE na jiném portu
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

