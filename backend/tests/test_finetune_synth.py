from __future__ import annotations

import json
from unittest.mock import MagicMock

from app.finetune.synth import ChunkRecord, generate_queries_for_chunk, load_chunks_jsonl


def make_chunk():
    return ChunkRecord(
        chunk_id=1,
        video_id=1,
        text="the gradient descent algorithm updates model weights iteratively",
        context_template="[LECTURE: ML] [SECTION: Optimisation] [POSITION: middle] [SLIDE: ] [SPEECH: the gradient descent...]",
        section_title="Optimisation",
        position_category="middle",
        slide_text=None,
    )


def mock_client(json_response: str):
    resp = MagicMock()
    resp.output_text = json_response
    client = MagicMock()
    client.responses.create.return_value = resp
    return client


def test_generate_queries_returns_all_four_types():
    client = mock_client(
        json.dumps(
            {
                "content": "when does she explain gradient descent?",
                "position": "near the middle of the lecture about optimisation",
                "section": "in the optimisation section when does he cover weight updates?",
                "multimodal": "where is the slide showing the update rule?",
            }
        )
    )

    pairs = generate_queries_for_chunk(make_chunk(), client)

    assert len(pairs) == 4
    types_returned = {qt for qt, _ in pairs}
    assert types_returned == {"content", "position", "section", "multimodal"}
    assert all(q for _, q in pairs)


def test_generate_queries_prompt_contains_chunk_text():
    client = mock_client(
        json.dumps(
            {
                "content": "q",
                "position": "q",
                "section": "q",
                "multimodal": "q",
            }
        )
    )

    chunk = make_chunk()
    generate_queries_for_chunk(chunk, client)

    call_kwargs = client.responses.create.call_args.kwargs
    prompt_content = call_kwargs["input"][0]["content"]
    assert chunk.text[:50] in prompt_content


def test_generate_queries_all_four_types_requested_in_prompt():
    client = mock_client(
        json.dumps(
            {
                "content": "q",
                "position": "q",
                "section": "q",
                "multimodal": "q",
            }
        )
    )

    generate_queries_for_chunk(make_chunk(), client)

    prompt_content = client.responses.create.call_args.kwargs["input"][0]["content"]
    for qt in ("content", "position", "section", "multimodal"):
        assert qt in prompt_content


def test_generate_queries_falls_back_on_api_failure():
    client = MagicMock()
    client.responses.create.side_effect = RuntimeError("api down")

    # should not raise
    pairs = generate_queries_for_chunk(make_chunk(), client)
    assert len(pairs) >= 1
    assert all(q for _, q in pairs)


def test_generate_queries_falls_back_on_invalid_json():
    client = mock_client("this is not json at all")

    pairs = generate_queries_for_chunk(make_chunk(), client)
    assert len(pairs) >= 1
    assert all(q for _, q in pairs)


def test_generate_queries_falls_back_on_empty_response():
    client = mock_client("")

    pairs = generate_queries_for_chunk(make_chunk(), client)
    assert len(pairs) >= 1


def test_load_chunks_jsonl_reads_all_fields(tmp_path):
    p = tmp_path / "chunks.jsonl"
    p.write_text(
        json.dumps(
            {
                "chunk_id": 5,
                "video_id": 2,
                "text": "hello world",
                "context_template": "[LECTURE: X] [SPEECH: hello world]",
                "section_title": "Intro",
                "position_category": "beginning",
                "slide_text": "slide content here",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    chunks = load_chunks_jsonl(p)
    assert len(chunks) == 1
    c = chunks[0]
    assert c.chunk_id == 5
    assert c.video_id == 2
    assert c.context_template == "[LECTURE: X] [SPEECH: hello world]"
    assert c.section_title == "Intro"
    assert c.position_category == "beginning"
    assert c.slide_text == "slide content here"


def test_load_chunks_jsonl_skips_empty_text(tmp_path):
    p = tmp_path / "chunks.jsonl"
    p.write_text(
        json.dumps({"chunk_id": 1, "video_id": 1, "text": "  "})
        + "\n"
        + json.dumps({"chunk_id": 2, "video_id": 1, "text": "real content"})
        + "\n",
        encoding="utf-8",
    )

    chunks = load_chunks_jsonl(p)
    assert len(chunks) == 1
    assert chunks[0].chunk_id == 2
