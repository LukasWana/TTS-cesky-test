
import f5_tts.api
import inspect

def print_signature():
    try:
        method = f5_tts.api.F5TTS.infer
        sig = inspect.signature(method)
        print(f"SIGNATURE_START")
        print(sig)
        print(f"SIGNATURE_END")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    print_signature()
