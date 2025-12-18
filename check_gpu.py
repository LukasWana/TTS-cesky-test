"""
Diagnostický skript pro kontrolu GPU a CUDA podpory
"""
import sys
import io

# Nastavení UTF-8 encoding pro Windows konzoli
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print("=" * 60)
print("DIAGNOSTIKA GPU A CUDA")
print("=" * 60)
print()

# 1. Kontrola PyTorch
print("1. KONTROLA PYTORCH")
print("-" * 60)
try:
    import torch
    print(f"✅ PyTorch je nainstalován")
    print(f"   Verze: {torch.__version__}")

    # Kontrola CUDA v PyTorch
    print(f"\n   CUDA dostupná v PyTorch: {torch.cuda.is_available()}")

    if torch.cuda.is_available():
        print(f"   ✅ CUDA je dostupná!")
        print(f"   CUDA verze: {torch.version.cuda}")
        print(f"   Počet GPU: {torch.cuda.device_count()}")
        for i in range(torch.cuda.device_count()):
            print(f"   GPU {i}: {torch.cuda.get_device_name(i)}")
            print(f"      VRAM: {torch.cuda.get_device_properties(i).total_memory / 1024**3:.2f} GB")
    else:
        print(f"   ❌ CUDA není dostupná v PyTorch")
        print(f"   Důvod: PyTorch je pravděpodobně nainstalován bez CUDA podpory")
        print(f"   Řešení: Nainstalujte PyTorch s CUDA pomocí:")
        print(f"   pip uninstall torch torchaudio -y")
        print(f"   pip install torch==2.1.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cu118")

except ImportError:
    print("❌ PyTorch není nainstalován")
    sys.exit(1)

print()

# 2. Kontrola CUDA toolkit v systému
print("2. KONTROLA CUDA TOOLKIT V SYSTÉMU")
print("-" * 60)
import subprocess
import os

# Zkus najít nvcc (CUDA compiler)
nvcc_path = None
for path in os.environ.get("PATH", "").split(os.pathsep):
    nvcc_candidate = os.path.join(path, "nvcc.exe" if sys.platform == "win32" else "nvcc")
    if os.path.exists(nvcc_candidate):
        nvcc_path = nvcc_candidate
        break

if nvcc_path:
    try:
        result = subprocess.run(
            [nvcc_path, "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Extrahuj verzi z výstupu
            lines = result.stdout.split('\n')
            for line in lines:
                if "release" in line.lower():
                    print(f"✅ CUDA toolkit je nainstalován")
                    print(f"   {line.strip()}")
                    break
        else:
            print("⚠️  nvcc nalezen, ale nelze získat verzi")
    except Exception as e:
        print(f"⚠️  Nelze spustit nvcc: {e}")
else:
    print("⚠️  CUDA toolkit (nvcc) není v PATH")
    print("   To může být v pořádku - PyTorch může používat CUDA i bez nvcc v PATH")

print()

# 3. Kontrola GPU přes nvidia-smi (pokud je dostupný)
print("3. KONTROLA GPU PŘES NVIDIA-SMI")
print("-" * 60)
try:
    result = subprocess.run(
        ["nvidia-smi"],
        capture_output=True,
        text=True,
        timeout=5
    )
    if result.returncode == 0:
        print("✅ nvidia-smi je dostupný")
        # Zobraz první řádky výstupu
        lines = result.stdout.split('\n')[:10]
        for line in lines:
            if line.strip():
                print(f"   {line}")
    else:
        print("⚠️  nvidia-smi nelze spustit")
except FileNotFoundError:
    print("⚠️  nvidia-smi není nainstalován nebo není v PATH")
    print("   To může znamenat, že NVIDIA GPU driver není nainstalován")
except Exception as e:
    print(f"⚠️  Chyba při spuštění nvidia-smi: {e}")

print()

# 4. Shrnutí a doporučení
print("=" * 60)
print("SHRNUTÍ A DOPORUČENÍ")
print("=" * 60)
print()

if torch.cuda.is_available():
    print("✅ Vše je v pořádku! GPU by mělo být dostupné.")
    print("   Pokud backend stále hlásí 'GPU nedostupné', zkontrolujte:")
    print("   1. Zda není nastavena environment variable FORCE_DEVICE=cpu")
    print("   2. Zda backend používá správný config.py")
else:
    print("❌ GPU není dostupné. Postupujte podle těchto kroků:")
    print()
    print("KROK 1: Zkontrolujte, zda máte NVIDIA GPU")
    print("   - Otevřete Device Manager (Správce zařízení)")
    print("   - Podívejte se do sekce 'Display adapters'")
    print("   - Měli byste vidět vaši NVIDIA GPU")
    print()
    print("KROK 2: Nainstalujte NVIDIA GPU driver (pokud chybí)")
    print("   - Stáhněte z: https://www.nvidia.com/drivers")
    print("   - Nainstalujte nejnovější driver pro vaši GPU")
    print()
    print("KROK 3: Nainstalujte PyTorch s CUDA podporou")
    print("   - Spusťte: install_pytorch_gpu.bat")
    print("   - Nebo ručně:")
    print("     pip uninstall torch torchaudio -y")
    print("     pip install torch==2.1.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cu118")
    print()
    print("KROK 4: Restartujte backend server")
    print()

print("=" * 60)

