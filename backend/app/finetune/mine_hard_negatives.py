from __future__ import annotations

import argparse
import json
import logging
import random
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from app.finetune.dataset import TripletExample, _neg_too_similar, load_triplets_jsonl
from app.finetune.synth import load_chunks_jsonl

log = logging.getLogger(__name__)


def _normalize_rows(mat: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    return mat / norms


def _write_triplets_jsonl(path: Path, triplets: list[TripletExample]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for t in triplets:
            f.write(
                json.dumps(
                    {"query": t.query, "positive": t.positive, "negative": t.negative},
                    ensure_ascii=True,
                )
                + "\n"
            )


def _pick_negative(
    ranked: np.ndarray,
    pos_indices: set[int],
    corpus_texts: list[str],
    corpus_meta: list[tuple[int, str | None]],
    pos_vid: int,
    pos_section: str | None,
    positive_text: str,
    rng: random.Random,
    hard_frac: float,
    medium_frac: float,
    similarity_threshold: float,
) -> tuple[int, str]:
    best_idx: dict[str, int | None] = {"hard": None, "medium": None, "easy": None}

    for ridx_raw in ranked:
        ridx = int(ridx_raw)
        if ridx in pos_indices:
            continue
        # skip if the candidate is too lexically similar to positive
        if _neg_too_similar(positive_text, corpus_texts[ridx], similarity_threshold):
            continue

        vid, section = corpus_meta[ridx]
        if vid == pos_vid:
            if section != pos_section and best_idx["hard"] is None:
                best_idx["hard"] = ridx
            elif section == pos_section and best_idx["medium"] is None:
                best_idx["medium"] = ridx
        elif best_idx["easy"] is None:
            best_idx["easy"] = ridx

        if all(v is not None for v in best_idx.values()):
            break

    roll = rng.random()
    if roll < hard_frac and best_idx["hard"] is not None:
        return best_idx["hard"], "hard"
    if roll < hard_frac + medium_frac and best_idx["medium"] is not None:
        return best_idx["medium"], "medium"
    if best_idx["easy"] is not None:
        return best_idx["easy"], "easy"

    # tier preference failed; take whatever was found
    for tier in ("hard", "medium", "easy"):
        if best_idx[tier] is not None:
            return best_idx[tier], tier  # type: ignore[return-value]

    for ridx_raw in ranked:
        ridx = int(ridx_raw)
        if ridx not in pos_indices:
            return ridx, "fallback"

    return next(iter(pos_indices)), "fallback"


def mine_hard_negatives(
    *,
    model_path: str,
    chunks_file: Path,
    input_triplets: Path,
    output_triplets: Path,
    stats_path: Path,
    batch_size: int = 64,
    hard_frac: float = 0.4,
    medium_frac: float = 0.3,
    similarity_threshold: float = 0.45,
    seed: int = 42,
) -> dict[str, int]:
    try:
        from sentence_transformers import SentenceTransformer
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "sentence_transformers is required; install requirements_ml.txt"
        ) from exc

    chunks = load_chunks_jsonl(chunks_file)
    triplets = load_triplets_jsonl(input_triplets)
    if not chunks:
        raise ValueError(f"no chunks found in {chunks_file}")
    if not triplets:
        raise ValueError(f"no triplets found in {input_triplets}")

    corpus_texts = [c.context_template or c.text for c in chunks]
    corpus_meta: list[tuple[int, str | None]] = [(c.video_id, c.section_title) for c in chunks]

    by_positive: dict[str, list[int]] = defaultdict(list)
    for idx, txt in enumerate(corpus_texts):
        by_positive[txt].append(idx)

    model = SentenceTransformer(model_path, local_files_only=True)

    doc_emb = _normalize_rows(
        np.asarray(model.encode(corpus_texts, batch_size=batch_size, convert_to_numpy=True))
    )
    qry_emb = _normalize_rows(
        np.asarray(
            model.encode([t.query for t in triplets], batch_size=batch_size, convert_to_numpy=True)
        )
    )

    stats: Counter[str] = Counter(
        {
            "total_examples": len(triplets),
            "hard": 0,
            "medium": 0,
            "easy": 0,
            "fallback": 0,
            "missing_positive_text": 0,
        }
    )

    rng = random.Random(seed)
    mined: list[TripletExample] = []
    for i, ex in enumerate(triplets):
        pos_indices = set(by_positive.get(ex.positive, []))
        if not pos_indices:
            stats["missing_positive_text"] += 1
            mined.append(
                TripletExample(
                    query=ex.query, positive=ex.positive, negative=ex.negative or ex.positive
                )
            )
            continue

        pos_vid, pos_section = corpus_meta[next(iter(pos_indices))]
        sims = np.dot(doc_emb, qry_emb[i])
        ranked = np.argsort(-sims)

        chosen_idx, tier = _pick_negative(
            ranked,
            pos_indices,
            corpus_texts,
            corpus_meta,
            pos_vid,
            pos_section,
            ex.positive,
            rng,
            hard_frac,
            medium_frac,
            similarity_threshold,
        )
        stats[tier] += 1
        mined.append(
            TripletExample(query=ex.query, positive=ex.positive, negative=corpus_texts[chosen_idx])
        )

    _write_triplets_jsonl(output_triplets, mined)
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    stats_path.write_text(json.dumps(dict(stats), indent=2), encoding="utf-8")
    log.info("wrote %d mined triplets to %s", len(mined), output_triplets)
    return dict(stats)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--chunks-file", type=Path, required=True)
    parser.add_argument("--input-triplets", type=Path, required=True)
    parser.add_argument("--output-triplets", type=Path, required=True)
    parser.add_argument("--stats-path", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--hard-frac", type=float, default=0.4)
    parser.add_argument("--medium-frac", type=float, default=0.3)
    parser.add_argument("--similarity-threshold", type=float, default=0.45)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    mine_hard_negatives(
        model_path=args.model_path,
        chunks_file=args.chunks_file,
        input_triplets=args.input_triplets,
        output_triplets=args.output_triplets,
        stats_path=args.stats_path,
        batch_size=args.batch_size,
        hard_frac=args.hard_frac,
        medium_frac=args.medium_frac,
        similarity_threshold=args.similarity_threshold,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
