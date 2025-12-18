import requests
import json
import time
from pathlib import Path

API_URL = "http://localhost:8000"

def test_generate_with_features():
    print("Testing TTS generation with specific quality features...")

    # 1. Test with everything ON (default)
    payload = {
        "text": "Toto je test s plným vylepšením zvuku.",
        "demo_voice": "lucie",
        "enable_enhancement": "true",
        "enable_normalization": "true",
        "enable_denoiser": "true",
        "enable_trim": "true"
    }

    try:
        response = requests.post(f"{API_URL}/api/tts/generate", data=payload)
        if response.status_code == 200:
            print("✅ Generation with all features ON successful")
            data = response.json()
            print(f"   Audio URL: {data.get('audio_url')}")
        else:
            print(f"❌ Generation with all features ON failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

    # 2. Test with normalization OFF
    payload_no_norm = {
        "text": "Toto je test bez normalizace.",
        "demo_voice": "lucie",
        "enable_enhancement": "true",
        "enable_normalization": "false"
    }

    try:
        response = requests.post(f"{API_URL}/api/tts/generate", data=payload_no_norm)
        if response.status_code == 200:
            print("✅ Generation with normalization OFF successful")
        else:
            print(f"❌ Generation with normalization OFF failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

    # 3. Test with trim OFF
    payload_no_trim = {
        "text": "Toto je test bez ořezu ticha.",
        "demo_voice": "lucie",
        "enable_enhancement": "true",
        "enable_trim": "false"
    }

    # 4. Test with HiFi-GAN ON
    payload_hifigan = {
        "text": "Toto je test s HiFi-GAN vocoderem.",
        "demo_voice": "lucie",
        "use_hifigan": "true"
    }

    try:
        response = requests.post(f"{API_URL}/api/tts/generate", data=payload_hifigan)
        if response.status_code == 200:
            print("✅ Generation with HiFi-GAN successful")
        else:
            print(f"❌ Generation with HiFi-GAN failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

    return True

if __name__ == "__main__":
    # Check if server is running
    try:
        requests.get(API_URL)
        if test_generate_with_features():
            print("\nVerification completed successfully!")
        else:
            print("\nVerification failed.")
    except Exception:
        print(f"❌ Backend server not running at {API_URL}. Please start it first.")
