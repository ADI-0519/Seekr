from __future__ import annotations

import logging
import random
import re
from datetime import datetime, timezone

from app.evaluation.ablation import DEFAULT_K_VALUES, AblationConfig, AblationResult
from app.evaluation.metrics.breakdown import metrics_by_query_type
from app.evaluation.metrics.segmentation import segmentation_f1
from app.evaluation.schemas import GroundTruthQuery, SegmentationGoldLabel
from app.services.chunking import ChunkingService
from app.services.embedding import EmbeddingService
from app.services.qdrant_client import QdrantService
from app.services.reranker import RerankingService

log = logging.getLogger(__name__)

# strips " [SLIDE: ...]" tags from the context template when OCR is disabled
_SLIDE_TAG_RE = re.compile(r" \[SLIDE:[^\]]*\]")

_SENTINEL_CHUNK_ID = -1
_CANDIDATES = 100
_RRF_TOP = 50


def _rrf_fuse(dense: list[dict], sparse: list[dict], k: int = 60) -> list[dict]:
    scores: dict[int, float] = {}
    by_id: dict[int, dict] = {}
    for rank, item in enumerate(dense):
        cid = int(item["id"])
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
        by_id[cid] = item
    for rank, item in enumerate(sparse):
        cid = int(item["id"])
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
        if cid not in by_id:
            by_id[cid] = item
    return [
        {**by_id[cid], "score": scores[cid]}
        for cid in sorted(scores, key=lambda x: scores[x], reverse=True)
    ]


def _resolve_chunk_ids(
    queries: list[GroundTruthQuery], chunks: list[dict], video_id: int
) -> list[GroundTruthQuery]:
    # sentinel means chunk ID wasn't known at annotation time; resolve it now
    resolved = []
    for q in queries:
        if q.relevant_chunk_ids != [_SENTINEL_CHUNK_ID]:
            resolved.append(q)
            continue
        matched = [
            video_id * 100_000 + i
            for i, chunk in enumerate(chunks)
            if any(
                chunk["start_time"] < end and chunk["end_time"] > start
                for start, end in q.relevant_time_ranges
            )
        ]
        ids = matched if matched else [_SENTINEL_CHUNK_ID]
        resolved.append(
            GroundTruthQuery.model_validate({**q.model_dump(), "relevant_chunk_ids": ids})
        )
    return resolved


class EvaluationRunner:
    def __init__(
        self,
        chunking_svc: ChunkingService,
        embed_svc: EmbeddingService,
        qdrant_svc: QdrantService,
        extra_embed_svcs: dict[str, EmbeddingService] | None = None,
    ) -> None:
        self._chunking = chunking_svc
        self._qdrant = qdrant_svc
        # "bge-m3" is default; fine-tuned variants are registered by name
        self._embed_svcs: dict[str, EmbeddingService] = {"bge-m3": embed_svc}
        if extra_embed_svcs:
            self._embed_svcs.update(extra_embed_svcs)

    def run_ablation(
        self,
        config: AblationConfig,
        queries: list[GroundTruthQuery],
        sentences: list[dict[str, object]],
        video_duration: float,
        video_title: str = "",
        slide_frames: list[dict[str, object]] | None = None,
        segments: list[dict[str, object]] | None = None,
        k_values: list[int] | None = None,
        seg_labels: list[SegmentationGoldLabel] | None = None,
        use_hyde: bool = False,
    ) -> AblationResult:
        resolved_k = k_values if k_values is not None else DEFAULT_K_VALUES

        random.seed(config.seed)

        # fall back to base model if requested one isn't registered
        embed = self._embed_svcs.get(config.embedding_model)
        if embed is None:
            log.warning(
                "no embedding service registered for model %r, falling back to bge-m3",
                config.embedding_model,
            )
            embed = self._embed_svcs["bge-m3"]

        chunks = self._chunking.create_chunks(
            sentences, video_duration, slide_frames, segments, video_title=video_title
        )

        for chunk in chunks:
            if not config.include_slide_text:
                chunk["slide_text"] = ""
                chunk["context_template"] = _SLIDE_TAG_RE.sub("", str(chunk["context_template"]))
            if not config.include_context_template:
                # no position/section context, but keep slide text if config asks for it
                slide = chunk.get("slide_text", "")
                if config.include_slide_text and slide:
                    chunk["context_template"] = f"[SLIDE: {slide}] {chunk['text']}"
                else:
                    chunk["context_template"] = chunk["text"]

        dense_vecs: list[list[float]] = embed.embed_texts(
            [str(c["context_template"]) for c in chunks]
        )
        sparse_vecs: list[dict[str, float]] = embed.bm25_encode([str(c["text"]) for c in chunks])

        video_id = queries[0].video_id if queries else 0

        # resolve any sentinel IDs now that chunks are built
        queries = _resolve_chunk_ids(queries, chunks, video_id)

        upsert_list: list[dict[str, object]] = []
        for i, (chunk, vec, sp) in enumerate(zip(chunks, dense_vecs, sparse_vecs)):
            upsert_list.append(
                {
                    "id": video_id * 100_000 + i,
                    "vector": vec,
                    "sparse_vector": sp,
                    "payload": {
                        "video_id": video_id,
                        "text": chunk["text"],
                        "start_time": chunk["start_time"],
                        "end_time": chunk["end_time"],
                        "position_category": chunk["position_category"],
                        "slide_text": chunk.get("slide_text", ""),
                        "section_title": chunk.get("section_title", ""),
                    },
                }
            )

        original_collection = self._qdrant.collection
        self._qdrant.collection = config.collection_name()
        try:
            self._qdrant.ensure_collection_with_sparse()  # type: ignore[no-untyped-call]
            self._qdrant.upsert_chunks(upsert_list)

            max_k = max(resolved_k)
            reranker = RerankingService()

            # lookup used by retrieval_fn closure to identify query type for HyDE
            _query_type_map = {q.query_id: q.query_type for q in queries}
            _query_id_map = {(q.query_text, q.video_id): q.query_id for q in queries}

            def retrieval_fn(query_text: str, vid: int) -> list[int]:
                embed_text = query_text
                if use_hyde:
                    qid = _query_id_map.get((query_text, vid), "")
                    if _query_type_map.get(qid) == "conceptual":
                        from app.evaluation.hyde import expand_query_with_hyde

                        embed_text = expand_query_with_hyde(query_text)
                query_vec = embed.embed_texts([embed_text])[0]
                bm25_weights = embed.bm25_encode([embed_text])[0]
                dense = self._qdrant.search_chunks(vid, query_vec, _CANDIDATES)
                sparse = self._qdrant.search_chunks_sparse(vid, bm25_weights, _CANDIDATES)
                fused = _rrf_fuse(dense, sparse)
                reranked = reranker.rerank(query_text, fused[:_RRF_TOP], max_k)
                return [int(r["id"]) for r in reranked]

            breakdown = metrics_by_query_type(queries, retrieval_fn, resolved_k)

        finally:
            self._qdrant.client.delete_collection(config.collection_name())
            self._qdrant.collection = original_collection

        overall = breakdown.get("_overall")
        retrieval_metrics: dict[str, float] = overall if overall is not None else {}

        seg_metrics: dict[str, float] = {}
        if seg_labels:
            label_by_vid = {sl.video_id: sl for sl in seg_labels}
            label = label_by_vid.get(video_id)
            if label:
                # segment start times are boundaries (t=0 is video start not topic change)
                if segments:
                    predicted = sorted(
                        float(seg["start_time"])  # type: ignore[arg-type]
                        for seg in segments
                        if float(seg["start_time"]) > 0.0  # type: ignore[arg-type]
                    )
                else:
                    predicted = []
                seg_metrics = segmentation_f1(
                    predicted, label.expected_boundaries, label.tolerance_secs
                )

        return AblationResult(
            config=config,
            retrieval_metrics=retrieval_metrics,
            segmentation_metrics=seg_metrics,
            query_type_breakdown=breakdown,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
