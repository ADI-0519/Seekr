#!/usr/bin/env python3
# regenerates chunks.jsonl from evaluation_output/sentences.json


from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def rebuild(sentences_json: Path, output: Path) -> int:
    from app.services.chunking import ChunkingService

    data = json.loads(sentences_json.read_text(encoding="utf-8"))
    videos = data.get("videos") or []
    if not videos:
        raise ValueError(f"no videos found in {sentences_json}")

    svc = ChunkingService()
    output.parent.mkdir(parents=True, exist_ok=True)

    chunk_id = 0
    written = 0

    with output.open("w", encoding="utf-8") as f:
        for entry in videos:
            video_id = int(entry["video_id"])
            title = str(entry.get("title") or "")
            duration = float(entry.get("duration") or 0.0)
            sentences = list(entry.get("sentences") or [])
            slide_frames = entry.get("slide_frames") or None
            segments = entry.get("segments") or None

            if not sentences:
                log.warning("video %d has no sentences, skipping", video_id)
                continue

            chunks = svc.create_chunks(sentences, duration, slide_frames, segments, title)

            for c in chunks:
                payload = {
                    "chunk_id": chunk_id,
                    "video_id": video_id,
                    "start_time": c["start_time"],
                    "end_time": c["end_time"],
                    "text": c["text"],
                    "context_template": c["context_template"],
                    "section_title": c.get("section_title") or "",
                    "position_category": c.get("position_category") or "",
                    "slide_text": c.get("slide_text") or "",
                }
                f.write(json.dumps(payload, ensure_ascii=True) + "\n")
                chunk_id += 1
                written += 1

            log.info("video %d: %d chunks", video_id, len(chunks))

    return written


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    parser = argparse.ArgumentParser()
    parser.add_argument("--sentences-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    n = rebuild(args.sentences_json, args.output)
    log.info("wrote %d chunks to %s", n, args.output)


if __name__ == "__main__":
    main()
