from __future__ import annotations

import pytest
from app.finetune.dataset import (
    ChunkMeta,
    StructureAwareNegativeSampler,
    TripletExample,
    _jaccard_words,
    _neg_too_similar,
    materialize_triplets_structured,
)


def make_corpus_and_metadata():
    corpus = [
        "gradient descent updates weights",  # 0: vid=1, section=optimization
        "learning rate controls step size",  # 1: vid=1, section=optimization
        "relu is an activation function",  # 2: vid=1, section=architectures
        "convolution applies learned filters",  # 3: vid=1, section=architectures
        "backprop computes gradients",  # 4: vid=1, section=optimization
        "trees store sorted data",  # 5: vid=2, section=data-structures
        "hash tables enable fast lookup",  # 6: vid=2, section=data-structures
        "graphs model relationships",  # 7: vid=2, section=graphs
        "bfs explores level by level",  # 8: vid=2, section=graphs
        "sorting arranges elements in order",  # 9: vid=3, section=sorting
    ]
    metadata = [
        ChunkMeta(video_id=1, section_title="optimization"),
        ChunkMeta(video_id=1, section_title="optimization"),
        ChunkMeta(video_id=1, section_title="architectures"),
        ChunkMeta(video_id=1, section_title="architectures"),
        ChunkMeta(video_id=1, section_title="optimization"),
        ChunkMeta(video_id=2, section_title="data-structures"),
        ChunkMeta(video_id=2, section_title="data-structures"),
        ChunkMeta(video_id=2, section_title="graphs"),
        ChunkMeta(video_id=2, section_title="graphs"),
        ChunkMeta(video_id=3, section_title="sorting"),
    ]
    return corpus, metadata


def test_hard_negative_comes_from_same_video_different_section():
    corpus, metadata = make_corpus_and_metadata()
    sampler = StructureAwareNegativeSampler(corpus, metadata, seed=42)

    vid1_architectures_indices = {2, 3}

    for _ in range(50):
        neg = sampler.sample_hard(
            "gradient descent updates weights", video_id=1, section_title="optimization"
        )
        assert neg is not None
        idx = corpus.index(neg)
        assert idx in vid1_architectures_indices


def test_medium_negative_comes_from_same_section():
    corpus, metadata = make_corpus_and_metadata()
    sampler = StructureAwareNegativeSampler(corpus, metadata, seed=42)

    for _ in range(50):
        neg = sampler.sample_medium(
            "gradient descent updates weights", video_id=1, section_title="optimization"
        )
        assert neg is not None
        idx = corpus.index(neg)
        assert metadata[idx].video_id == 1
        assert metadata[idx].section_title == "optimization"
        assert neg != "gradient descent updates weights"


def test_easy_negative_comes_from_different_video():
    corpus, metadata = make_corpus_and_metadata()
    sampler = StructureAwareNegativeSampler(corpus, metadata, seed=42)

    for _ in range(50):
        neg = sampler.sample_easy("gradient descent updates weights", video_id=1)
        assert neg is not None
        idx = corpus.index(neg)
        assert metadata[idx].video_id != 1


def test_hard_negative_returns_none_when_only_one_section():
    corpus = ["chunk a", "chunk b"]
    metadata = [
        ChunkMeta(video_id=1, section_title="only-section"),
        ChunkMeta(video_id=1, section_title="only-section"),
    ]
    sampler = StructureAwareNegativeSampler(corpus, metadata, seed=42)
    neg = sampler.sample_hard("chunk a", video_id=1, section_title="only-section")
    assert neg is None


def test_medium_negative_returns_none_when_section_has_one_chunk():
    corpus = ["chunk a", "chunk b"]
    metadata = [
        ChunkMeta(video_id=1, section_title="sec-a"),
        ChunkMeta(video_id=1, section_title="sec-b"),
    ]
    sampler = StructureAwareNegativeSampler(corpus, metadata, seed=42)
    neg = sampler.sample_medium("chunk a", video_id=1, section_title="sec-a")
    assert neg is None


def test_easy_negative_returns_none_when_single_video():
    corpus = ["chunk a", "chunk b"]
    metadata = [
        ChunkMeta(video_id=1, section_title="sec-a"),
        ChunkMeta(video_id=1, section_title="sec-b"),
    ]
    sampler = StructureAwareNegativeSampler(corpus, metadata, seed=42)
    neg = sampler.sample_easy("chunk a", video_id=1)
    assert neg is None


def test_sample_falls_through_tiers_gracefully():
    corpus = ["chunk a", "chunk b", "chunk c"]
    metadata = [
        ChunkMeta(video_id=1, section_title="sec"),
        ChunkMeta(video_id=1, section_title="sec"),
        ChunkMeta(video_id=1, section_title="sec"),
    ]
    sampler = StructureAwareNegativeSampler(corpus, metadata, seed=42)
    for _ in range(20):
        neg = sampler.sample("chunk a", video_id=1, section_title="sec")
        assert neg != "chunk a"
        assert neg in corpus


def test_sample_never_returns_positive():
    corpus, metadata = make_corpus_and_metadata()
    sampler = StructureAwareNegativeSampler(corpus, metadata, seed=0)
    for _ in range(200):
        neg = sampler.sample(
            "gradient descent updates weights", video_id=1, section_title="optimization"
        )
        assert neg != "gradient descent updates weights"


def test_sample_distribution_has_all_three_tiers():
    corpus, metadata = make_corpus_and_metadata()
    hard_count = 0
    medium_count = 0
    easy_count = 0

    for seed in range(500):
        sampler = StructureAwareNegativeSampler(corpus, metadata, seed=seed)
        neg = sampler.sample(
            "gradient descent updates weights", video_id=1, section_title="optimization"
        )
        idx = corpus.index(neg)
        meta = metadata[idx]

        if meta.video_id == 1 and meta.section_title != "optimization":
            hard_count += 1
        elif meta.video_id == 1 and meta.section_title == "optimization":
            medium_count += 1
        elif meta.video_id != 1:
            easy_count += 1

    assert hard_count > 50
    assert medium_count > 50
    assert easy_count > 50


def test_sampler_is_deterministic():
    corpus, metadata = make_corpus_and_metadata()
    s1 = StructureAwareNegativeSampler(corpus, metadata, seed=42)
    s2 = StructureAwareNegativeSampler(corpus, metadata, seed=42)

    results1 = [s1.sample("gradient descent updates weights", 1, "optimization") for _ in range(20)]
    results2 = [s2.sample("gradient descent updates weights", 1, "optimization") for _ in range(20)]
    assert results1 == results2


def test_materialize_triplets_structured_basic():
    corpus, corpus_metadata = make_corpus_and_metadata()
    examples = [
        TripletExample(
            query="what is gradient descent?", positive="gradient descent updates weights"
        ),
        TripletExample(query="what is relu?", positive="relu is an activation function"),
    ]
    metadata = [
        ChunkMeta(video_id=1, section_title="optimization"),
        ChunkMeta(video_id=1, section_title="architectures"),
    ]

    result = materialize_triplets_structured(
        examples, metadata, corpus=corpus, corpus_metadata=corpus_metadata, seed=42
    )

    assert len(result) == 2
    assert all(t.negative is not None for t in result)
    assert all(t.negative != t.positive for t in result)


def test_materialize_triplets_structured_mismatched_lengths_raises():
    corpus, corpus_metadata = make_corpus_and_metadata()
    examples = [TripletExample(query="q", positive="gradient descent updates weights")]
    metadata = []

    with pytest.raises(ValueError):
        materialize_triplets_structured(
            examples, metadata, corpus=corpus, corpus_metadata=corpus_metadata, seed=42
        )


def test_materialize_triplets_structured_preserves_existing_negatives():
    corpus, corpus_metadata = make_corpus_and_metadata()
    examples = [
        TripletExample(
            query="q", positive="gradient descent updates weights", negative="pre-assigned negative"
        ),
    ]
    metadata = [ChunkMeta(video_id=1, section_title="optimization")]

    result = materialize_triplets_structured(
        examples, metadata, corpus=corpus, corpus_metadata=corpus_metadata, seed=42
    )

    assert result[0].negative == "pre-assigned negative"


def test_jaccard_words_identical_strings():
    assert _jaccard_words("same text here", "same text here") == 1.0


def test_jaccard_words_no_overlap():
    assert _jaccard_words("alpha beta gamma", "delta epsilon zeta") == 0.0


def test_jaccard_words_partial_overlap():
    # intersection {b,c}=2, union=4, so 0.5
    result = _jaccard_words("a b c", "b c d")
    assert abs(result - 0.5) < 1e-9


def test_jaccard_words_empty_strings():
    assert _jaccard_words("", "") == 0.0


def test_neg_too_similar_returns_true_above_threshold():
    # identical texts have Jaccard=1.0, always above any sane threshold
    assert _neg_too_similar("gradient descent", "gradient descent", threshold=0.45) is True


def test_neg_too_similar_returns_false_below_threshold():
    # no shared words means Jaccard=0.0
    assert _neg_too_similar("neural networks", "sorting algorithms", threshold=0.45) is False


def test_neg_too_similar_exactly_at_threshold():
    # >= means exactly at threshold still counts as too similar; "a b c" vs "b c d" is 0.5
    assert _neg_too_similar("a b c", "b c d", threshold=0.5) is True
    assert _neg_too_similar("a b c", "b c d", threshold=0.51) is False


def test_similarity_filter_blocks_near_duplicate_hard_negative():
    # hard candidate shares 5 of 7 words with the positive (Jaccard ~0.71), so gets filtered
    corpus = [
        "neural network layers process input data",
        "neural network layers classify input data",
        "completely different topic about sorting",
    ]
    metadata = [
        ChunkMeta(video_id=1, section_title="sec-a"),
        ChunkMeta(video_id=1, section_title="sec-b"),
        ChunkMeta(video_id=2, section_title="sec-x"),
    ]
    sampler = StructureAwareNegativeSampler(corpus, metadata, seed=42, similarity_threshold=0.45)

    neg = sampler.sample_hard(corpus[0], video_id=1, section_title="sec-a")
    assert neg is None


def test_similarity_filter_passes_dissimilar_easy_negative():
    corpus = [
        "neural network layers process input data",
        "neural network layers classify input data",
        "completely different topic about sorting",
    ]
    metadata = [
        ChunkMeta(video_id=1, section_title="sec-a"),
        ChunkMeta(video_id=1, section_title="sec-b"),
        ChunkMeta(video_id=2, section_title="sec-x"),
    ]
    sampler = StructureAwareNegativeSampler(corpus, metadata, seed=42, similarity_threshold=0.45)

    neg = sampler.sample_easy(corpus[0], video_id=1)
    assert neg == "completely different topic about sorting"


def test_high_threshold_disables_filtering():
    # threshold=1.0 means only exact duplicates get blocked; corpus[1] not identical to corpus[0]
    corpus = [
        "neural network layers process input data",
        "neural network layers classify input data",
        "completely different topic about sorting",
    ]
    metadata = [
        ChunkMeta(video_id=1, section_title="sec-a"),
        ChunkMeta(video_id=1, section_title="sec-b"),
        ChunkMeta(video_id=2, section_title="sec-x"),
    ]
    sampler = StructureAwareNegativeSampler(corpus, metadata, seed=42, similarity_threshold=1.0)

    neg = sampler.sample_hard(corpus[0], video_id=1, section_title="sec-a")
    # with threshold=1.0 the similar candidate is no longer blocked
    assert neg == corpus[1]


def test_materialize_triplets_resamples_similar_prefilled_negative():
    # pre-filled negative shares ~0.71 Jaccard with positive, so gets resampled
    corpus = [
        "gradient descent updates the model weights",
        "gradient descent adjusts the model weights",
        "hash tables enable fast lookup operations",
    ]
    corpus_metadata = [
        ChunkMeta(video_id=1, section_title="optimization"),
        ChunkMeta(video_id=1, section_title="optimization"),
        ChunkMeta(video_id=2, section_title="data-structures"),
    ]
    examples = [
        TripletExample(
            query="when does gradient descent run?",
            positive="gradient descent updates the model weights",
            negative="gradient descent adjusts the model weights",
        )
    ]
    example_metadata = [ChunkMeta(video_id=1, section_title="optimization")]

    result = materialize_triplets_structured(
        examples,
        example_metadata,
        corpus=corpus,
        corpus_metadata=corpus_metadata,
        seed=42,
        similarity_threshold=0.45,
    )

    assert len(result) == 1
    assert result[0].negative != result[0].positive
    # the only dissimilar candidate available is corpus[2]
    assert result[0].negative == "hash tables enable fast lookup operations"


def test_materialize_triplets_stats_counts_resampled_negative():
    corpus = [
        "gradient descent updates the model weights",
        "gradient descent adjusts the model weights",
        "hash tables enable fast lookup operations",
    ]
    corpus_metadata = [
        ChunkMeta(video_id=1, section_title="optimization"),
        ChunkMeta(video_id=1, section_title="optimization"),
        ChunkMeta(video_id=2, section_title="data-structures"),
    ]
    examples = [
        TripletExample(
            query="q",
            positive="gradient descent updates the model weights",
            negative="gradient descent adjusts the model weights",
        )
    ]
    example_metadata = [ChunkMeta(video_id=1, section_title="optimization")]

    stats: dict[str, int] = {}
    materialize_triplets_structured(
        examples,
        example_metadata,
        corpus=corpus,
        corpus_metadata=corpus_metadata,
        seed=42,
        similarity_threshold=0.45,
        stats_out=stats,
    )

    # resampled negatives don't increment prefilled counter
    assert stats.get("prefilled", 0) == 0
