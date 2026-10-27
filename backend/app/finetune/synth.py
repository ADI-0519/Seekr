from __future__ import annotations

import argparse
import json
import logging
import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from app.finetune.dataset import TripletExample

log = logging.getLogger(__name__)

_WS_RE = re.compile(r"\s+")

# the five query categories we train on
QUERY_TYPES = ("content", "position", "section", "multimodal", "conceptual")

SYNTH_MAX_OUTPUT_TOKENS = 320
SYNTH_REASONING_EFFORT = "minimal"
SYNTH_SPEECH_CHARS = 220
SYNTH_SLIDE_CHARS = 180
SYNTH_JSON_RETRY_ATTEMPTS = 2
SYNTH_RATE_LIMIT_SLEEP = 60
SYNTH_MAX_WORKERS = 20


def _fallback_query(section_title: str | None) -> str:
    return f"what is covered in the {section_title or 'lecture'} section?"


_QUERY_PROMPT = (
    "You are generating training data for a lecture video retrieval system.\n\n"
    "Given the chunk info below, write one natural student query for each of the five types.\n"
    "Return ONLY a valid JSON object with keys: content, position, section, multimodal, conceptual.\n\n"
    "Chunk info:\n"
    "- Section: {section}\n"
    "- Position in lecture: {position}\n"
    "- Slide text: {slide}\n"
    "- Speech transcript: {speech}\n\n"
    "Query types:\n"
    "- content: asks about a specific mechanism, process, or fact explained in this chunk "
    '(e.g. "how does the hash function map keys to buckets?", "what happens when a B+ tree node overflows?")\n'
    "- position: references the position in the lecture AND the topic "
    '(e.g. "near the beginning where she introduces gradient descent", "in the middle section about backpropagation")\n'
    "- section: references the section by name and asks about something within it "
    '(e.g. "in the sorting section when does he show the merge sort example?")\n'
    "- multimodal: asks about a concept, formula, or diagram visible on a slide — "
    "must reference actual content, NOT slide formatting or verbatim text "
    '(e.g. "where is the slide showing the softmax formula?", "which slide has the confusion matrix diagram?")\n'
    "- conceptual: abstract question requiring synthesis across the whole section, not answerable from a single moment "
    '(e.g. "why is amortised analysis valid even when individual operations are expensive?", '
    '"how do attention mechanisms allow transformers to capture long-range dependencies?")\n\n'
    "Rules:\n"
    "- Each query must be distinct; do not write the same question twice in different words\n"
    "- Queries should sound like a student wrote them, not a textbook\n"
    "- Keep each query under 20 words\n"
    "- Return valid JSON only, no extra text, no markdown fences."
)

GENERIC_QUERY_PHRASES = {
    "explain this",
    "what is this",
    "help me",
    "tell me more",
    "summarise this",
    "summary please",
    "how do",
}

_AMBIGUOUS_REF_STARTS = ("this", "that", "it", "these", "those")


class QualityThresholds(TypedDict):
    min_chars: int
    min_words: int
    enforce_generic: bool
    enforce_ambiguous_ref: bool


def _quality_thresholds(strictness: str) -> QualityThresholds:
    if strictness == "low":
        return {
            "min_chars": 8,
            "min_words": 2,
            "enforce_generic": False,
            "enforce_ambiguous_ref": False,
        }
    if strictness == "high":
        return {
            "min_chars": 16,
            "min_words": 4,
            "enforce_generic": True,
            "enforce_ambiguous_ref": True,
        }
    # medium default
    return {
        "min_chars": 12,
        "min_words": 3,
        "enforce_generic": True,
        "enforce_ambiguous_ref": False,
    }


@dataclass(frozen=True)
class ChunkRecord:
    chunk_id: int
    video_id: int
    text: str
    context_template: str | None = None
    section_title: str | None = None
    position_category: str | None = None
    slide_text: str | None = None


def _clean(s: str) -> str:
    return _WS_RE.sub(" ", s.strip())


def _normalize_query(q: str) -> str:
    return _WS_RE.sub(" ", q.strip())


def _is_low_quality_query(
    q: str,
    *,
    min_chars: int,
    min_words: int,
    enforce_generic: bool,
    enforce_ambiguous_ref: bool,
) -> tuple[bool, str | None]:
    if len(q) < min_chars:
        return True, "too_short"
    words = q.split()
    if len(words) < min_words:
        return True, "too_few_words"
    if not re.search(r"[A-Za-z]", q):
        return True, "no_alpha"
    lowered = q.lower()
    if enforce_generic and lowered in GENERIC_QUERY_PHRASES:
        return True, "generic"
    if enforce_ambiguous_ref and len(words) <= 5 and lowered.startswith(_AMBIGUOUS_REF_STARTS):
        return True, "ambiguous_reference"
    return False, None


def load_chunks_jsonl(path: str | Path) -> list[ChunkRecord]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))

    out: list[ChunkRecord] = []
    for idx, line in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on line {idx} in {p}") from exc

        text = _clean(str(obj.get("text") or ""))
        if not text:
            continue

        out.append(
            ChunkRecord(
                chunk_id=int(obj.get("chunk_id") or 0),
                video_id=int(obj.get("video_id") or 0),
                text=text,
                context_template=_clean(str(obj.get("context_template") or "")) or None,
                section_title=_clean(str(obj.get("section_title") or "")) or None,
                position_category=str(obj.get("position_category") or "") or None,
                slide_text=_clean(str(obj.get("slide_text") or "")) or None,
            )
        )

    return out


def generate_queries_for_chunk(chunk: ChunkRecord, client) -> list[tuple[str, str]]:
    speech = (chunk.text or "")[:SYNTH_SPEECH_CHARS]
    slide = (chunk.slide_text or "none")[:SYNTH_SLIDE_CHARS]
    prompt = _QUERY_PROMPT.format(
        section=chunk.section_title or "unknown",
        position=chunk.position_category or "unknown",
        slide=slide,
        speech=speech,
    )

    last_exc: Exception | None = None
    for attempt in range(1, SYNTH_JSON_RETRY_ATTEMPTS + 1):
        retry_instruction = ""
        if attempt > 1:
            retry_instruction = (
                "\n\nIMPORTANT: Your previous response was invalid JSON. "
                "Return ONLY a valid JSON object with exactly these keys: "
                "content, position, section, multimodal, conceptual."
            )

        try:
            resp = client.responses.create(
                model="gpt-5-mini",
                input=[{"role": "user", "content": prompt + retry_instruction}],
                max_output_tokens=SYNTH_MAX_OUTPUT_TOKENS,
                reasoning={"effort": SYNTH_REASONING_EFFORT},
            )
            raw = (resp.output_text or "").strip()
            # strip markdown fences if the model wraps JSON
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.DOTALL).strip()
            parsed = json.loads(raw)
            pairs = [(qt, str(parsed.get(qt) or "").strip()) for qt in QUERY_TYPES]
            pairs = [(qt, q) for qt, q in pairs if q]
            if pairs:
                return pairs
        except Exception as exc:
            last_exc = exc
            if type(exc).__name__ == "RateLimitError":
                log.warning(
                    "rate limit hit on chunk %d, sleeping %ds",
                    chunk.chunk_id,
                    SYNTH_RATE_LIMIT_SLEEP,
                )
                time.sleep(SYNTH_RATE_LIMIT_SLEEP)

    if last_exc is not None:
        log.warning("query generation failed for chunk %d: %s", chunk.chunk_id, last_exc)

    # fallback so we don't silently drop chunk from training data
    return [("content", _fallback_query(chunk.section_title))]


def write_triplets_jsonl(triplets: list[TripletExample], path: str | Path) -> int:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    n = 0
    with p.open("w", encoding="utf-8") as f:
        for t in triplets:
            f.write(
                json.dumps(
                    {"query": t.query, "positive": t.positive, "negative": t.negative},
                    ensure_ascii=True,
                )
                + "\n"
            )
            n += 1

    return n


def _process_chunk(
    chunk: ChunkRecord, client, thresholds: QualityThresholds
) -> tuple[ChunkRecord, list[tuple[str, str]]]:
    # returns (chunk, pairs),  pairs already filtered for empty strings
    pairs = generate_queries_for_chunk(chunk, client)
    return chunk, pairs


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    parser = argparse.ArgumentParser()
    parser.add_argument("--chunks-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--quality-strictness",
        choices=("low", "medium", "high"),
        default="medium",
    )
    parser.add_argument("--workers", type=int, default=SYNTH_MAX_WORKERS)
    args = parser.parse_args(argv)

    import openai

    client = openai.OpenAI()

    chunks = load_chunks_jsonl(args.chunks_file)
    if args.limit is not None:
        chunks = chunks[: args.limit]

    log.info("generating queries for %d chunks (workers=%d)", len(chunks), args.workers)
    thresholds = _quality_thresholds(args.quality_strictness)

    # results keyed by chunk index to preserve order for reproducibility
    results: dict[int, tuple[ChunkRecord, list[tuple[str, str]]]] = {}
    completed = 0

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(_process_chunk, chunk, client, thresholds): idx
            for idx, chunk in enumerate(chunks)
        }
        for future in as_completed(futures):
            idx = futures[future]
            try:
                chunk, pairs = future.result()
                results[idx] = (chunk, pairs)
            except Exception as exc:
                chunk = chunks[idx]
                log.warning("chunk %d failed: %s", chunk.chunk_id, exc)
                results[idx] = (chunk, [("content", _fallback_query(chunk.section_title))])

            completed += 1
            if completed % 50 == 0:
                log.info("%d/%d chunks processed", completed, len(chunks))

    # process results in original chunk order
    triplets: list[TripletExample] = []
    drop_counts: Counter[str] = Counter()
    generated_total = 0
    kept_total = 0
    fallback_query_count = 0
    fallback_chunk_count = 0

    for idx in range(len(chunks)):
        chunk, pairs = results[idx]
        positive = chunk.context_template or chunk.text
        seen_queries: set[str] = set()
        fallback_used_for_chunk = False

        for _, query in pairs:
            generated_total += 1
            normalized = _normalize_query(query)
            if not normalized:
                drop_counts["too_short"] += 1
                continue

            if normalized.lower() in seen_queries:
                drop_counts["duplicate"] += 1
                continue

            is_bad, reason = _is_low_quality_query(
                normalized,
                min_chars=thresholds["min_chars"],
                min_words=thresholds["min_words"],
                enforce_generic=thresholds["enforce_generic"],
                enforce_ambiguous_ref=thresholds["enforce_ambiguous_ref"],
            )
            if is_bad:
                drop_counts[str(reason)] += 1
                continue

            seen_queries.add(normalized.lower())
            triplets.append(TripletExample(query=normalized, positive=positive, negative=None))
            kept_total += 1
            if normalized == _fallback_query(chunk.section_title):
                fallback_query_count += 1
                fallback_used_for_chunk = True

        if fallback_used_for_chunk:
            fallback_chunk_count += 1

    n = write_triplets_jsonl(triplets, args.output)
    log.info("wrote %d raw triplets to %s", n, args.output)

    report = {
        "input_chunks": len(chunks),
        "quality_strictness": args.quality_strictness,
        "thresholds": thresholds,
        "generated_total": generated_total,
        "kept_total": kept_total,
        "kept_ratio": round((kept_total / generated_total), 4) if generated_total else 0.0,
        "fallback_chunk_count": fallback_chunk_count,
        "fallback_query_count": fallback_query_count,
        "dropped": {
            "too_short": int(drop_counts["too_short"]),
            "too_few_words": int(drop_counts["too_few_words"]),
            "generic": int(drop_counts["generic"]),
            "no_alpha": int(drop_counts["no_alpha"]),
            "duplicate": int(drop_counts["duplicate"]),
            "ambiguous_reference": int(drop_counts["ambiguous_reference"]),
        },
    }
    report_path = args.output.with_suffix(".quality_report.json")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    log.info("wrote quality report to %s", report_path)


if __name__ == "__main__":
    main()
