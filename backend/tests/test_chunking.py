from types import SimpleNamespace

import pytest
from app.services.chunking import ChunkingService


def sent(text, start, end):
    return SimpleNamespace(text=text, start_time=start, end_time=end)


def slide(ocr, start, end):
    return {"ocr_text": ocr, "start_time": start, "end_time": end}


def seg(title, start, end):
    return {"title": title, "start_time": start, "end_time": end}


def test_basic_30s_window():
    sentences = [
        sent("s1", 0, 20),
        sent("s2", 20, 40),
        sent("s3", 40, 60),
        sent("s4", 60, 80),
        sent("s5", 80, 100),
    ]
    svc = ChunkingService()
    chunks = svc.create_chunks(sentences, video_duration=100.0)

    # WINDOW_STEP=10 means windows with duplicate sentence sets are collapsed
    assert len(chunks) == 4
    assert [c["start_time"] for c in chunks] == [0.0, 20.0, 40.0, 60.0]
    assert chunks[-1]["end_time"] == 100.0


def test_overlap_coverage():
    # sentence at 25-35s overlaps both [0,30] and [20,50]
    sentences = [
        sent("early sentence", 0, 5),
        sent("boundary sentence", 25, 35),
        sent("late sentence", 55, 65),
    ]
    svc = ChunkingService()
    chunks = svc.create_chunks(sentences, video_duration=100.0)

    first = next(c for c in chunks if c["start_time"] == 0.0)
    # second window covering boundary sentence starts at 30.0 under WINDOW_STEP=10
    second = next(c for c in chunks if c["start_time"] == 30.0)

    assert "boundary sentence" in first["text"]
    assert "boundary sentence" in second["text"]


def test_short_video_single_chunk():
    sentences = [
        sent("intro", 0, 7),
        sent("main point", 7, 14),
        sent("wrap up", 14, 20),
    ]
    svc = ChunkingService()
    chunks = svc.create_chunks(sentences, video_duration=20.0)

    assert len(chunks) == 1
    assert chunks[0]["start_time"] == 0.0
    assert chunks[0]["end_time"] == 20.0


def test_position_categories():
    # 600s video makes percentages easy to reason about
    sentences = [sent(f"sent {i}", i * 10, i * 10 + 10) for i in range(60)]
    svc = ChunkingService()
    chunks = svc.create_chunks(sentences, video_duration=600.0)

    def find(target):
        return min(chunks, key=lambda c: abs(c["start_time"] - target))

    assert find(30)["position_category"] == "beginning"  # 5%
    assert find(120)["position_category"] == "early-middle"  # 20%
    assert find(270)["position_category"] == "middle"  # 45%
    assert find(450)["position_category"] == "late-middle"  # 75%
    assert find(570)["position_category"] == "end"  # 95%


def test_position_boundary_values():
    # 100/600 = 16.7%, which is just inside early-middle bucket (threshold at 15%)
    sentences = [sent(f"sent {i}", i * 10, i * 10 + 10) for i in range(60)]
    svc = ChunkingService()
    chunks = svc.create_chunks(sentences, video_duration=600.0)

    boundary = next((c for c in chunks if abs(c["start_time"] - 100.0) < 1.0), None)
    assert boundary is not None
    assert boundary["position_category"] == "early-middle"


def test_slide_text_overlap():
    sentences = [sent("gradient descent is an optimisation method", 0, 40)]
    slides = [
        slide("Gradient Descent", 0, 30),
        slide("Learning Rate", 25, 55),
    ]
    svc = ChunkingService()
    chunks = svc.create_chunks(sentences, video_duration=60.0, slide_frames=slides)

    assert len(chunks) == 1
    assert "Gradient Descent" in chunks[0]["slide_text"]
    assert "Learning Rate" in chunks[0]["slide_text"]


def test_slide_text_no_overlap():
    sentences = [sent("this is the intro", 0, 30)]
    slides = [slide("Advanced Topics", 100, 130)]
    svc = ChunkingService()
    chunks = svc.create_chunks(sentences, video_duration=130.0, slide_frames=slides)

    assert not chunks[0]["slide_text"]


def test_slide_text_deduplication():
    sentences = [sent("talking about neural nets", 5, 35)]
    # same OCR text from two frames (animation artifact)
    slides = [
        slide("Neural Networks Overview", 0, 25),
        slide("Neural Networks Overview", 20, 40),
    ]
    svc = ChunkingService()
    chunks = svc.create_chunks(sentences, video_duration=60.0, slide_frames=slides)

    text = chunks[0]["slide_text"] or ""
    assert text.count("Neural Networks Overview") == 1


def test_slide_text_truncation():
    long_ocr = "word " * 200  # well over 500 chars
    sentences = [sent("some speech here", 5, 35)]
    slides = [slide(long_ocr, 0, 40)]
    svc = ChunkingService()
    chunks = svc.create_chunks(sentences, video_duration=60.0, slide_frames=slides)

    assert len(chunks[0]["slide_text"]) <= 500


def test_context_template_format():
    sentences = [sent("the learning rate controls step size", 0, 30)]
    svc = ChunkingService()
    chunks = svc.create_chunks(sentences, video_duration=30.0, video_title="Intro to ML")

    tpl = chunks[0]["context_template"]
    assert tpl
    for tag in ["[LECTURE:", "[SECTION:", "[POSITION:", "[SLIDE:", "[SPEECH:"]:
        assert tag in tpl


def test_context_template_no_segment():
    # [SECTION:] should still be in there, just empty
    sentences = [sent("some content here", 10, 40)]
    svc = ChunkingService()
    chunks = svc.create_chunks(sentences, video_duration=60.0)

    assert chunks[0]["context_template"] is not None
    assert "[SECTION:" in chunks[0]["context_template"]


def test_empty_sentences():
    svc = ChunkingService()
    assert svc.create_chunks([], video_duration=300.0) == []


def test_chunk_text_content():
    sentences = [
        sent("The cat sat.", 0, 5),
        sent("The dog ran.", 5, 10),
        sent("The bird flew.", 10, 15),
    ]
    svc = ChunkingService()
    chunks = svc.create_chunks(sentences, video_duration=30.0)

    assert len(chunks) == 1
    assert "The cat sat." in chunks[0]["text"]
    assert "The dog ran." in chunks[0]["text"]
    assert "The bird flew." in chunks[0]["text"]


def test_section_title_present_in_chunk():
    svc = ChunkingService()
    segs = [
        seg("Introduction", 0, 100),
        seg("Advanced Topics", 100, 200),
    ]
    sentences = [
        sent("intro content", 0, 5),
        sent("advanced content", 150, 155),
    ]
    chunks = svc.create_chunks(sentences, video_duration=200.0, segments=segs)

    # make sure section_title is in every chunk and has the right value
    for chunk in chunks:
        assert "section_title" in chunk
        assert isinstance(chunk["section_title"], str)
        assert chunk["section_title"] != ""

    # check the right section gets assigned to each chunk
    intro_chunk = next(c for c in chunks if "intro content" in c["text"])
    adv_chunk = next(c for c in chunks if "advanced content" in c["text"])
    assert intro_chunk["section_title"] == "Introduction"
    assert adv_chunk["section_title"] == "Advanced Topics"


def test_section_title_no_segments():
    # Empty string fallback when segments are missing
    svc = ChunkingService()
    sentences = [sent("some content", 0, 20)]
    chunks = svc.create_chunks(sentences, video_duration=20.0, segments=None)

    for chunk in chunks:
        assert chunk["section_title"] == ""


def test_section_title_boundary():
    svc = ChunkingService()
    segs = [
        seg("Segment A", 0, 50),
        seg("Segment B", 50, 100),
    ]
    sentences = [
        sent("early content", 0, 25),
        sent("late content", 60, 85),
    ]
    chunks = svc.create_chunks(sentences, video_duration=100.0, segments=segs)

    early = next(
        c for c in chunks if "early content" in c["text"] and "late content" not in c["text"]
    )
    late = next(
        c for c in chunks if "late content" in c["text"] and "early content" not in c["text"]
    )
    assert early["section_title"] == "Segment A"
    assert late["section_title"] == "Segment B"


def get_encoder():
    # tiktoken needs to download encoding data on first use; skip if unavailable
    tiktoken = pytest.importorskip("tiktoken")
    try:
        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        pytest.skip("tiktoken encoding data not available in this environment")


def test_token_budget_worst_case():
    # worst case: 500-char title, 500-char section, maxed-out slide and speech ;BGE-M3 accepts up to 8192 tokens so we verify the actual template stays well under
    enc = get_encoder()

    long_title = "A " * 249 + "A"  # 499 chars
    long_section = "B " * 249 + "B"
    long_slide_ocr = "word " * 300  # fusion.py caps this at 150 tokens
    long_speech = "sentence content here " * 30  # chunking.py caps at 300 chars

    svc = ChunkingService()
    sentences = [sent(long_speech, 0, 30)]
    slides = [slide(long_slide_ocr, 0, 30)]
    segs = [seg(long_section, 0, 30)]
    chunks = svc.create_chunks(
        sentences,
        video_duration=30.0,
        slide_frames=slides,
        segments=segs,
        video_title=long_title,
    )

    for chunk in chunks:
        token_count = len(enc.encode(chunk["context_template"]))
        assert token_count < 8192, f"context_template exceeds BGE-M3 limit: {token_count} tokens"


def test_token_budget_simulated_full_lecture():  # simulate a 60-minute lecture and make sure no chunk blows the token limit
    enc = get_encoder()

    sentences = [
        sent(
            f"In this part of the lecture we discuss topic number {i} in some detail.",
            i * 5,
            i * 5 + 5,
        )
        for i in range(720)  # 720 sentences across 3600s
    ]
    slides = [
        slide(f"Slide content topic {i} formula equation example", i * 30, i * 30 + 30)
        for i in range(120)
    ]
    segs = [seg(f"Section {i}", i * 300, i * 300 + 300) for i in range(12)]

    svc = ChunkingService()
    chunks = svc.create_chunks(
        sentences,
        video_duration=3600.0,
        slide_frames=slides,
        segments=segs,
        video_title="Introduction to Machine Learning",
    )

    assert len(chunks) > 0

    violations = [
        (c["start_time"], len(enc.encode(c["context_template"])))
        for c in chunks
        if len(enc.encode(c["context_template"])) >= 8192
    ]
    assert violations == [], f"token limit violations at: {violations}"


def test_position_bucket_all_boundaries():
    svc = ChunkingService()
    # Sentence distribution every 10s
    sentences = [sent(f"sent {i}", i * 10, i * 10 + 10) for i in range(60)]
    sentences.append(sent("sent end", 599, 600))
    chunks = svc.create_chunks(sentences, video_duration=600.0)

    def cat_near(t):
        return min(chunks, key=lambda c: abs(c["start_time"] - t))["position_category"]

    assert cat_near(40) == "beginning"  # 40/600=6.7%
    assert cat_near(140) == "early-middle"  # 140/600=23.3%
    assert cat_near(280) == "middle"  # 280/600=46.7%
    assert cat_near(420) == "late-middle"  # 420/600=70%
    assert cat_near(540) == "end"  # 540/600=90%
    assert cat_near(580) == "end"  # 580/600=96.7%
