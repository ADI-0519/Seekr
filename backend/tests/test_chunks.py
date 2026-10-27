import os

import psycopg2
import pytest
from app.db.session import Base
from app.models.video import Chunk, ProcessingStatus, SlideFrame, Video
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tests.db_helpers import (
    assert_fk_on_delete_cascade,
    assert_index_exists,
    assert_table_exists,
    get_admin_url,
    normalise_db_url,
    rand_dbname,
    replace_db_in_url,
    run_alembic_upgrade,
)

TEST_DB = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="function")
async def sqlite_db():
    """In-memory SQLite session with full schema."""
    engine = create_async_engine(TEST_DB)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess
    await engine.dispose()


async def make_video(session: AsyncSession) -> Video:
    video = Video(
        title="Test Lecture",
        youtube_url="https://youtu.be/test",
        duration=300.0,
        status=ProcessingStatus.PENDING,
    )
    session.add(video)
    await session.commit()
    await session.refresh(video)
    return video


@pytest.mark.asyncio
async def test_chunk_create_and_read(sqlite_db):
    video = await make_video(sqlite_db)

    chunk = Chunk(
        video_id=video.id,
        text="Gradient descent minimises the loss function.",
        start_time=10.0,
        end_time=40.0,
        slide_text="Loss Function L(θ)",
        position_category="early-middle",
        context_template="[SECTION: Optimisation] [POSITION: early-middle]",
    )
    sqlite_db.add(chunk)
    await sqlite_db.commit()
    await sqlite_db.refresh(chunk)

    assert chunk.id is not None
    assert chunk.video_id == video.id
    assert chunk.slide_text == "Loss Function L(θ)"
    assert chunk.position_category == "early-middle"
    assert chunk.context_template == "[SECTION: Optimisation] [POSITION: early-middle]"


@pytest.mark.asyncio
async def test_chunk_nullable_enrichment_fields(sqlite_db):
    video = await make_video(sqlite_db)

    chunk = Chunk(
        video_id=video.id,
        text="Introduction to backpropagation.",
        start_time=0.0,
        end_time=30.0,
    )
    sqlite_db.add(chunk)
    await sqlite_db.commit()
    await sqlite_db.refresh(chunk)

    assert chunk.slide_text is None
    assert chunk.position_category is None
    assert chunk.context_template is None


@pytest.mark.asyncio
async def test_chunk_query_by_time_range(sqlite_db):
    video = await make_video(sqlite_db)

    sqlite_db.add_all(
        [
            Chunk(video_id=video.id, text="A", start_time=0.0, end_time=30.0),
            Chunk(video_id=video.id, text="B", start_time=20.0, end_time=50.0),
            Chunk(video_id=video.id, text="C", start_time=60.0, end_time=90.0),
        ]
    )
    await sqlite_db.commit()

    stmt = (
        select(Chunk)
        .where(
            Chunk.video_id == video.id,
            Chunk.start_time >= 0.0,
            Chunk.end_time <= 55.0,
        )
        .order_by(Chunk.start_time)
    )
    result = await sqlite_db.execute(stmt)
    hits = result.scalars().all()

    assert [h.text for h in hits] == ["A", "B"]


@pytest.mark.asyncio
async def test_chunk_cascade_delete(sqlite_db):
    video = await make_video(sqlite_db)

    sqlite_db.add(Chunk(video_id=video.id, text="Will be deleted.", start_time=0.0, end_time=30.0))
    await sqlite_db.commit()

    await sqlite_db.delete(video)
    await sqlite_db.commit()

    result = await sqlite_db.execute(select(Chunk).where(Chunk.video_id == video.id))
    assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_slide_frame_create_and_read(sqlite_db):
    video = await make_video(sqlite_db)

    frame = SlideFrame(
        video_id=video.id,
        frame_path="/frames/video_1/frame_042.jpg",
        ocr_text="Learning Rate η — Controls step size",
        start_time=12.0,
        end_time=45.0,
    )
    sqlite_db.add(frame)
    await sqlite_db.commit()
    await sqlite_db.refresh(frame)

    assert frame.id is not None
    assert frame.video_id == video.id
    assert frame.frame_path == "/frames/video_1/frame_042.jpg"
    assert frame.ocr_text == "Learning Rate η — Controls step size"
    assert frame.start_time == 12.0
    assert frame.end_time == 45.0


@pytest.mark.asyncio
async def test_slide_frame_nullable_ocr(sqlite_db):
    video = await make_video(sqlite_db)

    frame = SlideFrame(
        video_id=video.id,
        frame_path="/frames/video_1/frame_001.jpg",
        start_time=0.0,
        end_time=30.0,
    )
    sqlite_db.add(frame)
    await sqlite_db.commit()
    await sqlite_db.refresh(frame)

    assert frame.ocr_text is None


@pytest.mark.asyncio
async def test_slide_frame_query_by_time_range(sqlite_db):
    video = await make_video(sqlite_db)

    sqlite_db.add_all(
        [
            SlideFrame(video_id=video.id, frame_path="f1.jpg", start_time=0.0, end_time=30.0),
            SlideFrame(video_id=video.id, frame_path="f2.jpg", start_time=30.0, end_time=60.0),
            SlideFrame(video_id=video.id, frame_path="f3.jpg", start_time=120.0, end_time=150.0),
        ]
    )
    await sqlite_db.commit()

    stmt = (
        select(SlideFrame)
        .where(
            SlideFrame.video_id == video.id,
            SlideFrame.start_time >= 0.0,
            SlideFrame.end_time <= 65.0,
        )
        .order_by(SlideFrame.start_time)
    )
    result = await sqlite_db.execute(stmt)
    hits = result.scalars().all()

    assert len(hits) == 2
    assert hits[0].frame_path == "f1.jpg"
    assert hits[1].frame_path == "f2.jpg"


@pytest.mark.asyncio
async def test_slide_frame_cascade_delete(sqlite_db):
    video = await make_video(sqlite_db)

    sqlite_db.add(
        SlideFrame(video_id=video.id, frame_path="to_delete.jpg", start_time=0.0, end_time=30.0)
    )
    await sqlite_db.commit()

    await sqlite_db.delete(video)
    await sqlite_db.commit()

    result = await sqlite_db.execute(select(SlideFrame).where(SlideFrame.video_id == video.id))
    assert result.scalars().all() == []


@pytest.fixture(scope="session")
def base_db_url() -> str:
    url = os.getenv("DATABASE_URL") or os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set DATABASE_URL (or TEST_DATABASE_URL) to run postgres migration tests.")
    return normalise_db_url(url)


@pytest.fixture()
def fresh_db_url(base_db_url: str):
    db_name = rand_dbname()
    admin_url = get_admin_url(base_db_url)

    conn = psycopg2.connect(admin_url)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(f'CREATE DATABASE "{db_name}";')
    finally:
        conn.close()

    try:
        yield replace_db_in_url(base_db_url, db_name)
    finally:
        conn = psycopg2.connect(admin_url)
        conn.autocommit = True
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = %s AND pid <> pg_backend_pid();",
                    (db_name,),
                )
                cur.execute(f'DROP DATABASE IF EXISTS "{db_name}";')
        finally:
            conn.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_chunks_migration_schema(fresh_db_url: str):
    run_alembic_upgrade(fresh_db_url)

    assert_table_exists(fresh_db_url, "chunks")
    assert_fk_on_delete_cascade(fresh_db_url, "chunks", "videos")
    assert_index_exists(
        fresh_db_url,
        "chunks",
        "ix_chunks_video_time",
        "(video_id, start_time, end_time)",
    )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_chunks_integration_dod(fresh_db_url: str):
    run_alembic_upgrade(fresh_db_url)

    engine = create_async_engine(fresh_db_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        video = Video(
            title="DoD Lecture",
            youtube_url="https://example.com",
            duration=600.0,
            status=ProcessingStatus.PENDING,
        )
        session.add(video)
        await session.commit()
        await session.refresh(video)

        session.add_all(
            [
                Chunk(
                    video_id=video.id,
                    text="Slide explains learning rate.",
                    start_time=12.0,
                    end_time=42.0,
                    slide_text="Learning Rate η",
                    position_category="early-middle",
                    context_template="[SECTION: Gradient Descent] [POSITION: early-middle]",
                ),
                Chunk(
                    video_id=video.id,
                    text="Slide explains momentum.",
                    start_time=42.0,
                    end_time=72.0,
                    slide_text="Momentum β",
                    position_category="middle",
                    context_template="[SECTION: Gradient Descent] [POSITION: middle]",
                ),
                Chunk(
                    video_id=video.id,
                    text="Conclusion slide.",
                    start_time=550.0,
                    end_time=580.0,
                    slide_text="Summary",
                    position_category="end",
                    context_template="[SECTION: Conclusion] [POSITION: end]",
                ),
            ]
        )
        await session.commit()

        stmt = (
            select(Chunk)
            .where(
                Chunk.video_id == video.id,
                Chunk.start_time >= 10.0,
                Chunk.end_time <= 75.0,
            )
            .order_by(Chunk.start_time)
        )
        result = await session.execute(stmt)
        hits = result.scalars().all()

        assert len(hits) == 2
        assert hits[0].slide_text == "Learning Rate η"
        assert hits[1].position_category == "middle"

    await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_slide_frames_integration_dod(fresh_db_url: str):
    run_alembic_upgrade(fresh_db_url)

    engine = create_async_engine(fresh_db_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        video = Video(
            title="Slide Frames DoD Lecture",
            youtube_url="https://example.com/slides",
            duration=300.0,
            status=ProcessingStatus.PENDING,
        )
        session.add(video)
        await session.commit()
        await session.refresh(video)

        session.add_all(
            [
                SlideFrame(
                    video_id=video.id,
                    frame_path="/frames/frame_001.jpg",
                    ocr_text="Introduction to Neural Networks",
                    start_time=0.0,
                    end_time=30.0,
                ),
                SlideFrame(
                    video_id=video.id,
                    frame_path="/frames/frame_002.jpg",
                    ocr_text="Learning Rate η — Controls step size",
                    start_time=30.0,
                    end_time=60.0,
                ),
                SlideFrame(
                    video_id=video.id,
                    frame_path="/frames/frame_003.jpg",
                    ocr_text="Conclusion",
                    start_time=250.0,
                    end_time=300.0,
                ),
            ]
        )
        await session.commit()

        stmt = (
            select(SlideFrame)
            .where(
                SlideFrame.video_id == video.id,
                SlideFrame.start_time >= 0.0,
                SlideFrame.end_time <= 65.0,
            )
            .order_by(SlideFrame.start_time)
        )
        result = await session.execute(stmt)
        hits = result.scalars().all()

        assert len(hits) == 2
        assert hits[0].ocr_text == "Introduction to Neural Networks"
        assert hits[1].ocr_text == "Learning Rate η — Controls step size"

    await engine.dispose()
