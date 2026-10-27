from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)


def _to_sync_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql://", 1)
    return url


def export_all(output_dir: Path, video_ids: set[int] | None = None) -> None:
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import sessionmaker

    from app.core.config import get_settings
    from app.models.video import Segment, Sentence, SlideFrame, Video

    settings = get_settings()
    engine = create_engine(_to_sync_url(settings.database_url), pool_pre_ping=True)
    Session = sessionmaker(bind=engine)

    videos_payload: list[dict] = []
    video_id_map: dict[str, int] = {}

    with Session() as session:
        videos = session.execute(select(Video).order_by(Video.id)).scalars().all()

        for video in videos:
            if video_ids is not None and video.id not in video_ids:
                continue

            sentences = (
                session.execute(
                    select(Sentence)
                    .where(Sentence.video_id == video.id)
                    .order_by(Sentence.start_time)
                )
                .scalars()
                .all()
            )

            if not sentences:
                log.warning("video %d (%s) has no sentences, skipping", video.id, video.title)
                continue

            slide_frames = (
                session.execute(
                    select(SlideFrame)
                    .where(SlideFrame.video_id == video.id)
                    .order_by(SlideFrame.start_time)
                )
                .scalars()
                .all()
            )

            segments = (
                session.execute(
                    select(Segment).where(Segment.video_id == video.id).order_by(Segment.start_time)
                )
                .scalars()
                .all()
            )

            videos_payload.append(
                {
                    "video_id": video.id,
                    "title": video.title,
                    "youtube_url": video.youtube_url or "",
                    "duration": float(video.duration or 0.0),
                    "sentences": [
                        {
                            "text": s.text,
                            "start_time": float(s.start_time),
                            "end_time": float(s.end_time),
                        }
                        for s in sentences
                    ],
                    "slide_frames": [
                        {
                            "ocr_text": sf.ocr_text or "",
                            "start_time": float(sf.start_time),
                            "end_time": float(sf.end_time),
                        }
                        for sf in slide_frames
                    ],
                    "segments": [
                        {
                            "title": seg.title,
                            "start_time": float(seg.start_time),
                            "end_time": float(seg.end_time),
                        }
                        for seg in segments
                    ],
                }
            )

            # title holds drive ID; add youtube URL too so data_loader can resolve either
            if video.youtube_url:
                video_id_map[video.youtube_url] = video.id
            if video.title:
                video_id_map[video.title] = video.id

            log.info(
                "exported video %d: %d sentences, %d slide frames, %d segments",
                video.id,
                len(sentences),
                len(slide_frames),
                len(segments),
            )

    output_dir.mkdir(parents=True, exist_ok=True)

    sentences_path = output_dir / "sentences.json"
    sentences_path.write_text(
        json.dumps(
            {"exported_at": datetime.now(timezone.utc).isoformat(), "videos": videos_payload},
            indent=2,
        ),
        encoding="utf-8",
    )
    log.info("wrote %d videos to %s", len(videos_payload), sentences_path)

    map_path = output_dir / "video_id_map.json"
    map_path.write_text(json.dumps(video_id_map, indent=2), encoding="utf-8")
    log.info("wrote %d entries to %s", len(video_id_map), map_path)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m app.evaluation.export")
    parser.add_argument(
        "--output-dir",
        metavar="PATH",
        default="evaluation_output",
    )
    parser.add_argument(
        "--video-ids",
        metavar="IDS",
        help="comma-separated video IDs to export (default: all)",
    )
    args = parser.parse_args(argv)

    video_ids = None
    if args.video_ids:
        video_ids = {int(x) for x in args.video_ids.split(",") if x.strip()}

    export_all(Path(args.output_dir), video_ids=video_ids)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    main()
