try:
    from parallel_wavegan.utils import download_pretrained_model
    import inspect
    print("Checking parallel-wavegan available models...")
    # This might print something, or I can try to find where they are defined
except ImportError:
    print("parallel-wavegan not installed")
