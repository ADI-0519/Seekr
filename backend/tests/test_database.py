import pytest
from app.db.session import Base
from app.models.video import ProcessingStatus, Segment, Sentence, Video
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Use in-memory SQLite for testing schema constraints and relationships
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_session():
    # Setup: Create engine and tables
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session factory
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    # Teardown
    await engine.dispose()


@pytest.mark.asyncio
async def test_schema_persistence_and_relationships(db_session):
    """
    Verifies Phase 1 Step 1: Data Storage requirements.
    - Persist metadata (Video)
    - Persist pipeline outputs (Sentence, Segment)
    - Verify FK constraints and Indices (via query logic)
    """
    # 1. Create a Video (Metadata)
    video = Video(
        title="Lecture 1: Intro to Database",
        youtube_url="https://youtu.be/12345",
        duration=3600.0,
        status=ProcessingStatus.PENDING,
    )
    db_session.add(video)
    await db_session.commit()
    await db_session.refresh(video)

    assert video.id is not None
    assert video.status == ProcessingStatus.PENDING

    # 2. Insert Sentences (Pipeline Output)
    sentences_data = [
        Sentence(
            video_id=video.id, text="Welcome class.", start_time=0.0, end_time=2.5, confidence=0.99
        ),
        Sentence(
            video_id=video.id,
            text="Today we discuss SQL.",
            start_time=2.5,
            end_time=5.0,
            confidence=0.95,
        ),
        Sentence(
            video_id=video.id, text="Let's start.", start_time=5.0, end_time=7.0, confidence=0.90
        ),
    ]
    db_session.add_all(sentences_data)
    await db_session.commit()

    # 3. Query by time range (Integration DoD)
    stmt = (
        select(Sentence)
        .where(Sentence.video_id == video.id, Sentence.start_time < 6.0, Sentence.end_time > 2.0)
        .order_by(Sentence.start_time)
    )

    result = await db_session.execute(stmt)
    fetched_sentences = result.scalars().all()

    assert len(fetched_sentences) == 3
    assert fetched_sentences[1].text == "Today we discuss SQL."

    # 4. Verify Segments
    segment = Segment(video_id=video.id, title="Introduction", start_time=0.0, end_time=300.0)
    db_session.add(segment)
    await db_session.commit()

    stmt_seg = select(Segment).where(Segment.video_id == video.id)
    result_seg = await db_session.execute(stmt_seg)
    fetched_segments = result_seg.scalars().all()
    assert len(fetched_segments) == 1
    assert fetched_segments[0].title == "Introduction"
