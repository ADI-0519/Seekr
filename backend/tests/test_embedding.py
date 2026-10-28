from unittest.mock import MagicMock, patch

import pytest
from app.services.embedding import EmbeddingService


@pytest.fixture
def embed_svc():
    # inject a mock so tests don't try loading BGE-M3 from disk
    svc = EmbeddingService()
    mock_model = MagicMock()
    svc._model = mock_model
    svc._use_st = False
    return svc, mock_model


@pytest.fixture
def sparse_svc():
    svc = EmbeddingService()
    model = MagicMock()
    svc._sparse_model = model
    return svc, model


def test_embed_texts_returns_correct_dims(embed_svc):
    svc, mock_model = embed_svc
    mock_model.encode.return_value = {"dense_vecs": [[0.1] * 1024, [0.2] * 1024]}

    result = svc.embed_texts(["text a", "text b"])

    assert len(result) == 2
    assert len(result[0]) == 1024


def test_embed_texts_empty_input():
    svc = EmbeddingService()
    assert svc.embed_texts([]) == []


def test_embed_texts_batching(embed_svc):
    svc, mock_model = embed_svc

    def side_effect(texts, **kwargs):
        return {"dense_vecs": [[0.1] * 1024] * len(texts)}

    mock_model.encode.side_effect = side_effect
    svc.embed_texts([f"text {i}" for i in range(70)])

    # 70 texts at batch_size=32: 32 + 32 + 6 = 3 calls
    assert mock_model.encode.call_count == 3


def sparse_embedding(values):
    embedding = MagicMock()
    embedding.as_dict.return_value = values
    return embedding


def test_bm25_encode_basic(sparse_svc):
    svc, model = sparse_svc
    model.embed.return_value = iter(
        [sparse_embedding({101: 1.2, 202: 0.8}), sparse_embedding({303: 1.1})]
    )
    results = svc.bm25_encode(
        [
            "gradient descent optimises the loss",
            "learning rate controls step size",
        ]
    )

    assert len(results) == 2
    assert isinstance(results[0], dict)
    assert results[0] == {101: 1.2, 202: 0.8}
    assert results[1] == {303: 1.1}
    model.embed.assert_called_once()


def test_bm25_encode_empty_input():
    svc = EmbeddingService()
    assert svc.bm25_encode([]) == []


def test_bm25_encode_weights_positive(sparse_svc):
    svc, model = sparse_svc
    model.embed.return_value = iter([sparse_embedding({101: 1.2}), sparse_embedding({202: 0.7})])
    results = svc.bm25_encode(
        [
            "neural networks learn representations from data",
            "backpropagation computes gradients efficiently",
        ]
    )

    for doc in results:
        for val in doc.values():
            assert val > 0


def test_bm25_encode_single_doc(sparse_svc):
    svc, model = sparse_svc
    model.embed.return_value = iter([sparse_embedding({101: 1.0})])
    results = svc.bm25_encode(["neural networks are great"])
    assert len(results) == 1
    assert results[0] == {101: 1.0}


def test_bm25_uses_same_model_across_calls(sparse_svc):
    svc, model = sparse_svc
    model.embed.side_effect = [
        iter([sparse_embedding({101: 1.0})]),
        iter([sparse_embedding({101: 0.5})]),
    ]

    document = svc.bm25_encode(["backpropagation lecture"])[0]
    query = svc.bm25_encode(["backpropagation"])[0]

    assert set(document) & set(query) == {101}
    assert model.embed.call_count == 2


def test_embedding_import_error_graceful():
    # even without GPU dep installed init should always work
    svc = EmbeddingService()
    assert svc._model is None

    # simulating FlagEmbedding not available should raise clearly
    with patch("app.services.embedding._flag_ok", False):
        svc._use_st = False  # ensure we hit the FlagEmbedding branch
        with pytest.raises((RuntimeError, ImportError)):
            svc.embed_texts(["some text"])
