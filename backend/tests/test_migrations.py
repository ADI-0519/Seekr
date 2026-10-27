import os
from datetime import datetime, timezone

from alembic import command
from alembic.config import Config
from app.models.video import ProcessingStatus, Sentence, Video
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session


# Helper fucntion
def alembic_config(db_url: str) -> Config:
    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


# Test migrations by applying them to a temporary SQLite database and query it.
def test_migrations_apply_and_sentence_query(alembic_sqlite_env):
    db_url = alembic_sqlite_env

    cfg = alembic_config(db_url)
    command.upgrade(cfg, "head")

    engine = create_engine(db_url, future=True)
    try:
        now = datetime.now(timezone.utc)
        with Session(engine) as session:
            video = Video(
                title="Test Video",
                duration=None,
                youtube_url=None,
                storage_path=None,
                status=ProcessingStatus.PENDING,
                error_message=None,
                created_at=now,
                updated_at=now,
            )
            session.add(video)
            session.flush()

            sentence = Sentence(
                video_id=video.id,
                text="hello",
                start_time=1.0,
                end_time=2.0,
                confidence=0.9,
            )
            session.add(sentence)
            session.commit()

            stmt = (
                select(Sentence)
                .where(Sentence.video_id == video.id)
                .where(Sentence.start_time <= 1.5)
                .where(Sentence.end_time >= 1.5)
            )
            results = session.execute(stmt).scalars().all()
            assert len(results) == 1
    finally:
        engine.dispose()
