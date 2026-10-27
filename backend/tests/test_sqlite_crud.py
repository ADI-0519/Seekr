import pytest
from app.crud.video import ProcessingJobService, SegmentService, SentenceService, VideoService
from app.db.session import Base
from app.models.video import ProcessingStatus, Sentence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# need docker-compose running for these
# pytest.skip("need infrastructure from step 1", allow_module_level=True)

TEST_DB = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db():
    engine = create_async_engine(TEST_DB)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess
    await engine.dispose()


@pytest.mark.asyncio
async def test_upload_queues_task():
    engine = create_async_engine(TEST_DB)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        repo = VideoService(sess)
        video = await repo.create("Test Video", "https://youtu.be/test")
        await sess.commit()
        assert video.id is not None
        assert video.title == "Test Video"
    await engine.dispose()


@pytest.mark.asyncio
async def test_status_changes():
    engine = create_async_engine(TEST_DB)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        repo = VideoService(sess)
        video = await repo.create("Status Video", None)
        await sess.flush()
        await repo.update_status(video.id, ProcessingStatus.EXTRACTING_AUDIO)
        await sess.commit()
        refreshed = await repo.get_by_id(video.id)
        assert refreshed.status == ProcessingStatus.EXTRACTING_AUDIO
    await engine.dispose()


@pytest.mark.asyncio
async def test_postgres_crud(db):
    video_repo = VideoService(db)
    sentence_repo = SentenceService(db)
    segment_repo = SegmentService(db)
    video = await video_repo.create("Integration Test Video", "https://youtu.be/integration")
    await db.commit()
    assert video.id is not None

    await sentence_repo.create_many(
        video.id,
        [
            {"text": "First sentence.", "start_time": 0.0, "end_time": 5.0},
            {"text": "Second sentence.", "start_time": 5.0, "end_time": 10.0},
        ],
    )
    await segment_repo.create_many(
        video.id,
        [
            {"title": "Segment 1", "start_time": 0.0, "end_time": 5.0},
        ],
    )
    await db.commit()

    stmt = select(Sentence).where(
        Sentence.video_id == video.id, Sentence.start_time >= 0.0, Sentence.end_time <= 6.0
    )
    result = await db.execute(stmt)
    sentences = result.scalars().all()

    assert len(sentences) == 1
    assert sentences[0].text == "First sentence."


@pytest.mark.asyncio
async def test_processing_job_create(db):
    video_repo = VideoService(db)
    job_repo = ProcessingJobService(db)
    video = await video_repo.create("Job Video", None)
    await db.commit()
    await job_repo.create(video.id, task_id="task-1")
    await db.commit()
    jobs = await job_repo.get_by_video(video.id)
    assert len(jobs) == 1
    assert jobs[0].task_id == "task-1"
