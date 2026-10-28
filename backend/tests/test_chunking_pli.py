from unittest.mock import MagicMock

import pytest
from app.db.session import Base
from app.models.video import Chunk, Sentence, Video
from app.services.chunking import ChunkingService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def sync_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Sess = sessionmaker(bind=engine)
    session = Sess()
    yield session
    session.close()
    engine.dispose()


def make_video(session, duration=300.0):
    v = Video(title="Test Lecture", duration=duration)
    session.add(v)
    session.flush()
    return v


def make_sentences(session, video_id, count=20, total_duration=300.0):
    step = total_duration / count
    rows = [
        Sentence(
            video_id=video_id,
            text=f"This is sentence number {i}.",
            start_time=round(i * step, 2),
            end_time=round((i + 1) * step, 2),
        )
        for i in range(count)
    ]
    session.add_all(rows)
    session.flush()
    return rows


def test_full_pipeline_sentences_to_chunks_db(sync_db):
    video = make_video(sync_db, duration=300.0)
    sentences = make_sentences(sync_db, video.id, count=20, total_duration=300.0)

    svc = ChunkingService()
    chunks = svc.create_chunks(sentences, video_duration=300.0)

    chunk_rows = []
    for c in chunks:
        row = Chunk(
            video_id=video.id,
            text=c["text"],
            start_time=c["start_time"],
            end_time=c["end_time"],
            position_category=c["position_category"],
            slide_text=c.get("slide_text", ""),
            context_template=c.get("context_template", ""),
        )
        chunk_rows.append(row)

    sync_db.add_all(chunk_rows)
    sync_db.commit()

    stored = (
        sync_db.query(Chunk).filter(Chunk.video_id == video.id).order_by(Chunk.start_time).all()
    )

    assert len(stored) > 0
    assert stored[0].start_time == 0.0
    assert abs(stored[-1].end_time - sentences[-1].end_time) < 1.0
    assert all(c.position_category is not None for c in stored)

    # window step is 20s so no two consecutive chunks should start more than 20s apart
    for a, b in zip(stored, stored[1:]):
        assert b.start_time - a.start_time <= 20.0


def test_pipeline_qdrant_payload_shape(sync_db):
    video = make_video(sync_db, duration=120.0)
    sentences = make_sentences(sync_db, video.id, count=12, total_duration=120.0)

    svc = ChunkingService()
    chunks = svc.create_chunks(sentences, video_duration=120.0)

    mock_embed = MagicMock()
    mock_embed.embed_texts.return_value = [[0.1] * 1024 for _ in chunks]
    mock_embed.bm25_encode.return_value = [{101: 1.0} for _ in chunks]

    mock_qdrant = MagicMock()

    # build the payload the same way video_tasks would
    vectors = mock_embed.embed_texts([c["context_template"] for c in chunks])
    sparse = mock_embed.bm25_encode([c["text"] for c in chunks])

    upsert_args = []
    for i, (chunk, vec, sp) in enumerate(zip(chunks, vectors, sparse)):
        upsert_args.append(
            {
                "id": video.id * 100000 + i,
                "vector": vec,
                "sparse_vector": sp,
                "payload": {
                    "video_id": video.id,
                    "text": chunk["text"],
                    "start_time": chunk["start_time"],
                    "end_time": chunk["end_time"],
                    "position_category": chunk["position_category"],
                    "slide_text": chunk.get("slide_text", ""),
                    "section_title": chunk.get("section_title", ""),
                },
            }
        )

    mock_qdrant.upsert_chunks(upsert_args)

    call_args = mock_qdrant.upsert_chunks.call_args[0][0]
    assert len(call_args) == len(chunks)

    for item in call_args:
        assert "id" in item
        assert len(item["vector"]) == 1024
        assert isinstance(item["sparse_vector"], dict)
        payload = item["payload"]
        for field in (
            "video_id",
            "text",
            "start_time",
            "end_time",
            "position_category",
            "slide_text",
            "section_title",
        ):
            assert field in payload


def test_pipeline_replaces_existing_chunks(sync_db):
    video = make_video(sync_db, duration=60.0)

    # insert stale chunks from a previous run
    old = Chunk(
        video_id=video.id,
        text="old stale chunk",
        start_time=0.0,
        end_time=30.0,
        position_category="beginning",
        context_template="old",
    )
    sync_db.add(old)
    sync_db.commit()

    sentences = make_sentences(sync_db, video.id, count=6, total_duration=60.0)

    svc = ChunkingService()
    new_chunks = svc.create_chunks(sentences, video_duration=60.0)

    # simulate what the embedding task does: delete old, insert new
    sync_db.query(Chunk).filter(Chunk.video_id == video.id).delete(synchronize_session=False)
    for c in new_chunks:
        sync_db.add(
            Chunk(
                video_id=video.id,
                text=c["text"],
                start_time=c["start_time"],
                end_time=c["end_time"],
                position_category=c["position_category"],
                slide_text=c.get("slide_text", ""),
                section_title=c.get("section_title", ""),
                context_template=c.get("context_template", ""),
            )
        )
    sync_db.commit()

    result = sync_db.query(Chunk).filter(Chunk.video_id == video.id).all()
    assert len(result) == len(new_chunks)
    assert all(c.text != "old stale chunk" for c in result)
