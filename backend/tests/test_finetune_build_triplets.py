from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from app.finetune.build_triplets import build_triplets_from_chunks


def write_chunks(path: Path, chunks: list[dict]):
    with path.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c) + "\n")


def fake_generate(chunk, client):
    # deterministic stub, returns one content query per chunk
    return [("content", f"what does the lecture say about {chunk.text[:15]}?")]


def make_chunks(n: int = 10):
    # two video ids so split has something to work with
    return [
        {
            "chunk_id": i,
            "video_id": 1 if i < (n // 2) else 2,
            "text": f"chunk text number {i} about some topic",
            "context_template": f"[LECTURE: L] [SECTION: S] [SPEECH: chunk text number {i}]",
            "section_title": "Introduction",
            "position_category": "middle",
            "slide_text": "",
        }
        for i in range(n)
    ]


def test_build_triplets_creates_output_files(tmp_path):
    chunks_file = tmp_path / "chunks.jsonl"
    write_chunks(chunks_file, make_chunks())

    with (
        patch("app.finetune.build_triplets.OpenAI"),
        patch("app.finetune.build_triplets.generate_queries_for_chunk", side_effect=fake_generate),
    ):
        build_triplets_from_chunks(chunks_file, tmp_path / "out", seed=42)

    assert (tmp_path / "out" / "train.jsonl").exists()
    assert (tmp_path / "out" / "check.jsonl").exists()
    assert (tmp_path / "out" / "split.json").exists()


def test_build_triplets_positives_are_context_templates(tmp_path):
    chunks_file = tmp_path / "chunks.jsonl"
    write_chunks(chunks_file, make_chunks())

    with (
        patch("app.finetune.build_triplets.OpenAI"),
        patch("app.finetune.build_triplets.generate_queries_for_chunk", side_effect=fake_generate),
    ):
        build_triplets_from_chunks(chunks_file, tmp_path / "out", seed=42)

    for fname in ["train.jsonl", "check.jsonl"]:
        for line in (tmp_path / "out" / fname).read_text().splitlines():
            obj = json.loads(line)
            assert obj["positive"].startswith("[LECTURE:")


def test_build_triplets_falls_back_to_text_when_no_context_template(tmp_path):
    chunks = [
        {
            "chunk_id": i,
            "video_id": 1 if i < 5 else 2,
            "text": f"raw speech {i}",
            "context_template": None,
            "section_title": None,
            "position_category": None,
            "slide_text": None,
        }
        for i in range(10)
    ]
    chunks_file = tmp_path / "chunks.jsonl"
    write_chunks(chunks_file, chunks)

    with (
        patch("app.finetune.build_triplets.OpenAI"),
        patch("app.finetune.build_triplets.generate_queries_for_chunk", side_effect=fake_generate),
    ):
        build_triplets_from_chunks(chunks_file, tmp_path / "out", seed=42)

    for fname in ["train.jsonl", "check.jsonl"]:
        for line in (tmp_path / "out" / fname).read_text().splitlines():
            obj = json.loads(line)
            assert obj["positive"].startswith("raw speech")


def test_build_triplets_negatives_differ_from_positives(tmp_path):
    chunks_file = tmp_path / "chunks.jsonl"
    write_chunks(chunks_file, make_chunks())

    with (
        patch("app.finetune.build_triplets.OpenAI"),
        patch("app.finetune.build_triplets.generate_queries_for_chunk", side_effect=fake_generate),
    ):
        build_triplets_from_chunks(chunks_file, tmp_path / "out", seed=42)

    for fname in ["train.jsonl", "check.jsonl"]:
        for line in (tmp_path / "out" / fname).read_text().splitlines():
            obj = json.loads(line)
            assert obj["negative"] is not None
            assert obj["negative"] != obj["positive"]


def test_build_triplets_is_deterministic(tmp_path):
    chunks_file = tmp_path / "chunks.jsonl"
    write_chunks(chunks_file, make_chunks())

    kwargs = dict(check_ratio=0.13, seed=42)

    with (
        patch("app.finetune.build_triplets.OpenAI"),
        patch("app.finetune.build_triplets.generate_queries_for_chunk", side_effect=fake_generate),
    ):
        build_triplets_from_chunks(chunks_file, tmp_path / "out1", **kwargs)

    with (
        patch("app.finetune.build_triplets.OpenAI"),
        patch("app.finetune.build_triplets.generate_queries_for_chunk", side_effect=fake_generate),
    ):
        build_triplets_from_chunks(chunks_file, tmp_path / "out2", **kwargs)

    assert (tmp_path / "out1" / "train.jsonl").read_text() == (
        tmp_path / "out2" / "train.jsonl"
    ).read_text()
    assert (tmp_path / "out1" / "check.jsonl").read_text() == (
        tmp_path / "out2" / "check.jsonl"
    ).read_text()


def test_build_triplets_split_is_by_video(tmp_path):
    # all chunks from video 1 should be in same split, not scattered
    chunks_file = tmp_path / "chunks.jsonl"
    write_chunks(chunks_file, make_chunks(10))

    with (
        patch("app.finetune.build_triplets.OpenAI"),
        patch("app.finetune.build_triplets.generate_queries_for_chunk", side_effect=fake_generate),
    ):
        info = build_triplets_from_chunks(chunks_file, tmp_path / "out", seed=42)

    train_vids = set(info["train_videos"])
    check_vids = set(info["check_videos"])
    assert train_vids.isdisjoint(check_vids)


def test_build_triplets_does_not_accept_annotations_dir(tmp_path):
    ann_dir = tmp_path / "annotations"
    ann_dir.mkdir()
    (ann_dir / "lecture.json").write_text(
        json.dumps({"timestamp_queries": [{"query": "q", "answer_snippet": "a"}]}),
        encoding="utf-8",
    )

    with (
        patch("app.finetune.build_triplets.OpenAI"),
        patch("app.finetune.build_triplets.generate_queries_for_chunk", side_effect=fake_generate),
    ):
        with pytest.raises((IsADirectoryError, PermissionError)):
            build_triplets_from_chunks(ann_dir, tmp_path / "out", seed=42)


def test_build_triplets_empty_chunks_file_raises(tmp_path):
    chunks_file = tmp_path / "empty.jsonl"
    chunks_file.write_text("", encoding="utf-8")

    with (
        patch("app.finetune.build_triplets.OpenAI"),
        patch("app.finetune.build_triplets.generate_queries_for_chunk", side_effect=fake_generate),
    ):
        with pytest.raises(ValueError):
            build_triplets_from_chunks(chunks_file, tmp_path / "out", seed=42)
