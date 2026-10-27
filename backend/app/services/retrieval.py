import logging
from concurrent.futures import ThreadPoolExecutor

from app.services.embedding import EmbeddingService
from app.services.qdrant_client import QdrantService
from app.services.reranker import RerankingService

log = logging.getLogger(__name__)

CANDIDATES = 50
RRF_TOP = 20  # Limit cross-encoder candidates to conserve processing time
embedder_singleton: EmbeddingService | None = None


def get_embedder() -> EmbeddingService:
    global embedder_singleton
    if embedder_singleton is None:
        embedder_singleton = EmbeddingService()
    return embedder_singleton


# Combine dense and sparse search results using Reciprocal Rank Fusion (RRF)
def rrf_fuse(dense: list[dict], sparse: list[dict], k: int = 60) -> list[dict]:
    scores: dict[int, float] = {}
    by_id = {}

    # Calculate reciprocal rank scores for dense results
    for rank, item in enumerate(dense):
        cid = item["id"]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
        by_id[cid] = item

    # Add reciprocal rank scores for sparse results
    for rank, item in enumerate(sparse):
        cid = item["id"]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
        if cid not in by_id:
            by_id[cid] = item

    out = []
    # Sort combined results by total RRF score in descending order
    for cid in sorted(scores, key=lambda x: scores[x], reverse=True):
        merged = dict(by_id[cid])
        merged["score"] = scores[cid]
        out.append(merged)

    return out


# Orchestrate hybrid search queries across dense, sparse, and reranking pipelines
class RetrievalService:
    def search(self, video_id: int, query: str, top_k: int = 5) -> list[dict]:
        if not query or not query.strip():
            return []

        # Generate dense vectors and sparse BM25 weights for the search query
        embedder = get_embedder()
        dense_vec = embedder.embed_texts([query])[0]
        bm25_weights = embedder.bm25_encode([query])[0]

        qdrant = QdrantService()

        # Execute dense and sparse searches concurrently to minimize latency
        with ThreadPoolExecutor(max_workers=2) as pool:
            dense_f = pool.submit(qdrant.search_chunks, video_id, dense_vec, CANDIDATES)
            sparse_f = pool.submit(qdrant.search_chunks_sparse, video_id, bm25_weights, CANDIDATES)

        dense_res = dense_f.result()
        sparse_res = sparse_f.result()

        if not dense_res and not sparse_res:
            return []

        # Merge parallel search results and apply cross-encoder reranking to the top candidates
        fused = rrf_fuse(dense_res, sparse_res)
        reranked = RerankingService().rerank(query, fused[:RRF_TOP], top_k)

        # Format final ranked results for the API response
        results = []
        for r in reranked[:top_k]:
            results.append(
                {
                    "text": r.get("text", ""),
                    "start_time": r.get("start_time", 0.0),
                    "end_time": r.get("end_time", 0.0),
                    "score": r.get("score", 0.0),
                    "segment_title": r.get("section_title") or None,
                }
            )

        return results
