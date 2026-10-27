from __future__ import annotations

from typing import Literal, cast
from unittest.mock import MagicMock

import pytest
from app.evaluation.ablation import AblationConfig, get_standard_configs
from app.evaluation.runner import EvaluationRunner, _resolve_chunk_ids
from app.evaluation.schemas import GroundTruthQuery, SegmentationGoldLabel
from app.services.chunking import ChunkingService
from app.services.embedding import EmbeddingService
from app.services.qdrant_client import QdrantService

_QueryType = Literal["factual", "conceptual", "temporal", "slide-ref"]


def make_query(
    query_id: str,
    query_type: _QueryType = "factual",
    video_id: int = 1,
    relevant_chunk_ids: list[int] | None = None,
) -> GroundTruthQuery:
    return GroundTruthQuery(
        query_id=query_id,
        query_text=f"question for {query_id}",
        query_type=query_type,
        video_id=video_id,
        relevant_chunk_ids=relevant_chunk_ids if relevant_chunk_ids is not None else [100001],
        relevant_time_ranges=[(0.0, 30.0)],
    )


def make_sentences(count: int = 5, duration: float = 100.0) -> list[dict[str, object]]:
    step = duration / count
    return [
        {"text": f"sentence {i}", "start_time": i * step, "end_time": (i + 1) * step}
        for i in range(count)
    ]


def make_chunks(n: int = 2, slide_text: str = "Slide Content") -> list[dict[str, object]]:
    return [
        {
            "index": i,
            "text": f"chunk text {i}",
            "start_time": float(i * 30),
            "end_time": float((i + 1) * 30),
            "position_category": "beginning",
            "slide_text": slide_text,
            "section_title": "",
            # runner reads and rewrites context_template, so embed realistic content
            "context_template": (
                f"[LECTURE: test] [SECTION: ] [POSITION: beginning]"
                f" [SLIDE: {slide_text}] [SPEECH: chunk text {i}]"
            ),
        }
        for i in range(n)
    ]


def make_config(
    name: str = "test",
    include_slide_text: bool = False,
    include_context_template: bool = False,
    embedding_model: str = "bge-m3",
    seed: int = 42,
) -> AblationConfig:
    return AblationConfig(
        name=name,
        include_slide_text=include_slide_text,
        include_context_template=include_context_template,
        embedding_model=embedding_model,
        seed=seed,
    )


def mock_services(
    relevant_ids: list[int] | None = None,
    slide_text: str = "Slide Content",
) -> tuple[MagicMock, MagicMock, MagicMock]:
    ids = relevant_ids if relevant_ids is not None else [100001]

    mock_chunking = MagicMock()
    # return a fresh list each call so in-place mutations don't bleed between tests
    mock_chunking.create_chunks.side_effect = lambda *a, **kw: make_chunks(slide_text=slide_text)

    mock_embed = MagicMock()
    mock_embed.embed_texts.side_effect = lambda texts: [[0.1] * 1024 for _ in texts]
    mock_embed.bm25_encode.side_effect = lambda texts: [{"word": 1.0} for _ in texts]

    mock_qdrant = MagicMock()
    mock_qdrant.collection = "test_collection"
    mock_qdrant.search_chunks.return_value = [
        {
            "id": cid,
            "score": 0.9,
            "text": "",
            "start_time": 0.0,
            "end_time": 30.0,
            "position_category": "beginning",
            "slide_text": "",
            "section_title": "",
        }
        for cid in ids
    ]

    return mock_chunking, mock_embed, mock_qdrant


def make_runner(
    mock_chunking: MagicMock, mock_embed: MagicMock, mock_qdrant: MagicMock
) -> EvaluationRunner:
    return EvaluationRunner(
        cast(ChunkingService, mock_chunking),
        cast(EmbeddingService, mock_embed),
        cast(QdrantService, mock_qdrant),
    )


class TestAblationConfig:
    def test_collection_name_deterministic(self) -> None:
        cfg1 = make_config(name="baseline", seed=42)
        cfg2 = make_config(name="baseline", seed=42)
        assert cfg1.collection_name() == cfg2.collection_name()

    def test_collection_name_sanitised(self) -> None:
        cfg = make_config(name="+OCR+Context", seed=42)
        name = cfg.collection_name()
        # only alphanumeric and underscores are safe for Qdrant
        assert all(c.isalnum() or c == "_" for c in name)

    def test_to_dict_round_trip(self) -> None:
        cfg = make_config(name="baseline", include_slide_text=True, seed=7)
        d = cfg.to_dict()
        assert d["name"] == "baseline"
        assert d["include_slide_text"] is True
        assert d["seed"] == 7
        assert "include_context_template" in d
        assert "embedding_model" in d

    def test_get_standard_configs(self) -> None:
        configs = get_standard_configs()
        assert len(configs) == 5
        names = [c.name for c in configs]
        assert names == ["baseline", "+OCR", "+Context", "+OCR+Context", "+OCR+Context+Training"]

    def test_finetuned_config_uses_different_model(self) -> None:
        configs = get_standard_configs()
        finetuned = next(c for c in configs if c.name == "+OCR+Context+Training")
        assert finetuned.embedding_model == "bge-m3-finetuned"
        # fine-tuned config should have both modalities enabled
        assert finetuned.include_slide_text is True
        assert finetuned.include_context_template is True


class TestRunnerSlideTextAblation:
    def test_slide_text_stripped_when_disabled(self) -> None:
        mock_chunking, mock_embed, mock_qdrant = mock_services(slide_text="Gradient Descent")
        runner = make_runner(mock_chunking, mock_embed, mock_qdrant)
        queries = [make_query("q1", relevant_chunk_ids=[100001])]

        config = make_config(include_slide_text=False, include_context_template=True)
        runner.run_ablation(config, queries, make_sentences(), video_duration=100.0)

        # first call to embed_texts is the chunk embedding pass
        chunk_texts: list[str] = mock_embed.embed_texts.call_args_list[0].args[0]
        for text in chunk_texts:
            assert "Gradient Descent" not in text

        # upsert payload must have slide_text=""
        upsert_payload = mock_qdrant.upsert_chunks.call_args.args[0]
        for item in upsert_payload:
            assert item["payload"]["slide_text"] == ""

    def test_slide_text_preserved_when_enabled(self) -> None:
        mock_chunking, mock_embed, mock_qdrant = mock_services(slide_text="Backpropagation")
        runner = make_runner(mock_chunking, mock_embed, mock_qdrant)
        queries = [make_query("q1", relevant_chunk_ids=[100001])]

        config = make_config(include_slide_text=True, include_context_template=True)
        runner.run_ablation(config, queries, make_sentences(), video_duration=100.0)

        chunk_texts: list[str] = mock_embed.embed_texts.call_args_list[0].args[0]
        assert any("Backpropagation" in t for t in chunk_texts)


class TestRunnerContextAblation:
    def test_context_stripped_when_disabled(self) -> None:
        mock_chunking, mock_embed, mock_qdrant = mock_services()
        runner = make_runner(mock_chunking, mock_embed, mock_qdrant)
        queries = [make_query("q1", relevant_chunk_ids=[100001])]

        config = make_config(include_slide_text=False, include_context_template=False)
        runner.run_ablation(config, queries, make_sentences(), video_duration=100.0)

        chunk_texts: list[str] = mock_embed.embed_texts.call_args_list[0].args[0]
        # when context is disabled, texts should be raw speech, not the [LECTURE:...] prefix
        for text in chunk_texts:
            assert not text.startswith("[LECTURE:")

    def test_context_preserved_when_enabled(self) -> None:
        mock_chunking, mock_embed, mock_qdrant = mock_services()
        runner = make_runner(mock_chunking, mock_embed, mock_qdrant)
        queries = [make_query("q1", relevant_chunk_ids=[100001])]

        config = make_config(include_slide_text=True, include_context_template=True)
        runner.run_ablation(config, queries, make_sentences(), video_duration=100.0)

        chunk_texts: list[str] = mock_embed.embed_texts.call_args_list[0].args[0]
        assert all(text.startswith("[LECTURE:") for text in chunk_texts)

    def test_video_title_passed_to_chunking_service(self) -> None:
        mock_chunking, mock_embed, mock_qdrant = mock_services()
        runner = make_runner(mock_chunking, mock_embed, mock_qdrant)
        queries = [make_query("q1", relevant_chunk_ids=[100001])]

        config = make_config(include_slide_text=False, include_context_template=True)
        runner.run_ablation(
            config,
            queries,
            make_sentences(),
            video_duration=100.0,
            video_title="Deep Learning 101",
        )

        call_kwargs = mock_chunking.create_chunks.call_args
        assert call_kwargs.kwargs.get("video_title") == "Deep Learning 101"


class TestRunnerReproducibility:
    def test_same_seed_same_results(self) -> None:
        config = make_config(seed=42)
        queries = [make_query("q1", relevant_chunk_ids=[100001])]
        sentences = make_sentences()

        mock_chunking, mock_embed, mock_qdrant = mock_services()
        runner = make_runner(mock_chunking, mock_embed, mock_qdrant)
        r1 = runner.run_ablation(config, queries, sentences, video_duration=100.0)

        mock_chunking2, mock_embed2, mock_qdrant2 = mock_services()
        runner2 = make_runner(mock_chunking2, mock_embed2, mock_qdrant2)
        r2 = runner2.run_ablation(config, queries, sentences, video_duration=100.0)

        assert r1.retrieval_metrics == r2.retrieval_metrics

    def test_different_seed_noted_in_config(self) -> None:
        cfg_a = make_config(name="test", seed=1)
        cfg_b = make_config(name="test", seed=2)
        assert cfg_a.collection_name() != cfg_b.collection_name()


class TestRunnerCleanup:
    def test_temp_collection_deleted_on_success(self) -> None:
        mock_chunking, mock_embed, mock_qdrant = mock_services()
        runner = make_runner(mock_chunking, mock_embed, mock_qdrant)
        queries = [make_query("q1", relevant_chunk_ids=[100001])]
        config = make_config(name="cleanup_test")

        runner.run_ablation(config, queries, make_sentences(), video_duration=100.0)

        expected_name = config.collection_name()
        mock_qdrant.client.delete_collection.assert_called_once_with(expected_name)
        # collection attribute restored to original value after the run
        assert mock_qdrant.collection == "test_collection"

    def test_temp_collection_deleted_on_failure(self) -> None:
        mock_chunking, mock_embed, mock_qdrant = mock_services()

        # succeed on the first call (chunk embedding) but fail on query embedding
        _calls: list[int] = [0]

        def side(texts: list[str]) -> list[list[float]]:
            _calls[0] += 1
            if _calls[0] == 1:
                return [[0.1] * 1024 for _ in texts]
            raise RuntimeError("simulated embed failure")

        mock_embed.embed_texts.side_effect = side

        runner = make_runner(mock_chunking, mock_embed, mock_qdrant)
        queries = [make_query("q1", relevant_chunk_ids=[100001])]
        config = make_config(name="failure_test")

        with pytest.raises(RuntimeError, match="simulated embed failure"):
            runner.run_ablation(config, queries, make_sentences(), video_duration=100.0)

        mock_qdrant.client.delete_collection.assert_called_once_with(config.collection_name())
        assert mock_qdrant.collection == "test_collection"


class TestResolveChunkIds:
    def test_sentinel_replaced_by_overlapping_chunk(self) -> None:
        chunks = [{"start_time": 0.0, "end_time": 30.0}, {"start_time": 30.0, "end_time": 60.0}]
        q = GroundTruthQuery(
            query_id="q1",
            query_text="test",
            query_type="factual",
            video_id=1,
            relevant_chunk_ids=[-1],
            relevant_time_ranges=[(5.0, 25.0)],
        )
        resolved = _resolve_chunk_ids([q], chunks, video_id=1)
        assert resolved[0].relevant_chunk_ids == [1 * 100_000 + 0]

    def test_multiple_overlapping_chunks_all_matched(self) -> None:
        chunks = [{"start_time": 0.0, "end_time": 30.0}, {"start_time": 20.0, "end_time": 50.0}]
        q = GroundTruthQuery(
            query_id="q1",
            query_text="test",
            query_type="factual",
            video_id=1,
            relevant_chunk_ids=[-1],
            relevant_time_ranges=[(10.0, 40.0)],
        )
        resolved = _resolve_chunk_ids([q], chunks, video_id=1)
        assert set(resolved[0].relevant_chunk_ids) == {1 * 100_000, 1 * 100_000 + 1}

    def test_no_overlap_keeps_sentinel(self) -> None:
        chunks = [{"start_time": 0.0, "end_time": 30.0}]
        q = GroundTruthQuery(
            query_id="q1",
            query_text="test",
            query_type="factual",
            video_id=1,
            relevant_chunk_ids=[-1],
            relevant_time_ranges=[(500.0, 600.0)],
        )
        resolved = _resolve_chunk_ids([q], chunks, video_id=1)
        assert resolved[0].relevant_chunk_ids == [-1]

    def test_non_sentinel_and_empty_pass_through(self) -> None:
        chunks = [{"start_time": 0.0, "end_time": 30.0}]
        # already-resolved query should be unchanged
        q = make_query("q1", relevant_chunk_ids=[999])
        assert _resolve_chunk_ids([q], chunks, video_id=1)[0].relevant_chunk_ids == [999]
        # empty list is a no-op
        assert _resolve_chunk_ids([], chunks, video_id=1) == []


class TestRunnerSegmentationMetrics:
    def test_seg_metrics_computed_when_label_provided(self) -> None:
        mock_chunking, mock_embed, mock_qdrant = mock_services()
        runner = make_runner(mock_chunking, mock_embed, mock_qdrant)
        queries = [make_query("q1", relevant_chunk_ids=[100001])]

        label = SegmentationGoldLabel(video_id=1, expected_boundaries=[30.0], tolerance_secs=15.0)
        result = runner.run_ablation(
            make_config(),
            queries,
            make_sentences(),
            video_duration=100.0,
            seg_labels=[label],
        )
        assert "f1" in result.segmentation_metrics
        assert "precision" in result.segmentation_metrics
        assert "recall" in result.segmentation_metrics

    def test_seg_metrics_uses_segment_boundaries_not_chunk_starts(self) -> None:
        mock_chunking, mock_embed, mock_qdrant = mock_services()
        runner = make_runner(mock_chunking, mock_embed, mock_qdrant)
        queries = [make_query("q1", relevant_chunk_ids=[100001])]

        # gold boundary at 40s
        segments = [
            {"title": "Intro", "start_time": 0.0, "end_time": 40.0},
            {"title": "Main", "start_time": 40.0, "end_time": 100.0},
        ]
        label = SegmentationGoldLabel(video_id=1, expected_boundaries=[40.0], tolerance_secs=15.0)
        result = runner.run_ablation(
            make_config(),
            queries,
            make_sentences(),
            video_duration=100.0,
            segments=segments,
            seg_labels=[label],
        )
        # predicted = [40.0], gold = [40.0] -> perfect match
        assert result.segmentation_metrics["f1"] == pytest.approx(1.0)
        assert result.segmentation_metrics["precision"] == pytest.approx(1.0)
        assert result.segmentation_metrics["recall"] == pytest.approx(1.0)

    def test_seg_metrics_empty_without_matching_label(self) -> None:
        mock_chunking, mock_embed, mock_qdrant = mock_services()
        runner = make_runner(mock_chunking, mock_embed, mock_qdrant)
        queries = [make_query("q1", video_id=1, relevant_chunk_ids=[100001])]

        # no labels at all
        result = runner.run_ablation(
            make_config(),
            queries,
            make_sentences(),
            video_duration=100.0,
        )
        assert result.segmentation_metrics == {}

        # label exists but for different video
        label = SegmentationGoldLabel(video_id=99, expected_boundaries=[30.0], tolerance_secs=15.0)
        result = runner.run_ablation(
            make_config(),
            queries,
            make_sentences(),
            video_duration=100.0,
            seg_labels=[label],
        )
        assert result.segmentation_metrics == {}


class TestRunnerModelSelection:
    def test_falls_back_to_base_when_finetuned_not_registered(self) -> None:
        mock_chunking, mock_embed, mock_qdrant = mock_services()
        runner = make_runner(mock_chunking, mock_embed, mock_qdrant)
        queries = [make_query("q1", relevant_chunk_ids=[100001])]

        config = make_config(name="ft-test", embedding_model="bge-m3-finetuned")
        result = runner.run_ablation(config, queries, make_sentences(), video_duration=100.0)
        assert result.config.name == "ft-test"
        mock_embed.embed_texts.assert_called()

    def test_finetuned_service_used_when_registered(self) -> None:
        mock_chunking, mock_embed, mock_qdrant = mock_services()

        mock_finetuned = MagicMock()
        mock_finetuned.embed_texts.side_effect = lambda texts: [[0.9] * 1024 for _ in texts]
        mock_finetuned.bm25_encode.side_effect = lambda texts: [{"word": 1.0} for _ in texts]

        runner = EvaluationRunner(
            cast(ChunkingService, mock_chunking),
            cast(EmbeddingService, mock_embed),
            cast(QdrantService, mock_qdrant),
            extra_embed_svcs={"bge-m3-finetuned": cast(EmbeddingService, mock_finetuned)},
        )
        queries = [make_query("q1", relevant_chunk_ids=[100001])]
        config = make_config(name="ft-test", embedding_model="bge-m3-finetuned")

        runner.run_ablation(config, queries, make_sentences(), video_duration=100.0)

        mock_finetuned.embed_texts.assert_called()
        mock_finetuned.bm25_encode.assert_called()
        mock_embed.embed_texts.assert_not_called()
        mock_embed.bm25_encode.assert_not_called()
