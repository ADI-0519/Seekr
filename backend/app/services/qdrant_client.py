import hashlib
import logging
import random

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

from app.core.config import get_settings

settings = get_settings()
log = logging.getLogger(__name__)


# Generate a deterministic hash for BM25 token indices to ensure consistency across pipeline stages
def token_index(token: str) -> int:
    return int(hashlib.sha1(token.encode()).hexdigest(), 16) % (2**20)


# Manage connections and operations for the Qdrant vector database
class QdrantService:
    def __init__(self, in_memory: bool = False):
        if in_memory:
            self.client = QdrantClient(":memory:")
        else:
            self.client = QdrantClient(url=settings.qdrant_url, timeout=5)
        self.collection = settings.qdrant_collection
        self.vector_size = settings.qdrant_vector_size

    # Initialize a standard vector collection if it does not already exist
    def create_collection(self):
        collections = self.client.get_collections().collections
        existing = {c.name for c in collections}

        if self.collection not in existing:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
            )

    # Initialize or recreate the collection to support hybrid dense and sparse vector storage
    def ensure_collection_with_sparse(self):
        collections = self.client.get_collections().collections
        existing = {c.name for c in collections}

        if self.collection in existing:
            info = self.client.get_collection(self.collection)
            sparse = info.config.params.sparse_vectors or {}
            if "bm25" not in sparse:
                log.warning("collection %s missing bm25 sparse config, recreating", self.collection)
                self.client.delete_collection(self.collection)
            else:
                return

        self.client.create_collection(
            collection_name=self.collection,
            vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
            sparse_vectors_config={"bm25": SparseVectorParams()},
        )

    # Batch upload text chunks alongside their dense and sparse vector embeddings
    def upsert_chunks(self, chunks: list[dict]) -> None:
        points = []
        for chunk in chunks:
            token_weights = chunk["sparse_vector"]

            # Aggregate weights for tokens that resolve to the same hash index
            merged: dict[int, float] = {}
            for token, weight in token_weights.items():
                idx = token_index(token)
                merged[idx] = merged.get(idx, 0.0) + float(weight)

            indices = list(merged.keys())
            values = list(merged.values())

            points.append(
                PointStruct(
                    id=chunk["id"],
                    vector={
                        "": chunk["vector"],
                        "bm25": SparseVector(indices=indices, values=values),
                    },
                    payload=chunk["payload"],
                )
            )

        batch_size = 100
        for i in range(0, len(points), batch_size):
            self.client.upsert(
                collection_name=self.collection,
                points=points[i : i + batch_size],
            )

    # Remove all embedded points associated with a specific video ID
    def delete_video_points(self, video_id: int) -> None:
        for value in (video_id, str(video_id)):
            filter = Filter(must=[FieldCondition(key="video_id", match=MatchValue(value=value))])
            self.client.delete(
                collection_name=self.collection,
                points_selector=filter,
                wait=True,
            )

    # Perform semantic similarity searches using dense vectors
    def search_chunks(
        self, video_id: int, query_vector: list[float], top_k: int = 10
    ) -> list[dict]:
        f = Filter(must=[FieldCondition(key="video_id", match=MatchValue(value=video_id))])

        response = self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            query_filter=f,
            limit=top_k,
        )

        results = []
        for point in response.points:
            p = point.payload or {}
            results.append(
                {
                    "id": point.id,
                    "score": point.score,
                    "text": p.get("text", ""),
                    "start_time": p.get("start_time", 0.0),
                    "end_time": p.get("end_time", 0.0),
                    "position_category": p.get("position_category", ""),
                    "slide_text": p.get("slide_text", ""),
                    "section_title": p.get("section_title", ""),
                }
            )

        return results

    # Perform exact keyword matches using BM25 sparse vectors
    def search_chunks_sparse(
        self, video_id: int, bm25_weights: dict[str, float], top_k: int = 10
    ) -> list[dict]:
        f = Filter(must=[FieldCondition(key="video_id", match=MatchValue(value=video_id))])

        merged: dict[int, float] = {}
        for token, weight in bm25_weights.items():
            idx = token_index(token)
            merged[idx] = merged.get(idx, 0.0) + float(weight)

        indices = list(merged.keys())
        values = list(merged.values())

        response = self.client.query_points(
            collection_name=self.collection,
            query=SparseVector(indices=indices, values=values),
            using="bm25",
            query_filter=f,
            limit=top_k,
        )

        results = []
        for point in response.points:
            p = point.payload or {}
            results.append(
                {
                    "id": point.id,
                    "score": point.score,
                    "text": p.get("text", ""),
                    "start_time": p.get("start_time", 0.0),
                    "end_time": p.get("end_time", 0.0),
                    "position_category": p.get("position_category", ""),
                    "slide_text": p.get("slide_text", ""),
                    "section_title": p.get("section_title", ""),
                }
            )

        return results

    # Inject randomized dummy vectors into the database for connectivity testing
    def upsert_test_points(self, video_id, n=2):
        points = []
        base = int(video_id) * 1_000_000

        for i in range(n):
            points.append(
                PointStruct(
                    id=base + i,
                    vector=[random.random() for _ in range(self.vector_size)],
                    payload={"video_id": int(video_id), "kind": "dummy", "index": i},
                )
            )

        self.client.upsert(collection_name=self.collection, points=points)

    # Execute a dummy similarity search for connectivity testing
    def search_vector(self, video_id, top_k=3):
        query_vector = [random.random() for _ in range(self.vector_size)]

        filter = Filter(must=[FieldCondition(key="video_id", match=MatchValue(value=video_id))])

        response = self.client.query_points(
            collection_name=self.collection,
            prefetch=None,
            query=query_vector,
            limit=top_k,
            query_filter=filter,
        )

        return response.points
