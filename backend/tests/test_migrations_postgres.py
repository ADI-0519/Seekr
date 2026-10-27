import os

import psycopg2
import pytest
from app.models.video import ProcessingStatus, Sentence, Video
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tests.db_helpers import (
    assert_alembic_version_present,
    assert_column_exists,
    assert_fk_on_delete_cascade,
    assert_index_exists,
    assert_table_exists,
    get_admin_url,
    normalise_db_url,
    rand_dbname,
    replace_db_in_url,
    run_alembic_upgrade,
)

pytestmark = pytest.mark.integration


@pytest.fixture(scope="session")
def base_db_url() -> str:
    # Resolve database URL from environment
    url = os.getenv("DATABASE_URL") or os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set DATABASE_URL (or TEST_DATABASE_URL) to run integration migration tests.")
    return normalise_db_url(url)


@pytest.fixture()
def fresh_db_url(base_db_url: str):
    db_name = rand_dbname()
    admin_url = get_admin_url(base_db_url)

    # Create temporary test database
    connection = psycopg2.connect(admin_url)
    connection.autocommit = True
    try:
        with connection.cursor() as cur:
            cur.execute(f'CREATE DATABASE "{db_name}";')
    finally:
        connection.close()

    try:
        yield replace_db_in_url(base_db_url, db_name)
    finally:
        # Cleanup: terminate connections and drop database
        connection = psycopg2.connect(admin_url)
        connection.autocommit = True
        try:
            with connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = %s AND pid <> pg_backend_pid();
                    """,
                    (db_name,),
                )
                cur.execute(f'DROP DATABASE IF EXISTS "{db_name}";')
        finally:
            connection.close()


@pytest.mark.asyncio
async def test_migrations_apply_and_schema_is_correct(fresh_db_url: str):
    # Run migrations to head
    run_alembic_upgrade(fresh_db_url)
    assert_alembic_version_present(fresh_db_url)

    # Verify table existence
    for t in ["videos", "sentences", "segments", "slide_frames", "processing_jobs", "chunks"]:
        assert_table_exists(fresh_db_url, t)
    assert_column_exists(fresh_db_url, "videos", "owner_uid")

    # Verify foreign keys and cascade constraints
    assert_fk_on_delete_cascade(fresh_db_url, "sentences", "videos")
    assert_fk_on_delete_cascade(fresh_db_url, "segments", "videos")
    assert_fk_on_delete_cascade(fresh_db_url, "slide_frames", "videos")
    assert_fk_on_delete_cascade(fresh_db_url, "processing_jobs", "videos")
    assert_fk_on_delete_cascade(fresh_db_url, "chunks", "videos")

    # Verify index presence for time-based queries
    assert_index_exists(
        fresh_db_url, "sentences", "ix_sentences_video_time", "(video_id, start_time, end_time)"
    )
    assert_index_exists(
        fresh_db_url, "segments", "ix_segments_video_time", "(video_id, start_time, end_time)"
    )
    assert_index_exists(
        fresh_db_url,
        "slide_frames",
        "ix_slide_frames_video_time",
        "(video_id, start_time, end_time)",
    )
    assert_index_exists(
        fresh_db_url,
        "chunks",
        "ix_chunks_video_time",
        "(video_id, start_time, end_time)",
    )

    # Database engine setup for integration check
    engine = create_async_engine(fresh_db_url, echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as session:
        # Insert test video record
        video = Video(
            title="Migration DoD Test",
            youtube_url="https://example.com",
            duration=123.0,
            status=ProcessingStatus.PENDING,
        )
        session.add(video)
        await session.commit()
        await session.refresh(video)

        # Insert associated sentence data
        session.add_all(
            [
                Sentence(video_id=video.id, text="A", start_time=0.0, end_time=2.0, confidence=0.9),
                Sentence(video_id=video.id, text="B", start_time=2.0, end_time=5.0, confidence=0.9),
                Sentence(
                    video_id=video.id, text="C", start_time=10.0, end_time=12.0, confidence=0.9
                ),
            ]
        )
        await session.commit()

        # Query and validate time-range filtering
        stmt = (
            select(Sentence)
            .where(
                Sentence.video_id == video.id,
                Sentence.start_time >= 0.0,
                Sentence.end_time <= 6.0,
            )
            .order_by(Sentence.start_time)
        )
        res = await session.execute(stmt)
        hits = list(res.scalars().all())
        assert [h.text for h in hits] == ["A", "B"]

    await engine.dispose()
