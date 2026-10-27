from __future__ import annotations

import argparse
import json
import logging
import random
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class TripletExample:
    query: str
    positive: str
    negative: str | None = None


@dataclass(frozen=True)
class ChunkMeta:
    video_id: int
    section_title: str | None = None


def _jaccard_words(a: str, b: str) -> float:
    wa = set(a.lower().split())
    wb = set(b.lower().split())
    union = len(wa | wb)
    return len(wa & wb) / union if union else 0.0


def _neg_too_similar(pos: str, neg: str, threshold: float) -> bool:
    # full context template comparison (shared lecture/section header tokens count)
    return _jaccard_words(pos, neg) >= threshold


class NegativeSampler:
    # deterministic negative sampler backed by seeded RNG
    def __init__(self, seed: int = 0) -> None:
        self._rng = random.Random(seed)

    def sample_index(self, n_items: int, *, exclude: set[int]) -> int:
        if n_items <= 0:
            raise ValueError("n_items must be > 0")
        if len(exclude) >= n_items:
            raise ValueError("No available negatives")
        while True:
            idx = self._rng.randrange(n_items)
            if idx not in exclude:
                return idx


class StructureAwareNegativeSampler:
    def __init__(
        self,
        corpus: list[str],
        metadata: list[ChunkMeta],
        seed: int = 0,
        hard_frac: float = 0.4,
        medium_frac: float = 0.3,
        similarity_threshold: float = 0.45,
    ) -> None:
        if len(corpus) != len(metadata):
            raise ValueError("corpus and metadata must have the same length")
        if len(set(corpus)) < 2:
            raise ValueError("corpus must contain at least two distinct items")
        if hard_frac <= 0 or medium_frac <= 0:
            raise ValueError("hard_frac and medium_frac must both be positive")
        if hard_frac + medium_frac >= 1.0:
            raise ValueError("hard_frac + medium_frac must be less than 1.0")

        self._corpus = corpus
        self._metadata = metadata
        self._rng = random.Random(seed)
        self._hard_frac = hard_frac
        self._medium_frac = medium_frac
        self._sim_threshold = similarity_threshold

        self._by_text: dict[str, set[int]] = defaultdict(set)
        for i, t in enumerate(corpus):
            self._by_text[t].add(i)

        self._by_video: dict[int, list[int]] = defaultdict(list)
        self._by_video_section: dict[tuple[int, str | None], list[int]] = defaultdict(list)

        for i, m in enumerate(metadata):
            self._by_video[m.video_id].append(i)
            self._by_video_section[(m.video_id, m.section_title)].append(i)

    def _exclude_for(self, positive: str) -> set[int]:
        return set(self._by_text.get(positive, set()))

    def _pick_from(self, candidates: list[int], positive: str) -> str | None:
        # shuffle and return first candidate passing similarity gate
        if not candidates:
            return None
        order = list(candidates)
        self._rng.shuffle(order)
        for idx in order:
            text = self._corpus[idx]
            if not _neg_too_similar(positive, text, self._sim_threshold):
                return text
        return None

    def sample_hard(self, positive: str, video_id: int, section_title: str | None) -> str | None:
        # same video, different section, tests structural context discrimination
        exclude = self._exclude_for(positive)
        same_video = self._by_video.get(video_id, [])
        same_section = set(self._by_video_section.get((video_id, section_title), []))
        candidates = [i for i in same_video if i not in same_section and i not in exclude]
        return self._pick_from(candidates, positive)

    def sample_medium(self, positive: str, video_id: int, section_title: str | None) -> str | None:
        # same video, same section, different chunk, tests semantic discrimination within context
        exclude = self._exclude_for(positive)
        same_section = self._by_video_section.get((video_id, section_title), [])
        candidates = [i for i in same_section if i not in exclude]
        return self._pick_from(candidates, positive)

    def sample_easy(self, positive: str, video_id: int) -> str | None:
        # different video entirely
        exclude = self._exclude_for(positive)
        other_video = [
            i for vid, indices in self._by_video.items() if vid != video_id for i in indices
        ]
        candidates = [i for i in other_video if i not in exclude]
        return self._pick_from(candidates, positive)

    def sample_with_tier(
        self, positive: str, video_id: int, section_title: str | None
    ) -> tuple[str, str]:
        tier = self._rng.random()

        if tier < self._hard_frac:
            neg = self.sample_hard(positive, video_id, section_title)
            if neg is not None:
                return neg, "hard"

        if tier < self._hard_frac + self._medium_frac:
            neg = self.sample_medium(positive, video_id, section_title)
            if neg is not None:
                return neg, "medium"

        neg = self.sample_easy(positive, video_id)
        if neg is not None:
            return neg, "easy"

        # fallback tries any candidate that passes similarity filter
        exclude = self._exclude_for(positive)
        all_cands = [i for i in range(len(self._corpus)) if i not in exclude]
        neg = self._pick_from(all_cands, positive)
        if neg is not None:
            return neg, "fallback"

        # skip similarity filter as last resort
        sampler = NegativeSampler(seed=self._rng.randint(0, 2**31))
        idx = sampler.sample_index(len(self._corpus), exclude=exclude)
        return self._corpus[idx], "fallback"

    def sample(self, positive: str, video_id: int, section_title: str | None) -> str:
        neg, _tier = self.sample_with_tier(positive, video_id, section_title)
        return neg


def materialize_triplets(
    examples: list[TripletExample],
    *,
    corpus: list[str],
    seed: int = 0,
) -> list[TripletExample]:
    # fills in missing negatives by sampling from corpus
    if len(set(corpus)) < 2:
        raise ValueError("Corpus must contain at least two distinct items")

    by_text: dict[str, set[int]] = {}
    for i, t in enumerate(corpus):
        by_text.setdefault(t, set()).add(i)

    sampler = NegativeSampler(seed=seed)
    out: list[TripletExample] = []
    for ex in examples:
        neg = (ex.negative or "").strip() or None
        if neg is None:
            exclude = set(by_text.get(ex.positive, set()))
            idx = sampler.sample_index(len(corpus), exclude=exclude)
            neg = corpus[idx]
        out.append(replace(ex, negative=neg))
    return out


def materialize_triplets_structured(
    examples: list[TripletExample],
    metadata: list[ChunkMeta],
    *,
    corpus: list[str],
    corpus_metadata: list[ChunkMeta],
    seed: int = 0,
    hard_frac: float = 0.4,
    medium_frac: float = 0.3,
    similarity_threshold: float = 0.45,
    stats_out: dict[str, int] | None = None,
) -> list[TripletExample]:
    if len(examples) != len(metadata):
        raise ValueError("examples and metadata must have the same length")

    sampler = StructureAwareNegativeSampler(
        corpus,
        corpus_metadata,
        seed=seed,
        hard_frac=hard_frac,
        medium_frac=medium_frac,
        similarity_threshold=similarity_threshold,
    )
    out: list[TripletExample] = []
    stats = Counter(
        {
            "hard": 0,
            "medium": 0,
            "easy": 0,
            "fallback": 0,
            "prefilled": 0,
            "total_examples": len(examples),
        }
    )

    for ex, meta in zip(examples, metadata):
        neg = (ex.negative or "").strip() or None
        if neg is None:
            neg, tier = sampler.sample_with_tier(ex.positive, meta.video_id, meta.section_title)
            stats[tier] += 1
        else:
            # drop pre-filled negatives that are too similar; resample instead
            if _neg_too_similar(ex.positive, neg, similarity_threshold):
                neg, tier = sampler.sample_with_tier(ex.positive, meta.video_id, meta.section_title)
                stats[tier] += 1
            else:
                stats["prefilled"] += 1
        out.append(replace(ex, negative=neg))

    if stats_out is not None:
        stats_out.clear()
        stats_out.update({k: int(v) for k, v in stats.items()})

    return out


def load_triplets_jsonl(path: str | Path) -> list[TripletExample]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))

    out: list[TripletExample] = []
    for idx, line in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on line {idx} in {p}") from exc

        query = str(obj.get("query") or "").strip()
        positive = str(obj.get("positive") or "").strip()
        negative = str(obj.get("negative") or "").strip() or None

        if not query or not positive:
            raise ValueError(f"Missing query/positive on line {idx} in {p}")

        out.append(TripletExample(query=query, positive=positive, negative=negative))

    return out


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    parser = argparse.ArgumentParser()
    parser.add_argument("--triplets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    raw = load_triplets_jsonl(args.triplets)
    # derive corpus from unique positives, these are chunk texts synth used
    corpus = list(dict.fromkeys(t.positive for t in raw))
    log.info("loaded %d triplets, corpus size %d", len(raw), len(corpus))

    filled = materialize_triplets(raw, corpus=corpus, seed=args.seed)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out.open("w", encoding="utf-8") as f:
        for t in filled:
            f.write(
                json.dumps(
                    {"query": t.query, "positive": t.positive, "negative": t.negative},
                    ensure_ascii=True,
                )
                + "\n"
            )
            n += 1

    log.info("wrote %d triplets to %s", n, out)


if __name__ == "__main__":
    main()
