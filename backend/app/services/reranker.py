import logging
import os

log = logging.getLogger(__name__)

_model = None
_load_attempted = False

# Default to a standard MS MARCO model for passage ranking
_MODEL_ID = "cross-encoder/ms-marco-MiniLM-L-6-v2"


# Load the machine learning model lazily to conserve memory during application boot
def get_model():
    global _model, _load_attempted
    if _load_attempted:
        return _model
    _load_attempted = True

    # Allow environment variable override for testing or continuous integration pipelines
    model_path = os.environ.get("CROSS_ENCODER_PATH", _MODEL_ID)
    local_only = model_path != _MODEL_ID

    try:
        from sentence_transformers import CrossEncoder

        _model = CrossEncoder(model_path, local_files_only=local_only)
    except Exception as e:
        log.warning("cross-encoder failed to load, falling back to passthrough: %s", e)
    return _model


# Combine the spoken transcript and the visual slide text into a single document for evaluation
def build_doc(candidate: dict[str, object]) -> str:
    text = str(candidate.get("text") or "")
    slide = str(candidate.get("slide_text") or "")
    if slide:
        return f"{text}\n[Slide: {slide}]"
    return text


# Service class to re-evaluate and sort search results using a high-accuracy neural network
class RerankingService:
    def rerank(self, query: str, candidates: list[dict[str, object]], top_k: int) -> list[dict]:
        if not candidates:
            return []

        model = get_model()

        # Skip reranking and return original order if the model failed to load
        if model is None:
            return candidates[:top_k]

        pairs = [(query, build_doc(c)) for c in candidates]

        try:
            # Generate a relevance score for each query and document pair
            scores = model.predict(pairs)
        except Exception as e:
            log.warning("reranker inference failed, falling back to RRF order: %s", e)
            return candidates[:top_k]

        # Sort the candidates by the new relevance score in descending order
        ranked = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)
        out = []

        for score, candidate in ranked[:top_k]:
            result = dict(candidate)
            result["score"] = float(score)
            out.append(result)

        return out
