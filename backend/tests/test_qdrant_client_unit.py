from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.qdrant_client import QdrantService, to_sparse_vector
from qdrant_client.models import Modifier


def make_service(client: MagicMock) -> QdrantService:
    with patch("app.services.qdrant_client.QdrantClient", return_value=client):
        return QdrantService()


def test_to_sparse_vector_preserves_fastembed_indices_and_values():
    vector = to_sparse_vector({101: 1.25, 202: 0.75})

    assert vector.indices == [101, 202]
    assert vector.values == [1.25, 0.75]


def test_new_collection_enables_qdrant_idf():
    client = MagicMock()
    client.get_collections.return_value.collections = []
    service = make_service(client)

    service.ensure_collection_with_sparse()

    config = client.create_collection.call_args.kwargs["sparse_vectors_config"]["bm25"]
    assert config.modifier == Modifier.IDF


def test_incompatible_collection_is_recreated_with_idf():
    client = MagicMock()
    client.get_collections.return_value.collections = [SimpleNamespace(name="lecture_chunks")]
    client.get_collection.return_value.config.params.sparse_vectors = {
        "bm25": SimpleNamespace(modifier=None)
    }
    service = make_service(client)

    service.ensure_collection_with_sparse()

    client.delete_collection.assert_called_once_with("lecture_chunks")
    config = client.create_collection.call_args.kwargs["sparse_vectors_config"]["bm25"]
    assert config.modifier == Modifier.IDF


def test_compatible_collection_is_left_untouched():
    client = MagicMock()
    client.get_collections.return_value.collections = [SimpleNamespace(name="lecture_chunks")]
    client.get_collection.return_value.config.params.sparse_vectors = {
        "bm25": SimpleNamespace(modifier=Modifier.IDF)
    }
    service = make_service(client)

    service.ensure_collection_with_sparse()

    client.delete_collection.assert_not_called()
    client.create_collection.assert_not_called()
