from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.core.config import get_settings
from app.models.video import Chunk
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker


def _to_sync_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql://", 1)
    return url


def export_chunks_jsonl(
    output_path: str | Path,
    *,
    database_url: str | None = None,
    video_id: int | None = None,
    video_ids: set[int] | None = None,
    limit: int | None = None,
) -> int:
    settings = get_settings()
    db_url = _to_sync_url(database_url or settings.database_url)

    engine = create_engine(db_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)

    stmt = select(Chunk).order_by(Chunk.video_id, Chunk.start_time, Chunk.id)
    if video_id is not None:
        stmt = stmt.where(Chunk.video_id == video_id)
    elif video_ids is not None:
        stmt = stmt.where(Chunk.video_id.in_(video_ids))
    if limit is not None:
        stmt = stmt.limit(int(limit))

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with SessionLocal() as session:
        rows = session.execute(stmt).scalars().all()
        with out_path.open("w", encoding="utf-8") as f:
            for c in rows:
                payload = {
                    "chunk_id": c.id,
                    "video_id": c.video_id,
                    "start_time": float(c.start_time),
                    "end_time": float(c.end_time),
                    "text": c.text,
                    "context_template": c.context_template,
                    "section_title": c.section_title,
                    "position_category": getattr(c, "position_category", None),
                    "slide_text": getattr(c, "slide_text", None),
                }
                f.write(json.dumps(payload, ensure_ascii=True) + "\n")
                count += 1

    return count


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.finetune.export")
    parser.add_argument("--output-dir", metavar="PATH", default="runs/finetune/data")
    parser.add_argument(
        "--video-ids",
        metavar="IDS",
        help="comma-separated video IDs to export (default: all)",
    )
    parser.add_argument("--limit", type=int, metavar="N")
    args = parser.parse_args()

    video_ids = None
    if args.video_ids:
        video_ids = {int(x) for x in args.video_ids.split(",") if x.strip()}

    out = Path(args.output_dir) / "chunks.jsonl"
    n = export_chunks_jsonl(out, video_ids=video_ids, limit=args.limit)
    print(f"wrote {n} chunks to {out}")


if __name__ == "__main__":
    main()
