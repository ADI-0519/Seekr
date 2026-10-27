from __future__ import annotations

import hashlib
import json
import random
import types
from pathlib import Path
from unittest.mock import patch

import pytest
import torch
from app.finetune.dataset import TripletExample

sentence_transformers = pytest.importorskip("sentence_transformers")
train_module = pytest.importorskip("app.finetune.train")

_diversify_batches = train_module._diversify_batches
_lecture_key = train_module._lecture_key
check_metrics = train_module.check_metrics
run_training = train_module.run_training


InputExample = sentence_transformers.InputExample

pytestmark = pytest.mark.integration


class _TinyModel(torch.nn.Module):
    # minimal SentenceTransformer-compatible model for tests
    def __init__(self, dim=8):
        super().__init__()
        self.linear = torch.nn.Linear(4, dim)

    def tokenize(self, texts):
        # hash each text to reproducible float vector
        ids = []
        for t in texts:
            h = int(hashlib.md5(t.encode()).hexdigest(), 16) % 1000
            ids.append([float(h)] * 4)
        return {
            "input_ids": torch.tensor(ids),
            "attention_mask": torch.ones(len(texts), 4),
        }

    def forward(self, features):
        x = features["input_ids"].to(self.linear.weight.dtype)
        return {"sentence_embedding": self.linear(x)}

    def encode(self, texts, batch_size=32, convert_to_numpy=False):
        self.eval()
        device = next(self.parameters()).device
        with torch.no_grad():
            feats = self.tokenize(texts)
            feats = {k: v.to(device) for k, v in feats.items()}
            out = self.forward(feats)["sentence_embedding"]
        if convert_to_numpy:
            return out.float().cpu().numpy()
        return out

    def save(self, path):
        Path(path).mkdir(parents=True, exist_ok=True)
        torch.save(self.state_dict(), Path(path) / "model.pt")


def make_examples(n=6):
    triplets = [
        TripletExample(query=f"query {i}", positive=f"positive {i}", negative=f"negative {i}")
        for i in range(n)
    ]
    return [InputExample(texts=[t.query, t.positive, t.negative]) for t in triplets]


def test_training_creates_output_files(tmp_path):
    examples = make_examples(6)

    torch.manual_seed(0)
    model = _TinyModel(dim=8)

    run_training(examples, examples[:2], model, tmp_path, epochs=1, batch_size=2, seed=42)

    assert (tmp_path / "final").exists()
    assert (tmp_path / "final" / "model.pt").exists()
    # best checkpoint always gets saved since recall starts at -1.0
    assert (tmp_path / "best").exists()


def test_training_returns_epoch_losses(tmp_path):
    examples = make_examples(6)

    torch.manual_seed(0)
    model = _TinyModel(dim=8)

    result = run_training(examples, examples[:2], model, tmp_path, epochs=2, batch_size=2, seed=42)

    assert len(result["epoch_losses"]) == 2
    assert all(isinstance(v, float) for v in result["epoch_losses"])
    assert "best_hit" in result


def test_training_is_deterministic(tmp_path):
    examples = make_examples(8)
    check = examples[:2]

    torch.manual_seed(0)
    model_a = _TinyModel(dim=8)
    model_b = _TinyModel(dim=8)
    model_b.load_state_dict(model_a.state_dict())

    result_a = run_training(
        examples, check, model_a, tmp_path / "a", epochs=2, batch_size=2, seed=42
    )
    result_b = run_training(
        examples, check, model_b, tmp_path / "b", epochs=2, batch_size=2, seed=42
    )

    assert result_a["epoch_losses"] == result_b["epoch_losses"]


def test_config_is_saved(tmp_path):
    from app.finetune.train import main

    train_path = tmp_path / "train.jsonl"
    check_path = tmp_path / "check.jsonl"
    out_dir = tmp_path / "out"

    for p in (train_path, check_path):
        p.write_text(
            "\n".join(
                json.dumps({"query": f"q{i}", "positive": f"p{i}", "negative": f"n{i}"})
                for i in range(4)
            ),
            encoding="utf-8",
        )

    torch.manual_seed(0)
    tiny = _TinyModel(dim=8)

    with patch("app.finetune.train._CLEARML_OK", False):
        with patch("app.finetune.train.SentenceTransformer", return_value=tiny):
            main(
                [
                    "--train-data",
                    str(train_path),
                    "--check-data",
                    str(check_path),
                    "--output-dir",
                    str(out_dir),
                    "--epochs",
                    "1",
                    "--batch-size",
                    "2",
                    "--seed",
                    "7",
                ]
            )

    config = json.loads((out_dir / "training_config.json").read_text())
    assert config["seed"] == 7
    assert config["epochs"] == 1
    assert config["batch_size"] == 2
    assert config["train_count"] == 4
    assert config["check_count"] == 4
    assert "base_model" in config
    assert config["similarity_threshold"] == 0.45


def test_config_saved_before_training_starts(tmp_path):
    # config written before run_training is called
    from app.finetune.train import main

    train_path = tmp_path / "train.jsonl"
    check_path = tmp_path / "check.jsonl"
    out_dir = tmp_path / "out"

    for p in (train_path, check_path):
        p.write_text(
            json.dumps({"query": "q", "positive": "p", "negative": "n"}) + "\n",
            encoding="utf-8",
        )

    torch.manual_seed(0)
    tiny = _TinyModel(dim=8)

    with patch("app.finetune.train._CLEARML_OK", False):
        with patch("app.finetune.train.SentenceTransformer", return_value=tiny):
            with patch("app.finetune.train.run_training", side_effect=RuntimeError("boom")):
                try:
                    main(
                        [
                            "--train-data",
                            str(train_path),
                            "--check-data",
                            str(check_path),
                            "--output-dir",
                            str(out_dir),
                            "--epochs",
                            "1",
                            "--batch-size",
                            "2",
                            "--seed",
                            "42",
                        ]
                    )
                except RuntimeError:
                    pass

    assert (out_dir / "training_config.json").exists()


def test_check_metrics_deduplicates_shared_positives():
    # 6 examples sharing 3 positives (2 query types each) -> eval handles deduplication cleanly
    torch.manual_seed(0)
    model = _TinyModel(dim=8)
    device = "cpu"

    chunks = [f"chunk_positive_{i}" for i in range(3)]
    examples = [
        InputExample(texts=[f"{qt} query about {pos}", pos, "irrelevant negative"])
        for pos in chunks
        for qt in ["content", "position"]
    ]

    m = check_metrics(model, examples, device)
    assert 0.0 <= m.hit_at_1 <= 1.0
    assert 0.0 <= m.hit_at_5 <= 1.0
    assert 0.0 <= m.mrr <= 1.0


def test_check_metrics_returns_zero_metrics_when_no_positives_in_corpus():
    # if positives not in supplied full_corpus_texts, skip eval, return zeros
    torch.manual_seed(0)
    model = _TinyModel(dim=8)
    device = "cpu"

    examples = [InputExample(texts=["query", "positive_not_in_corpus", "neg"])]
    m = check_metrics(model, examples, device, full_corpus_texts=["unrelated_a", "unrelated_b"])
    assert m.hit_at_1 == 0.0
    assert m.mrr == 0.0


def test_check_metrics_with_full_corpus_returns_valid_metrics():
    torch.manual_seed(0)
    model = _TinyModel(dim=8)
    device = "cpu"

    positives = ["chunk_a", "chunk_b", "chunk_c"]
    examples = [InputExample(texts=[f"query about {p}", p, "neg"]) for p in positives]
    full_corpus = positives + [f"distractor_{i}" for i in range(10)]

    m = check_metrics(model, examples, device, full_corpus_texts=full_corpus)
    assert 0.0 <= m.hit_at_1 <= 1.0
    assert 0.0 <= m.hit_at_5 <= 1.0
    assert 0.0 <= m.mrr <= 1.0


def _fake_ex(lecture: str, idx: int) -> types.SimpleNamespace:
    # duck-typed stand-in for InputExample; _diversify_batches only reads .texts[1]
    o = types.SimpleNamespace()
    o.texts = ["query", f"[LECTURE: {lecture}] positive text {idx}", "neg"]
    return o


def test_lecture_key_extracts_lecture_name():
    assert _lecture_key("[LECTURE: Introduction to ML] some speech text") == "Introduction to ML"


def test_lecture_key_returns_empty_string_when_no_tag():
    assert _lecture_key("plain text without lecture tag") == ""


def test_diversify_batches_preserves_all_examples():
    examples = [_fake_ex("L1", 0), _fake_ex("L1", 1), _fake_ex("L2", 2), _fake_ex("L2", 3)]
    rng = random.Random(42)
    result = _diversify_batches(examples, batch_size=2, rng=rng)

    assert len(result) == len(examples)
    result_ids = {e.texts[1] for e in result}
    orig_ids = {e.texts[1] for e in examples}
    assert result_ids == orig_ids


def test_diversify_batches_interleaves_lectures():
    # round-robin should produce alternating keys
    examples = [_fake_ex("L1", 0), _fake_ex("L1", 1), _fake_ex("L2", 2), _fake_ex("L2", 3)]
    rng = random.Random(0)
    result = _diversify_batches(examples, batch_size=2, rng=rng)

    keys = [_lecture_key(e.texts[1]) for e in result]
    consecutive_same = sum(1 for i in range(len(keys) - 1) if keys[i] == keys[i + 1])
    assert consecutive_same == 0


def test_diversify_batches_single_lecture_still_returns_all():
    # only one lecture group -> interleave degenerates to plain shuffle, all examples kept
    examples = [_fake_ex("L1", i) for i in range(4)]
    rng = random.Random(7)
    result = _diversify_batches(examples, batch_size=2, rng=rng)
    assert len(result) == 4


def test_diversify_batches_is_deterministic():
    examples = [_fake_ex("L1", 0), _fake_ex("L2", 1), _fake_ex("L1", 2), _fake_ex("L2", 3)]
    r1 = _diversify_batches(examples, batch_size=2, rng=random.Random(99))
    r2 = _diversify_batches(examples, batch_size=2, rng=random.Random(99))
    assert [e.texts[1] for e in r1] == [e.texts[1] for e in r2]
