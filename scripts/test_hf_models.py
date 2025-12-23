import warnings
# Potlačení FutureWarning z huggingface_hub o resume_download
warnings.filterwarnings("ignore", message=".*resume_download.*", category=FutureWarning)

from huggingface_hub import snapshot_download
from pathlib import Path

models_to_test = [
    "kan-bayashi/ljspeech_hifigan.v1",
    "espnet/kan-bayashi_ljspeech_hifigan",
    "espnet/kan-bayashi_ljspeech_joint_finetune_conformer_fastspeech2_hifigan"
]

for model_id in models_to_test:
    print(f"Testing {model_id}...")
    try:
        path = snapshot_download(repo_id=model_id, local_files_only=False)
        print(f"✅ Success! Downloaded to {path}")
        break
    except Exception as e:
        print(f"❌ Failed: {e}")
