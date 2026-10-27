from __future__ import annotations

from unittest.mock import patch

patch("nltk.download", lambda *a, **kw: None).start()

from app.services.segmentation import (  # noqa: E402
    TopicSegmenter,
    _RawSegment,
    find_common_lines,
    get_ocr_hint,
    normalize_ocr,
)
from app.services.sentence_reconstruction import ReconstructedSentence  # noqa: E402


def make_sentences(count: int, duration_each: float = 10.0) -> list[ReconstructedSentence]:
    sentences = []
    for i in range(count):
        sentences.append(
            ReconstructedSentence(
                text=f"This is sentence number {i} about topic {'alpha' if i < count // 2 else 'beta'}.",
                start_time=i * duration_each,
                end_time=(i + 1) * duration_each - 0.1,
                word_start_idx=i * 8,
                word_end_idx=i * 8 + 7,
            )
        )
    return sentences


class TestSegmentProperties:
    def test_segments_are_ordered(self):
        sentences = make_sentences(30)
        segmenter = TopicSegmenter(
            min_segment_duration_ratio=0.0, min_segment_duration_floor_secs=30
        )
        results = segmenter.segment(sentences, video_title="Test")

        orders = [r.segment_order for r in results]
        assert orders == sorted(orders)
        assert orders == list(range(1, len(results) + 1))

    def test_segments_non_overlapping(self):
        sentences = make_sentences(30)
        segmenter = TopicSegmenter(
            min_segment_duration_ratio=0.0, min_segment_duration_floor_secs=30
        )
        results = segmenter.segment(sentences, video_title="Test")

        for i in range(len(results) - 1):
            assert results[i].end_time <= results[i + 1].start_time

    def test_segments_cover_full_duration(self):
        sentences = make_sentences(30)
        segmenter = TopicSegmenter(
            min_segment_duration_ratio=0.0, min_segment_duration_floor_secs=30
        )
        results = segmenter.segment(sentences, video_title="Test")

        assert results[0].start_time == sentences[0].start_time
        assert results[-1].end_time == sentences[-1].end_time

    def test_no_short_segments_except_last(self):
        sentences = make_sentences(30)
        min_dur = 30.0
        segmenter = TopicSegmenter(
            min_segment_duration_ratio=0.0, min_segment_duration_floor_secs=min_dur
        )
        results = segmenter.segment(sentences, video_title="Test")

        for seg in results[:-1]:
            assert seg.end_time - seg.start_time >= min_dur

    def test_titles_present(self):
        sentences = make_sentences(30)
        segmenter = TopicSegmenter(
            min_segment_duration_ratio=0.0, min_segment_duration_floor_secs=30
        )
        results = segmenter.segment(sentences, video_title="Test")

        for seg in results:
            assert seg.title
            assert len(seg.title) > 0

    def test_max_segments_respected(self):
        sentences = make_sentences(100, duration_each=5.0)
        segmenter = TopicSegmenter(
            min_segment_duration_ratio=0.0, min_segment_duration_floor_secs=10, max_segments=5
        )
        results = segmenter.segment(sentences, video_title="Test")

        assert len(results) <= 5

    def test_empty_input(self):
        segmenter = TopicSegmenter()
        assert segmenter.segment([], video_title="Test") == []

    def test_single_sentence(self):
        sentences = make_sentences(1)
        segmenter = TopicSegmenter()
        results = segmenter.segment(sentences, video_title="My Lecture")

        assert len(results) == 1
        assert results[0].title == "My Lecture"

    def test_two_sentences(self):
        sentences = make_sentences(2)
        segmenter = TopicSegmenter()
        results = segmenter.segment(sentences, video_title="Test")

        assert len(results) == 1

    def test_scaled_max_segments_returns_base_for_short_lecture(self):
        segmenter = TopicSegmenter(max_segments=12)
        # anything up to and including 3600s stays at max_segments
        assert segmenter._scaled_max_segments(1800) == 12
        assert segmenter._scaled_max_segments(3600) == 12

    def test_scaled_max_segments_increments_per_ten_minutes_above_one_hour(self):
        segmenter = TopicSegmenter(max_segments=12)
        # 3600 + 600 = 70 mins -> +1
        assert segmenter._scaled_max_segments(4200) == 13
        # 3600 + 1200 = 80 mins -> +2
        assert segmenter._scaled_max_segments(4800) == 14

    def test_scaled_max_segments_caps_at_twenty(self):
        segmenter = TopicSegmenter(max_segments=12)
        assert segmenter._scaled_max_segments(100_000) == 20

    def test_cap_segments_respects_max_segs_override(self):
        segments = [
            _RawSegment(start_time=float(i * 10), end_time=float((i + 1) * 10), sentences=[])
            for i in range(8)
        ]
        segmenter = TopicSegmenter(max_segments=12)
        result = segmenter.cap_segments(segments, max_segs=3)
        assert len(result) <= 3

    def test_cap_segments_without_override_uses_instance_max(self):
        segments = [
            _RawSegment(start_time=float(i * 10), end_time=float((i + 1) * 10), sentences=[])
            for i in range(8)
        ]
        segmenter = TopicSegmenter(max_segments=5)
        result = segmenter.cap_segments(segments)
        assert len(result) <= 5

    def test_long_lecture_gets_scaled_segment_cap(self):
        # 90-minute lecture -> _scaled_max_segments(5400) = 12 + int((5400-3600)/600) = 15
        # test the two pieces together without going through segment() to avoid NLTK
        segmenter = TopicSegmenter(max_segments=12)
        assert segmenter._scaled_max_segments(5400) == 15

        segments = [
            _RawSegment(start_time=float(i * 300), end_time=float((i + 1) * 300), sentences=[])
            for i in range(20)
        ]
        result = segmenter.cap_segments(segments, max_segs=segmenter._scaled_max_segments(5400))
        assert len(result) <= 15


class TestOcrHelpers:
    def test_normalize_ocr_strips_punct_and_lowercases(self):
        result = normalize_ocr("Hello, World! ∀x → P(x)")
        assert result == result.lower()
        assert "," not in result
        assert "!" not in result

    def test_normalize_ocr_empty(self):
        assert normalize_ocr("") == ""
        assert normalize_ocr(None) == ""

    def test_find_common_lines_detects_persistent_header(self):
        frames = [
            {"ocr_text": "Logical Equivalences\nNegation Rules"},
            {"ocr_text": "Logical Equivalences\nConjunction Rules"},
            {"ocr_text": "Logical Equivalences\nDisjunction Rules"},
        ]
        common = find_common_lines(frames)
        assert "logical equivalences" in common
        # section-specific lines should not be marked common
        assert "negation rules" not in common

    def test_find_common_lines_empty(self):
        assert find_common_lines([]) == set()

    def test_get_ocr_hint_returns_overlapping_lines(self):
        frames = [
            {"ocr_text": "Negation Rules\nRule 1", "start_time": 10.0, "end_time": 40.0},
            {"ocr_text": "Conjunction Rules\nRule 2", "start_time": 40.0, "end_time": 70.0},
        ]
        hint = get_ocr_hint(frames, 0.0, 45.0, set())
        assert "Negation Rules" in hint
        assert "Rule 1" in hint
        # frame starting at 40 overlaps with end=45 so it should be included too
        assert "Conjunction Rules" in hint

    def test_get_ocr_hint_strips_common_lines(self):
        frames = [
            {
                "ocr_text": "Logical Equivalences\nNegation Rules",
                "start_time": 0.0,
                "end_time": 30.0,
            },
        ]
        common = {"logical equivalences"}
        hint = get_ocr_hint(frames, 0.0, 30.0, common)
        assert "logical equivalences" not in hint.lower()
        assert "Negation Rules" in hint

    def test_get_ocr_hint_no_overlap_returns_empty(self):
        frames = [{"ocr_text": "Some text", "start_time": 100.0, "end_time": 130.0}]
        assert get_ocr_hint(frames, 0.0, 50.0, set()) == ""


class TestOcrChangeBoundaries:
    def make_sentences(self, count: int, duration_each: float = 10.0):
        return [
            ReconstructedSentence(
                text=f"Sentence {i}.",
                start_time=i * duration_each,
                end_time=(i + 1) * duration_each - 0.1,
                word_start_idx=0,
                word_end_idx=2,
            )
            for i in range(count)
        ]

    def s(self, i, start, end):
        return ReconstructedSentence(
            text=f"Sentence {i}.",
            start_time=start,
            end_time=end,
            word_start_idx=0,
            word_end_idx=2,
        )

    def test_detects_content_change(self):
        segmenter = TopicSegmenter(
            min_segment_duration_ratio=0.0, min_segment_duration_floor_secs=10
        )
        sentences = self.make_sentences(10)
        frames = [
            {"ocr_text": "alpha beta gamma delta", "start_time": 0.0, "end_time": 33.0},
            {"ocr_text": "zeta eta theta iota kappa", "start_time": 33.0, "end_time": 66.0},
            {"ocr_text": "zeta eta theta iota kappa", "start_time": 66.0, "end_time": 100.0},
        ]
        boundaries = segmenter.ocr_change_boundaries(frames, sentences)
        assert len(boundaries) == 1

    def test_no_change_when_identical_content(self):
        segmenter = TopicSegmenter()
        sentences = self.make_sentences(10)
        frames = [
            {"ocr_text": "same text same text", "start_time": 0.0, "end_time": 50.0},
            {"ocr_text": "same text same text", "start_time": 50.0, "end_time": 100.0},
        ]
        assert segmenter.ocr_change_boundaries(frames, sentences) == []

    def test_single_frame_returns_empty(self):
        segmenter = TopicSegmenter()
        sentences = self.make_sentences(5)
        frames = [{"ocr_text": "only one frame", "start_time": 0.0, "end_time": 50.0}]
        assert segmenter.ocr_change_boundaries(frames, sentences) == []

    def test_title_change_fires_boundary(self):
        # different section headings -> boundary even if body vocab overlaps heavily
        segmenter = TopicSegmenter(
            min_segment_duration_ratio=0.0, min_segment_duration_floor_secs=10
        )
        sentences = self.make_sentences(10)
        shared = "quantifier formula predicate logical"
        frames = [
            {
                "ocr_text": f"Negations and Quantifiers\n{shared}",
                "start_time": 0.0,
                "end_time": 33.0,
            },
            {
                "ocr_text": f"Conjunctions and Quantifiers\n{shared}",
                "start_time": 33.0,
                "end_time": 66.0,
            },
            {
                "ocr_text": f"Conjunctions and Quantifiers\n{shared}",
                "start_time": 66.0,
                "end_time": 100.0,
            },
        ]
        boundaries = segmenter.ocr_change_boundaries(frames, sentences)
        assert len(boundaries) == 1

    def test_part_numbers_do_not_create_boundary(self):
        # Part 1 -> Part 2 on same heading should NOT make a boundary
        segmenter = TopicSegmenter(
            min_segment_duration_ratio=0.0, min_segment_duration_floor_secs=10
        )
        sentences = self.make_sentences(20)
        # each new title is repeated so _next_title_persists can confirm real section changes
        frames = [
            {
                "ocr_text": "Lecture Header\nNegations and Quantifiers\n(Part 1)",
                "start_time": 0.0,
                "end_time": 25.0,
            },
            {
                "ocr_text": "Lecture Header\nNegations and Quantifiers\n(Part 2)",
                "start_time": 25.0,
                "end_time": 50.0,
            },
            {
                "ocr_text": "Lecture Header\nDistributing Quantifiers",
                "start_time": 50.0,
                "end_time": 100.0,
            },
            {
                "ocr_text": "Lecture Header\nDistributing Quantifiers",
                "start_time": 100.0,
                "end_time": 150.0,
            },
            {
                "ocr_text": "Lecture Header\nRenaming Variables",
                "start_time": 150.0,
                "end_time": 175.0,
            },
            {
                "ocr_text": "Lecture Header\nRenaming Variables",
                "start_time": 175.0,
                "end_time": 200.0,
            },
        ]
        common = find_common_lines(frames)
        boundaries = segmenter.ocr_change_boundaries(frames, sentences, common_lines=common)
        # Part 1 -> Part 2: same first non-common line -> same title -> no boundary
        assert len(boundaries) == 2

    def test_same_title_different_content_skips_jaccard(self):
        # same heading with totally different body text -> no boundary
        segmenter = TopicSegmenter(
            min_segment_duration_ratio=0.0, min_segment_duration_floor_secs=10
        )
        sentences = self.make_sentences(20)
        frames = [
            {"ocr_text": "Introduction\nsome intro text", "start_time": 0.0, "end_time": 20.0},
            {"ocr_text": "Other Section\nsome other text", "start_time": 20.0, "end_time": 40.0},
            {"ocr_text": "Other Section\nsome other text", "start_time": 40.0, "end_time": 50.0},
            {
                "ocr_text": "Variable Assignment\nalpha beta gamma delta epsilon",
                "start_time": 50.0,
                "end_time": 125.0,
            },
            {
                "ocr_text": "Variable Assignment\nzeta eta theta iota kappa",
                "start_time": 125.0,
                "end_time": 200.0,
            },
        ]
        common = find_common_lines(frames)
        boundaries = segmenter.ocr_change_boundaries(frames, sentences, common_lines=common)
        assert len(boundaries) == 2
        # persistent header is common; body content differs -> boundary fires
        segmenter = TopicSegmenter(
            min_segment_duration_ratio=0.0, min_segment_duration_floor_secs=10
        )
        sentences = self.make_sentences(10)
        frames = [
            {
                "ocr_text": "Logical Equivalences\nNegation Rules\nalpha beta",
                "start_time": 0.0,
                "end_time": 50.0,
            },
            {
                "ocr_text": "Logical Equivalences\nConjunction Rules\nzeta eta",
                "start_time": 50.0,
                "end_time": 100.0,
            },
            {
                "ocr_text": "Logical Equivalences\nConjunction Rules\nzeta eta",
                "start_time": 100.0,
                "end_time": 150.0,
            },
        ]
        common = {"logical equivalences"}
        boundaries = segmenter.ocr_change_boundaries(frames, sentences, common_lines=common)
        # first transition: different titles -> boundary; second: identical -> no boundary
        assert len(boundaries) == 1

    def test_weak_boundary_merged_by_hard_floor(self):
        # Jaccard boundary producing a tiny segment gets merged via hard_min_secs
        s = self.s
        raw = [
            _RawSegment(start_time=0.0, end_time=100.0, sentences=[s(0, 0, 100)]),
            _RawSegment(start_time=100.0, end_time=110.0, sentences=[s(1, 100, 110)]),
            _RawSegment(start_time=110.0, end_time=210.0, sentences=[s(2, 110, 210)]),
        ]
        ocr_protected = {100.0, 110.0}
        segmenter = TopicSegmenter(
            min_segment_duration_ratio=0.0, min_segment_duration_floor_secs=60, hard_min_secs=20.0
        )
        result = segmenter.merge_short_segments(raw, ocr_protected)
        # 10s middle segment < hard_min_secs -> merged despite protection
        assert len(result) == 2

    def test_segment_works_with_and_without_frames(self):
        sentences = make_sentences(20)
        segmenter = TopicSegmenter(
            min_segment_duration_ratio=0.0, min_segment_duration_floor_secs=30
        )
        results = segmenter.segment(sentences, video_title="Test", slide_frames=None)
        assert len(results) >= 1
        results_with_frames = segmenter.segment(
            sentences,
            video_title="Test",
            slide_frames=[{"ocr_text": "some ocr", "start_time": 0.0, "end_time": 200.0}],
        )
        assert len(results_with_frames) >= 1

    def test_ocr_boundary_survives_merge_even_when_short(self):
        # a 35s OCR-protected segment should survive (35s > 20s hard minimum)
        s = self.s
        # 3 segments: 100s, 35s (short but OCR-protected), 100s
        sentences = [
            s(0, 0, 20),
            s(1, 20, 40),
            s(2, 40, 60),
            s(3, 60, 80),
            s(4, 80, 100),
            s(5, 100, 115),
            s(6, 115, 130),
            s(7, 130, 135),
            s(8, 135, 155),
            s(9, 155, 175),
            s(10, 175, 195),
            s(11, 195, 215),
            s(12, 215, 235),
        ]

        ocr_protected = {100.0, 135.0}
        segmenter = TopicSegmenter(
            min_segment_duration_ratio=0.0, min_segment_duration_floor_secs=60, hard_min_secs=20.0
        )

        raw = [
            _RawSegment(start_time=0.0, end_time=100.0, sentences=sentences[:5]),
            _RawSegment(start_time=100.0, end_time=135.0, sentences=sentences[5:8]),
            _RawSegment(start_time=135.0, end_time=235.0, sentences=sentences[8:]),
        ]
        result = segmenter.merge_short_segments(raw, ocr_protected)
        assert len(result) == 3

    def test_protected_segment_under_hard_min_gets_merged(self):
        # 40s protected segment should be merged when hard_min_secs=45
        s = self.s
        raw = [
            _RawSegment(start_time=0.0, end_time=263.0, sentences=[s(0, 0, 263)]),
            _RawSegment(start_time=263.0, end_time=303.0, sentences=[s(1, 263, 303)]),
            _RawSegment(start_time=303.0, end_time=600.0, sentences=[s(2, 303, 600)]),
        ]
        ocr_protected = {263.0, 303.0}
        segmenter = TopicSegmenter(
            min_segment_duration_ratio=0.0, min_segment_duration_floor_secs=60
        )
        result = segmenter.merge_short_segments(raw, ocr_protected)
        # 40s < default hard_min_secs=45 -> force-merged despite OCR protection
        assert len(result) == 2

    def test_hard_min_forces_merge_of_tiny_protected_segment(self):
        # a 7s protected segment should get merged even though its boundaries are strong
        s = self.s
        sentences = [s(0, 0, 100), s(1, 100, 107), s(2, 107, 200)]
        ocr_protected = {100.0, 107.0}
        segmenter = TopicSegmenter(
            min_segment_duration_ratio=0.0, min_segment_duration_floor_secs=60, hard_min_secs=20.0
        )

        raw = [
            _RawSegment(start_time=0.0, end_time=100.0, sentences=[sentences[0]]),
            _RawSegment(start_time=100.0, end_time=107.0, sentences=[sentences[1]]),
            _RawSegment(start_time=107.0, end_time=200.0, sentences=[sentences[2]]),
        ]
        result = segmenter.merge_short_segments(raw, ocr_protected)
        assert len(result) == 2

    def test_unprotected_short_segment_still_merges(self):
        s = self.s
        raw = [
            _RawSegment(start_time=0.0, end_time=100.0, sentences=[s(0, 0, 100)]),
            _RawSegment(start_time=100.0, end_time=130.0, sentences=[s(1, 100, 130)]),
            _RawSegment(start_time=130.0, end_time=230.0, sentences=[s(2, 130, 230)]),
        ]
        segmenter = TopicSegmenter(
            min_segment_duration_ratio=0.0, min_segment_duration_floor_secs=60
        )
        result = segmenter.merge_short_segments(raw, ocr_protected=set())
        assert len(result) == 2


class TestProportionalDuration:
    def test_short_lecture_uses_floor(self):
        # none of the unprotected segments should be shorter than 30s
        sentences = make_sentences(20, duration_each=15.0)
        segmenter = TopicSegmenter(
            min_segment_duration_ratio=0.05,
            min_segment_duration_floor_secs=30.0,
            min_segment_duration_cap_secs=120.0,
        )
        results = segmenter.segment(sentences, video_title="Test")
        for seg in results[:-1]:
            assert seg.end_time - seg.start_time >= 30.0

    def test_long_lecture_segments_respect_cap(self):
        sentences = make_sentences(20, duration_each=180.0)
        segmenter = TopicSegmenter(
            min_segment_duration_ratio=0.05,
            min_segment_duration_floor_secs=30.0,
            min_segment_duration_cap_secs=120.0,
        )
        results = segmenter.segment(sentences, video_title="Test")
        for seg in results[:-1]:
            assert seg.end_time - seg.start_time >= 120.0

    def test_ratio_zero_falls_back_to_floor(self):
        # ratio = 0, floor always wins
        sentences = make_sentences(20, duration_each=50.0)
        segmenter = TopicSegmenter(
            min_segment_duration_ratio=0.0,
            min_segment_duration_floor_secs=40.0,
            min_segment_duration_cap_secs=120.0,
        )
        results = segmenter.segment(sentences, video_title="Test")
        for seg in results[:-1]:
            assert seg.end_time - seg.start_time >= 40.0


class TestOcrPrimaryPath:
    def frames(
        self, intervals: list[tuple[float, float]], text: str = "alpha beta gamma"
    ) -> list[dict]:
        return [{"ocr_text": text, "start_time": s, "end_time": e} for s, e in intervals]

    def test_coverage_sufficient_when_frames_cover_most_of_lecture(self):
        sentences = make_sentences(10, duration_each=10.0)  # 0-100s
        segmenter = TopicSegmenter(ocr_coverage_threshold=0.7)
        frames = self.frames([(0, 40), (40, 80)])
        assert segmenter.ocr_coverage_sufficient(frames, sentences) is True

    def test_coverage_insufficient_when_frames_are_sparse(self):
        sentences = make_sentences(10, duration_each=10.0)
        segmenter = TopicSegmenter(ocr_coverage_threshold=0.7)
        frames = self.frames([(0, 30)])
        assert segmenter.ocr_coverage_sufficient(frames, sentences) is False

    def test_ocr_path_used_when_coverage_sufficient(self):
        # two distinct slide contents -> one OCR boundary detected
        sentences = make_sentences(20, duration_each=5.0)  # 0-100s
        frames = [
            {"ocr_text": "alpha beta gamma delta", "start_time": 0.0, "end_time": 33.0},
            {"ocr_text": "zeta eta theta iota kappa", "start_time": 33.0, "end_time": 66.0},
            {"ocr_text": "zeta eta theta iota kappa", "start_time": 66.0, "end_time": 100.0},
        ]
        segmenter = TopicSegmenter(
            ocr_coverage_threshold=0.7,
            min_segment_duration_ratio=0.0,
            min_segment_duration_floor_secs=1.0,
        )
        boundaries, protected = segmenter.find_boundaries(sentences, frames)
        assert len(boundaries) == 1
        assert len(protected) == 1

    def test_texttiling_fallback_when_no_frames(self):
        sentences = make_sentences(30, duration_each=10.0)
        segmenter = TopicSegmenter(ocr_coverage_threshold=0.7)
        # no frames -> must go through TextTiling without error
        boundaries, protected = segmenter.find_boundaries(sentences, slide_frames=None)
        assert protected == set()
