from types import SimpleNamespace

import pytest
from app.services.chunking import ChunkingService
from app.services.multimodal.fusion import SlideChunkFusion


def frame(ocr, start, end):
    return {"ocr_text": ocr, "start_time": start, "end_time": end}


def sent(text, start, end):
    return SimpleNamespace(text=text, start_time=start, end_time=end)


def test_no_frames_returns_empty():
    fusion = SlideChunkFusion()
    assert fusion.get_slide_text(0, 30, None) == ""
    assert fusion.get_slide_text(0, 30, []) == ""


def test_non_overlapping_frames_excluded():
    fusion = SlideChunkFusion()
    # frame entirely before window
    assert fusion.get_slide_text(20, 50, [frame("Old slide", 0, 10)]) == ""
    # frame entirely after window
    assert fusion.get_slide_text(0, 30, [frame("Future slide", 60, 90)]) == ""


def test_exact_boundary_excluded():
    # frame ending at win_start and frame starting at win_end are both outside
    fusion = SlideChunkFusion()
    assert fusion.get_slide_text(10, 40, [frame("Before", 0, 10)]) == ""
    assert fusion.get_slide_text(10, 40, [frame("After", 40, 70)]) == ""


def test_overlapping_frame_included():
    fusion = SlideChunkFusion()
    frames = [frame("Gradient Descent", 5, 35)]
    assert fusion.get_slide_text(0, 30, frames) == "Gradient Descent"


def test_empty_ocr_skipped():
    fusion = SlideChunkFusion()
    assert fusion.get_slide_text(0, 30, [frame(None, 0, 30)]) == ""
    assert fusion.get_slide_text(0, 30, [frame("", 0, 30)]) == ""


def test_multiple_overlapping_frames_both_included():
    fusion = SlideChunkFusion()
    frames = [frame("Slide A", 0, 20), frame("Slide B", 15, 40)]
    result = fusion.get_slide_text(10, 35, frames)
    assert "Slide A" in result
    assert "Slide B" in result


def test_duplicate_ocr_deduplicated():
    fusion = SlideChunkFusion()
    frames = [
        frame("Neural Networks Overview", 0, 20),
        frame("Neural Networks Overview", 15, 35),
    ]
    result = fusion.get_slide_text(0, 30, frames)
    assert result.count("Neural Networks Overview") == 1


def test_slide_text_key_present_in_chunks():
    svc = ChunkingService()
    sentences = [sent("intro sentence here", 0, 20), sent("another sentence", 20, 40)]
    chunks = svc.create_chunks(sentences, video_duration=40.0, slide_frames=None)

    assert len(chunks) > 0
    for chunk in chunks:
        assert "slide_text" in chunk
        assert not chunk["slide_text"]  # empty when no slides


def test_long_ocr_truncated():
    fusion = SlideChunkFusion()
    long_ocr = "word " * 200  # ~1000 chars
    result = fusion.get_slide_text(0, 30, [frame(long_ocr, 0, 30)])
    assert len(result) <= 500


def test_combined_long_text_stays_bounded():
    fusion = SlideChunkFusion()
    frames = [frame("alpha " * 100, 0, 20), frame("beta " * 100, 15, 35)]
    result = fusion.get_slide_text(0, 30, frames)
    assert len(result) <= 500


def test_token_aware_truncation():
    tiktoken = pytest.importorskip("tiktoken")

    fusion = SlideChunkFusion(max_slide_tokens=5)
    if fusion._enc is None:
        pytest.skip("tiktoken encoder not available in this environment")

    long_text = "gradient descent neural network backpropagation learning rate optimisation"
    result = fusion.get_slide_text(0, 30, [frame(long_text, 0, 30)])

    assert len(result) < len(long_text)
    enc = tiktoken.get_encoding("cl100k_base")
    # small slack for tokenizer boundary effects
    assert len(enc.encode(result)) <= 10
