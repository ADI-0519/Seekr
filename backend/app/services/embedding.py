import logging
import os

from app.core.config import get_settings

log = logging.getLogger(__name__)

# Configure HuggingFace cache directory before ML libraries are imported
_settings = get_settings()
if _settings.hf_home:
    os.environ.setdefault("HF_HOME", _settings.hf_home)

# Safely attempt to import heavy ML dependencies to allow application boot in environments without GPUs
_flag_ok = False
_flag_import_error: Exception | None = None
try:
    from FlagEmbedding import BGEM3FlagModel

    _flag_ok = True
except Exception as e:
    _flag_import_error = e

_st_ok = False
try:
    from sentence_transformers import SentenceTransformer

    _st_ok = True
except ImportError:
    pass

_fastembed_ok = False
_fastembed_import_error: Exception | None = None
try:
    from fastembed import SparseTextEmbedding

    _fastembed_ok = True
except Exception as e:
    _fastembed_import_error = e


# Service to generate mathematical vector representations of text for search and retrieval
class EmbeddingService:
    def __init__(self, model_path: str | None = None):
        settings = get_settings()
        self._model_path = model_path if model_path else settings.embedding_model

        # Determine the model backend based on whether the path points to a local directory
        self._use_st = os.path.isdir(self._model_path)
        self._model = None
        self._sparse_model = None

    # Load the specified embedding model into GPU or CPU memory
    def load(self):
        if self._model is not None:
            return

        import torch

        device = "cuda" if torch.cuda.is_available() else "cpu"

        if self._use_st:
            if not _st_ok:
                raise RuntimeError(
                    "sentence-transformers is not installed but a local checkpoint path was given. "
                    "Run: pip install sentence-transformers"
                )
            log.info(
                "loading fine-tuned embedding model from %s on device=%s", self._model_path, device
            )
            self._model = SentenceTransformer(self._model_path, device=device)
            log.info("fine-tuned embedding model loaded")
        else:
            if not _flag_ok:
                detail = (
                    f"FlagEmbedding failed to import: {type(_flag_import_error).__name__}: "
                    f"{_flag_import_error}"
                    if _flag_import_error
                    else "FlagEmbedding is unavailable for an unknown reason"
                )
                raise RuntimeError(
                    "Embedding backend unavailable. "
                    f"{detail}. "
                    "Check requirements_ml.txt version pins (FlagEmbedding/transformers/torch) "
                    "and rebuild the worker image."
                ) from _flag_import_error

            log.info("loading BGE-M3 on device=%s", device)
            self._model = BGEM3FlagModel(
                self._model_path, use_fp16=(device == "cuda"), local_files_only=True
            )
            log.info("BGE-M3 loaded")

    # Convert a list of text strings into dense vector representations
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        self.load()
        assert self._model is not None

        all_vecs = []

        # Process text in chunks to prevent memory exhaustion on large inputs
        for i in range(0, len(texts), 32):
            batch = texts[i : i + 32]

            if self._use_st:
                vecs = self._model.encode(batch, normalize_embeddings=True, show_progress_bar=False)
                for vec in vecs:
                    all_vecs.append(vec.tolist() if hasattr(vec, "tolist") else list(vec))
            else:
                out = self._model.encode(
                    batch,
                    return_dense=True,
                    return_sparse=False,
                    return_colbert_vecs=False,
                )
                for vec in out["dense_vecs"]:
                    all_vecs.append(vec.tolist() if hasattr(vec, "tolist") else list(vec))

        return all_vecs

    def _load_sparse_model(self):
        if self._sparse_model is not None:
            return self._sparse_model

        if not _fastembed_ok:
            detail = (
                f"{type(_fastembed_import_error).__name__}: {_fastembed_import_error}"
                if _fastembed_import_error
                else "unknown import error"
            )
            raise RuntimeError(
                "BM25 encoder unavailable. Install fastembed and rebuild the worker image. "
                f"Import failed with {detail}."
            ) from _fastembed_import_error

        settings = get_settings()
        self._sparse_model = SparseTextEmbedding(
            model_name="Qdrant/bm25",
            cache_dir=settings.hf_home or None,
            lazy_load=True,
        )
        return self._sparse_model

    # Generate BM25 term-frequency vectors. Qdrant applies collection-level IDF at search time.
    def bm25_encode(self, texts: list[str]) -> list[dict[int, float]]:
        if not texts:
            return []

        model = self._load_sparse_model()
        return [embedding.as_dict() for embedding in model.embed(texts)]
