"""
Test script for Applio integration
Run this to verify the Applio module is correctly set up
"""

import sys
import asyncio
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))


def test_imports():
    """Test basic imports"""
    print("Testing imports...")

    try:
        from backend.applio.config import (
            APPLIO_ENABLED,
            APPLIO_DIR,
            APPLIO_MODELS_DIR,
            APPLIO_VOICES_DIR,
            APPLIO_BASE_URL,
            RVC_PITCH_METHOD,
            RVC_INDEX_RATIO,
            EDGE_TTS_VOICES,
        )

        print("  [OK] Config imports OK")
        print(f"     APPLIO_ENABLED: {APPLIO_ENABLED}")
        print(f"     APPLIO_DIR: {APPLIO_DIR}")
        print(f"     RVC_PITCH_METHOD: {RVC_PITCH_METHOD}")
        print(f"     RVC_INDEX_RATIO: {RVC_INDEX_RATIO}")
        print(f"     Supported languages: {list(EDGE_TTS_VOICES.keys())}")
    except ImportError as e:
        print(f"  [FAIL] Config imports failed: {e}")
        return False

    try:
        from backend.applio.engine import ApplioEngine

        print("  [OK] Engine imports OK")
    except ImportError as e:
        print(f"  [FAIL] Engine imports failed: {e}")
        return False

    try:
        from backend.applio.subprocess_manager import ApplioSubprocessManager

        print("  [OK] Subprocess Manager imports OK")
    except ImportError as e:
        print(f"  [FAIL] Subprocess Manager failed: {e}")
        return False

    try:
        from backend.applio.integration import (
            ApplioIntegration,
            get_applio_integration,
            init_applio,
        )

        print("  [OK] Integration imports OK")
    except ImportError as e:
        print(f"  [FAIL] Integration imports failed: {e}")
        return False

    return True


def test_applio_directory():
    """Test if Applio directory exists"""
    print("\nChecking Applio directory...")

    from backend.applio.config import APPLIO_DIR

    if APPLIO_DIR.exists():
        print(f"  [OK] Applio directory exists: {APPLIO_DIR}")

        # Check for run script
        run_script = APPLIO_DIR / "run-applio.bat"
        run_sh = APPLIO_DIR / "run-applio.sh"

        if run_script.exists():
            print(f"  [OK] Windows script found: {run_script}")
        elif run_sh.exists():
            print(f"  [OK] Linux script found: {run_sh}")
        else:
            print(
                "  [WARN] No run script found (expected: run-applio.bat or run-applio.sh)"
            )
            print("      Download Applio from https://applio.org")
    else:
        print(f"  [FAIL] Applio directory missing: {APPLIO_DIR}")
        print(
            "      Download Applio from https://applio.org and extract to this directory"
        )
        return False

    return True


async def test_engine_creation():
    """Test engine creation"""
    print("\nTesting engine creation...")

    try:
        from backend.applio.engine import ApplioEngine

        engine = ApplioEngine()
        print(f"  [OK] Engine created: {engine.base_url}")
        return True
    except Exception as e:
        print(f"  [FAIL] Engine creation failed: {e}")
        return False


def test_integration():
    """Test integration helper"""
    print("\nTesting integration helper...")

    try:
        from backend.applio.integration import get_applio_integration

        integration = get_applio_integration()
        print("  [OK] Integration helper created")
        return True
    except Exception as e:
        print(f"  [FAIL] Integration helper failed: {e}")
        return False


async def run_tests():
    """Run all tests"""
    print("=" * 60)
    print("APPLIO INTEGRATION TEST")
    print("=" * 60)

    results = []

    # Test imports
    results.append(("Imports", test_imports()))

    # Test directory
    results.append(("Directory", test_applio_directory()))

    # Test engine
    results.append(("Engine Creation", await test_engine_creation()))

    # Test integration
    results.append(("Integration Helper", test_integration()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("All tests passed! Applio is ready to use.")
        print("\nNext steps:")
        print("1. Download Applio from https://applio.org")
        print("2. Extract to backend/applio/")
        print("3. Run ./run-applio.bat")
        print("4. Access API at http://localhost:9874")
    else:
        print("Some tests failed. Check the errors above.")
        print("\nIf Applio directory is missing:")
        print("  - Download Applio from https://applio.org")
        print("  - Extract to backend/applio/")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
