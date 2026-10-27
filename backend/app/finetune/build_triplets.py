from __future__ import annotations

import argparse
import json
import logging
import random
from collections import defaultdict
from pathlib import Path

from app.finetune.dataset import (
    ChunkMeta,
    TripletExample,
    load_triplets_jsonl,
    materialize_triplets_structured,
)
from app.finetune.synth import generate_queries_for_chunk, load_chunks_jsonl, write_triplets_jsonl
from openai import OpenAI

log = logging.getLogger(__name__)


def _split_by_video(
    video_ids: list[int], check_ratio: float, seed: int
) -> tuple[set[int], set[int]]:
    # split at video level so no lecture's chunks leak across train/check
    unique_vids = sorted(set(video_ids))
    if len(unique_vids) < 2:
        raise ValueError(
            "Need chunks from at least 2 distinct video_ids to build a non-empty "
            "train/check split. Process another lecture or broaden your export filter."
        )
    rng = random.Random(seed)
    rng.shuffle(unique_vids)
    n_check = max(1, int(len(unique_vids) * check_ratio))
    check_vids = set(unique_vids[:n_check])
    train_vids = set(unique_vids[n_check:])
    return train_vids, check_vids


def _attach_metadata_from_positive_text(
    triplets: list[TripletExample],
    *,
    chunks,
) -> tuple[list[TripletExample], list[ChunkMeta], list[int], int]:
    # map positive text to one or more chunk metas; duplicates can exist across videos
    by_positive: dict[str, list[ChunkMeta]] = defaultdict(list)
    for c in chunks:
        key = c.context_template or c.text
        by_positive[key].append(ChunkMeta(video_id=c.video_id, section_title=c.section_title))

    assigned_triplets: list[TripletExample] = []
    assigned_meta: list[ChunkMeta] = []
    assigned_video_ids: list[int] = []
    missing = 0
    per_text_cursor: dict[str, int] = defaultdict(int)

    for t in triplets:
        metas = by_positive.get(t.positive, [])
        if not metas:
            missing += 1
            continue
        # Deterministic round-robin assignment when the same positive text appears multiple times.
        idx = per_text_cursor[t.positive] % len(metas)
        meta = metas[idx]
        per_text_cursor[t.positive] += 1

        assigned_triplets.append(t)
        assigned_meta.append(meta)
        assigned_video_ids.append(meta.video_id)

    return assigned_triplets, assigned_meta, assigned_video_ids, missing


def _generate_triplets_from_chunks(
    chunks,
) -> tuple[list[TripletExample], list[ChunkMeta], list[int]]:
    client = OpenAI()
    examples: list[TripletExample] = []
    metadata: list[ChunkMeta] = []
    video_ids: list[int] = []

    for i, chunk in enumerate(chunks):
        positive = chunk.context_template or chunk.text
        meta = ChunkMeta(video_id=chunk.video_id, section_title=chunk.section_title)
        pairs = generate_queries_for_chunk(chunk, client)
        for _qt, q in pairs:
            examples.append(TripletExample(query=q, positive=positive))
            metadata.append(meta)
            video_ids.append(chunk.video_id)

        if (i + 1) % 50 == 0:
            log.info("  processed %d / %d chunks", i + 1, len(chunks))

    return examples, metadata, video_ids


def build_triplets_from_chunks(
    chunks_file: Path,
    output_dir: Path,
    check_ratio: float = 0.13,
    seed: int = 42,
    raw_triplets_file: Path | None = None,
    similarity_threshold: float = 0.45,
) -> dict:
    chunks = load_chunks_jsonl(chunks_file)
    if not chunks:
        raise ValueError(f"No chunks loaded from {chunks_file}")

    log.info("loaded %d chunks", len(chunks))
    missing_positive_count = 0
    source = "generated_from_chunks"

    if raw_triplets_file is not None:
        raw_triplets = load_triplets_jsonl(raw_triplets_file)
        all_examples, all_metadata, all_video_ids, missing_positive_count = (
            _attach_metadata_from_positive_text(raw_triplets, chunks=chunks)
        )
        source = "raw_triplets"
        log.info(
            "loaded %d raw triplets, mapped %d (missing positives: %d)",
            len(raw_triplets),
            len(all_examples),
            missing_positive_count,
        )
        if not all_examples:
            raise ValueError(
                "No raw triplets could be mapped back to chunk metadata. "
                "Check that raw triplets were generated from the same chunks file."
            )
    else:
        all_examples, all_metadata, all_video_ids = _generate_triplets_from_chunks(chunks)
        log.info("generated %d query-positive pairs", len(all_examples))

    train_vids, check_vids = _split_by_video(all_video_ids, check_ratio, seed)

    train_ex = []
    train_meta = []
    check_ex = []
    check_meta = []

    for ex, meta, vid in zip(all_examples, all_metadata, all_video_ids):
        if vid in train_vids:
            train_ex.append(ex)
            train_meta.append(meta)
        else:
            check_ex.append(ex)
            check_meta.append(meta)

    # negatives sampled from full corpus so train and check negatives are realistic
    corpus = [ex.positive for ex in all_examples]
    corpus_metadata = list(all_metadata)

    train_stats: dict[str, int] = {}
    check_stats: dict[str, int] = {}

    train_triplets = materialize_triplets_structured(
        train_ex,
        train_meta,
        corpus=corpus,
        corpus_metadata=corpus_metadata,
        seed=seed,
        similarity_threshold=similarity_threshold,
        stats_out=train_stats,
    )
    check_triplets = materialize_triplets_structured(
        check_ex,
        check_meta,
        corpus=corpus,
        corpus_metadata=corpus_metadata,
        seed=seed + 1,
        similarity_threshold=similarity_threshold,
        stats_out=check_stats,
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    n_train = write_triplets_jsonl(train_triplets, output_dir / "train.jsonl")
    n_check = write_triplets_jsonl(check_triplets, output_dir / "check.jsonl")

    split_info = {
        "source": source,
        "raw_triplets_file": str(raw_triplets_file) if raw_triplets_file is not None else None,
        "missing_positive_count": int(missing_positive_count),
        "seed": seed,
        "check_ratio": check_ratio,
        "total_videos": len(sorted(set(all_video_ids))),
        "total_chunks": len(chunks),
        "train_videos": sorted(train_vids),
        "check_videos": sorted(check_vids),
        "train_count": n_train,
        "check_count": n_check,
    }
    if n_train == 0:
        raise ValueError(
            "Computed train split is empty. Ensure at least 2 videos are present and "
            "check-ratio is not overly aggressive for your dataset size."
        )
    if n_check == 0:
        raise ValueError(
            "Computed check split is empty. Increase dataset size or raise --check-ratio."
        )
    (output_dir / "split.json").write_text(json.dumps(split_info, indent=2), encoding="utf-8")

    negative_stats = {
        "seed": seed,
        "train": train_stats,
        "check": check_stats,
        "combined": {
            "hard": int(train_stats.get("hard", 0) + check_stats.get("hard", 0)),
            "medium": int(train_stats.get("medium", 0) + check_stats.get("medium", 0)),
            "easy": int(train_stats.get("easy", 0) + check_stats.get("easy", 0)),
            "fallback": int(train_stats.get("fallback", 0) + check_stats.get("fallback", 0)),
            "prefilled": int(train_stats.get("prefilled", 0) + check_stats.get("prefilled", 0)),
            "total_examples": int(
                train_stats.get("total_examples", 0) + check_stats.get("total_examples", 0)
            ),
        },
    }
    (output_dir / "negative_sampling_stats.json").write_text(
        json.dumps(negative_stats, indent=2), encoding="utf-8"
    )

    log.info("wrote %d train, %d check triplets to %s", n_train, n_check, output_dir)
    return split_info


def main(argv: list[str] | None = None):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    parser = argparse.ArgumentParser()
    parser.add_argument("--chunks-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("app/finetune/triplets"))
    parser.add_argument("--raw-triplets", type=Path, default=None)
    parser.add_argument("--check-ratio", type=float, default=0.13)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--similarity-threshold", type=float, default=0.45)
    args = parser.parse_args(argv)

    build_triplets_from_chunks(
        args.chunks_file,
        args.output_dir,
        check_ratio=args.check_ratio,
        seed=args.seed,
        raw_triplets_file=args.raw_triplets,
        similarity_threshold=args.similarity_threshold,
    )


if __name__ == "__main__":
    main()
