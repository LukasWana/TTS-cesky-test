
import f5_tts.api
import inspect

try:
    print(f"Inspecting F5TTS.infer...")
    sig = inspect.signature(f5_tts.api.F5TTS.infer)
    print(f"Signature: {sig}")

    # Print source code if possible
    try:
        source = inspect.getsource(f5_tts.api.F5TTS.infer)
        print("\nSource code:")
        print(source)
    except:
        print("\nCould not get source code.")

except Exception as e:
    print(f"Error: {e}")
