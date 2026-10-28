import easyocr
from huggingface_hub import snapshot_download

MODELS = [
    "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
    "BAAI/bge-m3",
    "cross-encoder/ms-marco-MiniLM-L-6-v2",
    "Qdrant/bm25",
]


def ensure_model(model_id):
    try:
        snapshot_download(model_id, local_files_only=True, max_workers=1)
        print(f"hf_cache_init: {model_id} already cached")
    except Exception:
        print(f"hf_cache_init: downloading {model_id}")
        snapshot_download(model_id, max_workers=1)


for model_id in MODELS:
    ensure_model(model_id)

print("hf_cache_init: downloading easyocr models...")
easyocr.Reader(["en"], gpu=False)
print("hf_cache_init: models present")
