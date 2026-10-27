from unittest.mock import MagicMock, patch

import pytest
from app.core.firebase_auth import require_firebase_user
from app.db.session import Base, get_db
from app.main import app
from app.models.video import Segment, Sentence, SlideFrame, Video
from app.services.notes_generation import (
    MAX_INPUT_CHARS,
    MAX_SLIDE_CHARS,
    NotesGenerator,
    NotesInput,
    NotesResult,
    build_prompt,
)
from app.services.pdf_export import (
    format_timestamp,
    generate_notes_pdf,
    markdown_to_paragraph,
)
from httpx import ASGITransport, AsyncClient
from reportlab.lib.styles import getSampleStyleSheet
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


async def make_complete_video(db, title="Test Lecture"):
    video = Video(title=title, status="complete", duration=3600.0, owner_uid="test-user-1")
    db.add(video)
    await db.flush()
    return video


def make_input(**overrides) -> NotesInput:
    defaults = dict(
        segment_id=1,
        title="Introduction to Neural Networks",
        transcript_text=(
            "Today we will discuss neural networks. A neural network is a "
            "computational model inspired by biological neurons. It consists of "
            "layers of interconnected nodes that transform input data into useful "
            "outputs through learned weights. The learning process uses an "
            "algorithm called backpropagation to adjust these weights. "
            "The key formula is w = w - eta * dL/dw where eta is the learning rate."
        ),
        start_time=0.0,
        end_time=120.0,
        slide_text="",
    )
    defaults.update(overrides)
    return NotesInput(**defaults)  # type: ignore[arg-type]


def make_result(**overrides) -> NotesResult:
    defaults = dict(
        segment_id=1,
        title="Introduction to Neural Networks",
        notes_markdown=(
            "Neural networks are computational models inspired by biological neurons, "
            "consisting of interconnected layers that transform input data.\n\n"
            "- **Neural network**: A model with layers of nodes (neurons)\n"
            "- **Backpropagation**: Algorithm for adjusting weights during training\n"
            "  - Uses gradient descent to minimize loss\n"
            "  - Key formula: `w = w - eta * dL/dw`\n"
            "- **Learning rate** (eta): Controls step size during optimization\n"
            "- Weights are updated iteratively across training epochs"
        ),
        start_time=0.0,
        end_time=120.0,
    )
    defaults.update(overrides)
    return NotesResult(**defaults)  # type: ignore[arg-type]


def mock_openai_response(text: str):
    response = MagicMock()
    response.output_text = text
    return response


class TestTimestampFormatting:
    def test_seconds_only(self):
        assert format_timestamp(45.0) == "0:45"

    def test_minutes_and_seconds(self):
        assert format_timestamp(125.0) == "2:05"

    def test_hours(self):
        assert format_timestamp(3661.0) == "1:01:01"

    def test_zero(self):
        assert format_timestamp(0.0) == "0:00"


class TestMarkdownToParagraph:
    def test_bold_conversion(self):
        styles = getSampleStyleSheet()
        elements = markdown_to_paragraph("**bold text** here", styles["Normal"])
        assert len(elements) >= 1

    def test_bullet_points(self):
        styles = getSampleStyleSheet()
        md = "- First point\n- Second point\n  - Sub point"
        elements = markdown_to_paragraph(md, styles["Normal"])
        assert len(elements) == 3

    def test_empty_lines_become_spacers(self):
        styles = getSampleStyleSheet()
        md = "Paragraph one\n\nParagraph two"
        elements = markdown_to_paragraph(md, styles["Normal"])
        assert len(elements) == 3

    def test_nested_bullets_indented(self):
        styles = getSampleStyleSheet()
        md = "- **Parent point**\n  - Child point under parent\n  - Another child"
        elements = markdown_to_paragraph(md, styles["Normal"])
        assert len(elements) == 3
        assert elements[1].style.leftIndent > elements[0].style.leftIndent
        assert elements[2].style.leftIndent == elements[1].style.leftIndent

    def test_subscript_rendered(self):
        styles = getSampleStyleSheet()
        elements = markdown_to_paragraph("A_{i-1} is updated each step", styles["Normal"])
        assert len(elements) == 1

    def test_superscript_rendered(self):
        styles = getSampleStyleSheet()
        elements = markdown_to_paragraph("w(e^{2}) is the squared weight", styles["Normal"])
        assert len(elements) == 1


class TestBuildPrompt:
    def test_includes_title_and_duration(self):
        seg = make_input()
        prompt = build_prompt(seg)
        assert "Introduction to Neural Networks" in prompt
        assert "0s" in prompt

    def test_slide_text_injected_when_present(self):
        seg = make_input(slide_text="Learning Rate\nGradient Descent")
        prompt = build_prompt(seg)
        assert "Slide text" in prompt
        assert "Learning Rate" in prompt

    def test_slide_text_omitted_when_empty(self):
        seg = make_input(slide_text="")
        prompt = build_prompt(seg)
        assert "Slide text" not in prompt

    def test_slide_text_omitted_when_whitespace(self):
        seg = make_input(slide_text="   \n  ")
        prompt = build_prompt(seg)
        assert "Slide text" not in prompt

    def test_slide_text_truncated_when_long(self):
        seg = make_input(slide_text="word " * 500)
        prompt = build_prompt(seg)
        assert "[truncated]" in prompt
        assert len(prompt) < MAX_INPUT_CHARS + MAX_SLIDE_CHARS + 500

    def test_transcript_truncated_when_long(self):
        seg = make_input(transcript_text="word " * 5000)
        prompt = build_prompt(seg)
        assert "[truncated]" in prompt


class TestNotesGenerator:
    def test_short_segment_fallback(self):
        seg = make_input(transcript_text="Hi.", title="Intro")
        generator = NotesGenerator()
        result = generator.generate(seg)
        assert isinstance(result, NotesResult)
        assert "minimal content" in result.notes_markdown

    def test_successful_generation(self):
        valid_notes = (
            "Neural networks are models inspired by biology.\n\n"
            "- **Backpropagation** adjusts weights\n"
            "- Learning rate controls step size"
        )
        mock_client = MagicMock()
        mock_client.responses.create.return_value = mock_openai_response(valid_notes)

        with patch("app.services.notes_generation.OpenAI", return_value=mock_client):
            generator = NotesGenerator()
            result = generator.generate(make_input())

        assert result.notes_markdown == valid_notes
        assert result.title == "Introduction to Neural Networks"
        assert mock_client.responses.create.call_count == 1

    def test_api_failure_retries_then_falls_back(self):
        mock_client = MagicMock()
        mock_client.responses.create.side_effect = Exception("rate limit")

        with patch("app.services.notes_generation.OpenAI", return_value=mock_client):
            generator = NotesGenerator()
            result = generator.generate(make_input())

        assert isinstance(result, NotesResult)
        assert "could not be generated" in result.notes_markdown
        assert mock_client.responses.create.call_count == 2

    def test_retries_once_on_transient_failure(self):
        valid_notes = "Overview paragraph.\n\n- Key point one\n- Key point two"
        mock_client = MagicMock()
        mock_client.responses.create.side_effect = [
            Exception("timeout"),
            mock_openai_response(valid_notes),
        ]

        with patch("app.services.notes_generation.OpenAI", return_value=mock_client):
            generator = NotesGenerator()
            result = generator.generate(make_input())

        assert result.notes_markdown == valid_notes
        assert mock_client.responses.create.call_count == 2

    def test_client_init_failure_returns_fallback(self):
        with patch("app.services.notes_generation.OpenAI", side_effect=Exception("no key")):
            generator = NotesGenerator()
            result = generator.generate(make_input())

        assert isinstance(result, NotesResult)
        assert "could not be generated" in result.notes_markdown

    def test_client_is_reused_across_calls(self):
        valid_notes = "Overview.\n\n- Point one"
        mock_client = MagicMock()
        mock_client.responses.create.return_value = mock_openai_response(valid_notes)

        with patch("app.services.notes_generation.OpenAI", return_value=mock_client) as mock_cls:
            generator = NotesGenerator()
            generator.generate(make_input(segment_id=1))
            generator.generate(make_input(segment_id=2))

        # OpenAI() only instantiated once even across multiple generate() calls
        assert mock_cls.call_count == 1

    def test_generate_all(self):
        valid = "Overview paragraph.\n\n- Key point one\n- Key point two"
        mock_client = MagicMock()
        mock_client.responses.create.return_value = mock_openai_response(valid)

        inputs = [make_input(segment_id=i, title=f"Section {i}") for i in range(4)]

        with patch("app.services.notes_generation.OpenAI", return_value=mock_client):
            generator = NotesGenerator()
            results = generator.generate_all(inputs)

        assert len(results) == 4
        assert all(isinstance(r, NotesResult) for r in results)

    def test_generate_all_empty(self):
        generator = NotesGenerator()
        assert generator.generate_all([]) == []


class TestPDFExport:
    def test_generates_valid_pdf(self):
        notes = [make_result(segment_id=i, title=f"Section {i}") for i in range(3)]
        pdf_buffer = generate_notes_pdf("Test Lecture", notes, lecture_duration=3600.0)

        content = pdf_buffer.read()
        assert content[:5] == b"%PDF-"
        assert len(content) > 500

    def test_handles_long_lectures(self):
        notes = [
            make_result(
                segment_id=i,
                title=f"Section {i}: {'Long Title ' * 5}",
                start_time=i * 600.0,
                end_time=(i + 1) * 600.0,
            )
            for i in range(20)
        ]
        pdf_buffer = generate_notes_pdf("Very Long Lecture", notes, lecture_duration=12000.0)

        content = pdf_buffer.read()
        assert content[:5] == b"%PDF-"
        assert len(content) > 1000

    def test_handles_unicode_and_code(self):
        unicode_notes = NotesResult(
            segment_id=1,
            title="Mathematics & Symbols",
            notes_markdown=(
                "The formula uses eta for learning rate.\n\n"
                "- **Loss function**: L = sum(y - y_hat)^2\n"
                "- Code example: `model.fit(X, y)`\n"
                "- Greek letters: alpha, beta, gamma\n"
                "- Operators: partial, nabla"
            ),
            start_time=0.0,
            end_time=300.0,
        )
        pdf_buffer = generate_notes_pdf("Math Lecture", [unicode_notes])

        content = pdf_buffer.read()
        assert content[:5] == b"%PDF-"

    def test_correct_section_ordering(self):
        notes = [
            make_result(segment_id=1, title="First Section", start_time=0.0, end_time=100.0),
            make_result(segment_id=2, title="Second Section", start_time=100.0, end_time=200.0),
            make_result(segment_id=3, title="Third Section", start_time=200.0, end_time=300.0),
        ]
        pdf_buffer = generate_notes_pdf("Ordered Lecture", notes)

        content = pdf_buffer.read()
        assert content[:5] == b"%PDF-"
        assert len(content) > 2000

    def test_empty_notes_list(self):
        pdf_buffer = generate_notes_pdf("Empty Lecture", [])
        content = pdf_buffer.read()
        assert content[:5] == b"%PDF-"

    def test_no_duration(self):
        notes = [make_result()]
        pdf_buffer = generate_notes_pdf("No Duration", notes, lecture_duration=None)
        content = pdf_buffer.read()
        assert content[:5] == b"%PDF-"


class TestGetNotesAPI:
    @pytest.mark.asyncio
    async def test_returns_404_for_missing_video(self, client):
        r = await client.get("/api/videos/99999/notes")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_400_for_incomplete_video(self, client, db):
        video = Video(title="Pending Video", status="pending", owner_uid="test-user-1")
        db.add(video)
        await db.flush()

        r = await client.get(f"/api/videos/{video.id}/notes")
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_returns_404_when_no_segments(self, client, db):
        video = await make_complete_video(db)
        r = await client.get(f"/api/videos/{video.id}/notes")
        assert r.status_code == 404

    @pytest.mark.asyncio
    @patch("app.api.videos.NotesGenerator")
    async def test_returns_notes_json(self, mock_gen_cls, client, db):
        video = await make_complete_video(db, title="ML Lecture")

        seg = Segment(
            video_id=video.id,
            title="Gradient Descent",
            start_time=0.0,
            end_time=120.0,
        )
        db.add(seg)
        await db.flush()

        db.add(
            Sentence(
                video_id=video.id,
                text="Gradient descent minimises the loss function.",
                start_time=5.0,
                end_time=10.0,
            )
        )
        await db.flush()

        mock_gen = MagicMock()
        mock_gen.generate_all.return_value = [
            NotesResult(
                segment_id=seg.id,
                title="Gradient Descent",
                notes_markdown="Overview.\n\n- Key point",
                start_time=0.0,
                end_time=120.0,
            )
        ]
        mock_gen_cls.return_value = mock_gen

        video_id = video.id
        await db.commit()
        r = await client.get(f"/api/videos/{video_id}/notes")

        assert r.status_code == 200
        data = r.json()
        assert data["video_id"] == video_id
        assert len(data["notes"]) == 1
        assert data["notes"][0]["title"] == "Gradient Descent"
        assert "notes_markdown" in data["notes"][0]

    @pytest.mark.asyncio
    @patch("app.api.videos.NotesGenerator")
    async def test_slide_text_passed_to_generator(self, mock_gen_cls, client, db):
        video = await make_complete_video(db)

        seg = Segment(
            video_id=video.id,
            title="Neural Networks",
            start_time=0.0,
            end_time=120.0,
        )
        db.add(seg)
        await db.flush()

        db.add(
            Sentence(
                video_id=video.id,
                text="Neural networks have multiple layers.",
                start_time=5.0,
                end_time=10.0,
            )
        )
        db.add(
            SlideFrame(
                video_id=video.id,
                start_time=0.0,
                end_time=60.0,
                ocr_text="Activation Functions\nReLU\nSigmoid",
            )
        )
        await db.flush()

        mock_gen = MagicMock()
        mock_gen.generate_all.return_value = [
            NotesResult(
                segment_id=seg.id,
                title="Neural Networks",
                notes_markdown="Overview.\n\n- Point",
                start_time=0.0,
                end_time=120.0,
            )
        ]
        mock_gen_cls.return_value = mock_gen

        await client.get(f"/api/videos/{video.id}/notes")

        call_args = mock_gen.generate_all.call_args[0][0]
        assert len(call_args) == 1
        assert "Activation Functions" in call_args[0].slide_text


class TestExportNotesAPI:
    @pytest.mark.asyncio
    async def test_returns_404_for_missing_video(self, client):
        r = await client.post("/api/videos/99999/notes/export", json={"notes": []})
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_pdf_from_notes_body(self, client, db):
        video = await make_complete_video(db, title="ML Lecture")

        body = {
            "notes": [
                {
                    "segment_id": 1,
                    "title": "Introduction",
                    "notes_markdown": "Overview.\n\n- Key point one\n- Key point two",
                    "start_time": 0.0,
                    "end_time": 120.0,
                }
            ]
        }

        r = await client.post(f"/api/videos/{video.id}/notes/export", json=body)

        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert r.content[:5] == b"%PDF-"

    @pytest.mark.asyncio
    async def test_export_does_not_call_llm(self, client, db):
        video = await make_complete_video(db)

        body = {
            "notes": [
                {
                    "segment_id": 1,
                    "title": "Section",
                    "notes_markdown": "Some content.",
                    "start_time": 0.0,
                    "end_time": 60.0,
                }
            ]
        }

        with patch("app.api.videos.NotesGenerator") as mock_gen_cls:
            r = await client.post(f"/api/videos/{video.id}/notes/export", json=body)
            mock_gen_cls.assert_not_called()

        assert r.status_code == 200


class TestSaveNotes:
    @pytest.mark.asyncio
    async def test_save_notes_persists_markdown(self, db):
        from app.crud.video import SegmentService

        video = await make_complete_video(db)
        seg = Segment(
            video_id=video.id,
            title="Test Segment",
            start_time=0.0,
            end_time=60.0,
        )
        db.add(seg)
        await db.commit()
        await db.refresh(seg)

        svc = SegmentService(db)
        await svc.save_notes([{"segment_id": seg.id, "notes_markdown": "Some notes."}])
        await db.commit()
        await db.refresh(seg)

        assert seg.notes_markdown == "Some notes."

    @pytest.mark.asyncio
    async def test_save_notes_empty_list(self, db):
        from app.crud.video import SegmentService

        svc = SegmentService(db)
        # should not raise
        await svc.save_notes([])
