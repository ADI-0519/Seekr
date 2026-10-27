import pytest
from app.services.sentence_reconstruction import (
    SentenceReconstructionError,
    SentenceReconstructor,
)


def w(token: str, start: float, end: float) -> dict:
    return {"word": token, "start": start, "end": end, "probability": 0.99}


def test_every_word_is_assigned_exactly_once():
    words = [
        w("Hello", 0.0, 0.2),
        w(" world.", 0.21, 0.5),
        w(" Next", 0.8, 1.0),
        w(" sentence", 1.01, 1.2),
    ]

    reconstructor = SentenceReconstructor()
    sentences = reconstructor.reconstruct_sentences(words)

    covered: list[int] = []
    for s in sentences:
        covered.extend(range(s.word_start_idx, s.word_end_idx + 1))

    assert sorted(covered) == list(range(len(words)))
    assert len(covered) == len(set(covered))


def test_sentence_ranges_cover_full_transcript_without_overlap():
    words = [
        w("One", 0.0, 0.2),
        w(" two", 0.21, 0.4),
        w(" three.", 0.41, 0.7),
        w(" Four", 0.71, 0.9),
        w(" five.", 0.91, 1.1),
    ]

    reconstructor = SentenceReconstructor()
    sentences = reconstructor.reconstruct_sentences(words)

    assert sentences[0].start_time == pytest.approx(words[0]["start"])
    assert sentences[-1].end_time == pytest.approx(words[-1]["end"])

    for i in range(len(sentences) - 1):
        assert sentences[i].end_time <= sentences[i + 1].start_time


def test_pause_creates_sentence_break_even_without_period():
    words = [
        w("This", 0.0, 0.2),
        w(" is", 0.21, 0.4),
        w(" a", 0.41, 0.5),
        w(" pause", 0.51, 0.8),
        w(" New", 1.8, 2.0),
        w(" thought", 2.01, 2.2),
        w(" starts", 2.21, 2.4),
        w(" here", 2.41, 2.6),
    ]

    reconstructor = SentenceReconstructor(pause_threshold_secs=0.7)
    sentences = reconstructor.reconstruct_sentences(words)

    assert len(sentences) == 2
    assert sentences[0].text.endswith(".")
    assert sentences[1].text.endswith(".")


def test_abbreviation_does_not_force_sentence_split():
    words = [
        w("Dr.", 0.0, 0.2),
        w(" Smith", 0.21, 0.4),
        w(" explains", 0.41, 0.7),
        w(" this.", 0.71, 1.0),
    ]

    reconstructor = SentenceReconstructor()
    sentences = reconstructor.reconstruct_sentences(words)

    assert len(sentences) == 1


def test_empty_input_returns_empty_list():
    reconstructor = SentenceReconstructor()
    assert reconstructor.reconstruct_sentences([]) == []


def test_invalid_word_timestamps_raise_error():
    words = [w("bad", 1.0, 0.5)]
    reconstructor = SentenceReconstructor()

    with pytest.raises(SentenceReconstructionError):
        reconstructor.reconstruct_sentences(words)


def test_segment_hint_forces_boundary_without_pause_or_punctuation():
    # No punctuation and no large pause: split should come from segment hint only.
    words = [
        w("alpha", 0.0, 0.2),
        w(" beta", 0.21, 0.4),
        w(" gamma", 0.41, 0.6),
        w(" delta", 0.61, 0.8),
        w(" epsilon", 0.81, 1.0),
        w(" zeta", 1.01, 1.2),
        w(" eta", 1.21, 1.4),
        w(" theta", 1.41, 1.6),
    ]
    segment_ranges = [(0.0, 0.8), (0.8, 1.6)]

    reconstructor = SentenceReconstructor(
        pause_threshold_secs=10.0,  # Ensure pause logic does not trigger.
        segment_hint_tolerance_secs=0.05,
    )
    sentences = reconstructor.reconstruct_sentences(words, segment_ranges=segment_ranges)

    assert len(sentences) == 2
    assert sentences[0].word_start_idx == 0
    assert sentences[0].word_end_idx == 3
    assert sentences[1].word_start_idx == 4
    assert sentences[1].word_end_idx == 7


def test_punctuation_fragment_does_not_split_without_pause():
    words = [
        w("we.", 0.0, 0.1),
        w(" need.", 0.11, 0.2),
        w(" to.", 0.21, 0.3),
        w(" improve.", 0.31, 0.5),
    ]
    reconstructor = SentenceReconstructor(
        pause_threshold_secs=0.7,
        segment_hint_tolerance_secs=0.05,
    )
    sentences = reconstructor.reconstruct_sentences(words, segment_ranges=None)

    assert len(sentences) == 1
    assert sentences[0].text.endswith(".")


def test_short_fragment_merges_with_neighbour():
    words = [
        w(" Reflexivity", 0.0, 0.5),
        w(" and", 0.51, 0.7),
        w(" symmetry", 0.71, 1.0),
        w(" follow", 1.01, 1.3),
        w(" immediately.", 1.31, 1.6),
        w(" Transitivity.", 2.5, 2.8),  # 0.9s pause before - triggers break
        w(" requires", 2.81, 3.1),
        w(" extra", 3.11, 3.4),
        w(" work.", 3.41, 3.7),
    ]
    reconstructor = SentenceReconstructor(pause_threshold_secs=0.7, min_words_per_sentence=4)
    sentences = reconstructor.reconstruct_sentences(words)

    # "Transitivity." should merge into the next sentence, not stand alone
    for s in sentences:
        word_count = s.word_end_idx - s.word_start_idx + 1
        assert word_count >= 4, f"fragment sentence found: '{s.text}'"


def test_merge_picks_nearest_neighbour():
    # fragment at start should merge forward (no previous neighbour)
    words = [
        w(" Fine.", 0.0, 0.3),
        w(" This", 1.1, 1.3),
        w(" is", 1.31, 1.5),
        w(" sentence", 1.51, 1.7),
        w(" two.", 1.71, 2.0),
    ]
    reconstructor = SentenceReconstructor(pause_threshold_secs=0.7, min_words_per_sentence=4)
    sentences = reconstructor.reconstruct_sentences(words)

    assert len(sentences) == 1
    assert sentences[0].word_start_idx == 0
    assert sentences[0].word_end_idx == 4


def test_min_words_zero_disables_merging():
    # setting min_words=0 should leave fragments untouched
    words = [
        w(" Hi.", 0.0, 0.1),
        w(" there", 1.0, 1.2),
        w(" friend.", 1.21, 1.5),
    ]
    reconstructor = SentenceReconstructor(pause_threshold_secs=0.7, min_words_per_sentence=0)
    sentences = reconstructor.reconstruct_sentences(words)

    assert len(sentences) == 2
