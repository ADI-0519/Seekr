from __future__ import annotations

import json
from pathlib import Path

from app.db.session import Base
from app.finetune.export import export_chunks_jsonl
from app.models.video import Chunk, Video
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


def test_export_chunks_jsonl_writes_correct_fields(tmp_path: Path):
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        v = Video(title="V", youtube_url=None, status="pending")
        session.add(v)
        session.flush()

        session.add_all(
            [
                Chunk(
                    video_id=v.id,
                    text="a",
                    start_time=0.0,
                    end_time=10.0,
                    context_template="ctx a",
                    section_title="s1",
                ),
                Chunk(
                    video_id=v.id,
                    text="b",
                    start_time=10.0,
                    end_time=20.0,
                    context_template=None,
                    section_title=None,
                ),
            ]
        )
        session.commit()

    out_path = tmp_path / "chunks.jsonl"
    n = export_chunks_jsonl(out_path, database_url=db_url)
    assert n == 2

    lines = out_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2

    obj0 = json.loads(lines[0])
    obj1 = json.loads(lines[1])

    assert obj0["text"] == "a"
    assert obj0["context_template"] == "ctx a"
    assert obj1["text"] == "b"
    assert obj1["context_template"] is None


def test_export_chunks_jsonl_video_id_filter(tmp_path: Path):
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        v1 = Video(title="V1", youtube_url=None, status="pending")
        v2 = Video(title="V2", youtube_url=None, status="pending")
        session.add_all([v1, v2])
        session.flush()

        session.add_all(
            [
                Chunk(video_id=v1.id, text="chunk from v1", start_time=0.0, end_time=10.0),
                Chunk(video_id=v2.id, text="chunk from v2", start_time=0.0, end_time=10.0),
            ]
        )
        session.commit()

        v1_id = v1.id

    out_path = tmp_path / "chunks.jsonl"
    n = export_chunks_jsonl(out_path, database_url=db_url, video_id=v1_id)
    assert n == 1

    obj = json.loads(out_path.read_text().strip())
    assert obj["text"] == "chunk from v1"
