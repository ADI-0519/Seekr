from unittest.mock import patch

import pytest
from app.core.firebase_auth import require_firebase_user
from app.db.session import Base, get_db
from app.main import app
from app.models.video import Video
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DB = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db():
    engine = create_async_engine(TEST_DB)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession)
    async with factory() as sess:
        yield sess
    await engine.dispose()


@pytest.fixture
async def client(db):
    def override():
        yield db

    app.dependency_overrides[get_db] = override

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def auth_user():
    async def override_auth():
        return {"uid": "test-user-1", "email": "test@example.com"}

    app.dependency_overrides[require_firebase_user] = override_auth
    yield
    app.dependency_overrides.pop(require_firebase_user, None)


async def make_video(db, title="Test Lecture"):
    # status=complete so it passes any processing-state checks in the endpoint
    video = Video(title=title, status="complete", owner_uid="test-user-1")
    db.add(video)
    await db.flush()
    return video


def query_qa_result(answer="Gradient descent minimises the loss [1].", citations=None):
    if citations is None:
        citations = [
            {
                "start_time": 120.0,
                "end_time": 150.0,
                "text": "Gradient descent is an optimisation algorithm.",
                "segment_title": "Optimisation",
            }
        ]
    return {
        "question": "how does training work?",
        "answer": answer,
        "citations": citations,
        "mode": "qa",
    }


def query_retrieval_result(query="backpropagation"):
    return {
        "mode": "retrieval",
        "query": query,
        "results": [
            {
                "text": "Backpropagation computes gradients using the chain rule.",
                "start_time": 180.0,
                "end_time": 210.0,
                "score": 0.91,
                "segment_title": "Backprop",
            }
        ],
    }


class TestQueryEndpoint:
    @pytest.mark.asyncio
    @patch("app.api.videos.run_query")
    async def test_qa_mode_returns_answer(self, mock_task, client, db):
        mock_task.delay.return_value.get.return_value = query_qa_result()
        video = await make_video(db)

        r = await client.post(
            f"/api/videos/{video.id}/query", json={"query": "how does training work?", "mode": "qa"}
        )

        assert r.status_code == 200
        data = r.json()
        assert data["mode"] == "qa"
        assert "answer" in data
        assert "citations" in data

    @pytest.mark.asyncio
    @patch("app.api.videos.run_query")
    async def test_retrieval_mode_returns_results(self, mock_task, client, db):
        mock_task.delay.return_value.get.return_value = query_retrieval_result()
        video = await make_video(db)

        r = await client.post(
            f"/api/videos/{video.id}/query",
            json={"query": "backpropagation", "mode": "retrieval"},
        )

        assert r.status_code == 200
        data = r.json()
        assert data["mode"] == "retrieval"
        assert isinstance(data["results"], list)

    @pytest.mark.asyncio
    async def test_returns_404_for_missing_video(self, client):
        r = await client.post(
            "/api/videos/99999/query",
            json={"query": "what is backprop?"},
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    @patch("app.api.videos.run_query")
    async def test_returns_504_on_task_timeout(self, mock_task, client, db):
        mock_task.delay.return_value.get.side_effect = Exception("timeout")
        video = await make_video(db)

        r = await client.post(f"/api/videos/{video.id}/query", json={"query": "what is softmax?"})
        assert r.status_code == 504  # celery task took too long

    @pytest.mark.asyncio
    @patch("app.api.videos.run_query")
    async def test_citations_is_a_list_in_qa_response(self, mock_task, client, db):
        mock_task.delay.return_value.get.return_value = query_qa_result(citations=[])
        video = await make_video(db)

        r = await client.post(
            f"/api/videos/{video.id}/query",
            json={"query": "explain dropout", "mode": "qa"},
        )
        assert r.status_code == 200
        assert isinstance(r.json()["citations"], list)

    @pytest.mark.asyncio
    @patch("app.api.videos.run_query")
    async def test_citation_fields_present(self, mock_task, client, db):
        mock_task.delay.return_value.get.return_value = query_qa_result()
        video = await make_video(db)

        r = await client.post(
            f"/api/videos/{video.id}/query",
            json={"query": "how does training work?", "mode": "qa"},
        )
        assert r.status_code == 200
        citation = r.json()["citations"][0]
        assert "start_time" in citation
        assert "end_time" in citation
        assert "text" in citation
        assert "segment_title" in citation

    @pytest.mark.asyncio
    @patch("app.api.videos.run_query")
    async def test_result_fields_present_in_retrieval_response(self, mock_task, client, db):
        mock_task.delay.return_value.get.return_value = query_retrieval_result()
        video = await make_video(db)

        r = await client.post(
            f"/api/videos/{video.id}/query",
            json={"query": "backpropagation", "mode": "retrieval"},
        )
        assert r.status_code == 200
        result = r.json()["results"][0]
        assert "text" in result
        assert "start_time" in result
        assert "end_time" in result
        assert "score" in result
