from unittest.mock import MagicMock, patch

import pytest
from app.services.qa import QAService, build_messages, parse_citations


def chunk(
    text="Gradient descent is an optimisation algorithm.",
    start=120.0,
    end=150.0,
    title="Optimisation Methods",
):
    return {
        "text": text,
        "start_time": start,
        "end_time": end,
        "score": 0.85,
        "segment_title": title,
    }


def mock_response(text: str):
    r = MagicMock()
    r.output_text = text
    return r


@pytest.fixture
def chunks():
    return [
        chunk(
            "Gradient descent minimises loss by following the negative gradient.",
            120.0,
            150.0,
            "Optimisation",
        ),
        chunk("The learning rate controls how large each step is.", 150.0, 180.0, "Optimisation"),
        chunk("Backpropagation computes gradients using the chain rule.", 180.0, 210.0, "Backprop"),
    ]


@pytest.fixture
def mock_retrieval(chunks):
    with patch("app.services.qa.RetrievalService") as mock:
        mock.return_value.search.return_value = chunks
        yield mock


@pytest.fixture
def mock_openai():
    with patch("app.services.qa.OpenAI") as mock_cls:
        client = MagicMock()
        mock_cls.return_value = client
        yield client


def test_citation_markers_map_to_correct_chunks(chunks):
    answer = "Loss is minimised by following the gradient [1]. Step size is set by the learning rate [2]."
    result = parse_citations(answer, chunks)
    assert len(result) == 2
    assert result[0]["text"] == chunks[0]["text"]
    assert result[1]["text"] == chunks[1]["text"]


def test_out_of_range_marker_is_skipped(chunks):
    answer = "This references a chunk that doesn't exist [9]."
    result = parse_citations(answer, chunks)
    assert result == []  # only 3 chunks, [9] should be dropped


def test_no_markers_returns_empty_citations(chunks):
    result = parse_citations("The answer has no citation markers at all.", chunks)
    assert result == []


def test_duplicate_markers_produce_one_citation(chunks):
    # model sometimes repeats a citation, we should deduplicate
    answer = "The gradient [1] is computed first, then used again [1]."
    result = parse_citations(answer, chunks)
    assert len(result) == 1
    assert result[0]["text"] == chunks[0]["text"]


def test_citation_contains_expected_fields(chunks):
    answer = "Backpropagation uses the chain rule [3]."
    result = parse_citations(answer, chunks)
    assert len(result) == 1
    c = result[0]
    assert "start_time" in c
    assert "end_time" in c
    assert "text" in c
    assert "segment_title" in c
    assert c["start_time"] == 180.0
    assert c["end_time"] == 210.0


def test_no_chunks_returns_not_found_answer():
    with patch("app.services.qa.RetrievalService") as mock:
        mock.return_value.search.return_value = []
        result = QAService().answer(video_id=1, question="what is attention?")

    assert "cannot" in result["answer"].lower() or "not" in result["answer"].lower()
    assert result["citations"] == []


def test_openai_not_called_when_no_chunks():
    # no point hitting the API if retrieval came up empty
    with (
        patch("app.services.qa.RetrievalService") as mock_ret,
        patch("app.services.qa.OpenAI") as mock_cls,
    ):
        mock_ret.return_value.search.return_value = []
        QAService().answer(video_id=1, question="what is softmax?")
        mock_cls.assert_not_called()


def test_openai_failure_returns_fallback(mock_retrieval, mock_openai):
    mock_openai.responses.create.side_effect = Exception("timeout")
    result = QAService().answer(video_id=1, question="what is dropout?")
    assert result["answer"] != ""
    assert result["citations"] == []
    assert result["question"] == "what is dropout?"


def test_successful_response_has_required_keys(mock_retrieval, mock_openai):
    mock_openai.responses.create.return_value = mock_response(
        "Gradient descent minimises loss [1]."
    )
    result = QAService().answer(video_id=1, question="how does training work?")
    assert set(result.keys()) >= {"answer", "citations", "question"}


def test_successful_response_question_echoed(mock_retrieval, mock_openai):
    mock_openai.responses.create.return_value = mock_response("It works by [1].")
    result = QAService().answer(video_id=1, question="how does training work?")
    assert result["question"] == "how does training work?"


def test_build_messages_includes_question(chunks):
    messages = build_messages("what is gradient descent?", chunks)
    combined = " ".join(m["content"] for m in messages)
    assert "what is gradient descent?" in combined


def test_build_messages_includes_chunk_text(chunks):
    messages = build_messages("explain backprop", chunks)
    combined = " ".join(m["content"] for m in messages)
    for chunk in chunks:
        assert chunk["text"] in combined


def test_build_messages_includes_timestamps(chunks):
    messages = build_messages("explain backprop", chunks)
    combined = " ".join(m["content"] for m in messages)
    assert "2:00" in combined  # 120s formats to 2:00


def test_build_messages_numbers_chunks(chunks):
    messages = build_messages("test question", chunks)
    combined = " ".join(m["content"] for m in messages)
    assert "[1]" in combined
    assert "[2]" in combined
    assert "[3]" in combined


def test_client_reused_across_calls(mock_retrieval):
    # OpenAI() should only be instantiated once per service instance
    with patch("app.services.qa.OpenAI") as mock_cls:
        client = MagicMock()
        client.responses.create.return_value = mock_response("answer [1].")
        mock_cls.return_value = client

        svc = QAService()
        svc.answer(video_id=1, question="first question?")
        svc.answer(video_id=1, question="second question?")

    assert mock_cls.call_count == 1


def test_pre_fetched_chunks_skip_retrieval():  # RetrievalService should never be called when chunks passed in
    chunks = [chunk()]
    with (
        patch("app.services.qa.RetrievalService") as mock_ret,
        patch("app.services.qa.OpenAI") as mock_cls,
    ):
        client = MagicMock()
        client.responses.create.return_value = mock_response("some answer [1].")
        mock_cls.return_value = client
        QAService().answer(video_id=1, question="explain gradient descent", chunks=chunks)

    mock_ret.assert_not_called()


def test_pre_fetched_chunks_used_in_answer():
    chunks = [chunk("specific content about attention mechanisms", 60.0, 90.0, "Attention")]
    with patch("app.services.qa.OpenAI") as mock_cls:
        client = MagicMock()
        client.responses.create.return_value = mock_response("attention mechanisms [1].")
        mock_cls.return_value = client
        result = QAService().answer(video_id=1, question="what is attention", chunks=chunks)

    assert result["citations"][0]["text"] == "specific content about attention mechanisms"
    assert result["citations"][0]["start_time"] == 60.0


def test_empty_pre_fetched_chunks_returns_not_found():
    # empty chunks list passed directly should behave the same as retrieval returning nothing
    result = QAService().answer(video_id=1, question="what is attention", chunks=[])
    assert "cannot" in result["answer"].lower() or "not" in result["answer"].lower()
    assert result["citations"] == []
