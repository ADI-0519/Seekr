from __future__ import annotations

import pytest
from app.finetune.eval import evaluate_retrieval


def test_evaluate_retrieval_metrics():
    # 3 docs in 2D space.
    docs = [
        [1.0, 0.0],  # doc0
        [0.0, 1.0],  # doc1
        [0.7, 0.7],  # doc2
    ]

    # q0 best matches doc0; q1 best matches doc1.
    queries = [
        [2.0, 0.1],
        [0.1, 2.0],
    ]
    pos = [0, 1]

    m = evaluate_retrieval(query_embeddings=queries, doc_embeddings=docs, positive_doc_indices=pos)
    assert m.hit_at_1 == 1.0
    assert m.hit_at_5 == 1.0
    assert m.hit_at_10 == 1.0
    assert m.mrr == 1.0


def test_evaluate_retrieval_validates_inputs():
    with pytest.raises(ValueError):
        evaluate_retrieval(query_embeddings=[], doc_embeddings=[[1.0]], positive_doc_indices=[])

    with pytest.raises(ValueError):
        evaluate_retrieval(
            query_embeddings=[[1.0]], doc_embeddings=[[1.0]], positive_doc_indices=[]
        )
