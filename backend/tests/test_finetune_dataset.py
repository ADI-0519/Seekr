from __future__ import annotations

import json

import pytest
from app.finetune.dataset import TripletExample, load_triplets_jsonl, materialize_triplets


def test_materialize_triplets_is_deterministic():
    corpus = ["a", "b", "c"]
    base = [TripletExample(query="q1", positive="a"), TripletExample(query="q2", positive="b")]

    a = materialize_triplets(base, corpus=corpus, seed=123)
    b = materialize_triplets(base, corpus=corpus, seed=123)
    assert a == b


def test_materialize_triplets_negatives_differ_from_positives():
    corpus = ["a", "b", "c"]
    base = [TripletExample(query="q1", positive="a"), TripletExample(query="q2", positive="b")]

    result = materialize_triplets(base, corpus=corpus, seed=0)
    assert all(t.negative is not None for t in result)
    assert all(t.negative != t.positive for t in result)


def test_materialize_triplets_requires_distinct_corpus():
    with pytest.raises(ValueError):
        materialize_triplets(
            [TripletExample(query="q", positive="x")],
            corpus=["x", "x"],
            seed=0,
        )


def test_load_triplets_jsonl(tmp_path):
    p = tmp_path / "triplets.jsonl"
    p.write_text(
        "\n".join(
            [
                json.dumps({"query": "q", "positive": "p", "negative": "n"}),
                json.dumps({"query": "q2", "positive": "p2"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    items = load_triplets_jsonl(p)
    assert items[0] == TripletExample(query="q", positive="p", negative="n")
    assert items[1] == TripletExample(query="q2", positive="p2", negative=None)


def test_load_triplets_jsonl_missing_positive_raises(tmp_path):
    p = tmp_path / "bad.jsonl"
    p.write_text(json.dumps({"query": "q"}) + "\n", encoding="utf-8")

    with pytest.raises(ValueError):
        load_triplets_jsonl(p)
